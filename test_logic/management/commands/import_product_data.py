import json
import os
import uuid
import requests
import re
from datetime import datetime
from django.core.management.base import BaseCommand
from django.core.files.base import ContentFile
from django.conf import settings
from test_logic.models import Product, Test, Question, Option
from django.utils.dateparse import parse_date
from bs4 import BeautifulSoup


class Command(BaseCommand):
    help = 'Import product, tests, and questions from a JSON file'

    def add_arguments(self, parser):
        parser.add_argument('json_file', type=str, help='Path to the JSON file')
        parser.add_argument('--media-dir', type=str, help='Directory to save media files', default='media')
        parser.add_argument('--download-missing', action='store_true', help='Download missing images from a base URL')
        parser.add_argument('--base-url', type=str, help='Base URL for downloading missing images', default='')
        parser.add_argument('--extract-html-images', action='store_true', help='Extract and process images from HTML content')
        parser.add_argument('--clean-html', action='store_true', help='Clean HTML content by removing unwanted tags')
        parser.add_argument('--preserve-tags', type=str, help='Comma-separated list of HTML tags to preserve when cleaning', default='p,strong,em,br,img,sup,sub,span')

    def handle(self, *args, **options):
        json_file_path = options['json_file']
        media_dir = options['media_dir']
        download_missing = options.get('download_missing', False)
        base_url = options.get('base_url', '')
        extract_html_images = options.get('extract_html_images', False)
        clean_html = options.get('clean_html', False)
        preserve_tags = options.get('preserve_tags', 'p,strong,em,br,img,sup,sub,span').split(',')
        
        self.stdout.write(f"Starting import from {json_file_path}")
        self.stdout.write(f"Media directory: {media_dir}")
        self.stdout.write(f"Download missing: {download_missing}")
        self.stdout.write(f"Base URL: {base_url}")
        self.stdout.write(f"Extract HTML images: {extract_html_images}")
        self.stdout.write(f"Clean HTML: {clean_html}")
        self.stdout.write(f"Preserve tags: {preserve_tags}")
        
        # Ensure media directory exists
        os.makedirs(media_dir, exist_ok=True)
        self.stdout.write(f"Created/verified media directory: {media_dir}")
        
        # Ensure images directory exists
        images_dir = os.path.join(media_dir, 'images')
        os.makedirs(images_dir, exist_ok=True)
        self.stdout.write(f"Created/verified images directory: {images_dir}")
        
        # List existing images to help with debugging
        self.stdout.write("Existing images:")
        try:
            for file in os.listdir(images_dir):
                self.stdout.write(f"  - {file}")
        except Exception as e:
            self.stdout.write(self.style.WARNING(f"Error listing images: {e}"))
        
        try:
            with open(json_file_path, 'r', encoding='utf-8') as file:
                data = json.load(file)
                self.stdout.write(f"Successfully loaded JSON data from {json_file_path}")
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Error reading JSON file: {e}'))
            return
        
        # Process product data
        try:
            product = self.import_product(data.get('product', {}))
            if product:
                self.stdout.write(self.style.SUCCESS(f'Product imported successfully: {product.title}'))
            else:
                self.stdout.write(self.style.WARNING('No product data found or import failed'))
            
            # Process tests data
            tests_data = data.get('tests', [])
            self.stdout.write(f"Found {len(tests_data)} tests to import")
            imported_tests = 0
            for test_data in tests_data:
                test = self.import_test(test_data)
                if test:
                    imported_tests += 1
            self.stdout.write(self.style.SUCCESS(f'{imported_tests} tests imported successfully'))
            
            # Process questions data
            questions_data = data.get('questions', [])
            self.stdout.write(f"Found {len(questions_data)} questions to import")
            imported_questions = 0
            for question_data in questions_data:
                question = self.import_question(question_data, media_dir, download_missing, base_url)
                if question:
                    imported_questions += 1
            self.stdout.write(self.style.SUCCESS(f'{imported_questions} questions imported successfully'))
            
            # Process options data
            options_data = data.get('options', [])
            self.stdout.write(f"Found {len(options_data)} options to import")
            imported_options = 0
            for option_data in options_data:
                option = self.import_option(option_data, media_dir, download_missing, base_url)
                if option:
                    imported_options += 1
            self.stdout.write(self.style.SUCCESS(f'{imported_options} options imported successfully'))
            
            # Summary
            self.stdout.write("\nImport Summary:")
            self.stdout.write(f"Products: {1 if product else 0}")
            self.stdout.write(f"Tests: {imported_tests}/{len(tests_data)}")
            self.stdout.write(f"Questions: {imported_questions}/{len(questions_data)}")
            self.stdout.write(f"Options: {imported_options}/{len(options_data)}")
            
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Error importing data: {e}'))
            import traceback
            self.stdout.write(traceback.format_exc())
    
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
    
    def clean_image_path(self, img_path):
        """Clean image path by removing timestamps and other unwanted parts"""
        if not img_path or img_path == 'null' or img_path == '':
            return None
            
        # Extract the UUID part from the path if it exists
        uuid_pattern = r'([0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})'
        uuid_match = re.search(uuid_pattern, img_path)
        
        if uuid_match:
            uuid_str = uuid_match.group(1)
            # Get the file extension
            ext_match = re.search(r'\.([a-zA-Z0-9]+)', img_path)
            if ext_match:
                ext = ext_match.group(0)  # Include the dot
                # Create a clean path with just the UUID and extension
                clean_path = f"images/{uuid_str}{ext}"
                return clean_path
        
        # If no UUID found or couldn't extract extension, try the original approach
        # Remove timestamp from image path (e.g., .jpg1490335623040 -> .jpg)
        img_path = re.sub(r'(\.(jpg|png|gif|jpeg))\d+', r'\1', img_path)
        
        # Remove 'media/' prefix if present
        if img_path.startswith('media/'):
            img_path = img_path[6:]
            
        return img_path
        
    def get_clean_filename(self, img_path):
        """Get a clean filename without timestamps for saving to media directory"""
        if not img_path:
            return None
            
        # Extract the base filename
        base_name = os.path.basename(img_path)
        
        # Remove timestamp from filename (e.g., image.jpg1490335623040 -> image.jpg)
        clean_name = re.sub(r'(\.(jpg|png|gif|jpeg))\d+', r'\1', base_name)
        
        # Extract UUID if present
        uuid_pattern = r'([0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})'
        uuid_match = re.search(uuid_pattern, clean_name)
        
        if uuid_match:
            uuid_str = uuid_match.group(1)
            # Get the file extension
            ext_match = re.search(r'\.([a-zA-Z0-9]+)', clean_name)
            if ext_match:
                ext = ext_match.group(0)  # Include the dot
                # Create a clean filename with just the UUID and extension
                return f"{uuid_str}{ext}"
        
        return clean_name

    def handle_image(self, model_instance, img_field_name, img_path, media_dir, download_missing, base_url):
        """Handle image for a model instance"""
        if not img_path or img_path == 'null' or img_path == '':
            return
            
        self.stdout.write(f"Processing image: {img_path}")
            
        # Clean the image path
        clean_path = self.clean_image_path(img_path)
        if not clean_path:
            self.stdout.write(self.style.WARNING(f"Could not clean image path: {img_path}"))
            return
            
        self.stdout.write(f"Cleaned image path: {clean_path}")
        
        # Get a clean filename for saving
        clean_filename = self.get_clean_filename(img_path)
        self.stdout.write(f"Clean filename for saving: {clean_filename}")
            
        # Get the image field
        img_field = getattr(model_instance, img_field_name)
        
        # Handle remote images
        if clean_path.startswith('http'):
            try:
                response = requests.get(clean_path)
                if response.status_code == 200:
                    img_field.save(clean_filename, ContentFile(response.content), save=False)
                    self.stdout.write(self.style.SUCCESS(f'Downloaded image from {clean_path}'))
                else:
                    self.stdout.write(self.style.WARNING(f'Failed to download image from {clean_path}: {response.status_code}'))
            except Exception as e:
                self.stdout.write(self.style.WARNING(f'Error downloading image {clean_path}: {e}'))
        else:
            # Handle local images
            local_path = os.path.join(media_dir, clean_path)
            self.stdout.write(f"Looking for image at: {local_path}")
            
            # Check if the file exists
            if os.path.exists(local_path):
                with open(local_path, 'rb') as img_file:
                    img_field.save(clean_filename, ContentFile(img_file.read()), save=False)
                    self.stdout.write(self.style.SUCCESS(f'Loaded image from {local_path}'))
            elif download_missing and base_url:
                # Try to download the missing image
                try:
                    # Try with the clean path
                    img_url = f"{base_url.rstrip('/')}/{clean_path}"
                    self.stdout.write(f"Attempting to download from: {img_url}")
                    response = requests.get(img_url)
                    
                    # If that fails, try with just the filename
                    if response.status_code != 200:
                        img_name = os.path.basename(clean_path)
                        img_url = f"{base_url.rstrip('/')}/{img_name}"
                        self.stdout.write(f"Retrying with: {img_url}")
                        response = requests.get(img_url)
                    
                    if response.status_code == 200:
                        # Save the downloaded image to the media directory
                        os.makedirs(os.path.dirname(local_path), exist_ok=True)
                        with open(local_path, 'wb') as f:
                            f.write(response.content)
                            
                        # Save to the model
                        img_field.save(clean_filename, ContentFile(response.content), save=False)
                        self.stdout.write(self.style.SUCCESS(f'Downloaded missing image from {img_url}'))
                    else:
                        self.stdout.write(self.style.WARNING(f'Failed to download missing image from {img_url}: {response.status_code}'))
                        
                        # As a last resort, try to find a file with the same UUID in the media directory
                        uuid_pattern = r'([0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})'
                        uuid_match = re.search(uuid_pattern, clean_path)
                        
                        if uuid_match:
                            uuid_str = uuid_match.group(1)
                            self.stdout.write(f"Looking for any file with UUID: {uuid_str}")
                            
                            # Look for any file with this UUID in the media directory
                            for root, dirs, files in os.walk(media_dir):
                                for file in files:
                                    if uuid_str in file:
                                        file_path = os.path.join(root, file)
                                        self.stdout.write(f"Found matching file: {file_path}")
                                        
                                        with open(file_path, 'rb') as img_file:
                                            img_field.save(clean_filename, ContentFile(img_file.read()), save=False)
                                            self.stdout.write(self.style.SUCCESS(f'Used existing file with matching UUID: {file_path}'))
                                            return
                except Exception as e:
                    self.stdout.write(self.style.WARNING(f'Error downloading missing image {img_url}: {e}'))
            else:
                self.stdout.write(self.style.WARNING(f'Image file not found: {local_path}'))
                
                # Try to find a file with the same UUID in the media directory
                uuid_pattern = r'([0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})'
                uuid_match = re.search(uuid_pattern, clean_path)
                
                if uuid_match:
                    uuid_str = uuid_match.group(1)
                    self.stdout.write(f"Looking for any file with UUID: {uuid_str}")
                    
                    # Look for any file with this UUID in the media directory
                    for root, dirs, files in os.walk(media_dir):
                        for file in files:
                            if uuid_str in file:
                                file_path = os.path.join(root, file)
                                self.stdout.write(f"Found matching file: {file_path}")
                                
                                with open(file_path, 'rb') as img_file:
                                    img_field.save(clean_filename, ContentFile(img_file.read()), save=False)
                                    self.stdout.write(self.style.SUCCESS(f'Used existing file with matching UUID: {file_path}'))
                                    return
    
    def import_question(self, question_data, media_dir, download_missing=False, base_url=''):
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
        
        # Check if image is required and exists
        img_path = question_data.get('img')
        if img_path and img_path != 'null' and img_path != '':
            # Clean the image path
            clean_path = self.clean_image_path(img_path)
            if not clean_path:
                self.stdout.write(self.style.WARNING(f"Could not clean image path: {img_path}, skipping question"))
                return None
                
            # Check if the image exists
            local_path = os.path.join(media_dir, clean_path)
            if not os.path.exists(local_path) and not download_missing:
                self.stdout.write(self.style.WARNING(f"Image file not found: {local_path}, skipping question"))
                return None
        
        # Try to get existing question or create a new one
        try:
            question = Question.objects.get(id=question_id)
            self.stdout.write(self.style.SUCCESS(f'Found existing question: {question_id}'))
        except Question.DoesNotExist:
            question = Question(id=question_id)
            self.stdout.write(self.style.SUCCESS(f'Creating new question with ID: {question_id}'))
        
        # Clean HTML content from text fields
        for field in ['text', 'text2', 'text3']:
            self.clean_html_content(question_data, field, ['p', 'strong', 'em', 'br', 'img', 'sup', 'sub', 'span'])
        
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
        if img_path and img_path != 'null' and img_path != '':
            self.handle_image(question, 'img', img_path, media_dir, download_missing, base_url)
        
        question.save()
        return question
        
    def import_option(self, option_data, media_dir, download_missing=False, base_url=''):
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
        
        # Check if image is required and exists
        img_path = option_data.get('img')
        if img_path and img_path != 'null' and img_path != '':
            # Clean the image path
            clean_path = self.clean_image_path(img_path)
            if not clean_path:
                self.stdout.write(self.style.WARNING(f"Could not clean image path: {img_path}, skipping option"))
                return None
                
            # Check if the image exists
            local_path = os.path.join(media_dir, clean_path)
            if not os.path.exists(local_path) and not download_missing:
                self.stdout.write(self.style.WARNING(f"Image file not found: {local_path}, skipping option"))
                return None
        
        # Try to get existing option or create a new one
        try:
            option = Option.objects.get(id=option_id)
            self.stdout.write(self.style.SUCCESS(f'Found existing option: {option_id}'))
        except Option.DoesNotExist:
            option = Option(id=option_id)
            self.stdout.write(self.style.SUCCESS(f'Creating new option with ID: {option_id}'))
        
        # Clean HTML content from text field
        self.clean_html_content(option_data, 'text', ['p', 'strong', 'em', 'br', 'img', 'sup', 'sub', 'span'])
        
        # Update option fields
        option.question = question
        option.text = option_data.get('text', option.text)
        option.is_correct = option_data.get('is_correct', option.is_correct)
        
        # Handle image if provided
        if img_path and img_path != 'null' and img_path != '':
            self.handle_image(option, 'img', img_path, media_dir, download_missing, base_url)
        
        option.save()
        return option
    
    def clean_html_content(self, data, field_name, preserve_tags):
        """Clean HTML content by removing unwanted tags"""
        html_content = data.get(field_name)
        if not html_content:
            return
            
        try:
            # Parse the HTML content
            soup = BeautifulSoup(html_content, 'html.parser')
            
            # Remove script and style tags
            for script in soup(["script", "style"]):
                script.decompose()
                
            # Remove all tags except those in preserve_tags
            for tag in soup.find_all():
                if tag.name not in preserve_tags:
                    tag.unwrap()
            
            # Convert the soup back to a string
            clean_content = str(soup)
            
            # Update the data
            data[field_name] = clean_content
            self.stdout.write(self.style.SUCCESS(f'Cleaned HTML content in {field_name}'))
        except Exception as e:
            self.stdout.write(self.style.WARNING(f'Error cleaning HTML content: {e}'))
            
    def extract_images_from_html(self, data, field_name, media_dir, download_missing, base_url):
        """Extract images from HTML content and process them"""
        html_content = data.get(field_name)
        if not html_content:
            return
            
        try:
            soup = BeautifulSoup(html_content, 'html.parser')
            img_tags = soup.find_all('img')
            
            for img in img_tags:
                src = img.get('src')
                if src:
                    self.stdout.write(f"Found image in HTML: {src}")
                    
                    # Clean the image path
                    clean_path = self.clean_image_path(src)
                    if not clean_path:
                        continue
                        
                    # Get a clean filename for saving
                    clean_filename = self.get_clean_filename(src)
                    self.stdout.write(f"Clean filename for HTML image: {clean_filename}")
                        
                    # Process the image
                    local_path = os.path.join(media_dir, clean_path)
                    
                    # Check if the file exists
                    if not os.path.exists(local_path) and download_missing and base_url:
                        # Try to download the missing image
                        try:
                            img_url = f"{base_url.rstrip('/')}/{clean_path}"
                            self.stdout.write(f"Attempting to download HTML image from: {img_url}")
                            response = requests.get(img_url)
                            
                            # If that fails, try with just the filename
                            if response.status_code != 200:
                                img_name = os.path.basename(clean_path)
                                img_url = f"{base_url.rstrip('/')}/{img_name}"
                                self.stdout.write(f"Retrying with: {img_url}")
                                response = requests.get(img_url)
                            
                            if response.status_code == 200:
                                # Save the downloaded image to the media directory
                                os.makedirs(os.path.dirname(local_path), exist_ok=True)
                                with open(local_path, 'wb') as f:
                                    f.write(response.content)
                                self.stdout.write(self.style.SUCCESS(f'Downloaded HTML image to {local_path}'))
                                
                                # Update the src attribute in the HTML
                                img['src'] = f'media/{clean_path}'
                            else:
                                self.stdout.write(self.style.WARNING(f'Failed to download HTML image from {img_url}: {response.status_code}'))
                        except Exception as e:
                            self.stdout.write(self.style.WARNING(f'Error downloading HTML image {img_url}: {e}'))
                    elif os.path.exists(local_path):
                        # Update the src attribute in the HTML
                        img['src'] = f'media/{clean_path}'
                        self.stdout.write(self.style.SUCCESS(f'Updated HTML image path to {img["src"]}'))
                    
            # Update the HTML content in the data
            data[field_name] = str(soup)
            self.stdout.write(self.style.SUCCESS(f'Updated HTML content with clean image paths'))
        except Exception as e:
            self.stdout.write(self.style.WARNING(f'Error extracting images from HTML: {e}')) 