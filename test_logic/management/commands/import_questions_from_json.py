from django.core.management.base import BaseCommand, CommandError
import json
import uuid
from test_logic.models import Product, Test, Question, Option
from django.db import transaction

class Command(BaseCommand):
    help = 'Import questions from a JSON file in the export format'

    def add_arguments(self, parser):
        parser.add_argument('json_file', type=str, help='Path to the JSON file containing questions')
        parser.add_argument('--product-id', type=str, help='UUID of the product to import questions to (overrides the original test associations)')
        parser.add_argument('--skip-existing', action='store_true', help='Skip questions that already exist')

    def handle(self, *args, **options):
        json_file = options['json_file']
        product_id = options.get('product_id')
        skip_existing = options['skip_existing']
        
        # If product_id is provided, validate and get the product
        target_product = None
        if product_id:
            try:
                uuid_obj = uuid.UUID(product_id)
                try:
                    target_product = Product.objects.get(id=uuid_obj)
                    self.stdout.write(self.style.SUCCESS(f"Importing questions to product: {target_product.title} (ID: {product_id})"))
                except Product.DoesNotExist:
                    raise CommandError(f"Product with ID {product_id} does not exist")
            except ValueError:
                raise CommandError(f"Invalid UUID format: {product_id}")
        
        try:
            # Load JSON data
            with open(json_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            if not data:
                self.stdout.write(self.style.WARNING(f"No data found in {json_file}"))
                return
            
            # Statistics
            questions_imported = 0
            questions_skipped = 0
            options_imported = 0
            
            # Process each question
            with transaction.atomic():
                for item in data:
                    if item.get('model') != 'test_logic.question':
                        self.stdout.write(self.style.WARNING(f"Skipping non-question item: {item.get('model')}"))
                        continue
                    
                    question_id = item.get('pk')
                    fields = item.get('fields', {})
                    
                    try:
                        # Check if question already exists
                        if Question.objects.filter(id=question_id).exists():
                            if skip_existing:
                                self.stdout.write(self.style.WARNING(f"Skipping existing question: {question_id}"))
                                questions_skipped += 1
                                continue
                            else:
                                # Delete existing question and its options
                                Question.objects.get(id=question_id).delete()
                        
                        # Get test
                        if target_product:
                            # If importing to a specific product, find or create a test in that product
                            test_info = fields.get('test')
                            test_title = test_info.get('title') if isinstance(test_info, dict) else "Imported Test"
                            
                            # Truncate test title if needed
                            test_title = self.truncate_string(test_title, 200)
                            
                            # Try to find an existing test with the same title in the target product
                            test = Test.objects.filter(product=target_product, title=test_title).first()
                            
                            if not test:
                                # Create a new test in the target product
                                test = Test.objects.create(
                                    product=target_product,
                                    title=test_title,
                                    number_of_questions=0,  # Will be updated as questions are added
                                    time=fields.get('time', 45),
                                    score=0
                                )
                                self.stdout.write(self.style.SUCCESS(f"Created new test '{test_title}' in product {target_product.title}"))
                        else:
                            # Use the original test association
                            test_info = fields.get('test')
                            test_id = test_info.get('id') if isinstance(test_info, dict) else test_info
                            try:
                                test = Test.objects.get(id=test_id)
                            except Test.DoesNotExist:
                                test_title = test_info.get('title') if isinstance(test_info, dict) else "Unknown"
                                self.stdout.write(self.style.WARNING(f"Test with ID {test_id} ('{test_title}') does not exist. Skipping question {question_id}"))
                                questions_skipped += 1
                                continue
                        
                        # Truncate all string fields to be safe
                        # Create a dictionary of fields with truncated values
                        question_data = {
                            'id': question_id,
                            'test': test,
                            'text': fields.get('text', ''),
                            'img': fields.get('img') if fields.get('img') else None,
                            'task_type': fields.get('task_type'),
                            'level': fields.get('level'),
                            'status': fields.get('status'),
                            'category': self.truncate_string(fields.get('category'), 2000),
                            'subcategory': self.truncate_string(fields.get('subcategory'), 2000),
                            'theme': self.truncate_string(fields.get('theme'), 2000),
                            'subtheme': self.truncate_string(fields.get('subtheme'), 2000),
                            'target': self.truncate_string(fields.get('target'), 2000) if fields.get('target') else None,
                            'source': self.truncate_string(fields.get('source'), 2000) if fields.get('source') else None,
                            'detail_id': fields.get('detail_id'),
                            'lng_id': fields.get('lng_id'),
                            'lng_title': self.truncate_string(fields.get('lng_title'), 100),  # Truncate to 100 chars
                            'subject_id': fields.get('subject_id'),
                            'subject_title': self.truncate_string(fields.get('subject_title'), 100),  # Truncate to 100 chars
                            'class_number': fields.get('class_number'),
                            'question_usage': fields.get('question_usage', True)
                        }
                        
                        # Create question with truncated field values
                        question = Question(**question_data)
                        question.save()
                        questions_imported += 1
                        
                        # Create options with truncated text
                        options_data = fields.get('options', [])
                        for option_data in options_data:
                            option = Option(
                                id=option_data.get('id'),
                                question=question,
                                text=self.truncate_string(option_data.get('text', ''), 2000),
                                is_correct=option_data.get('is_correct', False),
                                img=option_data.get('img') if option_data.get('img') else None
                            )
                            option.save()
                            options_imported += 1
                    
                    except Exception as e:
                        # Print detailed error information for debugging
                        self.stdout.write(self.style.ERROR(f"Error importing question {question_id}: {str(e)}"))
                        self.stdout.write(self.style.ERROR(f"Fields: {fields}"))
                        raise  # Re-raise to abort the transaction
                
                # Update test question counts if we imported to a specific product
                if target_product:
                    for test in Test.objects.filter(product=target_product):
                        question_count = Question.objects.filter(test=test).count()
                        test.number_of_questions = question_count
                        test.save()
            
            self.stdout.write(
                self.style.SUCCESS(
                    f'Successfully imported {questions_imported} questions with {options_imported} options. '
                    f'Skipped {questions_skipped} questions.'
                )
            )
            
        except FileNotFoundError:
            raise CommandError(f"File not found: {json_file}")
        except json.JSONDecodeError:
            raise CommandError(f"Invalid JSON format in file: {json_file}")
        except Exception as e:
            # Add more detailed error information
            import traceback
            self.stdout.write(self.style.ERROR(f"Error stack trace: {traceback.format_exc()}"))
            raise CommandError(f"Error importing questions: {str(e)}")

    def truncate_string(self, value, max_length):
        """Truncate a string value to the specified maximum length"""
        if value and isinstance(value, str) and len(value) > max_length:
            self.stdout.write(self.style.WARNING(f'Truncating value from {len(value)} to {max_length} characters'))
            return value[:max_length]
        return value 