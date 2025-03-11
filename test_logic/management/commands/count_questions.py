from django.core.management.base import BaseCommand
from test_logic.models import Product, Test, Question

class Command(BaseCommand):
    help = 'Count questions by each Test and Tests by each Product'

    def handle(self, *args, **kwargs):
        products = Product.objects.all()

        for product in products:
            self.stdout.write(f"\nProduct: {product.title}")
            tests = Test.objects.filter(product=product)

            for test in tests:
                questions = Question.objects.filter(test=test)
                question_count = questions.count()
                
                # Calculate test grade (assuming each question has a grade field)
                total_grade = sum(question.grade for question in questions if hasattr(question, 'grade') and question.grade is not None)
                
                self.stdout.write(f"  Test: {test.title} - {question_count} questions, Total Grade: {total_grade}")
