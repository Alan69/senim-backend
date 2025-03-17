from django.core.management.base import BaseCommand
from test_logic.models import Question, Option, Test
from django.db.models import Q


class Command(BaseCommand):
    help = 'Counts Questions with empty text and Options with empty text for a specific Product ID'

    def handle(self, *args, **options):
        product_id = '4ce7261c-29e8-4514-94c0-68344010c2d9'
        
        # Get tests associated with the specific product
        tests = Test.objects.filter(product_id=product_id)
        
        if not tests.exists():
            self.stdout.write(self.style.WARNING(f"No tests found for Product ID: {product_id}"))
            return
        
        self.stdout.write(f"Found {tests.count()} tests for Product ID: {product_id}")
        
        # Find Questions with empty text for the specific product
        empty_questions = Question.objects.filter(
            Q(test__in=tests) &
            (Q(text__isnull=True) | Q(text='') | Q(text=' '))
        )
        
        question_count = empty_questions.count()
        if question_count > 0:
            self.stdout.write(self.style.WARNING(f"Found {question_count} Questions with empty text"))
            
            # Display details of each empty question
            for i, question in enumerate(empty_questions, 1):
                self.stdout.write(f"  {i}. Question ID: {question.id}, Test: {question.test.title}")
        else:
            self.stdout.write(self.style.SUCCESS("No Questions with empty text found"))
        
        # Find Options with empty text for the specific product
        empty_options = Option.objects.filter(
            Q(question__test__in=tests) &
            (Q(text__isnull=True) | Q(text='') | Q(text=' '))
        )
        
        option_count = empty_options.count()
        if option_count > 0:
            self.stdout.write(self.style.WARNING(f"Found {option_count} Options with empty text"))
            
            # Display details of each empty option
            for i, option in enumerate(empty_options, 1):
                self.stdout.write(f"  {i}. Option ID: {option.id}, Question ID: {option.question.id}")
        else:
            self.stdout.write(self.style.SUCCESS("No Options with empty text found"))
        
        self.stdout.write(self.style.SUCCESS(f"Completed counting for Product ID: {product_id}")) 