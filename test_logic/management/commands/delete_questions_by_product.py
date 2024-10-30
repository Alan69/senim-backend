from django.core.management.base import BaseCommand
from test_logic.models import Question, Test  # Adjust the import path if needed

class Command(BaseCommand):
    help = 'Delete questions associated with specific product IDs.'

    # List of product IDs for which questions will be deleted
    PRODUCT_IDS = [
        "577b67e9-bb52-45f2-9ee4-1d1cf6eaf27f",
        "2a8ca9b5-5b4d-4575-9aeb-e5a72c3e6573",
    ]

    def handle(self, *args, **kwargs):
        # Find all tests belonging to the specified product IDs
        tests = Test.objects.filter(product__id__in=self.PRODUCT_IDS)
        test_ids = [test.id for test in tests]

        # Find and delete all questions related to these tests
        questions_to_delete = Question.objects.filter(test__id__in=test_ids)
        question_count = questions_to_delete.count()

        if question_count > 0:
            questions_to_delete.delete()
            self.stdout.write(f"Successfully deleted {question_count} questions.")
        else:
            self.stdout.write("No questions found for the specified product IDs.")
