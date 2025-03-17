from django.core.management.base import BaseCommand
from test_logic.models import Option, Test
from django.db.models import Q


class Command(BaseCommand):
    help = 'Deletes Options with empty text for a specific Product ID'

    def add_arguments(self, parser):
        parser.add_argument(
            '--confirm',
            action='store_true',
            help='Confirm deletion without prompting',
        )

    def handle(self, *args, **options):
        product_id = '4ce7261c-29e8-4514-94c0-68344010c2d9'
        
        # Get tests associated with the specific product
        tests = Test.objects.filter(product_id=product_id)
        
        if not tests.exists():
            self.stdout.write(self.style.WARNING(f"No tests found for Product ID: {product_id}"))
            return
        
        self.stdout.write(f"Found {tests.count()} tests for Product ID: {product_id}")
        
        # Find Options with empty text for the specific product
        empty_options = Option.objects.filter(
            Q(question__test__in=tests) &
            (Q(text__isnull=True) | Q(text='') | Q(text=' '))
        )
        
        option_count = empty_options.count()
        if option_count > 0:
            self.stdout.write(self.style.WARNING(f"Found {option_count} Options with empty text"))
            
            # Ask for confirmation before deletion unless --confirm flag is used
            if not options['confirm']:
                confirm = input(f"Are you sure you want to delete {option_count} Options? (yes/no): ")
                if confirm.lower() != 'yes':
                    self.stdout.write(self.style.WARNING("Deletion cancelled."))
                    return
            
            # Delete the empty options
            empty_options.delete()
            self.stdout.write(self.style.SUCCESS(f"Successfully deleted {option_count} Options with empty text"))
        else:
            self.stdout.write(self.style.SUCCESS("No Options with empty text found")) 