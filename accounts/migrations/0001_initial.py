# Generated by Django 4.2.14 on 2025-02-12 11:43

from django.db import migrations, models
import uuid


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('auth', '0012_alter_user_first_name_max_length'),
    ]

    operations = [
        migrations.CreateModel(
            name='Region',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('name', models.CharField(max_length=255, unique=True, verbose_name='Название региона')),
                ('region_type', models.CharField(choices=[('Город', 'Город'), ('Село', 'Село')], default='Город', max_length=10, verbose_name='Тип региона')),
                ('description', models.TextField(blank=True, null=True, verbose_name='Описание')),
            ],
            options={
                'verbose_name': 'Регион',
                'verbose_name_plural': 'Регионы',
                'ordering': ['name'],
            },
        ),
        migrations.CreateModel(
            name='User',
            fields=[
                ('password', models.CharField(max_length=128, verbose_name='password')),
                ('last_login', models.DateTimeField(blank=True, null=True, verbose_name='last login')),
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('username', models.CharField(db_index=True, max_length=254, unique=True, verbose_name='ИИН')),
                ('email', models.EmailField(max_length=254, unique=True, verbose_name='Электронная почта')),
                ('first_name', models.CharField(max_length=250, verbose_name='Имя')),
                ('last_name', models.CharField(max_length=250, verbose_name='Фамилия')),
                ('school', models.CharField(blank=True, max_length=255, null=True, verbose_name='Образовательное учреждение')),
                ('phone_number', models.CharField(blank=True, max_length=15, null=True, verbose_name='Номер телефона')),
                ('balance', models.DecimalField(decimal_places=2, default=0.0, max_digits=10, verbose_name='Баланс')),
                ('referral_link', models.CharField(blank=True, max_length=100, null=True, unique=True)),
                ('referral_bonus', models.DecimalField(decimal_places=2, default=0, max_digits=10)),
                ('payment_id', models.CharField(blank=True, max_length=255, null=True)),
                ('test_is_started', models.BooleanField(default=False)),
                ('total_time', models.IntegerField(default=0)),
                ('test_start_time', models.DateTimeField(blank=True, null=True)),
                ('finish_test_time', models.DateTimeField(blank=True, null=True)),
                ('is_student', models.BooleanField(default=False, verbose_name='Это студент?')),
                ('is_teacher', models.BooleanField(default=False, verbose_name='Это учитель?')),
                ('is_principal', models.BooleanField(default=False, verbose_name='Это директор?')),
                ('is_staff', models.BooleanField(default=False, verbose_name='Это сотрудник?')),
                ('is_active', models.BooleanField(default=True, verbose_name='Активность?')),
                ('is_superuser', models.BooleanField(default=False, verbose_name='Суперадмин')),
                ('groups', models.ManyToManyField(blank=True, help_text='The groups this user belongs to. A user will get all permissions granted to each of their groups.', related_name='user_set', related_query_name='user', to='auth.group', verbose_name='groups')),
            ],
            options={
                'verbose_name': 'Пользователь',
                'verbose_name_plural': 'Пользователи',
            },
        ),
    ]
