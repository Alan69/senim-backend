from random import sample, shuffle
from rest_framework import serializers
from .models import Product, Test, Question, Option, Result, BookSuggestion, CompletedTest, CompletedQuestion
from accounts.models import User
from accounts.serializers import UserSerializer
from django.db.models import Q
from django.db.models import Count

# new
class CurrentOptionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Option
        fields = ['id', 'text', 'img']

class CurrentQuestionSerializer(serializers.ModelSerializer):
    options = serializers.SerializerMethodField()
    source_text = serializers.CharField(source='source_text.text', read_only=True)

    class Meta:
        model = Question
        fields = ['id', 'text', 'text2', 'text3', 'img', 'task_type', 'options', 'source_text']
    
    def get_options(self, obj):
        # Get all options for this question
        options = obj.options.all()
        # Convert queryset to list and randomize the order
        options_list = list(options)
        shuffle(options_list)
        # Serialize the randomized options
        return CurrentOptionSerializer(options_list, many=True).data

class CurrentTestSerializer(serializers.ModelSerializer):
    questions = serializers.SerializerMethodField()

    class Meta:
        model = Test
        fields = ['id', 'title', 'questions']

    def get_questions(self, obj):
        # Fetch all questions related to the test as a queryset
        all_questions = Question.objects.filter(test=obj)
        
        # Check if the user is an admin
        request = self.context.get('request')
        if request and request.user.is_authenticated and request.user.is_staff:
            # For admin users, return all questions without filtering
            return CurrentQuestionSerializer(all_questions, many=True).data

        # If the number of questions is not 40, return a random selection
        if obj.number_of_questions != 40:
            selected_questions = sample(list(all_questions), min(obj.number_of_questions, all_questions.count()))
            return CurrentQuestionSerializer(selected_questions, many=True).data

        # Initialize lists for selected questions
        selected_questions = []

        # Step 1: Select 25 questions (1–25) with any task_type except 10, 8, and 6
        questions_1_to_25 = list(all_questions.exclude(task_type__in=[10, 8, 6])[:25])
        selected_questions.extend(questions_1_to_25)

        # Step 2: Select 5 questions (26–30) with task_type=10
        questions_task_type_10 = list(all_questions.filter(task_type=10))
        
        # Group questions by source_id
        source_groups = {}
        for q in questions_task_type_10:
            if q.source_text:
                id = q.source_text
                if id not in source_groups:
                    source_groups[id] = []
                source_groups[id].append(q)

        # Select a group of 5 questions with the same source_id if available
        selected_source_questions = []
        for source_questions in source_groups.values():
            if len(source_questions) >= 5:
                selected_source_questions = sample(source_questions, 5)
                break

        # If no group of 5 found, take random questions
        if not selected_source_questions:
            selected_source_questions = sample(questions_task_type_10, min(5, len(questions_task_type_10)))
        
        selected_questions.extend(selected_source_questions)

        # Step 3: Select 5 questions (31–35) with task_type=8
        questions_task_type_8 = list(all_questions.filter(task_type=8)[:5])
        selected_questions.extend(questions_task_type_8)

        # If there are not enough questions with task_type=8, fill the gaps with random questions
        if len(questions_task_type_8) < 5:
            remaining_questions = all_questions.exclude(id__in=[q.id for q in selected_questions])
            additional_questions = sample(list(remaining_questions), min(5 - len(questions_task_type_8), remaining_questions.count()))
            selected_questions.extend(additional_questions)

        # Step 4: Select 5 questions (36–40) with task_type=6
        questions_task_type_6 = list(all_questions.filter(task_type=6)[:5])
        selected_questions.extend(questions_task_type_6)

        # If there are not enough questions with task_type=6, fill the gaps with random questions
        if len(questions_task_type_6) < 5:
            remaining_questions = all_questions.exclude(id__in=[q.id for q in selected_questions])
            additional_questions = sample(list(remaining_questions), min(5 - len(questions_task_type_6), remaining_questions.count()))
            selected_questions.extend(additional_questions)

        # Step 5: Ensure the list has exactly 40 questions
        if len(selected_questions) < 40:
            remaining_questions = all_questions.exclude(id__in=[q.id for q in selected_questions])
            additional_questions = sample(list(remaining_questions), min(40 - len(selected_questions), remaining_questions.count()))
            selected_questions.extend(additional_questions)

        # Serialize and return the selected questions
        return CurrentQuestionSerializer(selected_questions[:40], many=True).data

class CurrentProductSerializer(serializers.ModelSerializer):
    tests = CurrentTestSerializer(many=True)

    class Meta:
        model = Product
        fields = ['id', 'title', 'tests']


class ProductSerializer(serializers.ModelSerializer):
    subject_limit = serializers.SerializerMethodField()
    
    class Meta:
        model = Product
        fields = ['id', 'title', 'sum', 'description', 'time', 'subject_limit', 'product_type']
    
    def get_subject_limit(self, obj):
        # Check if the product ID matches one of the specified IDs
        special_product_ids = [
            '4ce7261c-29e8-4514-94c0-68344010c2d9',
            '59c6f3a4-14e9-4270-a859-c1131724f51c'
        ]
        
        if str(obj.id) in special_product_ids:
            # Return a value between 3 and 6 for the specified products
            return obj.subject_limit if 3 <= obj.subject_limit <= 6 else 3
        
        # Return the original value for other products
        return obj.subject_limit

class TestSerializer(serializers.ModelSerializer):
    class Meta:
        model = Test
        fields = ['id', 'title', 'is_required', 'grade']

class GradeGroupedTestSerializer(serializers.Serializer):
    grade = serializers.IntegerField()
    tests = TestSerializer(many=True)


class CompletedOptionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Option
        fields = ['id', 'text', 'is_correct']

class CompletedQuestionSerializer(serializers.ModelSerializer):
    options = CompletedOptionSerializer(many=True)

    class Meta:
        model = Question
        fields = ['id', 'text', 'options']

class CompletedQuestionSerializer(serializers.ModelSerializer):
    question = CurrentQuestionSerializer()
    selected_option = CurrentOptionSerializer()
    test = TestSerializer()

    class Meta:
        model = CompletedQuestion
        fields = ['id', 'test', 'question', 'selected_option']

class CompletedTestSerializer(serializers.ModelSerializer):
    # completed_questions = CompletedQuestionSerializer(many=True)
    # user = UserSerializer()
    product = ProductSerializer()

    # Adding custom fields for correct/incorrect answers and total question count
    correct_answers_count = serializers.SerializerMethodField()
    # incorrect_answers_count = serializers.SerializerMethodField()
    # total_question_count = serializers.SerializerMethodField()
    # subjects = serializers.SerializerMethodField()

    class Meta:
        model = CompletedTest
        fields = [
            'id', 
            'user', 
            'product', 
            'start_test_time', 
            'correct_answers_count',
            'completed_date',
            'time_spent'
        ]

    # Method to calculate correct answers for the specific test
    def get_correct_answers_count(self, obj):
        # Count questions where at least one selected option is correct
        return obj.completed_questions.filter(selected_option__is_correct=True).distinct().count()

    # Method to calculate incorrect answers for the specific test
    def get_incorrect_answers_count(self, obj):
        # Count questions where no selected option is correct or no option is selected
        return obj.completed_questions.annotate(
            correct_options=Count('selected_option', filter=Q(selected_option__is_correct=True))
        ).filter(correct_options=0).count()

    # Method to calculate total questions for the specific test
    def get_total_question_count(self, obj):
        return obj.completed_questions.count()

    # Method to return subjects with correct/incorrect counts for specific subjects
    def get_subjects(self, obj):
        subjects_stats = {}
        for completed_question in obj.completed_questions.all():
            subject_title = completed_question.question.subject_title
            if subject_title not in subjects_stats:
                subjects_stats[subject_title] = {'correct': 0, 'incorrect': 0}
            
            if completed_question.selected_option and completed_question.selected_option.is_correct:
                subjects_stats[subject_title]['correct'] += 1
            else:
                subjects_stats[subject_title]['incorrect'] += 1
        return [{'subject': k, 'correct': v['correct'], 'incorrect': v['incorrect']} for k, v in subjects_stats.items()]



# old
# class QuestionSerializer(serializers.ModelSerializer):
#     test = serializers.PrimaryKeyRelatedField(queryset=Test.objects.all())

#     class Meta:
#         model = Question
#         fields = '__all__'

#     def to_representation(self, instance):
#         representation = super().to_representation(instance)
#         representation['test'] = instance.test.id
#         return representation


# class OptionSerializer(serializers.ModelSerializer):
#     question = serializers.PrimaryKeyRelatedField(queryset=Question.objects.all())

#     class Meta:
#         model = Option
#         fields = '__all__'

#     def to_representation(self, instance):
#         representation = super().to_representation(instance)
#         representation['question'] = instance.question.id
#         return representation


# class ResultSerializer(serializers.ModelSerializer):
#     test = serializers.PrimaryKeyRelatedField(queryset=Test.objects.all())
#     student = serializers.PrimaryKeyRelatedField(queryset=User.objects.all())
#     question = serializers.PrimaryKeyRelatedField(queryset=Question.objects.all())
#     selected_option = serializers.PrimaryKeyRelatedField(queryset=Option.objects.all())

#     class Meta:
#         model = Result
#         fields = '__all__'

#     def to_representation(self, instance):
#         representation = super().to_representation(instance)
#         representation['test'] = instance.test.id
#         representation['student'] = instance.student.id
#         representation['question'] = instance.question.id
#         representation['selected_option'] = instance.selected_option.id
#         return representation


# class BookSuggestionSerializer(serializers.ModelSerializer):
#     question = serializers.PrimaryKeyRelatedField(queryset=Question.objects.all())

#     class Meta:
#         model = BookSuggestion
#         fields = '__all__'

#     def to_representation(self, instance):
#         representation = super().to_representation(instance)
#         representation['question'] = instance.question.id
#         return representation


# new

# Serializer for the options within a question
class OptionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Option
        fields = ['id', 'text', 'is_correct']

# Serializer for the questions within a test
class QuestionSerializer(serializers.ModelSerializer):
    # All options for the question, assuming reverse relation is 'options'
    all_options = serializers.SerializerMethodField()
    selected_option = OptionSerializer(many=True)  # Change to many=True

    # Add the text field explicitly by accessing it from the 'question' relation
    question_text = serializers.CharField(source='question.text', read_only=True)

    class Meta:
        model = CompletedQuestion  # Serializer is for CompletedQuestion model
        fields = ['id', 'question_text', 'selected_option', 'all_options']  # Include question_text
        
    def get_all_options(self, obj):
        # Get all options for this question
        options = obj.question.options.all()
        # Convert queryset to list and randomize the order
        options_list = list(options)
        shuffle(options_list)
        # Serialize the randomized options
        return OptionSerializer(options_list, many=True).data

# Serializer for tests within the product
class CTestSerializer(serializers.ModelSerializer):
    questions = serializers.SerializerMethodField()  # Custom method to include questions within a test
    total_correct_by_test = serializers.SerializerMethodField()  # Custom field for total correct answers by test
    total_incorrect_by_test = serializers.SerializerMethodField()  # Custom field for total incorrect answers by test

    class Meta:
        model = Test
        fields = ['id', 'title', 'questions', 'total_correct_by_test', 'total_incorrect_by_test']

    # Custom method to retrieve questions and their selected options for the test
    def get_questions(self, obj):
        completed_questions = CompletedQuestion.objects.filter(test=obj, completed_test=self.context.get('completed_test'))
        return QuestionSerializer(completed_questions, many=True).data

    # Custom method to calculate total correct answers for the test
    def get_total_correct_by_test(self, obj):
        completed_questions = CompletedQuestion.objects.filter(test=obj, completed_test=self.context.get('completed_test'))
        return completed_questions.filter(selected_option__is_correct=True).count()

    # Custom method to calculate total incorrect answers for the test
    def get_total_incorrect_by_test(self, obj):
        completed_test = self.context.get('completed_test')
        # Retrieve completed questions for the given test
        completed_questions = CompletedQuestion.objects.filter(test=obj, completed_test=completed_test)
        # Filter for incorrect answers where selected_option__is_correct is either False or Null
        return completed_questions.filter(Q(selected_option__is_correct=False) | Q(selected_option__is_correct__isnull=True)).count()
    
# Serializer for products
class CProductSerializer(serializers.ModelSerializer):
    tests = serializers.SerializerMethodField()  # Custom method to include tests within a product
    total_correct_by_all_tests = serializers.SerializerMethodField()  # Total correct answers across all tests
    total_incorrect_by_all_tests = serializers.SerializerMethodField()  # Total incorrect answers across all tests
    total_question_count_by_all_tests = serializers.SerializerMethodField()

    class Meta:
        model = Product
        fields = ['id', 'title', 'tests', 'total_correct_by_all_tests', 'total_incorrect_by_all_tests', 'total_question_count_by_all_tests']

    # Custom method to retrieve tests related to the completed test
    def get_tests(self, obj):
        completed_test = self.context.get('completed_test')  # Pass completed_test to the serializer context
        return CTestSerializer(completed_test.tests.all(), many=True, context={'completed_test': completed_test}).data

    # Custom method to calculate total correct answers across all tests
    def get_total_correct_by_all_tests(self, obj):
        completed_test = self.context.get('completed_test')
        return CompletedQuestion.objects.filter(completed_test=completed_test, selected_option__is_correct=True).count()

    # Custom method to calculate total incorrect answers across all tests
    def get_total_incorrect_by_all_tests(self, obj):
        completed_test = self.context.get('completed_test')
        # Filter for incorrect answers where selected_option__is_correct is either False or Null
        return CompletedQuestion.objects.filter(
            completed_test=completed_test
        ).filter(
            Q(selected_option__is_correct=False) | Q(selected_option__is_correct__isnull=True)
        ).count()
    
    def get_total_question_count_by_all_tests(self, obj):
        completed_test = self.context.get('completed_test')
        # Count the total number of completed questions for this test
        return CompletedQuestion.objects.filter(completed_test=completed_test).count()

# Serializer for the completed test
class CCompletedTestSerializer(serializers.ModelSerializer):
    product = CProductSerializer()
    user = serializers.StringRelatedField()  # Display user's string representation
    start_test_time = serializers.DateTimeField(format="%Y-%m-%d %H:%M:%S")
    completed_date = serializers.DateTimeField(format="%Y-%m-%d %H:%M:%S")

    class Meta:
        model = CompletedTest
        fields = ['id', 'user', 'product', 'start_test_time', 'completed_date']