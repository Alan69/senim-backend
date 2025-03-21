# Generated by Django 4.2.14 on 2025-02-12 11:43

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('accounts', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='RequestTest',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('school', models.CharField(max_length=120, verbose_name='Школа')),
                ('student_amount', models.IntegerField(null=True, verbose_name='колво. учеников')),
                ('name', models.CharField(blank=True, max_length=120, verbose_name='Ответственное лицо(ФИО)')),
                ('iin', models.CharField(blank=True, max_length=120, verbose_name='ИИН')),
                ('number', models.CharField(blank=True, max_length=120, verbose_name='Номер')),
                ('email', models.EmailField(blank=True, max_length=120, verbose_name='email')),
                ('is_active', models.BooleanField(default=False, verbose_name='Активность договора')),
                ('region', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='accounts.region', verbose_name='Регион')),
            ],
            options={
                'verbose_name_plural': 'Заявки',
            },
        ),
    ]
