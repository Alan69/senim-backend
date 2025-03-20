from django.core.management.base import BaseCommand
from test_logic.models import Question
from django.db import transaction
import time

class Command(BaseCommand):
    help = 'Deletes questions and their options where question_usage is False'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be deleted without actually deleting',
        )
        parser.add_argument(
            '--batch-size',
            type=int,
            default=1000,
            help='Number of questions to delete in each batch (default: 1000)',
        )
        parser.add_argument(
            '--confirm',
            action='store_true',
            help='Skip confirmation prompt and proceed with deletion',
        )
        parser.add_argument(
            '--product',
            type=str,
            help='Optional product ID to filter questions by product',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        batch_size = options['batch_size']
        skip_confirmation = options['confirm']
        product_id = options.get('product')

        # Build the base queryset
        queryset = Question.objects.filter(question_usage=False)

        # Apply product filter if specified
        if product_id:
            queryset = queryset.filter(test__product__id=product_id)
            self.stdout.write(f"Filtering by product ID: {product_id}")

        # Count total questions to be deleted
        total_count = queryset.count()
        
        if total_count == 0:
            self.stdout.write(self.style.SUCCESS("No unused questions found. Nothing to delete."))
            return

        self.stdout.write(f"Found {total_count} unused questions (question_usage=False)")

        # In dry run mode, show sample of questions
        if dry_run:
            sample_size = min(10, total_count)
            sample_questions = queryset[:sample_size]
            
            self.stdout.write(self.style.WARNING("DRY RUN - These questions would be deleted:"))
            for i, question in enumerate(sample_questions, 1):
                options_count = question.options.count()
                self.stdout.write(f"  {i}. Question ID: {question.id}")
                self.stdout.write(f"     Text: {question.text[:80]}...")
                self.stdout.write(f"     Test: {question.test.title if hasattr(question.test, 'title') else 'Unknown'}")
                self.stdout.write(f"     Options count: {options_count}")
                self.stdout.write(f"     Subject: {question.subject_title or 'Unknown'}")
                self.stdout.write("---")
            
            if total_count > sample_size:
                self.stdout.write(f"... and {total_count - sample_size} more questions")
            
            self.stdout.write(self.style.WARNING(f"DRY RUN - Would delete {total_count} questions with their options"))
            return

        # Ask for confirmation
        if not skip_confirmation:
            confirm = input(f"Are you sure you want to permanently delete {total_count} questions and their options? (yes/no): ")
            if confirm.lower() != 'yes':
                self.stdout.write(self.style.WARNING("Deletion cancelled."))
                return

        # Process in batches for better performance
        processed = 0
        start_time = time.time()
        
        # Get all question IDs
        question_ids = list(queryset.values_list('id', flat=True))
        total_options_deleted = 0
        
        while processed < total_count:
            # Get the next batch of question IDs
            batch_ids = question_ids[processed:processed+batch_size]
            
            # Process this batch
            with transaction.atomic():
                # Get the batch of questions
                batch_questions = Question.objects.filter(id__in=batch_ids)
                
                # Count options before deletion
                options_count = sum(q.options.count() for q in batch_questions)
                total_options_deleted += options_count
                
                # Delete the questions (will cascade delete options)
                deletion_count = batch_questions.delete()[0]
                processed += len(batch_ids)
            
            # Calculate and display progress
            progress = (processed / total_count) * 100
            elapsed = time.time() - start_time
            self.stdout.write(f"Progress: {processed}/{total_count} questions deleted ({progress:.1f}%) - {elapsed:.1f} seconds elapsed")
        
        # Final summary
        self.stdout.write(self.style.SUCCESS(
            f"Successfully deleted {processed} questions and {total_options_deleted} options in {time.time() - start_time:.1f} seconds"
        )) 