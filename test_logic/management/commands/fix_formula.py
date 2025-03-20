from django.core.management.base import BaseCommand
from test_logic.models import Question
import re
from django.db.models import Q

class Command(BaseCommand):
    help = 'Fix math formula syntax in questions'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be changed without modifying the database',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        
        # Common formula patterns to fix
        replacements = [
            # Fix incorrect \begin{...} usage
            (r'\\begin\{(\d+\^\w+)\}', r'\1'),
            # Fix incorrect braces
            (r'\\[\(\{](\d+\^\w+)\\[\)\}]', r'\\(\1\\)'),
            # Ensure proper spacing around equals signs
            (r'(\w+)=(\w+)', r'\1 = \2'),
            # Fix common LaTeX command errors
            (r'\\beging', r'\\begin'),
            # Fix missing closing parentheses
            (r'\\[(][^\\)]+$', r'\g<0>\\)'),
        ]
        
        questions = Question.objects.filter(
            Q(text__contains='\\') | 
            Q(text__contains='^') |
            Q(text__contains='$')
        )
        
        self.stdout.write(f"Found {questions.count()} questions with potential math formulas")
        
        fixed_count = 0
        for question in questions:
            original_text = question.text
            new_text = original_text
            
            # Apply all replacements
            for pattern, replacement in replacements:
                new_text = re.sub(pattern, replacement, new_text)
            
            # Only count as fixed if something changed
            if new_text != original_text:
                fixed_count += 1
                if dry_run:
                    self.stdout.write(f"Would fix question ID {question.id}:")
                    self.stdout.write(f"  Original: {original_text}")
                    self.stdout.write(f"  Fixed:    {new_text}")
                else:
                    question.text = new_text
                    question.save()
        
        if dry_run:
            self.stdout.write(self.style.SUCCESS(f"Would fix {fixed_count} questions (dry run)"))
        else:
            self.stdout.write(self.style.SUCCESS(f"Fixed {fixed_count} questions"))
