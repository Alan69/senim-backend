from django.core.management.base import BaseCommand
from test_logic.models import Question, Option, Test  # Adjust import paths if needed

class Command(BaseCommand):
    help = 'Delete questions with more than 4 options for specific product IDs.'

    # List of product IDs
    PRODUCT_IDS = [
        "577b67e9-bb52-45f2-9ee4-1d1cf6eaf27f",
        "2a8ca9b5-5b4d-4575-9aeb-e5a72c3e6573",
    ]

    def handle(self, *args, **kwargs):
        deleted_count = 0

        # Fetch tests related to the provided product IDs
        tests = Test.objects.filter(product__id__in=self.PRODUCT_IDS)

        # Iterate through the related tests
        for test in tests:
            # Fetch questions associated with the test
            questions = Question.objects.filter(test=test)

            for question in questions:
                # Count the number of options for each question
                option_count = question.options.count()

                if option_count > 4:
                    # Delete the question if it has more than 4 options
                    question.delete()
                    deleted_count += 1
                    self.stdout.write(f"Deleted Question ID {question.id} with {option_count} options.")

        # Output the total number of deleted questions
        self.stdout.write(f"Successfully deleted {deleted_count} questions with more than 4 options.")
