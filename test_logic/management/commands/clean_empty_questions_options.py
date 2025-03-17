from django.core.management.base import BaseCommand
from test_logic.models import Question, Option
from django.db.models import Q


class Command(BaseCommand):
    help = 'Removes Questions with empty text and Options with empty text'

    def handle(self, *args, **options):
        # Find Questions with empty text
        empty_questions = Question.objects.filter(
            Q(text__isnull=True) | 
            Q(text='') | 
            Q(text=' ')
        )
        
        question_count = empty_questions.count()
        if question_count > 0:
            self.stdout.write(f"Found {question_count} Questions with empty text")
            # Delete these Questions (Options will be deleted due to CASCADE)
            empty_questions.delete()
            self.stdout.write(self.style.SUCCESS(f"Deleted {question_count} Questions with empty text"))
        else:
            self.stdout.write("No Questions with empty text found")
        
        # Find Options with empty text
        empty_options = Option.objects.filter(
            Q(text__isnull=True) | 
            Q(text='') | 
            Q(text=' ')
        )
        
        option_count = empty_options.count()
        if option_count > 0:
            self.stdout.write(f"Found {option_count} Options with empty text")
            # Delete these Options
            empty_options.delete()
            self.stdout.write(self.style.SUCCESS(f"Deleted {option_count} Options with empty text"))
        else:
            self.stdout.write("No Options with empty text found")
        
        self.stdout.write(self.style.SUCCESS('Successfully cleaned empty Questions and Options')) 