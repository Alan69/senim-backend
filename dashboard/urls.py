from django.urls import path
from .views import test_list, profile, test_history, history_detail

urlpatterns = [
    path('', test_list, name='test_list'),
    path('profile/', profile, name='profile'),
    path('test_history/', test_history, name='test_history'),
    path('test_history/<int:pk>/', history_detail, name='history_detail'),
]