from django.core.management.base import BaseCommand, CommandError
from test_logic.models import Test  # Replace 'your_app' with the actual app name
from uuid import UUID

class Command(BaseCommand):
    help = 'Update time for tests with a specific product ID.'

    def add_arguments(self, parser):
        # Add the time and product_id as command-line arguments
        parser.add_argument('time', type=int, help='The new time value for the tests')
        parser.add_argument('product_id', type=str, help='The product ID to filter the tests')

    def handle(self, *args, **options):
        try:
            # Extract the command-line arguments
            time = options['time']
            product_id = UUID(options['product_id'])
        except ValueError as e:
            raise CommandError(f'Invalid input: {e}')

        # Filter and update the tests
        tests_to_update = Test.objects.filter(product_id=product_id)

        if not tests_to_update.exists():
            self.stdout.write(self.style.WARNING('No tests found with the specified product ID.'))
            return

        updated_count = tests_to_update.update(time=time)
        self.stdout.write(self.style.SUCCESS(f'Successfully updated {updated_count} test(s).'))
