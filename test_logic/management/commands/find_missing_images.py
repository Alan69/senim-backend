import os
import requests
from django.core.management.base import BaseCommand
from test_logic.models import Question, Option
from django.conf import settings
from concurrent.futures import ThreadPoolExecutor
import time
from urllib.parse import urlparse
from django.db.models import Q

class Command(BaseCommand):
    help = 'Find Questions and Options where the image file is missing (returns 404)'

    def add_arguments(self, parser):
        parser.add_argument(
            '--product',
            type=str,
            help='Optional product ID to filter questions by product',
        )
        parser.add_argument(
            '--fix',
            action='store_true',
            help='Set img field to NULL for items with missing images',
        )
        parser.add_argument(
            '--threads',
            type=int,
            default=5,
            help='Number of parallel threads to use for checking images (default: 5)',
        )
        parser.add_argument(
            '--timeout',
            type=int,
            default=5,
            help='Timeout in seconds for each image request (default: 5)',
        )
        parser.add_argument(
            '--check-local',
            action='store_true',
            help='Check if images exist in local media directory instead of making HTTP requests',
        )

    def handle(self, *args, **options):
        product_id = options.get('product')
        fix_missing = options.get('fix')
        num_threads = options.get('threads')
        timeout = options.get('timeout')
        check_local = options.get('check_local')
        
        # Build base queryset for questions with images
        questions_with_images = Question.objects.exclude(
            Q(img__isnull=True) | Q(img='')
        )
        
        # Apply product filter if specified
        if product_id:
            questions_with_images = questions_with_images.filter(test__product__id=product_id)
            self.stdout.write(f"Filtering by product ID: {product_id}")
        
        # Build base queryset for options with images
        options_with_images = Option.objects.exclude(
            Q(img__isnull=True) | Q(img='')
        )
        
        # Apply product filter if specified
        if product_id:
            options_with_images = options_with_images.filter(question__test__product__id=product_id)
        
        # Count total items to check
        questions_count = questions_with_images.count()
        options_count = options_with_images.count()
        total_items = questions_count + options_count
        
        if total_items == 0:
            self.stdout.write(self.style.SUCCESS("No images to check."))
            return
        
        self.stdout.write(f"Found {questions_count} questions and {options_count} options with images to check")
        
        # Start timing the operation
        start_time = time.time()
        
        # Create results containers
        missing_question_images = []
        missing_option_images = []
        processed_count = 0
        
        # Define check function based on check mode
        if check_local:
            check_func = self.check_local_image
            media_root = settings.MEDIA_ROOT
            self.stdout.write(f"Checking images in local media directory: {media_root}")
        else:
            check_func = self.check_remote_image
            timeout_value = timeout
            self.stdout.write(f"Checking images via HTTP requests with timeout: {timeout} seconds")
        
        # Process questions with ThreadPoolExecutor
        with ThreadPoolExecutor(max_workers=num_threads) as executor:
            self.stdout.write(f"Checking question images using {num_threads} threads...")
            
            # Process questions
            futures = []
            for question in questions_with_images:
                if check_local:
                    futures.append(executor.submit(check_func, question.img.path if hasattr(question.img, 'path') else None, question, 'question'))
                else:
                    img_url = self.get_image_url(question.img)
                    futures.append(executor.submit(check_func, img_url, question, 'question', timeout_value))
            
            # Process options
            self.stdout.write(f"Checking option images using {num_threads} threads...")
            for option in options_with_images:
                if check_local:
                    futures.append(executor.submit(check_func, option.img.path if hasattr(option.img, 'path') else None, option, 'option'))
                else:
                    img_url = self.get_image_url(option.img)
                    futures.append(executor.submit(check_func, img_url, option, 'option', timeout_value))
            
            # Process results as they complete
            for future in futures:
                result = future.result()
                if result:
                    item_type, item, missing = result
                    processed_count += 1
                    
                    if missing:
                        if item_type == 'question':
                            missing_question_images.append(item)
                        else:
                            missing_option_images.append(item)
                    
                    # Show progress every 100 items
                    if processed_count % 100 == 0 or processed_count == total_items:
                        progress = (processed_count / total_items) * 100
                        elapsed = time.time() - start_time
                        self.stdout.write(f"Progress: {processed_count}/{total_items} items checked ({progress:.1f}%) - {elapsed:.1f} seconds elapsed")
        
        # Display results
        self.stdout.write("\nResults:")
        self.stdout.write(f"Found {len(missing_question_images)} questions with missing images")
        self.stdout.write(f"Found {len(missing_option_images)} options with missing images")
        
        # Display sample of questions with missing images
        if missing_question_images:
            self.stdout.write("\nSample of questions with missing images:")
            for i, question in enumerate(missing_question_images[:10], 1):
                self.stdout.write(f"  {i}. Question ID: {question.id}")
                self.stdout.write(f"     Image path: {question.img}")
                self.stdout.write(f"     Test: {question.test.title if hasattr(question.test, 'title') else 'Unknown'}")
            
            if len(missing_question_images) > 10:
                self.stdout.write(f"  ... and {len(missing_question_images) - 10} more questions")
        
        # Display sample of options with missing images
        if missing_option_images:
            self.stdout.write("\nSample of options with missing images:")
            for i, option in enumerate(missing_option_images[:10], 1):
                self.stdout.write(f"  {i}. Option ID: {option.id}")
                self.stdout.write(f"     Image path: {option.img}")
                self.stdout.write(f"     Question ID: {option.question.id}")
            
            if len(missing_option_images) > 10:
                self.stdout.write(f"  ... and {len(missing_option_images) - 10} more options")
        
        # Fix missing images if requested
        if fix_missing and (missing_question_images or missing_option_images):
            self.stdout.write("\nFixing missing images...")
            
            # Fix questions
            if missing_question_images:
                questions_to_fix = Question.objects.filter(id__in=[q.id for q in missing_question_images])
                fixed_count = questions_to_fix.update(img=None)
                self.stdout.write(self.style.SUCCESS(f"Set img=NULL for {fixed_count} questions"))
            
            # Fix options
            if missing_option_images:
                options_to_fix = Option.objects.filter(id__in=[o.id for o in missing_option_images])
                fixed_count = options_to_fix.update(img=None)
                self.stdout.write(self.style.SUCCESS(f"Set img=NULL for {fixed_count} options"))
        
        # Final summary
        elapsed_time = time.time() - start_time
        self.stdout.write(self.style.SUCCESS(
            f"\nCompleted checking {total_items} items in {elapsed_time:.1f} seconds"
        ))

    def get_image_url(self, img_field):
        """Convert an image field to a fully qualified URL for checking"""
        if not img_field:
            return None
        
        # Use the image URL directly if it's already an absolute URL
        if str(img_field).startswith(('http://', 'https://')):
            return str(img_field)
        
        # Otherwise, join with MEDIA_URL from settings
        media_url = settings.MEDIA_URL or '/media/'
        
        # Handle media URL that might or might not end with slash
        if not media_url.endswith('/'):
            media_url += '/'
        
        # Remove leading slash from image path if present
        img_path = str(img_field)
        if img_path.startswith('/'):
            img_path = img_path[1:]
        
        # Build full URL 
        if media_url.startswith(('http://', 'https://')):
            # If MEDIA_URL is already a full URL
            return f"{media_url.rstrip('/')}/{img_path}"
        else:
            # If MEDIA_URL is relative, use the site domain
            domain = "https://api.sapatest.com"  # Use your site's domain
            return f"{domain.rstrip('/')}/{media_url.strip('/')}/{img_path}"

    def check_remote_image(self, img_url, item, item_type, timeout):
        """Check if an image URL returns 404"""
        if not img_url:
            return (item_type, item, True)  # Consider missing if URL is empty
        
        try:
            # Make a HEAD request only (faster than GET)
            response = requests.head(img_url, timeout=timeout, allow_redirects=True)
            
            # Consider 404 or any 4xx/5xx status as missing
            if response.status_code >= 400:
                return (item_type, item, True)  # Image is missing
            
            return (item_type, item, False)  # Image exists
            
        except Exception as e:
            # Consider any exception (timeout, connection error, etc.) as missing
            return (item_type, item, True)

    def check_local_image(self, img_path, item, item_type):
        """Check if an image exists in the local filesystem"""
        if not img_path:
            return (item_type, item, True)  # Consider missing if path is empty
        
        try:
            # Check if the file exists
            exists = os.path.isfile(img_path)
            return (item_type, item, not exists)  # Return True for missing
            
        except Exception as e:
            # Consider any exception as missing
            return (item_type, item, True) 