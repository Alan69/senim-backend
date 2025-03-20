from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.db.models import F
from django.core.cache import cache
from accounts.models import User, Region
from decimal import Decimal
import time

class Command(BaseCommand):
    help = 'Add balance to users with balance less than 1500, optionally filtered by region'

    def add_arguments(self, parser):
        parser.add_argument('amount', type=float, help='Amount to add to each user\'s balance')
        parser.add_argument('--region-id', type=str, help='Region ID to filter users by (optional)')
        parser.add_argument('--dry-run', action='store_true', help='Show what would be done without making changes')
        parser.add_argument('--batch-size', type=int, default=500, help='Number of users to update in each batch')
        parser.add_argument('--max-balance', type=float, default=1500, help='Maximum balance threshold (default: 1500)')
        parser.add_argument('--reset-cache', action='store_true', help='Reset related cache entries after update')
        
    def handle(self, *args, **options):
        amount = Decimal(str(options['amount']))
        region_id = options['region_id']
        dry_run = options['dry_run']
        batch_size = options['batch_size']
        max_balance = Decimal(str(options['max_balance']))
        reset_cache = options['reset_cache']
        
        if amount <= 0:
            raise CommandError('Amount must be greater than zero')
        
        # Build the base queryset
        queryset = User.objects.filter(is_active=True, balance__lt=max_balance)
        
        # Add region filter if specified
        if region_id:
            try:
                region = Region.objects.get(id=region_id)
                queryset = queryset.filter(region=region)
                self.stdout.write(f"Filtering users by region: {region.name}")
            except Region.DoesNotExist:
                raise CommandError(f"Region with ID {region_id} does not exist")
        
        # Count total users to be updated
        total_users = queryset.count()
        
        if total_users == 0:
            self.stdout.write(self.style.WARNING('No users found matching the criteria'))
            return
        
        self.stdout.write(f"Found {total_users} users with balance < {max_balance}")
        
        if dry_run:
            self.stdout.write(self.style.WARNING(f"DRY RUN: Would add {amount} to {total_users} users"))
            return
        
        # Process in batches for better performance
        processed = 0
        start_time = time.time()
        
        # Get all user IDs first
        user_ids = list(queryset.values_list('id', flat=True))
        
        while processed < total_users:
            # Get the next batch of user IDs
            batch_ids = user_ids[processed:processed+batch_size]
            
            # Update in a transaction for data consistency
            with transaction.atomic():
                # Use a new queryset with the batch IDs
                updated_count = User.objects.filter(id__in=batch_ids).update(balance=F('balance') + amount)
                processed += len(batch_ids)
            
            # Calculate and display progress
            progress = (processed / total_users) * 100
            elapsed = time.time() - start_time
            self.stdout.write(f"Progress: {processed}/{total_users} users updated ({progress:.1f}%) - {elapsed:.1f} seconds elapsed")
        
        self.stdout.write(self.style.SUCCESS(f"Successfully added {amount} to balance of {processed} users")) 