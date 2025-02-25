from django.core.management.base import BaseCommand
import json
from test_logic.models import CompletedQuestion

class Command(BaseCommand):
    help = 'Export CompletedQuestion data to a properly formatted JSON file'

    def handle(self, *args, **options):
        completed_questions = CompletedQuestion.objects.all()
        data = []

        for question in completed_questions:
            data.append({
                "model": "test_logic.completedquestion",
                "pk": str(question.id),
                "fields": {
                    "completed_test": str(question.completed_test.id),
                    "test": str(question.test.id),
                    "question": str(question.question.id) if question.question else None,
                    "selected_option": str(question.selected_option.id) if question.selected_option else None
                }
            })

        with open('fixture_completedquestion.json', 'w') as f:
            json.dump(data, f, indent=2)

        self.stdout.write(
            self.style.SUCCESS(f'Successfully exported {len(data)} CompletedQuestion records')
        ) 