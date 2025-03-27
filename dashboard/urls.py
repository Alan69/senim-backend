from django.urls import path
from .views import test_list, profile, test_history, history_detail, test_statistics, add_students, add_balance, question_management, reset_test_status, export_by_date, export_by_school

urlpatterns = [
    path('', test_statistics, name='test_statistics'),
    path('add-balance/', add_balance, name='add_balance2'),
    path('questions/', question_management, name='question_management'),
    path('reset-test-status/', reset_test_status, name='reset_test_status'),
    path('export-by-date/', export_by_date, name='export_by_date'),
    path('export-by-school/', export_by_school, name='export_by_school'),
]