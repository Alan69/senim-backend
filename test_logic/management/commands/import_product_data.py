import json
import os
import uuid
import requests
from datetime import datetime
from django.core.management.base import BaseCommand
from django.core.files.base import ContentFile
from django.conf import settings
from test_logic.models import Product, Test, Question, Option
from django.utils.dateparse import parse_date


class Command(BaseCommand):
    help = 'Import product, tests, and questions from a JSON file'

    def add_arguments(self, parser):
        parser.add_argument('json_file', type=str, help='Path to the JSON file')
        parser.add_argument('--media-dir', type=str, help='Directory to save media files', default='media')

    def handle(self, *args, **options):
        json_file_path = options['json_file']
        media_dir = options['media_dir']
        
        # Ensure media directory exists
        os.makedirs(media_dir, exist_ok=True)
        
        try:
            with open(json_file_path, 'r', encoding='utf-8') as file:
                data = json.load(file)
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Error reading JSON file: {e}'))
            return
        
        # Process product data
        try:
            self.import_product(data.get('product', {}))
            self.stdout.write(self.style.SUCCESS('Product imported successfully'))
            
            # Process tests data
            tests_data = data.get('tests', [])
            for test_data in tests_data:
                self.import_test(test_data)
            self.stdout.write(self.style.SUCCESS(f'{len(tests_data)} tests imported successfully'))
            
            # Process questions data
            questions_data = data.get('questions', [])
            for question_data in questions_data:
                self.import_question(question_data, media_dir)
            self.stdout.write(self.style.SUCCESS(f'{len(questions_data)} questions imported successfully'))
            
            # Process options data
            options_data = data.get('options', [])
            for option_data in options_data:
                self.import_option(option_data, media_dir)
            self.stdout.write(self.style.SUCCESS(f'{len(options_data)} options imported successfully'))
            
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Error importing data: {e}'))
    
    def import_product(self, product_data):
        """Import or update a product"""
        if not product_data:
            return None
        
        product_id = product_data.get('id')
        if not product_id:
            self.stdout.write(self.style.WARNING('Product ID is missing, skipping'))
            return None
        
        # Try to get existing product or create a new one
        try:
            product = Product.objects.get(id=product_id)
            self.stdout.write(self.style.SUCCESS(f'Found existing product: {product.title}'))
        except Product.DoesNotExist:
            product = Product(id=product_id)
            self.stdout.write(self.style.SUCCESS(f'Creating new product with ID: {product_id}'))
        
        # Update product fields
        product.title = product_data.get('title', product.title)
        product.description = product_data.get('description', product.description)
        product.sum = product_data.get('sum', product.sum)
        product.score = product_data.get('score', product.score)
        product.time = product_data.get('time', product.time)
        product.subject_limit = product_data.get('subject_limit', product.subject_limit)
        product.product_type = product_data.get('product_type', product.product_type)
        
        # Handle date_created if provided
        date_created = product_data.get('date_created')
        if date_created and not product.pk:  # Only set date_created for new products
            try:
                product.date_created = parse_date(date_created)
            except Exception as e:
                self.stdout.write(self.style.WARNING(f'Error parsing date: {e}'))
        
        product.save()
        return product
    
    def import_test(self, test_data):
        """Import or update a test"""
        if not test_data:
            return None
        
        test_id = test_data.get('id')
        if not test_id:
            self.stdout.write(self.style.WARNING('Test ID is missing, skipping'))
            return None
        
        # Get product
        product_id = test_data.get('product')
        try:
            product = Product.objects.get(id=product_id)
        except Product.DoesNotExist:
            self.stdout.write(self.style.ERROR(f'Product with ID {product_id} not found, skipping test'))
            return None
        
        # Try to get existing test or create a new one
        try:
            test = Test.objects.get(id=test_id)
            self.stdout.write(self.style.SUCCESS(f'Found existing test: {test.title}'))
        except Test.DoesNotExist:
            test = Test(id=test_id)
            self.stdout.write(self.style.SUCCESS(f'Creating new test with ID: {test_id}'))
        
        # Update test fields
        test.title = test_data.get('title', test.title)
        test.number_of_questions = test_data.get('number_of_questions', test.number_of_questions)
        test.time = test_data.get('time', test.time)
        test.score = test_data.get('score', test.score)
        test.product = product
        test.grade = test_data.get('grade', test.grade)
        test.is_required = test_data.get('is_required', test.is_required)
        
        # Handle date_created if provided
        date_created = test_data.get('date_created')
        if date_created and not test.pk:  # Only set date_created for new tests
            try:
                test.date_created = parse_date(date_created)
            except Exception as e:
                self.stdout.write(self.style.WARNING(f'Error parsing date: {e}'))
        
        test.save()
        return test
    
    def import_question(self, question_data, media_dir):
        """Import or update a question and handle media files"""
        if not question_data:
            return None
        
        question_id = question_data.get('id')
        if not question_id:
            self.stdout.write(self.style.WARNING('Question ID is missing, skipping'))
            return None
        
        # Get test
        test_id = question_data.get('test')
        try:
            test = Test.objects.get(id=test_id)
        except Test.DoesNotExist:
            self.stdout.write(self.style.ERROR(f'Test with ID {test_id} not found, skipping question'))
            return None
        
        # Try to get existing question or create a new one
        try:
            question = Question.objects.get(id=question_id)
            self.stdout.write(self.style.SUCCESS(f'Found existing question: {question_id}'))
        except Question.DoesNotExist:
            question = Question(id=question_id)
            self.stdout.write(self.style.SUCCESS(f'Creating new question with ID: {question_id}'))
        
        # Update question fields
        question.test = test
        question.text = question_data.get('text', question.text)
        question.text2 = question_data.get('text2', question.text2)
        question.text3 = question_data.get('text3', question.text3)
        question.task_type = question_data.get('task_type', question.task_type)
        question.level = question_data.get('level', question.level)
        question.status = question_data.get('status', question.status)
        question.category = question_data.get('category', question.category)
        question.subcategory = question_data.get('subcategory', question.subcategory)
        question.theme = question_data.get('theme', question.theme)
        question.subtheme = question_data.get('subtheme', question.subtheme)
        question.target = question_data.get('target', question.target)
        question.source = question_data.get('source', question.source)
        question.detail_id = question_data.get('detail_id', question.detail_id)
        question.lng_id = question_data.get('lng_id', question.lng_id)
        question.lng_title = question_data.get('lng_title', question.lng_title)
        question.subject_id = question_data.get('subject_id', question.subject_id)
        question.subject_title = question_data.get('subject_title', question.subject_title)
        question.class_number = question_data.get('class_number', question.class_number)
        question.question_usage = question_data.get('question_usage', question.question_usage)
        
        # Handle image if provided
        img_path = question_data.get('img')
        if img_path and img_path != 'null' and img_path != '':
            # Handle both remote and local images
            if img_path.startswith('http'):
                # Download remote image
                try:
                    response = requests.get(img_path)
                    if response.status_code == 200:
                        img_name = os.path.basename(img_path)
                        question.img.save(img_name, ContentFile(response.content), save=False)
                except Exception as e:
                    self.stdout.write(self.style.WARNING(f'Error downloading image {img_path}: {e}'))
            else:
                # Handle local image (assuming it's in the media directory)
                local_path = os.path.join(media_dir, img_path.replace('media/', ''))
                if os.path.exists(local_path):
                    with open(local_path, 'rb') as img_file:
                        img_name = os.path.basename(local_path)
                        question.img.save(img_name, ContentFile(img_file.read()), save=False)
                else:
                    self.stdout.write(self.style.WARNING(f'Image file not found: {local_path}'))
        
        question.save()
        return question
        
    def import_option(self, option_data, media_dir):
        """Import or update an option and handle media files"""
        if not option_data:
            return None
        
        option_id = option_data.get('id')
        if not option_id:
            self.stdout.write(self.style.WARNING('Option ID is missing, skipping'))
            return None
        
        # Get question
        question_id = option_data.get('question')
        try:
            question = Question.objects.get(id=question_id)
        except Question.DoesNotExist:
            self.stdout.write(self.style.ERROR(f'Question with ID {question_id} not found, skipping option'))
            return None
        
        # Try to get existing option or create a new one
        try:
            option = Option.objects.get(id=option_id)
            self.stdout.write(self.style.SUCCESS(f'Found existing option: {option_id}'))
        except Option.DoesNotExist:
            option = Option(id=option_id)
            self.stdout.write(self.style.SUCCESS(f'Creating new option with ID: {option_id}'))
        
        # Update option fields
        option.question = question
        option.text = option_data.get('text', option.text)
        option.is_correct = option_data.get('is_correct', option.is_correct)
        
        # Handle image if provided
        img_path = option_data.get('img')
        if img_path and img_path != 'null' and img_path != '':
            # Handle both remote and local images
            if img_path.startswith('http'):
                # Download remote image
                try:
                    response = requests.get(img_path)
                    if response.status_code == 200:
                        img_name = os.path.basename(img_path)
                        option.img.save(img_name, ContentFile(response.content), save=False)
                except Exception as e:
                    self.stdout.write(self.style.WARNING(f'Error downloading image {img_path}: {e}'))
            else:
                # Handle local image (assuming it's in the media directory)
                local_path = os.path.join(media_dir, img_path.replace('media/', ''))
                if os.path.exists(local_path):
                    with open(local_path, 'rb') as img_file:
                        img_name = os.path.basename(local_path)
                        option.img.save(img_name, ContentFile(img_file.read()), save=False)
                else:
                    self.stdout.write(self.style.WARNING(f'Image file not found: {local_path}'))
        
        option.save()
        return option 