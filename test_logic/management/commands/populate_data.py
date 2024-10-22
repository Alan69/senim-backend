import uuid
from django.core.management.base import BaseCommand
from test_logic.models import Product, Test, Question, Option

class Command(BaseCommand):
    help = 'Populates the database with sample data.'

    def handle(self, *args, **options):
        # Create one product
        product = Product.objects.create(
            id=uuid.uuid4(),
            title="Sample Product",
            sum=1500,
            time=45,
        )
        self.stdout.write(self.style.SUCCESS('Created Product'))

        # Create 6 tests
        for test_num in range(1, 8):
            test = Test.objects.create(
                id=uuid.uuid4(),
                title=f"Test {test_num}",
                number_of_questions=15,
                time=45,
                score=0,
                product=product,
                is_required=False
            )
            self.stdout.write(self.style.SUCCESS(f'Created Test {test_num}'))

            # Create 15 questions for each test
            for question_num in range(1, 16):
                question = Question.objects.create(
                    id=uuid.uuid4(),
                    test=test,
                    text=f"Question {question_num} text for Test {test_num}",
                    img=None
                )

                # Create 4 options for each question
                for option_num in range(1, 5):
                    Option.objects.create(
                        id=uuid.uuid4(),
                        question=question,
                        text=f"Option {option_num} for Question {question_num} of Test {test_num}",
                        is_correct=True if option_num == 1 else False
                    )

            self.stdout.write(self.style.SUCCESS(f'Added Questions and Options for Test {test_num}'))

        self.stdout.write(self.style.SUCCESS('Database population complete.'))
