from django.db import models

# Create your models here.
class FetchedEmailData(models.Model):
    fio_student = models.CharField(max_length=255)
    jsn_iin = models.CharField(max_length=255)
    payment_amount = models.DecimalField(max_digits=20, decimal_places=5)
    payment_id_match = models.CharField(max_length=255)
    is_payed = models.BooleanField(default=False)

    def __str__(self) -> str:
        return self.jsn_iin + " " + str(self.payment_amount)