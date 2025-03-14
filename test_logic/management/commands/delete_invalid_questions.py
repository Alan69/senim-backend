from django.core.management.base import BaseCommand
from test_logic.models import Question, Option
from django.db.models import Count

class Command(BaseCommand):
    help = 'Deletes questions that have fewer than 4 options'

    def handle(self, *args, **kwargs):
        # Get questions with their option count
        questions_to_delete = Question.objects.annotate(
            option_count=Count('options')
        ).filter(option_count__lt=4)

        count = questions_to_delete.count()
        
        if count > 0:
            questions_to_delete.delete()
            self.stdout.write(
                self.style.SUCCESS(f'Successfully deleted {count} questions with fewer than 4 options')
            )
        else:
            self.stdout.write(
                self.style.SUCCESS('No questions found with fewer than 4 options')
            )
