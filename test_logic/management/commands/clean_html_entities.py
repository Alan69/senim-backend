import re
import html
from django.core.management.base import BaseCommand
from test_logic.models import Question, Option  # Adjust the import path if needed

class Command(BaseCommand):
    help = 'Remove HTML entities like &nbsp; from Question and Option text fields.'

    # Regex pattern to find extra spaces (e.g., consecutive spaces, &nbsp; after unescaping)
    EXTRA_SPACE_RE = re.compile(r'\s+')

    def handle(self, *args, **kwargs):
        # Process Questions
        self.stdout.write("Processing Questions...")
        question_updates = self.clean_text_for_questions()

        # Process Options
        self.stdout.write("Processing Options...")
        option_updates = self.clean_text_for_options()

        # Summary
        self.stdout.write(f"Successfully updated {question_updates} questions.")
        self.stdout.write(f"Successfully updated {option_updates} options.")

    def clean_text_for_questions(self):
        updated_count = 0
        questions = Question.objects.all()

        for question in questions:
            original_text = question.text or ""  # Handle None as empty string
            cleaned_text = self.clean_text(original_text)

            if cleaned_text != original_text:
                question.text = cleaned_text
                question.save()
                updated_count += 1
                self.stdout.write(f"Updated Question ID {question.id}")

        return updated_count

    def clean_text_for_options(self):
        updated_count = 0
        options = Option.objects.all()

        for option in options:
            original_text = option.text or ""  # Handle None as empty string
            cleaned_text = self.clean_text(original_text)

            if cleaned_text != original_text:
                option.text = cleaned_text
                option.save()
                updated_count += 1
                self.stdout.write(f"Updated Option ID {option.id}")

        return updated_count

    def clean_text(self, text):
        # Unescape HTML entities (e.g., &nbsp; -> ' ')
        unescaped_text = html.unescape(text)

        # Replace multiple spaces with a single space
        cleaned_text = self.EXTRA_SPACE_RE.sub(' ', unescaped_text).strip()

        return cleaned_text
