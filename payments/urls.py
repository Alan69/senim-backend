from django.urls import path
from .views import AuthenticateGmailView, OAuth2CallbackView, FetchEmailsView, AddBalanceView, import_questions_view

urlpatterns = [
    path('authenticate-gmail/', AuthenticateGmailView.as_view(), name='authenticate_gmail'),
    path('oauth2callback/', OAuth2CallbackView.as_view(), name='oauth2callback'),
    path('fetch-emails/', FetchEmailsView.as_view(), name='fetch_emails'),
    path('add-balance/', AddBalanceView.as_view(), name='add_balance'),
    path('import-questions/', import_questions_view, name='import_questions'),
    # path('success/', TemplateView.as_view(template_name='success.html'), name='success_view'),  # Optional success page
]
