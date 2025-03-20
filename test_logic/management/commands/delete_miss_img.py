import os
import requests
from django.core.management.base import BaseCommand
from test_logic.models import Question, Option
from django.conf import settings
from concurrent.futures import ThreadPoolExecutor
import time
from urllib.parse import urlparse
from django.db.models import Q
from django.db import transaction

class Command(BaseCommand):
    help = 'Delete Questions that have missing images (returning 404)'

    def add_arguments(self, parser):
        parser.add_argument(
            '--product',
            type=str,
            help='Optional product ID to filter questions by product',
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
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Only report what would be deleted without actually deleting',
        )
        parser.add_argument(
            '--batch-size',
            type=int,
            default=100,
            help='Batch size for deletion operations (default: 100)',
        )
        parser.add_argument(
            '--confirm',
            action='store_true',
            help='Skip confirmation prompt',
        )

    def handle(self, *args, **options):
        product_id = options.get('product')
        num_threads = options.get('threads')
        timeout = options.get('timeout')
        check_local = options.get('check_local')
        dry_run = options.get('dry_run')
        batch_size = options.get('batch_size')
        skip_confirmation = options.get('confirm')
        
        # Build base queryset for questions with images
        questions_with_images = Question.objects.exclude(
            Q(img__isnull=True) | Q(img='')
        )
        
        # Apply product filter if specified
        if product_id:
            questions_with_images = questions_with_images.filter(test__product__id=product_id)
            self.stdout.write(f"Filtering by product ID: {product_id}")
        
        # Count total items to check
        questions_count = questions_with_images.count()
        
        if questions_count == 0:
            self.stdout.write(self.style.SUCCESS("No questions with images to check."))
            return
        
        self.stdout.write(f"Found {questions_count} questions with images to check")
        
        # Start timing the operation
        start_time = time.time()
        
        # Create results containers
        missing_question_images = []
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
                    futures.append(executor.submit(check_func, question.img.path if hasattr(question.img, 'path') else None, question))
                else:
                    img_url = self.get_image_url(question.img)
                    futures.append(executor.submit(check_func, img_url, question, timeout_value))
            
            # Process results as they complete
            for future in futures:
                question, missing = future.result()
                processed_count += 1
                
                if missing:
                    missing_question_images.append(question)
                
                # Show progress every 100 items
                if processed_count % 100 == 0 or processed_count == questions_count:
                    progress = (processed_count / questions_count) * 100
                    elapsed = time.time() - start_time
                    self.stdout.write(f"Progress: {processed_count}/{questions_count} questions checked ({progress:.1f}%) - {elapsed:.1f} seconds elapsed")
        
        # Display results
        self.stdout.write("\nResults:")
        self.stdout.write(f"Found {len(missing_question_images)} questions with missing images")
        
        # No questions to delete
        if not missing_question_images:
            self.stdout.write(self.style.SUCCESS("No questions with missing images found. Nothing to delete."))
            return
        
        # Display sample of questions with missing images
        if missing_question_images:
            self.stdout.write("\nSample of questions with missing images that will be deleted:")
            for i, question in enumerate(missing_question_images[:10], 1):
                self.stdout.write(f"  {i}. Question ID: {question.id}")
                self.stdout.write(f"     Image path: {question.img}")
                self.stdout.write(f"     Text: {question.text[:50]}...")
                self.stdout.write(f"     Test: {question.test.title if hasattr(question.test, 'title') else 'Unknown'}")
                options_count = question.options.count()
                self.stdout.write(f"     Options count: {options_count}")
            
            if len(missing_question_images) > 10:
                self.stdout.write(f"  ... and {len(missing_question_images) - 10} more questions")
        
        # If this is a dry run, stop here
        if dry_run:
            self.stdout.write(self.style.WARNING(f"DRY RUN: Would delete {len(missing_question_images)} questions with missing images"))
            total_options = sum(q.options.count() for q in missing_question_images)
            self.stdout.write(self.style.WARNING(f"DRY RUN: This would also delete {total_options} associated options"))
            return
        
        # Ask for confirmation unless --confirm flag was provided
        if not skip_confirmation:
            total_options = sum(q.options.count() for q in missing_question_images)
            confirm = input(f"Are you sure you want to delete {len(missing_question_images)} questions and {total_options} associated options? (yes/no): ")
            if confirm.lower() != 'yes':
                self.stdout.write(self.style.WARNING("Deletion cancelled."))
                return
        
        # Delete questions in batches
        self.stdout.write("\nDeleting questions with missing images...")
        question_ids = [q.id for q in missing_question_images]
        total_to_delete = len(question_ids)
        deleted_count = 0
        options_deleted = 0
        
        # Process in batches
        for i in range(0, total_to_delete, batch_size):
            batch_ids = question_ids[i:i+batch_size]
            
            with transaction.atomic():
                # Count options before deletion for reporting
                batch_questions = Question.objects.filter(id__in=batch_ids)
                batch_options_count = sum(q.options.count() for q in batch_questions)
                options_deleted += batch_options_count
                
                # Delete the questions (cascade will delete options)
                deleted = Question.objects.filter(id__in=batch_ids).delete()[0]
                deleted_count += len(batch_ids)
            
            # Report progress
            progress = (deleted_count / total_to_delete) * 100
            self.stdout.write(f"Progress: {deleted_count}/{total_to_delete} questions deleted ({progress:.1f}%)")
        
        # Final summary
        elapsed_time = time.time() - start_time
        self.stdout.write(self.style.SUCCESS(
            f"\nCompleted: Deleted {deleted_count} questions and {options_deleted} options in {elapsed_time:.1f} seconds"
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

    def check_remote_image(self, img_url, question, timeout):
        """Check if an image URL returns 404"""
        if not img_url:
            return (question, True)  # Consider missing if URL is empty
        
        try:
            # Make a HEAD request only (faster than GET)
            response = requests.head(img_url, timeout=timeout, allow_redirects=True)
            
            # Consider 404 or any 4xx/5xx status as missing
            if response.status_code >= 400:
                return (question, True)  # Image is missing
            
            return (question, False)  # Image exists
            
        except Exception as e:
            # Consider any exception (timeout, connection error, etc.) as missing
            return (question, True)

    def check_local_image(self, img_path, question):
        """Check if an image exists in the local filesystem"""
        if not img_path:
            return (question, True)  # Consider missing if path is empty
        
        try:
            # Check if the file exists
            exists = os.path.isfile(img_path)
            return (question, not exists)  # Return True for missing
            
        except Exception as e:
            # Consider any exception as missing
            return (question, True)