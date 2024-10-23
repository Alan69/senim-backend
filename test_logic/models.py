from django.db import models
from accounts.models import User
import uuid
from django.utils import timezone

class Product(models.Model):

    class ProductType(models.TextChoices):
        STUDENT = 'STUDENT', 'Student'
        TEACHER = 'TEACHER', 'Teacher'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    title = models.CharField(max_length=200, blank=True, verbose_name='Имя')
    description = models.TextField(null=True, blank=True, default="Test description")
    sum = models.IntegerField(verbose_name="Сумма", default=1500, null=True, blank=True)
    score = models.IntegerField(help_text="%", verbose_name="Баллы", default=0, null=True, blank=True)
    time = models.IntegerField(help_text="В минутах", verbose_name="Время теста", default=45, null=True, blank=True)
    subject_limit = models.IntegerField(help_text="Не обязательные предметы", verbose_name="Не обязательные предметы", default=1, null=True, blank=True)

    product_type = models.CharField(
        max_length=10,
        choices=ProductType.choices,
        default=ProductType.STUDENT,
        verbose_name='Тип продукта'
    )

    date_created = models.DateField(auto_now_add=True)

    def __str__(self):
        return self.title

    class Meta:
        verbose_name = 'Продукт'
        verbose_name_plural = 'Продукты'

class Test(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    title = models.CharField(max_length=200, blank=True, verbose_name='Имя')
    number_of_questions = models.IntegerField(verbose_name="Количество вопросов", default=15, null=True, blank=True)
    time = models.IntegerField(help_text="В минутах", verbose_name="Время теста", default=45, null=True, blank=True)
    score = models.IntegerField(help_text="%", verbose_name="Баллы", default=0, null=True, blank=True)
    product = models.ForeignKey(Product, on_delete=models.CASCADE, verbose_name="Продукт")
    date_created = models.DateField(auto_now_add=True)
    is_required = models.BooleanField(default=False)

    def __str__(self):
        return self.title

    class Meta:
        verbose_name = 'Тест'
        verbose_name_plural = 'Тесты'

class Question(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    test = models.ForeignKey(Test, on_delete=models.CASCADE)
    text = models.TextField()
    img = models.ImageField(upload_to='questions', null=True, blank=True)
    task_type = models.IntegerField(null=True, blank=True)
    level = models.IntegerField(null=True, blank=True)
    status = models.IntegerField(null=True, blank=True)
    category = models.CharField(max_length=200, null=True, blank=True)
    subcategory = models.CharField(max_length=200, null=True, blank=True)
    theme = models.CharField(max_length=200, null=True, blank=True)
    subtheme = models.CharField(max_length=200, null=True, blank=True)
    target = models.TextField(null=True, blank=True)
    source = models.TextField(null=True, blank=True)
    detail_id = models.IntegerField(null=True, blank=True)
    lng_id = models.IntegerField(null=True, blank=True)
    lng_title = models.CharField(max_length=200, null=True, blank=True)
    subject_id = models.IntegerField(null=True, blank=True)
    subject_title = models.CharField(max_length=200, null=True, blank=True)
    class_number = models.IntegerField(null=True, blank=True)

    def __str__(self):
        return self.text

    class Meta:
        verbose_name = 'Вопрос'
        verbose_name_plural = 'Вопросы'

class Option(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    question = models.ForeignKey(Question, on_delete=models.CASCADE, related_name='options')
    text = models.CharField(max_length=200)
    is_correct = models.BooleanField(default=False)

    def __str__(self):
        return self.text

    class Meta:
        verbose_name = 'Вариант'
        verbose_name_plural = 'Варианты'


class Result(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    test = models.ForeignKey(Test, on_delete=models.CASCADE)
    student = models.ForeignKey(User, on_delete=models.CASCADE)
    question = models.ForeignKey(Question, on_delete=models.CASCADE)
    selected_option = models.ForeignKey(Option, on_delete=models.CASCADE)
    score = models.FloatField(verbose_name="Балл")
    created = models.DateTimeField(auto_now=True)
    is_correct = models.BooleanField()

    def __str__(self):
        return str(self.test.title) + "-" + str(self.student.first_name) + " " +  str(self.score)

    class Meta:
        verbose_name = 'Результат'
        verbose_name_plural = 'Результаты'

class BookSuggestion(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    question = models.ForeignKey(Question, on_delete=models.CASCADE)
    book_title = models.CharField(max_length=200)
    book_url = models.URLField()

    def __str__(self):
        return self.book_title

    class Meta:
        verbose_name = 'Литература'
        verbose_name_plural = 'Литература'

class CompletedTest(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='completed_tests')
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='completed_tests')
    tests = models.ManyToManyField(Test, related_name='completed_tests')

    completed_date = models.DateTimeField(auto_now_add=True)

    start_test_time = models.DateTimeField(null=True, blank=True)

    time_spent = models.IntegerField(null=True, blank=True)

    def __str__(self):
        return f"CompletedTest for {self.user.username} - {self.product.title}"

    class Meta:
        verbose_name = 'Completed Test'
        verbose_name_plural = 'Completed Tests'


class CompletedQuestion(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    completed_test = models.ForeignKey(CompletedTest, on_delete=models.CASCADE, related_name='completed_questions')
    test = models.ForeignKey(Test, on_delete=models.CASCADE, related_name='completed_test_questions')
    question = models.ForeignKey(Question, on_delete=models.CASCADE, related_name='completed_test_questions',  null=True, blank=True)
    selected_option = models.ForeignKey(Option, on_delete=models.SET_NULL, null=True, blank=True)

    def __str__(self):
        return f"CompletedQuestion for {self.completed_test.user.username} - {self.question.text}"