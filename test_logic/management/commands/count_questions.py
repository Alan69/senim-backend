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
                question_count = Question.objects.filter(test=test).count()
                self.stdout.write(f"  Test: {test.title} - {question_count} questions")
