from django.urls import path
from . import views

urlpatterns = [
    path('empty-options/', views.empty_options_view, name='empty-options'),
    path('delete-empty-options/', views.delete_empty_options_view, name='delete-empty-options'),
]
