import os
import json
import requests
import uuid
import re
from bs4 import BeautifulSoup
from urllib.parse import urlparse, urljoin
from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand
from test_logic.models import Question, Option, Test
from django.conf import settings


class Command(BaseCommand):
    help = 'Import questions from a JSON file'

    def add_arguments(self, parser):
        parser.add_argument('json_file', type=str)
        parser.add_argument('--base-url', type=str, default='https://api.sapatest.com', 
                           help='Base URL for resolving relative image paths')
        parser.add_argument('--test-id', type=str, 
                           help='UUID of the test to associate questions with')
        parser.add_argument('--test-title', type=str, 
                           help='Title of the test to associate questions with (will use first match)')

    def handle(self, *args, **kwargs):
        json_file = kwargs['json_file']
        self.base_url = kwargs.get('base_url', 'https://api.sapatest.com')
        test_id = kwargs.get('test_id')
        test_title = kwargs.get('test_title')
        
        self.stdout.write(f"Using base URL: {self.base_url}")

        # Get the test to associate questions with
        test = None
        if test_id:
            try:
                test = Test.objects.get(id=test_id)
                self.stdout.write(self.style.SUCCESS(f"Using test with ID: {test_id}"))
            except Test.DoesNotExist:
                self.stdout.write(self.style.ERROR(f'Test with ID {test_id} does not exist.'))
                return
        elif test_title:
            try:
                test = Test.objects.filter(title__icontains=test_title).first()
                if test:
                    self.stdout.write(self.style.SUCCESS(f"Using test with title: {test.title} (ID: {test.id})"))
                else:
                    self.stdout.write(self.style.ERROR(f'No test found with title containing: {test_title}'))
                    return
            except Exception as e:
                self.stdout.write(self.style.ERROR(f'Error finding test by title: {e}'))
                return
        else:
            # List available tests and let the user choose
            tests = Test.objects.all().order_by('title')
            if not tests.exists():
                self.stdout.write(self.style.ERROR('No tests found in the database. Please create a test first.'))
                return
                
            self.stdout.write(self.style.SUCCESS('Available tests:'))
            for i, t in enumerate(tests):
                self.stdout.write(f"{i+1}. {t.title} (ID: {t.id})")
                
            try:
                choice = input("Enter the number of the test or the full UUID (or 'q' to quit): ")
                if choice.lower() == 'q':
                    return
                
                # First try to interpret the choice as a UUID
                try:
                    test = Test.objects.get(id=choice)
                    self.stdout.write(self.style.SUCCESS(f"Using test with ID: {test.id}"))
                except (Test.DoesNotExist, ValueError):
                    # If that fails, try to interpret it as a number
                    try:
                        choice_idx = int(choice) - 1
                        if 0 <= choice_idx < len(tests):
                            test = tests[choice_idx]
                            self.stdout.write(self.style.SUCCESS(f"Using test: {test.title} (ID: {test.id})"))
                        else:
                            self.stdout.write(self.style.ERROR(f'Invalid choice: {choice}'))
                            return
                    except ValueError:
                        self.stdout.write(self.style.ERROR(f'Invalid input: {choice}. Please enter a number or a valid UUID.'))
                        return
            except Exception as e:
                self.stdout.write(self.style.ERROR(f'Error selecting test: {e}'))
                return

        try:
            with open(json_file, 'r', encoding='utf-8') as file:
                data = json.load(file)
        except (UnicodeDecodeError, FileNotFoundError) as e:
            self.stdout.write(self.style.ERROR(f'Error reading file: {e}'))
            return

        for item in data:
            # Process question text and extract images
            question_text, question_img_path = self.process_html(item.get('question'))

            # Create the question object
            question = Question(
                test=test,
                text=question_text,
                task_type=item.get('task_type'),
                level=item.get('level'),
                status=item.get('status'),
                category=item.get('category'),
                subcategory=item.get('subcategory'),
                theme=item.get('theme'),
                subtheme=item.get('subtheme'),
                target=item.get('target'),
                source=item.get('source'),
                detail_id=item.get('detail_id'),
                lng_id=item.get('lng_id'),
                lng_title=item.get('lng_title'),
                subject_id=item.get('subject_id'),
                subject_title=item.get('subject_title'),
                class_number=item.get('class')
            )
            
            # Save the question to get an ID
            question.save()
            
            # If we have an image path, set the img field
            if question_img_path:
                # The img field is an ImageField, so we need to set it to the path relative to MEDIA_ROOT
                question.img = question_img_path
                question.save()
                self.stdout.write(self.style.SUCCESS(f'Saved question image: {question_img_path}'))

            # Process answer options
            answers = json.loads(item.get('answers', "[]"))  # Ensure it's a list
            options = {
                'var1': item.get('var1'),
                'var2': item.get('var2'),
                'var3': item.get('var3'),
                'var4': item.get('var4'),
                'var5': item.get('var5'),
                'var6': item.get('var6'),
                'var7': item.get('var7'),
                'var8': item.get('var8'),
                'var9': item.get('var9'),
                'var10': item.get('var10'),
                'var11': item.get('var11'),
                'var12': item.get('var12'),
            }

            for idx, (key, value) in enumerate(options.items()):
                if value:
                    option_text, option_img_path = self.process_html(value)

                    # Create the option object
                    option = Option(
                        question=question,
                        text=option_text,
                        is_correct=(idx + 1) in answers  # Match option index with correct answer index
                    )
                    
                    # Save the option to get an ID
                    option.save()
                    
                    # If we have an image path, set the img field
                    if option_img_path:
                        # The img field is an ImageField, so we need to set it to the path relative to MEDIA_ROOT
                        option.img = option_img_path
                        option.save()
                        self.stdout.write(self.style.SUCCESS(f'Saved option image: {option_img_path}'))

        self.stdout.write(self.style.SUCCESS('Successfully imported questions'))

    def process_html(self, html_content):
        """Extract image from HTML, download it, and return new HTML and image path"""
        if not html_content:
            return "", None

        # Special case for the format shown in the screenshot
        # Example: <p>Предельный угол полного внутреннего отражения на границе стекло – жидкость <img src="/public/uploaded/RG3xH8zBh3jmXq3lWM2YWWRQmcDauTXBwXkAwC.png" style="height:24px; width:80px"> Если показатель преломления стекла n=1,5, то показатель преломления жидкости равен <img src="/public/uploaded/blaUizZ2D2ZflWyFDolRRjpanl3jgW2HQ0xKQHbx.png" style="height:24px; width:124px"></p>
        img_urls = []
        img_paths = []
        
        # Look for patterns like <img src="..." style="..."> in the HTML content
        img_pattern = re.compile(r'<img\s+src=["\']([^"\']+)["\'].*?>')
        for match in img_pattern.finditer(html_content):
            img_url = match.group(1)
            # Handle relative URLs
            if img_url.startswith('/'):
                # Make sure we include /media in the path if it's not already there
                if not img_url.startswith('/media/') and not img_url.startswith('/static/'):
                    img_url = f'/media{img_url}'
                img_url = urljoin(self.base_url, img_url)
                
            if self.is_image_url(img_url):
                self.stdout.write(f"Found image URL in HTML: {img_url}")
                img_urls.append(img_url)
                new_img_name, new_img_path = self.download_image(img_url)
                if new_img_name:
                    img_path = f'public/uploaded/{new_img_name}'
                    img_paths.append(img_path)
                    # Replace the URL in the HTML content
                    html_content = html_content.replace(match.group(1), f'/media/{img_path}')
        
        # If we found images in the special case, use the first one for the img field
        if img_paths:
            img_path = img_paths[0]
            self.stdout.write(f"Using image path for model: {img_path}")
        else:
            # If no special case, proceed with the regular extraction
            img_path = None
            
            # First, try to extract image URL directly from the HTML content
            img_src_pattern = re.compile(r'src=["\']([^"\']+)["\']')
            match = img_src_pattern.search(html_content)
            if match:
                img_url = match.group(1)
                # Handle relative URLs
                if img_url.startswith('/'):
                    # Make sure we include /media in the path if it's not already there
                    if not img_url.startswith('/media/') and not img_url.startswith('/static/'):
                        img_url = f'/media{img_url}'
                    img_url = urljoin(self.base_url, img_url)
                    
                if self.is_image_url(img_url):
                    new_img_name, new_img_path = self.download_image(img_url)
                    if new_img_name:
                        img_path = f'public/uploaded/{new_img_name}'
            
            # Now parse the HTML with BeautifulSoup
            soup = BeautifulSoup(html_content, "html.parser")
            
            # If we didn't find an image URL directly, try to find it in the HTML structure
            if not img_path:
                # Check for img tags
                img_tag = soup.find('img')
                
                # If no img tag found, check for a tags that might contain image references
                if not img_tag:
                    a_tags = soup.find_all('a')
                    for a_tag in a_tags:
                        # Check if the a tag has an src attribute (which might contain image URL)
                        if a_tag.get('src'):
                            img_url = a_tag.get('src')
                            # Handle relative URLs
                            if img_url.startswith('/'):
                                # Make sure we include /media in the path if it's not already there
                                if not img_url.startswith('/media/') and not img_url.startswith('/static/'):
                                    img_url = f'/media{img_url}'
                                img_url = urljoin(self.base_url, img_url)
                                
                            if self.is_image_url(img_url):
                                # Create a new img tag to replace the a tag
                                new_img = soup.new_tag('img')
                                new_img['src'] = img_url
                                a_tag.replace_with(new_img)
                                img_tag = new_img
                                break
                                
                        # Check if the a tag has an href attribute that points to an image
                        elif a_tag.get('href'):
                            img_url = a_tag.get('href')
                            # Handle relative URLs
                            if img_url.startswith('/'):
                                # Make sure we include /media in the path if it's not already there
                                if not img_url.startswith('/media/') and not img_url.startswith('/static/'):
                                    img_url = f'/media{img_url}'
                                img_url = urljoin(self.base_url, img_url)
                                
                            if self.is_image_url(img_url):
                                # Create a new img tag to replace the a tag
                                new_img = soup.new_tag('img')
                                new_img['src'] = img_url
                                a_tag.replace_with(new_img)
                                img_tag = new_img
                                break
                
                # Process the image if found
                if img_tag and img_tag.get('src'):
                    img_url = img_tag['src']
                    # Handle relative URLs
                    if img_url.startswith('/'):
                        # Make sure we include /media in the path if it's not already there
                        if not img_url.startswith('/media/') and not img_url.startswith('/static/'):
                            img_url = f'/media{img_url}'
                        img_url = urljoin(self.base_url, img_url)
                        self.stdout.write(f"Converted relative URL to: {img_url}")
                    
                    new_img_name, new_img_path = self.download_image(img_url)
                    if new_img_name:
                        img_path = f'public/uploaded/{new_img_name}'
                        img_tag['src'] = f'/media/{img_path}'
        
        # Extract text content without HTML tags for the text field
        # Parse the HTML with BeautifulSoup to get clean text
        soup = BeautifulSoup(html_content, "html.parser")
        # Remove img tags before getting text to avoid including image URLs in the text
        for tag in soup.find_all('img'):
            tag.decompose()
        text_content = soup.get_text(strip=True)
        
        # Log the extraction results for debugging
        self.stdout.write(f"Extracted text: {text_content[:50]}...")
        if img_path:
            self.stdout.write(f"Extracted image: {img_path}")
        else:
            self.stdout.write("No image extracted")
            
        return text_content, img_path

    def is_image_url(self, url):
        """Check if a URL points to an image file"""
        if not url:
            return False
            
        # Check if URL ends with common image extensions
        image_extensions = ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp']
        parsed_url = urlparse(url)
        path = parsed_url.path.lower()
        
        return any(path.endswith(ext) for ext in image_extensions)

    def download_image(self, img_url):
        """Download image and save it to Django media folder"""
        if not img_url:
            return None, None

        # Use the correct media path structure
        base_path = os.path.join(settings.MEDIA_ROOT, 'public', 'uploaded')
        os.makedirs(base_path, exist_ok=True)

        # Check if this is a URL from our production server
        if 'api.sapatest.com' in img_url and '/media/' in img_url:
            # This is a production image, try to download it
            self.stdout.write(f"Downloading production image from: {img_url}")
            try:
                # Add a timeout to avoid hanging
                response = requests.get(img_url, stream=True, timeout=10)
                response.raise_for_status()
                
                # Check if the response is actually an image
                content_type = response.headers.get('Content-Type', '')
                if not content_type.startswith('image/'):
                    self.stdout.write(self.style.WARNING(f'URL does not return an image: {img_url}'))
                    return None, None
                
                # Determine file extension from content type
                extension = self.get_extension_from_content_type(content_type)
                img_name = f"{uuid.uuid4().hex}{extension}"
                img_path = os.path.join(base_path, img_name)

                with open(img_path, 'wb') as img_file:
                    for chunk in response.iter_content(1024):
                        img_file.write(chunk)

                self.stdout.write(self.style.SUCCESS(f'Successfully downloaded production image to: {img_path}'))
                return img_name, img_path
                
            except requests.exceptions.RequestException as e:
                self.stdout.write(self.style.ERROR(f'Error downloading production image: {e}'))
                return None, None
        
        # Check if this is a local URL from our own media
        elif self.base_url in img_url and '/media/' in img_url:
            # This is a local image, try to copy it instead of downloading
            try:
                # Extract the path relative to MEDIA_ROOT
                local_path = img_url.split('/media/')[1]
                source_path = os.path.join(settings.MEDIA_ROOT, local_path)
                
                self.stdout.write(f"Checking for local file at: {source_path}")
                
                if os.path.exists(source_path):
                    # Copy the file to our destination
                    import shutil
                    
                    # Get the file extension
                    _, extension = os.path.splitext(source_path)
                    if not extension:
                        extension = '.jpg'  # Default extension
                    
                    img_name = f"{uuid.uuid4().hex}{extension}"
                    dest_path = os.path.join(base_path, img_name)
                    
                    shutil.copy2(source_path, dest_path)
                    self.stdout.write(self.style.SUCCESS(f'Copied local image from {source_path} to {dest_path}'))
                    return img_name, dest_path
                else:
                    self.stdout.write(self.style.WARNING(f'Local image not found: {source_path}'))
            except Exception as e:
                self.stdout.write(self.style.ERROR(f'Error copying local image: {e}'))

        # If not a local or production image, try to download it from the web
        try:
            self.stdout.write(f"Downloading image from web: {img_url}")
            
            # Add a timeout to avoid hanging
            response = requests.get(img_url, stream=True, timeout=10)
            response.raise_for_status()
            
            # Check if the response is actually an image
            content_type = response.headers.get('Content-Type', '')
            if not content_type.startswith('image/'):
                self.stdout.write(self.style.WARNING(f'URL does not return an image: {img_url}'))
                return None, None
                
        except requests.exceptions.RequestException as e:
            self.stdout.write(self.style.ERROR(f'Error downloading image: {e}'))
            
            # If the URL is a local file path, try to access it directly
            if img_url.startswith('file://'):
                try:
                    file_path = img_url[7:]  # Remove 'file://' prefix
                    if os.path.exists(file_path):
                        import shutil
                        
                        # Get the file extension
                        _, extension = os.path.splitext(file_path)
                        if not extension:
                            extension = '.jpg'  # Default extension
                        
                        img_name = f"{uuid.uuid4().hex}{extension}"
                        dest_path = os.path.join(base_path, img_name)
                        
                        shutil.copy2(file_path, dest_path)
                        self.stdout.write(self.style.SUCCESS(f'Copied local file from {file_path} to {dest_path}'))
                        return img_name, dest_path
                except Exception as e:
                    self.stdout.write(self.style.ERROR(f'Error copying local file: {e}'))
            
            return None, None

        # Determine file extension from content type
        extension = self.get_extension_from_content_type(content_type)
        img_name = f"{uuid.uuid4().hex}{extension}"
        img_path = os.path.join(base_path, img_name)

        with open(img_path, 'wb') as img_file:
            for chunk in response.iter_content(1024):
                img_file.write(chunk)

        self.stdout.write(self.style.SUCCESS(f'Successfully downloaded image to: {img_path}'))
        # Return the path relative to MEDIA_ROOT for saving to the model
        return img_name, img_path
        
    def get_extension_from_content_type(self, content_type):
        """Get file extension from content type"""
        content_type_to_extension = {
            'image/jpeg': '.jpg',
            'image/png': '.png',
            'image/gif': '.gif',
            'image/bmp': '.bmp',
            'image/webp': '.webp'
        }
        return content_type_to_extension.get(content_type, '.jpg')  # Default to .jpg
