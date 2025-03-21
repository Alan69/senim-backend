# Generated by Django 4.2.14 on 2025-02-12 11:43

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import uuid


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='Option',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('img', models.ImageField(blank=True, null=True, upload_to='options')),
                ('text', models.CharField(max_length=200)),
                ('is_correct', models.BooleanField(default=False)),
            ],
            options={
                'verbose_name': 'Вариант',
                'verbose_name_plural': 'Варианты',
            },
        ),
        migrations.CreateModel(
            name='Product',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('title', models.CharField(blank=True, max_length=200, verbose_name='Имя')),
                ('description', models.TextField(blank=True, default='Test description', null=True)),
                ('sum', models.IntegerField(blank=True, default=1500, null=True, verbose_name='Сумма')),
                ('score', models.IntegerField(blank=True, default=0, help_text='%', null=True, verbose_name='Баллы')),
                ('time', models.IntegerField(blank=True, default=45, help_text='В минутах', null=True, verbose_name='Время теста')),
                ('subject_limit', models.IntegerField(blank=True, default=1, help_text='Не обязательные предметы', null=True, verbose_name='Не обязательные предметы')),
                ('product_type', models.CharField(choices=[('STUDENT', 'Student'), ('TEACHER', 'Teacher')], default='STUDENT', max_length=10, verbose_name='Тип продукта')),
                ('date_created', models.DateField(auto_now_add=True)),
            ],
            options={
                'verbose_name': 'Продукт',
                'verbose_name_plural': 'Продукты',
            },
        ),
        migrations.CreateModel(
            name='Question',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('text', models.TextField()),
                ('img', models.ImageField(blank=True, null=True, upload_to='questions')),
                ('task_type', models.IntegerField(blank=True, null=True)),
                ('level', models.IntegerField(blank=True, null=True)),
                ('status', models.IntegerField(blank=True, null=True)),
                ('category', models.CharField(blank=True, max_length=200, null=True)),
                ('subcategory', models.CharField(blank=True, max_length=200, null=True)),
                ('theme', models.CharField(blank=True, max_length=200, null=True)),
                ('subtheme', models.CharField(blank=True, max_length=200, null=True)),
                ('target', models.TextField(blank=True, null=True)),
                ('source', models.TextField(blank=True, null=True)),
                ('detail_id', models.IntegerField(blank=True, null=True)),
                ('lng_id', models.IntegerField(blank=True, null=True)),
                ('lng_title', models.CharField(blank=True, max_length=200, null=True)),
                ('subject_id', models.IntegerField(blank=True, null=True)),
                ('subject_title', models.CharField(blank=True, max_length=200, null=True)),
                ('class_number', models.IntegerField(blank=True, null=True)),
            ],
            options={
                'verbose_name': 'Вопрос',
                'verbose_name_plural': 'Вопросы',
            },
        ),
        migrations.CreateModel(
            name='Test',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('title', models.CharField(blank=True, max_length=200, verbose_name='Имя')),
                ('number_of_questions', models.IntegerField(blank=True, default=15, null=True, verbose_name='Количество вопросов')),
                ('time', models.IntegerField(blank=True, default=45, help_text='В минутах', null=True, verbose_name='Время теста')),
                ('score', models.IntegerField(blank=True, default=0, help_text='%', null=True, verbose_name='Баллы')),
                ('grade', models.IntegerField(blank=True, null=True, verbose_name='Класс')),
                ('date_created', models.DateField(auto_now_add=True)),
                ('is_required', models.BooleanField(default=False)),
                ('product', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='test_logic.product', verbose_name='Продукт')),
            ],
            options={
                'verbose_name': 'Тест',
                'verbose_name_plural': 'Тесты',
            },
        ),
        migrations.CreateModel(
            name='Result',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('score', models.FloatField(verbose_name='Балл')),
                ('created', models.DateTimeField(auto_now=True)),
                ('is_correct', models.BooleanField()),
                ('question', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='test_logic.question')),
                ('selected_option', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='test_logic.option')),
                ('student', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL)),
                ('test', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='test_logic.test')),
            ],
            options={
                'verbose_name': 'Результат',
                'verbose_name_plural': 'Результаты',
            },
        ),
        migrations.AddField(
            model_name='question',
            name='test',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='test_logic.test'),
        ),
        migrations.AddField(
            model_name='option',
            name='question',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='options', to='test_logic.question'),
        ),
        migrations.CreateModel(
            name='CompletedTest',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('completed_date', models.DateTimeField(auto_now_add=True)),
                ('start_test_time', models.DateTimeField(blank=True, null=True)),
                ('time_spent', models.IntegerField(blank=True, null=True)),
                ('product', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='completed_tests', to='test_logic.product')),
                ('tests', models.ManyToManyField(related_name='completed_tests', to='test_logic.test')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='completed_tests', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'verbose_name': 'Результаты',
                'verbose_name_plural': 'Результаты',
            },
        ),
        migrations.CreateModel(
            name='CompletedQuestion',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('completed_test', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='completed_questions', to='test_logic.completedtest')),
                ('question', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='completed_test_questions', to='test_logic.question')),
                ('selected_option', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='test_logic.option')),
                ('test', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='completed_test_questions', to='test_logic.test')),
            ],
            options={
                'verbose_name': 'Результаты вопросов',
                'verbose_name_plural': 'Результаты вопросов',
            },
        ),
        migrations.CreateModel(
            name='BookSuggestion',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('book_title', models.CharField(max_length=200)),
                ('book_url', models.URLField()),
                ('question', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='test_logic.question')),
            ],
            options={
                'verbose_name': 'Литература',
                'verbose_name_plural': 'Литература',
            },
        ),
    ]
