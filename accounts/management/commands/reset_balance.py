from django.core.management.base import BaseCommand
from accounts.models import User
from django.db.models import F
from django.db import transaction

class Command(BaseCommand):
    help = 'Reset balance to zero for all users in the system'

    def add_arguments(self, parser):
        # Optional argument to reset only specific users
        parser.add_argument(
            '--usernames',
            nargs='+',
            help='Optional list of usernames to reset balance for. If not provided, resets balance for all users.',
        )
        
        # Optional argument to set a different amount
        parser.add_argument(
            '--amount',
            type=float,
            default=0.00,
            help='Amount to set balance to (default: 0.00)',
        )
        
        # Add a dry-run option
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be done without actually updating the database',
        )

    def handle(self, *args, **options):
        usernames = options.get('usernames')
        amount = options.get('amount')
        dry_run = options.get('dry_run')
        
        # Build the queryset
        queryset = User.objects.all()
        
        # Filter by usernames if provided
        if usernames:
            queryset = queryset.filter(username__in=usernames)
            self.stdout.write(f"Targeting {queryset.count()} users with specified usernames")
        else:
            self.stdout.write(f"Targeting all {queryset.count()} users")
        
        # Show current balances for selected users
        if dry_run:
            for user in queryset:
                self.stdout.write(f"User: {user.username}, Current balance: {user.balance}")
            self.stdout.write(self.style.WARNING(f"DRY RUN: Would set balance to {amount} for {queryset.count()} users"))
            return
        
        # Perform the update in a transaction
        with transaction.atomic():
            updated_count = queryset.update(balance=amount)
            
            # Log information about the operation
            self.stdout.write(
                self.style.SUCCESS(f"Successfully reset balance to {amount} for {updated_count} users")
            )
            
            # Optional: Log the details of affected users
            for user in queryset:
                self.stdout.write(f"Reset balance for {user.username} ({user.first_name} {user.last_name})") 