from django.core.management.base import BaseCommand
from django.core import serializers
from test_logic.models import Product, Test, Question, Option, CompletedTest, CompletedQuestion
from accounts.models import User, Region

class Command(BaseCommand):
    help = 'Export data from SQLite to JSON for PostgreSQL import'

    def handle(self, *args, **options):
        models = [User, Region, Product, Test, Question, Option, CompletedTest, CompletedQuestion]
        
        for model in models:
            data = serializers.serialize('json', model.objects.all())
            filename = f'fixture_{model.__name__.lower()}.json'
            with open(filename, 'w') as f:
                f.write(data)
            self.stdout.write(self.style.SUCCESS(f'Successfully exported {model.__name__}'))