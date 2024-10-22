from django.db import models
from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin, BaseUserManager
import uuid

class Region(models.Model):
    CITY = 'Город'
    VILLAGE = 'Село'

    REGION_TYPE_CHOICES = [
        (CITY, 'Город'),
        (VILLAGE, 'Село'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255, unique=True, verbose_name="Название региона")
    region_type = models.CharField(max_length=10, choices=REGION_TYPE_CHOICES, default=CITY, verbose_name="Тип региона")
    description = models.TextField(blank=True, null=True, verbose_name="Описание")

    class Meta:
        verbose_name = 'Регион'
        verbose_name_plural = 'Регионы'
        ordering = ['name']

    def __str__(self):
        return f"{self.name} ({self.get_region_type_display()})"

class CustomUserManager(BaseUserManager):
    def _create_user(self, username, password, first_name, last_name, **extra_fields):
        if not username:
            raise ValueError("Необходимо указать логин")
        if not password:
            raise ValueError("Необходимо ввести пароль")

        user = self.model(
            username=username,
            first_name=first_name,
            last_name=last_name,
            **extra_fields
        )

        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_user(self, username, password, first_name, last_name, **extra_fields):
        extra_fields.setdefault('is_staff', False)
        extra_fields.setdefault('is_active', True)
        extra_fields.setdefault('is_superuser', False)
        return self._create_user(username, password, first_name, last_name, **extra_fields)

    def create_superuser(self, username, password, first_name, last_name, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_active', True)
        extra_fields.setdefault('is_superuser', True)
        return self._create_user(username, password, first_name, last_name, **extra_fields)

class User(AbstractBaseUser, PermissionsMixin):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    username = models.CharField(db_index=True, unique=True, max_length=254, verbose_name="ИИН")
    email = models.EmailField(unique=True, verbose_name="Электронная почта")
    first_name = models.CharField(max_length=250, verbose_name="Имя")
    last_name = models.CharField(max_length=250, verbose_name="Фамилия")
    region = models.ForeignKey(Region, on_delete=models.CASCADE, null=True, blank=True, verbose_name="Город")
    school = models.CharField(max_length=255, verbose_name="Образовательное учреждение", null=True, blank=True)
    phone_number = models.CharField(max_length=15, verbose_name="Номер телефона", null=True, blank=True)
    balance = models.DecimalField(max_digits=10, decimal_places=2, default=0.00, verbose_name="Баланс")
    referral_link = models.CharField(max_length=100, unique=True, null=True, blank=True)
    referral_bonus = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    payment_id = models.CharField(max_length=255, null=True, blank=True)

    test_is_started = models.BooleanField(default=False)
    total_time = models.IntegerField(default=0)
    test_start_time = models.DateTimeField(null=True, blank=True)
    finish_test_time = models.DateTimeField(null=True, blank=True)

    product = models.ForeignKey('test_logic.Product', on_delete=models.SET_NULL, null=True, blank=True)
    # class_name = models.CharField(max_length=255, verbose_name="Класс", null=True, blank=True)

    is_student = models.BooleanField(default=False, verbose_name="Это студент?")
    is_teacher = models.BooleanField(default=False, verbose_name="Это учитель?")
    is_principal = models.BooleanField(default=False, verbose_name="Это директор?")
    is_staff = models.BooleanField(default=False, verbose_name="Это сотрудник?")
    is_active = models.BooleanField(default=True, verbose_name="Активность?")
    is_superuser = models.BooleanField(default=False, verbose_name="Суперадмин")

    objects = CustomUserManager()

    USERNAME_FIELD = 'username'
    REQUIRED_FIELDS = ['first_name', 'last_name']

    class Meta:
        verbose_name = 'Пользователь'
        verbose_name_plural = "Пользователи"

    def __str__(self):
        return f"{self.first_name} {self.last_name} ({self.username})"
    
    def transfer_balance(self, recipient, amount):
        if self.balance < amount:
            raise ValueError("Insufficient balance to transfer.")
        if not recipient.is_student:
            raise ValueError("Recipient must be a student.")
        
        self.balance -= amount
        recipient.balance += amount
        self.save()
        recipient.save()
    
    def generate_referral_link(self):
        import secrets
        token = secrets.token_urlsafe(10)  # Generate a random token
        self.referral_link = f'/register-referral?ref={token}'  # Example URL format
        self.save()