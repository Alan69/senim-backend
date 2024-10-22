from django.db import models

# Create your models here.
class AddStudent(models.Model):
    excel_file = models.FileField(upload_to='files', verbose_name="Excel ученики")

    class Meta:
        verbose_name_plural = 'Список школьников'