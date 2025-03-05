from django.core.management.base import BaseCommand, CommandError
import json
import uuid
from test_logic.models import Product, Test, Question, Option

class Command(BaseCommand):
    help = 'Export questions for a specific product ID to a JSON file'

    def add_arguments(self, parser):
        parser.add_argument('product_id', type=str, help='UUID of the product to export questions from')
        parser.add_argument('--output', type=str, default='questions_export.json', help='Output file name')

    def handle(self, *args, **options):
        product_id = options['product_id']
        output_file = options['output']
        
        try:
            # Validate UUID format
            uuid_obj = uuid.UUID(product_id)
            
            # Check if product exists
            try:
                product = Product.objects.get(id=uuid_obj)
            except Product.DoesNotExist:
                raise CommandError(f"Product with ID {product_id} does not exist")
            
            # Get all tests for this product
            tests = Test.objects.filter(product=product)
            
            if not tests.exists():
                self.stdout.write(self.style.WARNING(f"No tests found for product '{product.title}' (ID: {product_id})"))
                return
            
            # Collect all questions and their options
            data = []
            question_count = 0
            
            for test in tests:
                questions = Question.objects.filter(test=test)
                
                for question in questions:
                    options = Option.objects.filter(question=question)
                    
                    question_data = {
                        "model": "test_logic.question",
                        "pk": str(question.id),
                        "fields": {
                            "test": {
                                "id": str(question.test.id),
                                "title": question.test.title
                            },
                            "text": question.text,
                            "img": question.img.url if question.img and question.img.name else None,
                            "task_type": question.task_type,
                            "level": question.level,
                            "status": question.status,
                            "category": question.category,
                            "subcategory": question.subcategory,
                            "theme": question.theme,
                            "subtheme": question.subtheme,
                            "target": question.target,
                            "source": question.source,
                            "detail_id": question.detail_id,
                            "lng_id": question.lng_id,
                            "lng_title": question.lng_title,
                            "subject_id": question.subject_id,
                            "subject_title": question.subject_title,
                            "class_number": question.class_number,
                            "question_usage": question.question_usage,
                            "options": [
                                {
                                    "id": str(option.id),
                                    "text": option.text,
                                    "is_correct": option.is_correct,
                                    "img": option.img.url if option.img and option.img.name else None
                                } for option in options
                            ]
                        }
                    }
                    
                    data.append(question_data)
                    question_count += 1
            
            # Write to JSON file
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            
            self.stdout.write(
                self.style.SUCCESS(
                    f'Successfully exported {question_count} questions from product "{product.title}" (ID: {product_id}) to {output_file}'
                )
            )
            
        except ValueError:
            raise CommandError(f"Invalid UUID format: {product_id}") 