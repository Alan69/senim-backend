from django.db import models
from accounts.models import Region

# Create your models here.
class RequestTest(models.Model):
    region = models.ForeignKey(Region, on_delete=models.CASCADE, verbose_name="Регион")
    school = models.CharField(max_length=120, verbose_name="Школа")
    student_amount = models.IntegerField(null=True, verbose_name="колво. учеников")
    name = models.CharField(max_length=120, blank=True, verbose_name="Ответственное лицо(ФИО)")
    iin = models.CharField(max_length=120, blank=True, verbose_name="ИИН")
    number = models.CharField(max_length=120, blank=True, verbose_name="Номер")
    email = models.EmailField(max_length=120, blank=True, verbose_name="email")
    excel_file = models.FileField(null=True, blank=True, verbose_name="Excel файл")
    is_active = models.BooleanField(default=False, verbose_name="Активность договора")

    def __str__(self):
        return self.name + " " + str(self.region) + " " + self.school
    
    class Meta:
        verbose_name_plural = 'Заявки'