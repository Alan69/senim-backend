# yourapp/management/commands/import_questions.py
import json
from django.core.management.base import BaseCommand
from test_logic.models import Question, Option, Test

class Command(BaseCommand):
    help = 'Import questions from a JSON file'

    def add_arguments(self, parser):
        parser.add_argument('json_file', type=str)

    def handle(self, *args, **kwargs):
        json_file = kwargs['json_file']

        try:
            with open(json_file, 'r', encoding='utf-8') as file:
                data = json.load(file)
        except UnicodeDecodeError:
            self.stdout.write(self.style.ERROR('Unable to decode file. Try using a different encoding.'))
            return
        except FileNotFoundError:
            self.stdout.write(self.style.ERROR(f'File {json_file} does not exist.'))
            return

        for item in data:
            test_id = item.get(2)  # Assuming there's a 'test_id' field in your JSON
            try:
                test = Test.objects.get(id="e606c902-f904-4edd-b3bb-9a877e2037be")
            except Test.DoesNotExist:
                self.stdout.write(self.style.ERROR(f'Test with ID {test_id} does not exist.'))
                continue

            question = Question.objects.create(
                test=test,
                text=item.get('question'),
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

            answers = item.get('answers', [])
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

            for key, value in options.items():
                if value:
                    Option.objects.create(
                        question=question,
                        text=value,
                        is_correct=value in answers
                    )

        self.stdout.write(self.style.SUCCESS('Successfully imported questions'))
