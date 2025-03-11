import re
import html
from django.core.management.base import BaseCommand
from test_logic.models import Product, Test, Question, Option

class Command(BaseCommand):
    help = 'Remove HTML tags from Question and Option text fields for a specific product ID.'

    def add_arguments(self, parser):
        parser.add_argument('product_id', type=str, help='UUID of the product')

    def handle(self, *args, **kwargs):
        product_id = kwargs['product_id']
        
        try:
            product = Product.objects.get(id=product_id)
            self.stdout.write(f"Processing product: {product.title} (ID: {product_id})")
            
            # Get all tests associated with this product
            tests = Test.objects.filter(product=product)
            self.stdout.write(f"Found {tests.count()} tests for this product")
            
            question_count = 0
            option_count = 0
            
            # Process each test
            for test in tests:
                # Get all questions for this test
                questions = Question.objects.filter(test=test)
                self.stdout.write(f"Processing {questions.count()} questions for test: {test.title}")
                
                # Process each question
                for question in questions:
                    original_text = question.text
                    cleaned_text = self.clean_html(original_text)
                    
                    if cleaned_text != original_text:
                        question.text = cleaned_text
                        question.save()
                        question_count += 1
                    
                    # Also clean text2 and text3 if they exist
                    if question.text2:
                        original_text2 = question.text2
                        cleaned_text2 = self.clean_html(original_text2)
                        if cleaned_text2 != original_text2:
                            question.text2 = cleaned_text2
                            question.save()
                    
                    if question.text3:
                        original_text3 = question.text3
                        cleaned_text3 = self.clean_html(original_text3)
                        if cleaned_text3 != original_text3:
                            question.text3 = cleaned_text3
                            question.save()
                    
                    # Process options for this question
                    options = Option.objects.filter(question=question)
                    for option in options:
                        original_option_text = option.text
                        cleaned_option_text = self.clean_html(original_option_text)
                        
                        if cleaned_option_text != original_option_text:
                            option.text = cleaned_option_text
                            option.save()
                            option_count += 1
            
            self.stdout.write(self.style.SUCCESS(f"Successfully cleaned HTML tags from {question_count} questions and {option_count} options for product ID: {product_id}"))
            
        except Product.DoesNotExist:
            self.stdout.write(self.style.ERROR(f"Product with ID {product_id} does not exist"))
            return
    
    def clean_html(self, text):
        """Remove HTML tags and clean up the text."""
        # First unescape HTML entities
        unescaped_text = html.unescape(text)
        
        # Remove HTML tags
        tag_pattern = re.compile(r'<[^>]+>')
        text_without_tags = tag_pattern.sub('', unescaped_text)
        
        # Replace multiple spaces with a single space
        space_pattern = re.compile(r'\s+')
        cleaned_text = space_pattern.sub(' ', text_without_tags).strip()
        
        return cleaned_text 