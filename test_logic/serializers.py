from rest_framework import serializers
from .models import Product, Test, Question, Option, Result, BookSuggestion, CompletedTest, CompletedQuestion
from accounts.models import User
from accounts.serializers import UserSerializer
from django.db.models import Q

# new
class CurrentOptionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Option
        fields = ['id', 'text']

class CurrentQuestionSerializer(serializers.ModelSerializer):
    options = CurrentOptionSerializer(many=True)

    class Meta:
        model = Question
        fields = ['id', 'text', 'options']

class CurrentTestSerializer(serializers.ModelSerializer):
    questions = serializers.SerializerMethodField()

    class Meta:
        model = Test
        fields = ['id', 'title', 'questions']

    def get_questions(self, obj):
        questions = Question.objects.filter(test=obj)[:15]
        return CurrentQuestionSerializer(questions, many=True).data

class CurrentProductSerializer(serializers.ModelSerializer):
    tests = CurrentTestSerializer(many=True)

    class Meta:
        model = Product
        fields = ['id', 'title', 'tests']


class ProductSerializer(serializers.ModelSerializer):
    class Meta:
        model = Product
        fields = ['id', 'title', 'sum', 'description', 'time', 'subject_limit']

class TestSerializer(serializers.ModelSerializer):

    class Meta:
        model = Test
        fields = ['id', 'title', 'is_required']

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
        return obj.completed_questions.filter(selected_option__is_correct=True).count()

    # Method to calculate incorrect answers for the specific test
    def get_incorrect_answers_count(self, obj):
        return obj.completed_questions.filter(selected_option__is_correct=False).count()

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
    all_options = OptionSerializer(source='question.options', many=True)
    selected_option = OptionSerializer()

    class Meta:
        model = CompletedQuestion  # Model is CompletedQuestion, not Question
        fields = ['id', 'question_text', 'selected_option', 'all_options']
    
    # Add the text field explicitly by accessing it from the 'question' relation
    question_text = serializers.CharField(source='question.text', read_only=True)

    class Meta:
        model = CompletedQuestion  # Serializer is for CompletedQuestion model
        fields = ['id', 'question_text', 'selected_option', 'all_options']  # Include question_text

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
    user = serializers.StringRelatedField()  # Display user’s string representation
    start_test_time = serializers.DateTimeField(format="%Y-%m-%d %H:%M:%S")
    completed_date = serializers.DateTimeField(format="%Y-%m-%d %H:%M:%S")

    class Meta:
        model = CompletedTest
        fields = ['id', 'user', 'product', 'start_test_time', 'completed_date']