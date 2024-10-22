from django.contrib import admin
from .models import RequestTest
# Register your models here.

class RequestTestAdmin(admin.ModelAdmin):
    list_display = ('region', 'name', 'is_active')

admin.site.register(RequestTest, RequestTestAdmin)
