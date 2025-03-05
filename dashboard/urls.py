from django.urls import path
from .views import test_list, profile, test_history, history_detail, test_statistics, add_students, add_balance

urlpatterns = [
    # path('', test_list, name='test_list'),
    # path('profile/', profile, name='profile'),
    # path('test_history/', test_history, name='test_history'),
    # path('test_history/<int:pk>/', history_detail, name='history_detail'),
    path('', test_statistics, name='test_statistics'),
    # path('add-students/', add_students, name='add_students'),
    path('add-balance/', add_balance, name='add_balance'),
]