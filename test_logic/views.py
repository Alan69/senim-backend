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

logger = logging.getLogger(__name__)

class ProductViewSet(viewsets.ModelViewSet):
    queryset = Product.objects.all()
    serializer_class = ProductSerializer


class TestViewSet(viewsets.ModelViewSet):
    queryset = Test.objects.all()
    serializer_class = TestSerializer

    @action(detail=True, methods=['get'])
    def questions(self, request, pk=None):
        test = self.get_object()
        questions = Question.objects.filter(test=test)
        data = QuestionSerializer(questions, many=True).data
        
        # for question in data:
        #     question['options'] = OptionSerializer(question['options'], many=True).data
        
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
    
    logger.debug(f"User attempting to complete test: {user.username}, is_authenticated: {user.is_authenticated}")
    logger.debug(f"Request headers: {request.headers}")
    
    product_id = request.data.get('product_id')
    tests_data = request.data.get('tests')
    
    logger.debug(f"Received data - product_id: {product_id}, tests_data length: {len(tests_data) if tests_data else 0}")

    # Validate request data
    if not product_id or not isinstance(tests_data, list):
        logger.error(f"Invalid input data: product_id={product_id}, tests_data type={type(tests_data)}")
        return Response({"detail": "Invalid input data"}, status=status.HTTP_400_BAD_REQUEST)

    # Get the product
    try:
        product = Product.objects.get(id=product_id)
    except Product.DoesNotExist:
        return Response({"detail": "Product not found."}, status=status.HTTP_404_NOT_FOUND)

    # Calculate time spent
    test_finish_test_time = now()
    test_start_time = user.test_start_time
    
    # Handle case where test_start_time is None
    if test_start_time is None:
        logger.warning(f"test_start_time is None for user {user.username}, using current time")
        time_spent = 0  # Default to 0 if we can't calculate actual time
    else:
        time_spent = (test_finish_test_time - test_start_time).total_seconds()

    # Create the CompletedTest instance
    completed_test = CompletedTest.objects.create(
        user=user,
        product=product,
        completed_date=test_finish_test_time,
        start_test_time=test_start_time or test_finish_test_time,  # Use finish time as start time if start time is None
        time_spent=time_spent
    )

    # Process each test and its questions
    for test_data in tests_data:
        test_id = test_data.get('id')
        questions_data = test_data.get('questions')

        # Validate test existence
        try:
            test = Test.objects.get(id=test_id, product=product)
        except Test.DoesNotExist:
            return Response({"detail": f"Test with id {test_id} not found."}, status=status.HTTP_404_NOT_FOUND)

        # Link the test to CompletedTest
        completed_test.tests.add(test)

        # Process each question
        for question_data in questions_data:
            question_id = question_data.get('id')
            selected_option_ids = question_data.get('option_id')
            
            # Convert single option_id to list if necessary
            if selected_option_ids is None:
                selected_option_ids = []
            elif isinstance(selected_option_ids, (str, uuid.UUID)):
                selected_option_ids = [selected_option_ids]
            elif isinstance(selected_option_ids, list):
                selected_option_ids = selected_option_ids
            else:
                selected_option_ids = []

            try:
                question = Question.objects.get(id=question_id, test=test)
            except Question.DoesNotExist:
                return Response({"detail": f"Question with id {question_id} not found in test {test_id}."}, status=status.HTTP_404_NOT_FOUND)

            # Create the CompletedQuestion instance
            completed_question = CompletedQuestion.objects.create(
                completed_test=completed_test,
                test=test,
                question=question
            )

            # Add selected options (if any)
            for option_id in selected_option_ids:
                try:
                    option = Option.objects.get(id=option_id, question=question)
                    completed_question.selected_option.add(option)
                except Option.DoesNotExist:
                    return Response({"detail": f"Option with id {option_id} not found for question {question_id}."}, status=status.HTTP_404_NOT_FOUND)

    # Reset user test state after completion
    user.test_is_started = False
    user.test_start_time = None
    user.finish_test_time = None
    user.save()
    
    print(f"user: {user.email} completed test {product.title}, user.test_is_started: {user.test_is_started}, user.test_start_time: {user.test_start_time}, user.finish_test_time: {user.finish_test_time}" )

    return Response({
        "completed_test_id": str(completed_test.id),
        "time_spent_minutes": time_spent / 60  # Convert seconds to minutes
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
    completed_tests = CompletedTest.objects.filter(user=request.user)

    # Serialize all CompletedTests
    serializer = CompletedTestSerializer(completed_tests, many=True)
    return Response(serializer.data, status=status.HTTP_200_OK)