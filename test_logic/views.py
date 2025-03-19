from collections import defaultdict
from rest_framework import viewsets, status
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from .models import Product, Test, Question, Option, CompletedTest, CompletedQuestion
from .serializers import (
    ProductSerializer, TestSerializer, QuestionSerializer,
    CurrentTestSerializer, CompletedTestSerializer, OptionSerializer,
    CCompletedTestSerializer
)
from rest_framework.decorators import api_view
from django.db.models import Sum
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi
from datetime import timezone
from django.utils.timezone import now
from django.utils import timezone
import logging
import uuid
from rest_framework.permissions import IsAuthenticated
from rest_framework.decorators import permission_classes
from decimal import Decimal
from random import shuffle
from django.db.models import Q
from django.core.cache import cache
from django.views.decorators.cache import cache_page
from django.utils.decorators import method_decorator
from django.db import transaction
from accounts.models import User

logger = logging.getLogger(__name__)

class ProductViewSet(viewsets.ModelViewSet):
    queryset = Product.objects.all()
    serializer_class = ProductSerializer
    
    @method_decorator(cache_page(60 * 15))  # Cache for 15 minutes
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)
    
    @method_decorator(cache_page(60 * 15))
    def retrieve(self, request, *args, **kwargs):
        return super().retrieve(request, *args, **kwargs)


class TestViewSet(viewsets.ModelViewSet):
    queryset = Test.objects.all()
    serializer_class = TestSerializer

    @method_decorator(cache_page(60 * 10), name='dispatch')
    @action(detail=True, methods=['get'])
    def questions(self, request, pk=None):
        # Cache key for this specific test's questions
        cache_key = f'test_questions:{pk}'
        data = cache.get(cache_key)
        
        if not data:
            test = self.get_object()
            questions = Question.objects.filter(test=test)
            data = QuestionSerializer(questions, many=True).data
            cache.set(cache_key, data, 60 * 10)  # Cache for 10 minutes
        
        return Response(data)


class QuestionViewSet(viewsets.ModelViewSet):
    queryset = Question.objects.all()
    serializer_class = QuestionSerializer

    @action(detail=True, methods=['get'], url_path='options')
    def get_options(self, request, pk=None):
        question = self.get_object()
        options = Option.objects.filter(question=question)
        # Convert queryset to list and randomize the order
        options_list = list(options)
        shuffle(options_list)
        return Response(OptionSerializer(options_list, many=True).data)


class OptionViewSet(viewsets.ModelViewSet):
    queryset = Option.objects.all()
    serializer_class = OptionSerializer
    # permission_classes = [IsAuthenticated]


@swagger_auto_schema(
    method='post',
    operation_description="Retrieve tests and their questions based on product and test IDs",
    request_body=openapi.Schema(
        type=openapi.TYPE_OBJECT,
        required=['product_id', 'tests_ids'],
        properties={
            'product_id': openapi.Schema(type=openapi.TYPE_STRING, description='UUID of the product'),
            'tests_ids': openapi.Schema(type=openapi.TYPE_ARRAY, items=openapi.Items(type=openapi.TYPE_STRING), description='List of test UUIDs')
        }
    ),
    responses={
        200: openapi.Response(
            description="Test data with questions and options",
            examples={
                "application/json": {
                    "time": 90,
                    "tests": [
                        {
                            "id": "some-test-uuid-1",
                            "title": "Test 1",
                            "questions": [
                                {
                                    "id": "some-question-uuid-1",
                                    "text": "What is the capital of France?",
                                    "options": [
                                        {
                                            "id": "some-option-uuid-1",
                                            "text": "Paris"
                                        },
                                        {
                                            "id": "some-option-uuid-2",
                                            "text": "London"
                                        }
                                    ]
                                }
                            ]
                        }
                    ]
                }
            }
        ),
        404: openapi.Response(description="Product not found"),
    }
)
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def product_tests_view(request):
    user = request.user
    product_id = request.data.get('product_id')
    tests_ids = request.data.get('tests_ids')

    # Validate request data
    if not product_id or not isinstance(tests_ids, list):
        return Response({"detail": "Invalid input data"}, status=status.HTTP_400_BAD_REQUEST)

    # Get the product
    try:
        product = Product.objects.get(id=product_id)
    except Product.DoesNotExist:
        return Response({"detail": "Product not found."}, status=status.HTTP_404_NOT_FOUND)

    # Check if the user has enough balance to purchase the product
    if user.balance < product.sum:
        return Response({"detail": "Insufficient balance."}, status=status.HTTP_400_BAD_REQUEST)

    # Deduct the product sum from the user's balance
    user.balance -= product.sum
    user.save()

    # Get the tests based on the provided IDs
    tests = Test.objects.filter(product=product, id__in=tests_ids)

    # Get total time for all tests
    total_time = tests.aggregate(total_time=Sum('time'))['total_time'] or 0

    # Serialize the tests
    serialized_tests = CurrentTestSerializer(tests, many=True).data

    # Set the product, test start flag, and times for the user
    user.product = product  # Set the product for the user
    user.test_is_started = True  # Set test_is_started to True
    user.total_time = total_time  # Set the total time to the sum of test and product time
    user.test_start_time = now()  # Store the start time
    user.save()

    # Return the response
    return Response({
        "time": user.total_time,
        "test_is_started": user.test_is_started,
        "tests": serialized_tests
    }, status=status.HTTP_200_OK)

test_schema = openapi.Schema(
    type=openapi.TYPE_OBJECT,
    properties={
        "id": openapi.Schema(type=openapi.TYPE_STRING, format='uuid', description="Test ID"),
        "title": openapi.Schema(type=openapi.TYPE_STRING, description="Test Title"),
        "is_required": openapi.Schema(type=openapi.TYPE_BOOLEAN, description="Is Test Required"),
    }
)

grouped_response_schema = openapi.Schema(
    type=openapi.TYPE_ARRAY,
    items=openapi.Schema(
        type=openapi.TYPE_OBJECT,
        properties={
            "grade": openapi.Schema(type=openapi.TYPE_STRING, description="Grade"),
            "tests": openapi.Schema(type=openapi.TYPE_ARRAY, items=test_schema),
        },
    ),
)

@swagger_auto_schema(
    method='get',
    operation_description="Retrieve required tests for a given product ID, grouped by grade.",
    responses={
        200: openapi.Response(description="Grouped Tests by Grade", schema=grouped_response_schema),
        404: openapi.Response(description="Product not found"),
    }
)
@api_view(['GET'])
def required_tests_by_product(request, product_id):
    # Get the product
    try:
        product = Product.objects.get(id=product_id)
    except Product.DoesNotExist:
        return Response({"detail": "Product not found."}, status=status.HTTP_404_NOT_FOUND)

    # Filter tests by product and only include grades 0, 4, or 9
    required_tests = Test.objects.filter(
        product=product,
        grade__in=[0, 4, 9]  # Only include tests with these specific grades
    )

    # Serialize the tests
    serialized_tests = TestSerializer(required_tests, many=True).data

    # Group tests by grade
    tests_by_grade = defaultdict(list)
    for test in serialized_tests:
        grade = str(test.get('grade', 0))  # Convert None to '0'
        test.pop('grade', None)  # Remove 'grade' from individual test objects
        tests_by_grade[grade].append(test)

    # Transform the grouped data into the desired structure
    grouped_response = [
        {"grade": grade, "tests": tests} for grade, tests in tests_by_grade.items()
    ]

    # Return the response
    return Response(grouped_response, status=status.HTTP_200_OK)





@swagger_auto_schema(
    method='post',
    operation_description="Submit completed test data and store selected options for each question.",
    request_body=openapi.Schema(
        type=openapi.TYPE_OBJECT,
        required=['product_id', 'tests'],
        properties={
            'product_id': openapi.Schema(type=openapi.TYPE_STRING, description='UUID of the product'),
            'tests': openapi.Schema(
                type=openapi.TYPE_ARRAY,
                items=openapi.Items(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'id': openapi.Schema(type=openapi.TYPE_STRING, description='UUID of the test'),
                        'questions': openapi.Schema(
                            type=openapi.TYPE_ARRAY,
                            items=openapi.Items(
                                type=openapi.TYPE_OBJECT,
                                properties={
                                    'id': openapi.Schema(type=openapi.TYPE_STRING, description='UUID of the question'),
                                    'option_id': openapi.Schema(type=openapi.TYPE_STRING, description='UUID of the selected option')
                                }
                            )
                        )
                    }
                ),
                description='List of tests and their corresponding questions and selected options'
            )
        }
    ),
    responses={
        201: openapi.Response(
            description="Test completed successfully",
            examples={
                "application/json": {
                    "completed_test_id": "some-completed-test-uuid"
                }
            }
        ),
        400: openapi.Response(description="Invalid input data"),
        404: openapi.Response(description="Product or Test/Question/Option not found")
    }
)
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def complete_test_view(request):
    user = request.user
    product_id = request.data.get('product_id')
    tests_data = request.data.get('tests')
    
    # Validation logic...
    
    # Database operations inside a transaction for atomicity and performance
    with transaction.atomic():
        # Get the product (using select_related if needed)
        try:
            product = Product.objects.get(id=product_id)
        except Product.DoesNotExist:
            return Response({"detail": "Product not found."}, status=status.HTTP_404_NOT_FOUND)

        # Calculate time spent
        test_finish_test_time = now()
        test_start_time = user.test_start_time
        
        if test_start_time is None:
            logger.warning(f"test_start_time is None for user {user.username}, using current time")
            time_spent = 0
        else:
            time_spent = (test_finish_test_time - test_start_time).total_seconds()

        # Create the CompletedTest instance
        completed_test = CompletedTest.objects.create(
            user=user,
            product=product,
            completed_date=test_finish_test_time,
            start_test_time=test_start_time or test_finish_test_time,
            time_spent=time_spent
        )

        # Collect all test IDs for bulk prefetching
        test_ids = [test_data.get('id') for test_data in tests_data]
        tests_dict = {str(test.id): test for test in Test.objects.filter(id__in=test_ids, product=product)}
        
        # Add tests to completed_test with bulk operation
        completed_test.tests.add(*list(tests_dict.values()))
        
        # Prepare bulk creation lists
        completed_questions = []
        option_mappings = []  # For M2M relationships
        
        # Process each test and question
        for test_data in tests_data:
            test_id = test_data.get('id')
            questions_data = test_data.get('questions', [])
            
            if test_id not in tests_dict:
                continue  # Skip invalid test ID
                
            test = tests_dict[test_id]
            
            # Collect question IDs for prefetching
            question_ids = [q.get('id') for q in questions_data if q.get('id')]
            questions_dict = {str(q.id): q for q in Question.objects.filter(id__in=question_ids, test=test)}
            
            # Collect option IDs for prefetching
            all_option_ids = []
            for q_data in questions_data:
                opt_ids = q_data.get('option_id')
                if isinstance(opt_ids, list):
                    all_option_ids.extend(opt_ids)
                elif opt_ids:
                    all_option_ids.append(opt_ids)
                    
            options_dict = {str(o.id): o for o in Option.objects.filter(id__in=all_option_ids)}
            
            # Create CompletedQuestion objects
            for q_data in questions_data:
                q_id = q_data.get('id')
                if q_id not in questions_dict:
                    continue  # Skip invalid question ID
                    
                question = questions_dict[q_id]
                completed_q = CompletedQuestion(
                    completed_test=completed_test,
                    test=test,
                    question=question
                )
                completed_questions.append(completed_q)
                
                # Track option mappings for bulk creation later
                opt_ids = q_data.get('option_id')
                if not opt_ids:
                    continue
                    
                if not isinstance(opt_ids, list):
                    opt_ids = [opt_ids]
                    
                for opt_id in opt_ids:
                    if opt_id in options_dict:
                        option_mappings.append((completed_q, options_dict[opt_id]))
        
        # Bulk create all CompletedQuestion objects
        if completed_questions:
            CompletedQuestion.objects.bulk_create(completed_questions)
            
            # Now add the M2M relationships for selected options
            for completed_q, option in option_mappings:
                completed_q.selected_option.add(option)
        
        # Reset user test state
        User.objects.filter(id=user.id).update(
            test_is_started=False,
            test_start_time=None,
            finish_test_time=None
        )

    # Clear user-specific caches
    cache.delete_pattern(f'test_questions:*:user:{user.id}')
    
    return Response({
        "completed_test_id": str(completed_test.id),
        "time_spent_minutes": time_spent / 60
    }, status=status.HTTP_201_CREATED)


@swagger_auto_schema(
    method='get',
    operation_description="Retrieve a specific completed test by ID along with related completed questions and selected options.",
    responses={
        200: openapi.Response(
            description="Details of the CompletedTest",
            examples={
                "application/json": {
                    "id": "some-completed-test-uuid",
                    "user": {
                        "id": 1,
                        "username": "student1"
                    },
                    "product": {
                        "id": "some-product-uuid",
                        "title": "Product 1"
                    },
                    "completed_at": "2024-01-01T15:30:00",
                    "completed_questions": [
                        {
                            "id": "some-completed-question-uuid",
                            "question": {
                                "id": "some-question-uuid",
                                "text": "What is the capital of France?",
                                "options": [
                                    {
                                        "id": "some-option-uuid-1",
                                        "text": "Paris",
                                        "is_correct": 'false'
                                    },
                                    {
                                        "id": "some-option-uuid-2",
                                        "text": "London",
                                        "is_correct": 'false'
                                    }
                                ]
                            },
                            "selected_option": {
                                "id": "some-option-uuid-1",
                                "text": "Paris",
                                "is_correct": 'true'
                            }
                        }
                    ]
                }
            }
        ),
        404: openapi.Response(description="CompletedTest not found.")
    }
)
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_completed_test_by_id(request, completed_test_id):
    try:
        completed_test = CompletedTest.objects.get(id=completed_test_id, user=request.user)
    except CompletedTest.DoesNotExist:
        return Response({"detail": "CompletedTest not found."}, status=status.HTTP_404_NOT_FOUND)

    # Pass the completed test to the serializer context
    serializer = CCompletedTestSerializer(completed_test, context={'completed_test': completed_test})
    return Response(serializer.data, status=status.HTTP_200_OK)



@swagger_auto_schema(
    method='get',
    operation_description="Retrieve all completed tests for the authenticated user.",
    responses={
        200: openapi.Response(
            description="List of all CompletedTests",
            examples={
                "application/json": [
                    {
                        "id": "some-completed-test-uuid-1",
                        "user": {
                            "id": 1,
                            "username": "student1"
                        },
                        "product": {
                            "id": "some-product-uuid",
                            "title": "Product 1"
                        },
                        "completed_at": "2024-01-01T15:30:00",
                        "completed_questions": [
                            {
                                "id": "some-completed-question-uuid-1",
                                "question": {
                                    "id": "some-question-uuid",
                                    "text": "What is the capital of France?",
                                    "options": [
                                        {
                                            "id": "some-option-uuid-1",
                                            "text": "Paris",
                                            "is_correct": 'true'
                                        },
                                        {
                                            "id": "some-option-uuid-2",
                                            "text": "London",
                                            "is_correct": 'false'
                                        }
                                    ]
                                },
                                "selected_option": {
                                    "id": "some-option-uuid-1",
                                    "text": "Paris",
                                    "is_correct": 'true'
                                }
                            }
                        ]
                    }
                ]
            }
        )
    }
)
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_all_completed_tests(request):
    # Use caching for user's completed tests
    cache_key = f'user_completed_tests:{request.user.id}'
    cached_data = cache.get(cache_key)
    
    if cached_data:
        return Response(cached_data, status=status.HTTP_200_OK)
    
    # Use select_related to reduce database queries
    completed_tests = CompletedTest.objects.filter(user=request.user)\
        .select_related('product')\
        .prefetch_related('tests')
    
    # Serialize all CompletedTests
    serializer = CompletedTestSerializer(completed_tests, many=True)
    data = serializer.data
    
    # Cache the result for 5 minutes
    cache.set(cache_key, data, 60 * 5)
    
    return Response(data, status=status.HTTP_200_OK)

@api_view(['GET'])
def empty_options_view(request):
    """View to display questions that have options with empty text."""
    # Get product ID from query params, default to the specific product ID
    product_id = request.GET.get('product_id', '4ce7261c-29e8-4514-94c0-68344010c2d9')
    
    # Get tests associated with the product
    tests = Test.objects.filter(product_id=product_id)
    
    if not tests.exists():
        return Response({"error": f"No tests found for Product ID: {product_id}"}, 
                       status=status.HTTP_404_NOT_FOUND)
    
    # Find questions that have options with empty text
    questions_with_empty_options = Question.objects.filter(
        test__in=tests,
        options__text__in=['', ' ']
    ).distinct()
    
    # Also find questions with null text options
    questions_with_null_options = Question.objects.filter(
        test__in=tests,
        options__text__isnull=True
    ).distinct()
    
    # Combine the querysets
    questions = (questions_with_empty_options | questions_with_null_options).distinct()
    
    # Prepare data for the template
    questions_data = []
    for question in questions:
        empty_options = Option.objects.filter(
            question=question
        ).filter(
            Q(text__in=['', ' ']) | Q(text__isnull=True)
        )
        
        questions_data.append({
            'question': question,
            'empty_options': empty_options,
            'test': question.test
        })
    
    # Always render HTML for this view
    from django.shortcuts import render
    from django.contrib import messages
    
    # Add a message if there are no empty options
    if not questions_data:
        messages.info(request, f"No questions with empty options found for Product ID: {product_id}")
    
    return render(request, 'test_logic/empty_options.html', {
        'questions_data': questions_data,
        'product_id': product_id,
        'tests_count': tests.count(),
        'questions_count': len(questions_data)
    })

@api_view(['POST'])
def delete_empty_options_view(request):
    """View to delete options with empty text and optionally delete their questions."""
    product_id = request.POST.get('product_id')
    question_id = request.POST.get('question_id')  # This will be None if deleting all empty options
    delete_questions = request.POST.get('delete_questions') == 'true'  # Check if we should delete questions too
    
    if not product_id:
        return Response({"error": "Product ID is required"}, status=status.HTTP_400_BAD_REQUEST)
    
    # Get tests associated with the product
    tests = Test.objects.filter(product_id=product_id)
    
    if not tests.exists():
        return Response({"error": f"No tests found for Product ID: {product_id}"}, 
                       status=status.HTTP_404_NOT_FOUND)
    
    # If question_id is provided, only process that specific question
    if question_id:
        try:
            question = Question.objects.get(id=question_id, test__in=tests)
            empty_options = Option.objects.filter(
                question=question
            ).filter(
                Q(text__in=['', ' ']) | Q(text__isnull=True)
            )
            
            count = empty_options.count()
            
            if delete_questions:
                # Delete the question (which will cascade delete its options)
                question.delete()
                message = f"Successfully deleted question {question_id} with {count} empty options"
            else:
                # Just delete the empty options
                empty_options.delete()
                message = f"Successfully deleted {count} empty options for question {question_id}"
            
            # Redirect back to the empty options page with a success message
            from django.shortcuts import redirect
            from django.contrib import messages
            
            messages.success(request, message)
            return redirect(f"/api/test-logic/empty-options/?product_id={product_id}")
            
        except Question.DoesNotExist:
            return Response({"error": f"Question with ID {question_id} not found"}, 
                           status=status.HTTP_404_NOT_FOUND)
    
    # Otherwise, process all questions with empty options for the product
    if delete_questions:
        # First, get a list of question IDs with empty options
        questions_with_empty_options = Question.objects.filter(
            test__in=tests,
            options__text__in=['', ' ']
        ).distinct().values_list('id', flat=True)
        
        questions_with_null_options = Question.objects.filter(
            test__in=tests,
            options__text__isnull=True
        ).distinct().values_list('id', flat=True)
        
        # Combine the IDs
        question_ids = list(questions_with_empty_options) + list(questions_with_null_options)
        
        # Get a count before deletion
        questions_count = len(set(question_ids))
        
        # Delete questions without using distinct()
        if question_ids:
            Question.objects.filter(id__in=question_ids).delete()
            
        message = f"Successfully deleted {questions_count} questions with empty options"
    else:
        # Find all empty options without using distinct()
        empty_options = Option.objects.filter(
            question__test__in=tests
        ).filter(
            Q(text__in=['', ' ']) | Q(text__isnull=True)
        )
        
        options_count = empty_options.count()
        empty_options.delete()
        
        message = f"Successfully deleted {options_count} empty options for product {product_id}"
    
    # Redirect back to the empty options page with a success message
    from django.shortcuts import redirect
    from django.contrib import messages
    
    messages.success(request, message)
    return redirect(f"/api/test-logic/empty-options/?product_id={product_id}")