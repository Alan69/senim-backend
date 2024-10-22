from rest_framework import status, views, reverse
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.shortcuts import get_object_or_404
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from django.conf import settings
from decimal import Decimal
import os
import re
import base64
from .models import FetchedEmailData
from accounts.models import User
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi

os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'

MY_GMAIL = 'synaqtest1@gmail.com'
SENDER_EMAIL = 'kaspi.payments@kaspibank.kz'


class AuthenticateGmailView(views.APIView):
    def get(self, request):
        creds = None
        token_path = os.path.join(settings.BASE_DIR, 'token.json')

        if os.path.exists(token_path):
            creds = Credentials.from_authorized_user_file(token_path, settings.GMAIL_SCOPES)

        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                flow = InstalledAppFlow.from_client_secrets_file(
                    settings.GMAIL_CREDENTIALS_PATH, settings.GMAIL_SCOPES)
                flow.redirect_uri = request.build_absolute_uri(reverse('oauth2callback'))
                authorization_url, state = flow.authorization_url(
                    access_type='offline',
                    include_granted_scopes='true'
                )
                request.session['state'] = state
                return Response({"authorization_url": authorization_url}, status=status.HTTP_302_FOUND)

            with open(token_path, 'w') as token:
                token.write(creds.to_json())

        return build('gmail', 'v1', credentials=creds)


class OAuth2CallbackView(views.APIView):
    def get(self, request):
        state = request.session.get('state')
        flow = InstalledAppFlow.from_client_secrets_file(
            settings.GMAIL_CREDENTIALS_PATH, settings.GMAIL_SCOPES, state=state)
        flow.redirect_uri = request.build_absolute_uri(reverse('oauth2callback'))

        authorization_response = request.build_absolute_uri()
        flow.fetch_token(authorization_response=authorization_response)

        creds = flow.credentials
        token_path = os.path.join(settings.BASE_DIR, 'token.json')
        with open(token_path, 'w') as token:
            token.write(creds.to_json())

        return Response({"message": "Token fetched successfully"}, status=status.HTTP_200_OK)


def parse_message(message):
    fio_match = re.search(r'ФИО учащегося: (.+)', message)
    jsn_iin_match = re.search(r'ЖСН\|ИИН = (\d+)', message)
    payment_amount_match = re.search(r'Платеж на сумму: (\d+\.\d{2})', message)
    payment_id_match = re.search(r'Идентификатор платежа: (\d+)', message)

    if fio_match and jsn_iin_match and payment_amount_match and payment_id_match:
        return {
            'fio_student': fio_match.group(1),
            'jsn_iin': jsn_iin_match.group(1),
            'payment_amount': payment_amount_match.group(1),
            'payment_id': payment_id_match.group(1)
        }
    return None


def get_messages(service):
    try:
        results = service.users().messages().list(userId='me', q='from:' + SENDER_EMAIL).execute()
        messages = results.get('messages', [])

        parsed_messages = []
        if messages:
            for message in messages:
                msg = service.users().messages().get(userId='me', id=message['id']).execute()
                msg_str = base64.urlsafe_b64decode(msg['payload']['body']['data']).decode('utf-8')
                parsed_message = parse_message(msg_str)
                if parsed_message:
                    parsed_messages.append(parsed_message)

        return parsed_messages
    except Exception as e:
        return []


class FetchEmailsView(views.APIView):
    def get(self, request):
        # Authenticate and build the Gmail service object
        service = AuthenticateGmailView().get(request)
        if isinstance(service, Response) and service.status_code == status.HTTP_302_FOUND:
            return service  # Redirect to OAuth2 authorization URL

        # Now use the service object to fetch the messages
        parsed_messages = get_messages(service)

        # Process the messages and save to the database
        for parsed_message in parsed_messages:
            fio_student = parsed_message.get('fio_student')
            jsn_iin = parsed_message.get('jsn_iin')
            payment_amount = parsed_message.get('payment_amount')
            payment_id = parsed_message.get('payment_id')

            if FetchedEmailData.objects.filter(payment_id_match=payment_id).exists():
                continue  # Skip saving if payment_id already exists

            FetchedEmailData.objects.create(
                fio_student=fio_student,
                jsn_iin=jsn_iin,
                payment_amount=payment_amount,
                payment_id_match=payment_id
            )

        return Response(parsed_messages, status=status.HTTP_200_OK)

def fetch_and_save_last_email(service):
    try:
        # Fetch the last message
        results = service.users().messages().list(userId='me', q=f'from:{SENDER_EMAIL}', maxResults=1).execute()
        messages = results.get('messages', [])

        if messages:
            # Get the last message
            message = messages[0]
            msg = service.users().messages().get(userId='me', id=message['id']).execute()
            msg_str = base64.urlsafe_b64decode(msg['payload']['body']['data']).decode('utf-8')
            parsed_message = parse_message(msg_str)

            if parsed_message:
                # Check if payment ID already exists
                if FetchedEmailData.objects.filter(payment_id_match=parsed_message['payment_id']).exists():
                    return None  # Skip if payment_id already exists

                # Save the parsed email data to the database
                fetched_email = FetchedEmailData.objects.create(
                    fio_student=parsed_message['fio_student'],
                    jsn_iin=parsed_message['jsn_iin'],
                    payment_amount=parsed_message['payment_amount'],
                    payment_id_match=parsed_message['payment_id']
                )
                return fetched_email
        return None
    except Exception as e:
        return None


class AddBalanceView(views.APIView):
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        operation_description="Adds the fetched payment amount to the authenticated user's balance.",
        responses={
            200: openapi.Response(
                description="Balance successfully added.",
                examples={
                    "application/json": {
                        "success": "Balance of 100.00 added to user 123456789."
                    }
                }
            ),
            500: openapi.Response(
                description="Error occurred while adding balance.",
                examples={
                    "application/json": {
                        "error": "Error adding balance: some error message."
                    }
                }
            )
        },
    )
    def post(self, request):
        try:
            # Authenticate and build the Gmail service object
            service = AuthenticateGmailView().get(request)
            if isinstance(service, Response) and service.status_code == status.HTTP_302_FOUND:
                return service  # Redirect to OAuth2 authorization URL if required

            # Fetch and save the last email
            fetched_email = fetch_and_save_last_email(service)

            if not fetched_email:
                return Response({'error': 'Вы не оплатили.'}, status=status.HTTP_404_NOT_FOUND)

            # Check if the payment has already been processed
            if fetched_email.is_payed:
                return Response({'error': 'Оалата уже прошла.'}, status=status.HTTP_400_BAD_REQUEST)

            # Update the user's payment_id before adding balance
            user = request.user
            user.payment_id = fetched_email.payment_id_match  # Assign fetched email's payment ID to the user
            user.save()

            # Check if the fetched email belongs to the current user by payment_id or jsn_iin
            if fetched_email.jsn_iin != user.username or fetched_email.payment_id_match != user.payment_id:
                return Response({'error': 'Fetched email data does not match the user.'}, status=status.HTTP_400_BAD_REQUEST)

            # Add balance to the user
            user.balance += Decimal(fetched_email.payment_amount)
            user.payment_id = None  # Set payment_id to None after successful payment
            user.save()

            # Mark the payment as processed
            fetched_email.is_payed = True
            fetched_email.save()

            return Response(
                {'success': f'Balance of {fetched_email.payment_amount} added to user {fetched_email.jsn_iin}.'},
                status=status.HTTP_200_OK
            )
        except Exception as e:
            return Response({'error': f'Error adding balance: {e}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)



from django.shortcuts import render, redirect
from django.core.files.storage import default_storage
from test_logic.models import Test, Question, Option
from .forms import ImportQuestionsForm
import json
from django.http import HttpResponse

def import_questions_view(request):
    if request.method == 'POST':
        form = ImportQuestionsForm(request.POST, request.FILES)
        if form.is_valid():
            test = form.cleaned_data['test']
            json_file = request.FILES['json_file']

            # Save the uploaded file temporarily
            file_path = default_storage.save(f'uploads/{json_file.name}', json_file)

            # Load the JSON data
            try:
                with open(default_storage.path(file_path), 'r', encoding='utf-8') as file:
                    data = json.load(file)
            except UnicodeDecodeError:
                return render(request, 'payments/import_questions.html', {'form': form, 'error': 'Unable to decode file. Try using a different encoding.'})
            except FileNotFoundError:
                return render(request, 'payments/import_questions.html', {'form': form, 'error': 'File not found.'})

            # Fetch the Test object
            # try:
            #     test = Test.objects.get(id=test_id)
            # except Test.DoesNotExist:
            #     return render(request, 'payments/import_questions.html', {'form': form, 'error': f'Test with ID {test_id} does not exist.'})

            # Process the questions and options
            for item in data:
                question = Question.objects.create(
                    test=test,
                    text=item.get('question'),
                    task_type=item.get('task_type'),
                    level=item.get('level'),
                    status=item.get('status'),
                    category=item.get('category'),
                    subcategory=item.get('subcategory'),
                    theme=item.get('theme'),
                    subtheme=item.get('subtheme'),
                    target=item.get('target'),
                    source=item.get('source'),
                    detail_id=item.get('detail_id'),
                    lng_id=item.get('lng_id'),
                    lng_title=item.get('lng_title'),
                    subject_id=item.get('subject_id'),
                    subject_title=item.get('subject_title'),
                    class_number=item.get('class')
                )

                answers = item.get('answers', [])
                options = {
                    'var1': item.get('var1'),
                    'var2': item.get('var2'),
                    'var3': item.get('var3'),
                    'var4': item.get('var4'),
                    'var5': item.get('var5'),
                    'var6': item.get('var6'),
                    'var7': item.get('var7'),
                    'var8': item.get('var8'),
                    'var9': item.get('var9'),
                    'var10': item.get('var10'),
                    'var11': item.get('var11'),
                    'var12': item.get('var12'),
                }

                for key, value in options.items():
                    if value:
                        Option.objects.create(
                            question=question,
                            text=value,
                            is_correct=value in answers
                        )

            # Cleanup: delete the uploaded file after processing
            default_storage.delete(file_path)

            return HttpResponse('success')  # Redirect to success page after import
    else:
        form = ImportQuestionsForm()

    return render(request, 'payments/import_questions.html', {'form': form})