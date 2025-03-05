from django.core.management.base import BaseCommand, CommandError
from test_logic.models import Product, Test, Question
import uuid

class Command(BaseCommand):
    help = 'Sets question_usage to False for all questions associated with a specific Product ID'

    def add_arguments(self, parser):
        parser.add_argument('product_id', type=str, help='UUID of the product')

    def handle(self, *args, **options):
        try:
            # Convert string to UUID
            product_id = uuid.UUID(options['product_id'])
            
            # Get the product
            try:
                product = Product.objects.get(id=product_id)
            except Product.DoesNotExist:
                raise CommandError(f'Product with ID "{product_id}" does not exist')
            
            # Get all tests associated with the product
            tests = Test.objects.filter(product=product)
            
            if not tests.exists():
                self.stdout.write(self.style.WARNING(f'No tests found for product "{product.title}"'))
                return
            
            # Get all questions from these tests
            questions_count = 0
            for test in tests:
                questions = Question.objects.filter(test=test)
                questions_updated = questions.update(question_usage=False)
                questions_count += questions_updated
            
            self.stdout.write(
                self.style.SUCCESS(
                    f'Successfully disabled question_usage for {questions_count} questions '
                    f'associated with product "{product.title}" (ID: {product_id})'
                )
            )
            
        except ValueError:
            raise CommandError('Invalid UUID format') 