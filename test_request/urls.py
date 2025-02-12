from django.urls import path
from .views import request_page

urlpatterns = [
    path('', request_page, name='request_page'),
]
