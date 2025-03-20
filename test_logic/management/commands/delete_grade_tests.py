from django.core.management.base import BaseCommand
from test_logic.models import Test, Question, Option, CompletedTest, CompletedQuestion
from django.db import transaction, models
from django.db.models import Count, Q
import time

class Command(BaseCommand):
    help = 'Delete Tests for specific grades along with all related data'

    def add_arguments(self, parser):
        parser.add_argument(
            '--grades',
            nargs='+',
            type=int,
            default=[5, 6, 7, 8, 10, 11],
            help='List of grade numbers to delete tests for (default: 5 6 7 8 10 11)'
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Only report what would be deleted without actually deleting'
        )
        parser.add_argument(
            '--batch-size',
            type=int,
            default=50,
            help='Batch size for deletion operations (default: 50)'
        )
        parser.add_argument(
            '--confirm',
            action='store_true',
            help='Skip confirmation prompt'
        )
        parser.add_argument(
            '--product',
            type=str,
            help='Optional product ID to filter tests by product'
        )

    def handle(self, *args, **options):
        grades = options.get('grades')
        dry_run = options.get('dry_run')
        batch_size = options.get('batch_size')
        skip_confirmation = options.get('confirm')
        product_id = options.get('product')
        
        # Start timing the operation
        start_time = time.time()
        
        # Build query for tests with specified grades
        tests_to_delete = Test.objects.filter(grade__in=grades)
        
        # Apply product filter if specified
        if product_id:
            tests_to_delete = tests_to_delete.filter(product_id=product_id)
            self.stdout.write(f"Filtering by product ID: {product_id}")
        
        # Count the tests that match our criteria
        tests_count = tests_to_delete.count()
        
        if tests_count == 0:
            self.stdout.write(self.style.SUCCESS(f"No tests found with grades {grades}"))
            return
        
        # Build relationships counts for reporting
        test_ids = list(tests_to_delete.values_list('id', flat=True))
        
        # Count related objects (in batches to avoid memory issues)
        questions_count = 0
        options_count = 0
        completed_tests_count = 0
        completed_questions_count = 0
        
        self.stdout.write(f"Counting related objects for {tests_count} tests...")
        
        # Process in batches for efficiency
        for i in range(0, len(test_ids), batch_size):
            batch_ids = test_ids[i:i+batch_size]
            
            # Count questions and associated options for this batch
            batch_questions = Question.objects.filter(test_id__in=batch_ids)
            batch_questions_count = batch_questions.count()
            questions_count += batch_questions_count
            
            # Count options if there are questions
            if batch_questions_count > 0:
                batch_question_ids = batch_questions.values_list('id', flat=True)
                batch_options_count = Option.objects.filter(question_id__in=batch_question_ids).count()
                options_count += batch_options_count
            
            # Count completed tests containing these tests
            batch_completed_tests = CompletedTest.objects.filter(tests__id__in=batch_ids).distinct()
            batch_completed_tests_count = batch_completed_tests.count()
            completed_tests_count += batch_completed_tests_count
            
            # Count completed questions for this batch
            batch_completed_questions = CompletedQuestion.objects.filter(test_id__in=batch_ids)
            batch_completed_questions_count = batch_completed_questions.count()
            completed_questions_count += batch_completed_questions_count
            
            # Show counting progress for large datasets
            if i % (batch_size * 5) == 0 or i + batch_size >= len(test_ids):
                progress = ((i + min(batch_size, len(test_ids) - i)) / len(test_ids)) * 100
                self.stdout.write(f"Counting progress: {progress:.1f}% complete")
        
        # Display summary of what will be deleted
        self.stdout.write("\nFound items to delete:")
        self.stdout.write(f"  • {tests_count} Tests with grades {grades}")
        self.stdout.write(f"  • {questions_count} Questions belonging to these tests")
        self.stdout.write(f"  • {options_count} Options belonging to these questions")
        self.stdout.write(f"  • {completed_questions_count} CompletedQuestions associated with these tests")
        self.stdout.write(f"  • {completed_tests_count} CompletedTests that include these tests")
        
        # Get sample tests for preview
        sample_tests = tests_to_delete.order_by('?')[:10]  # Random sample
        self.stdout.write("\nSample of Tests that will be deleted:")
        for i, test in enumerate(sample_tests, 1):
            self.stdout.write(f"  {i}. Test ID: {test.id}")
            self.stdout.write(f"     Title: {test.title}")
            self.stdout.write(f"     Grade: {test.grade}")
            self.stdout.write(f"     Product: {test.product.title if hasattr(test.product, 'title') else 'Unknown'}")
            self.stdout.write(f"     Questions count: {Question.objects.filter(test=test).count()}")
        
        if tests_count > 10:
            self.stdout.write(f"  ... and {tests_count - 10} more tests")
        
        # If this is a dry run, stop here
        if dry_run:
            self.stdout.write(self.style.WARNING(f"\nDRY RUN: Would delete {tests_count} tests and all related data"))
            self.stdout.write(self.style.WARNING("No changes have been made to the database"))
            return
        
        # Ask for confirmation unless --confirm flag was provided
        if not skip_confirmation:
            confirm = input(f"\nAre you sure you want to delete {tests_count} tests and all related data? This cannot be undone! (yes/no): ")
            if confirm.lower() != 'yes':
                self.stdout.write(self.style.WARNING("Deletion cancelled."))
                return
        
        # Perform deletions in a specific order to maintain referential integrity
        # and in batches to avoid memory issues
        self.stdout.write("\nBeginning deletion process...")
        
        # 1. First delete CompletedQuestions for these tests
        self.stdout.write("Deleting CompletedQuestions...")
        deleted_completed_questions = 0
        
        for i in range(0, len(test_ids), batch_size):
            batch_ids = test_ids[i:i+batch_size]
            with transaction.atomic():
                count, _ = CompletedQuestion.objects.filter(test_id__in=batch_ids).delete()
                deleted_completed_questions += count
            
            progress = ((i + min(batch_size, len(test_ids) - i)) / len(test_ids)) * 100
            self.stdout.write(f"  Progress: {progress:.1f}% - Deleted {deleted_completed_questions} CompletedQuestions")
        
        # 2. Delete the CompletedTests that only contained these tests
        # We don't delete CompletedTests that might still have other tests
        self.stdout.write("\nDeleting CompletedTests that only contained these tests...")
        deleted_completed_tests = 0
        
        # Find CompletedTests that would be empty after test deletion
        # This requires a subquery to identify tests with no remaining tests
        completed_test_ids_to_delete = (
            CompletedTest.objects.annotate(
                tests_count=Count('tests'),
                target_tests_count=Count('tests', filter=Q(tests__id__in=test_ids))
            )
            .filter(tests_count=models.F('target_tests_count'))
            .values_list('id', flat=True)
        )
        
        # Delete these identified CompletedTests in batches
        completed_test_ids_list = list(completed_test_ids_to_delete)
        for i in range(0, len(completed_test_ids_list), batch_size):
            batch_ids = completed_test_ids_list[i:i+batch_size]
            with transaction.atomic():
                count, _ = CompletedTest.objects.filter(id__in=batch_ids).delete()
                deleted_completed_tests += count
            
            if completed_test_ids_list:
                progress = ((i + min(batch_size, len(completed_test_ids_list) - i)) / len(completed_test_ids_list)) * 100
                self.stdout.write(f"  Progress: {progress:.1f}% - Deleted {deleted_completed_tests} CompletedTests")
        
        # 3. Remove the M2M relationships between remaining CompletedTests and the tests we're deleting
        self.stdout.write("\nRemoving tests from CompletedTests M2M relationships...")
        for i in range(0, len(test_ids), batch_size):
            batch_ids = test_ids[i:i+batch_size]
            count = 0
            with transaction.atomic():
                # For each CompletedTest, remove the tests we're deleting
                for completed_test in CompletedTest.objects.filter(tests__id__in=batch_ids).distinct():
                    count += completed_test.tests.filter(id__in=batch_ids).count()
                    completed_test.tests.remove(*batch_ids)
            
            progress = ((i + min(batch_size, len(test_ids) - i)) / len(test_ids)) * 100
            self.stdout.write(f"  Progress: {progress:.1f}% - Removed {count} test references from CompletedTests")
        
        # 4. Delete Questions and their Options
        self.stdout.write("\nDeleting Questions and Options...")
        deleted_questions = 0
        deleted_options = 0
        
        for i in range(0, len(test_ids), batch_size):
            batch_ids = test_ids[i:i+batch_size]
            with transaction.atomic():
                # Get questions for this batch of tests
                batch_question_ids = Question.objects.filter(test_id__in=batch_ids).values_list('id', flat=True)
                
                # Delete options for these questions
                if batch_question_ids:
                    options_result = Option.objects.filter(question_id__in=batch_question_ids).delete()
                    deleted_options += options_result[0]
                
                # Delete the questions
                questions_result = Question.objects.filter(test_id__in=batch_ids).delete()
                deleted_questions += questions_result[0]
            
            progress = ((i + min(batch_size, len(test_ids) - i)) / len(test_ids)) * 100
            self.stdout.write(f"  Progress: {progress:.1f}% - Deleted {deleted_questions} Questions and {deleted_options} Options")
        
        # 5. Finally delete the Tests
        self.stdout.write("\nDeleting Tests...")
        deleted_tests = 0
        
        for i in range(0, len(test_ids), batch_size):
            batch_ids = test_ids[i:i+batch_size]
            with transaction.atomic():
                test_result = Test.objects.filter(id__in=batch_ids).delete()
                deleted_tests += test_result[0]
            
            progress = ((i + min(batch_size, len(test_ids) - i)) / len(test_ids)) * 100
            self.stdout.write(f"  Progress: {progress:.1f}% - Deleted {deleted_tests} Tests")
        
        # Final summary
        elapsed_time = time.time() - start_time
        self.stdout.write(self.style.SUCCESS(
            f"\nCompleted in {elapsed_time:.1f} seconds:"
        ))
        self.stdout.write(self.style.SUCCESS(
            f"• Deleted {deleted_tests} Tests with grades {grades}"
        ))
        self.stdout.write(self.style.SUCCESS(
            f"• Deleted {deleted_questions} Questions and {deleted_options} Options"
        ))
        self.stdout.write(self.style.SUCCESS(
            f"• Deleted {deleted_completed_questions} CompletedQuestions"
        ))
        self.stdout.write(self.style.SUCCESS(
            f"• Deleted {deleted_completed_tests} CompletedTests"
        ))
        self.stdout.write(self.style.SUCCESS(
            f"• Removed test references from remaining CompletedTests"
        )) 