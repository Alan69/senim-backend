import re
import html
from django.core.management.base import BaseCommand
from test_logic.models import Question, Option, Test, Product
from bs4 import BeautifulSoup

class Command(BaseCommand):
    help = 'Remove HTML tags from Question and Option text fields for a specific Product ID.'

    PRODUCT_ID = '59c6f3a4-14e9-4270-a859-c1131724f51c'

    def handle(self, *args, **kwargs):
        self.stdout.write(f"Processing Questions and Options for Product ID: {self.PRODUCT_ID}")
        
        try:
            product = Product.objects.get(id=self.PRODUCT_ID)
            self.stdout.write(f"Found Product: {product.title}")
        except Product.DoesNotExist:
            self.stdout.write(self.style.ERROR(f"Product with ID {self.PRODUCT_ID} not found!"))
            return

        # Get tests related to the specified product
        tests = Test.objects.filter(product=product)
        self.stdout.write(f"Found {tests.count()} tests related to this product")

        # Get questions related to these tests
        test_ids = tests.values_list('id', flat=True)
        questions = Question.objects.filter(test_id__in=test_ids)
        self.stdout.write(f"Found {questions.count()} questions to process")

        # Process Questions
        question_updates = self.clean_html_from_questions(questions)

        # Process Options
        option_updates = self.clean_html_from_options(questions)

        # Summary
        self.stdout.write(self.style.SUCCESS(f"Successfully cleaned HTML from {question_updates} questions."))
        self.stdout.write(self.style.SUCCESS(f"Successfully cleaned HTML from {option_updates} options."))

    def clean_html_from_questions(self, questions):
        updated_count = 0

        for question in questions:
            original_text = question.text or ""
            original_text2 = question.text2 or ""
            original_text3 = question.text3 or ""
            
            cleaned_text = self.strip_html_tags(original_text)
            cleaned_text2 = self.strip_html_tags(original_text2)
            cleaned_text3 = self.strip_html_tags(original_text3)
            
            if (cleaned_text != original_text or 
                cleaned_text2 != original_text2 or 
                cleaned_text3 != original_text3):
                
                question.text = cleaned_text
                question.text2 = cleaned_text2
                question.text3 = cleaned_text3
                question.save()
                updated_count += 1
                self.stdout.write(f"Updated Question ID {question.id}")

        return updated_count

    def clean_html_from_options(self, questions):
        updated_count = 0
        
        # Get all options related to questions from the specified product
        question_ids = questions.values_list('id', flat=True)
        options = Option.objects.filter(question_id__in=question_ids)
        
        for option in options:
            original_text = option.text or ""
            cleaned_text = self.strip_html_tags(original_text)
            
            if cleaned_text != original_text:
                option.text = cleaned_text
                option.save()
                updated_count += 1
                self.stdout.write(f"Updated Option ID {option.id}")

        return updated_count

    def strip_html_tags(self, text):
        """Remove all HTML tags while preserving the text content."""
        if not text:
            return ""
            
        # Parse with BeautifulSoup to remove HTML tags
        soup = BeautifulSoup(text, 'html.parser')
        text_content = soup.get_text(separator=' ')
        
        # Also unescape any HTML entities
        unescaped_text = html.unescape(text_content)
        
        # Clean up extra whitespace
        cleaned_text = re.sub(r'\s+', ' ', unescaped_text).strip()
        
        return cleaned_text
