from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from test_logic.models import Test, Result, Option, Product, CompletedTest, CompletedQuestion
from django.http import HttpResponse
from openpyxl import load_workbook
from openpyxl.styles import Font, Alignment, Border, Side
from openpyxl.utils import get_column_letter
from django.db.models import Count, Q, F, Value, Case, When, FloatField
from django.db.models.functions import Cast, Coalesce
from django.core.paginator import Paginator
import xlsxwriter
from io import BytesIO
from django.db.models import Avg
from datetime import datetime
from django.contrib import messages
from decimal import Decimal
from accounts.models import User, Region
from .forms import AddBalanceForm, AddStudentForm

@login_required
def test_list(request):
    tests = Product.objects.all()
    return render(request, 'dashboard/test_list.html', {'tests': tests})

@login_required
def profile(request):
    user = request.user
    return render(request, 'dashboard/profile.html', {'user': user})

@login_required
def test_history(request):
    tests = Test.objects.filter(result__student=request.user).distinct()
    return render(request, 'dashboard/test_history.html', {'tests': tests})

@login_required
def history_detail(request, pk):
    test = get_object_or_404(Test, pk=pk)
    results = Result.objects.filter(student=request.user, test=test)
    
    history = []
    for result in results:
        correct_option = Option.objects.filter(question=result.question, is_correct=True).first()
        history.append({
            'result': result,
            'correct_option': correct_option,
        })
    
    return render(request, 'dashboard/history_detail.html', {'test': test, 'history': history})

@login_required
def add_students(request):
    if request.method == 'POST':
        workbook = load_workbook(request.FILES['document'])
        worksheet = workbook.active

        student_region = request.user.region
        school_region = request.user.school

        for row in worksheet.iter_rows():
            username = row[0].value
            password = row[0].value
            first_name = row[1].value
            last_name = row[2].value
            class_name = row[3].value
                
            user_class_name = username
            user_class_name = ''.join(filter(str.isdigit, user_class_name))

            user_class_password = password
            user_class_password = ''.join(filter(str.isdigit, user_class_password))

            # Try to get the user by username or create a new one
            user, created = User.objects.get_or_create(
                username=user_class_name,
                defaults={
                    'password': user_class_password,
                    'first_name': first_name,
                    'last_name': last_name,
                    'class_name': class_name,
                    'region': student_region,
                    'school': school_region
                }
            )

            # If the user already existed, update their information
            if not created:
                user.first_name = first_name
                user.last_name = last_name
                user.class_name = class_name
                user.region = student_region
                user.school = school_region
                user.save()

        return HttpResponse("Ученики добавлены")
    else:
        return render(request, 'dashboard/addstudent.html')

@login_required
def test_statistics(request):
    # Get filter parameters
    region_id = request.GET.get('region')
    school = request.GET.get('school')
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')
    page = request.GET.get('page', 1)

    # Base queryset with select_related and prefetch_related
    completed_tests = CompletedTest.objects.select_related(
        'user', 
        'user__region'
    ).prefetch_related(
        'completed_questions',
        'completed_questions__selected_option'
    ).order_by('-completed_date')  # Add ordering

    # Apply filters - Fix the region filter to handle empty strings
    if region_id and region_id != '':
        completed_tests = completed_tests.filter(user__region_id=region_id)
    if school:
        completed_tests = completed_tests.filter(user__school__icontains=school)
    if start_date:
        completed_tests = completed_tests.filter(completed_date__gte=start_date)
    if end_date:
        completed_tests = completed_tests.filter(completed_date__lte=end_date)

    # Annotate with correct and wrong answer counts
    completed_tests = completed_tests.annotate(
        correct_answers=Count(
            'completed_questions',
            filter=Q(completed_questions__selected_option__is_correct=True),
            distinct=True
        ),
        wrong_answers=Count(
            'completed_questions',
            filter=Q(completed_questions__selected_option__is_correct=False) | 
                  Q(completed_questions__selected_option__isnull=True),
            distinct=True
        )
    ).annotate(
        total_questions=F('correct_answers') + F('wrong_answers'),
        score_percentage=Case(
            When(total_questions=0, then=Value(0.0)),
            default=100.0 * F('correct_answers') / Cast(F('total_questions'), FloatField()),
            output_field=FloatField(),
        )
    )

    # Add more debug logging
    print("\nDEBUG: Checking completed questions")
    for test in CompletedTest.objects.filter(user__region_id=region_id)[:1]:
        print(f"\nTest ID: {test.id}")
        print(f"User: {test.user.username}")
        print(f"Product: {test.product.title}")
        questions = test.completed_questions.all().select_related('selected_option')
        print(f"Questions count: {questions.count()}")
        for q in questions:
            print(f"Question ID: {q.id}")
            print(f"Selected option: {q.selected_option}")
            if q.selected_option:
                print(f"Is correct: {q.selected_option.is_correct}")

    # Handle Excel export - do this before pagination to include all data
    if request.GET.get('export') == 'excel':
        all_statistics = []
        for completed_test in completed_tests:
            all_statistics.append({
                'completed_test': completed_test,
                'user': completed_test.user,
                'region': completed_test.user.region,
                'school': completed_test.user.school,
                'completed_date': completed_test.completed_date,
                'correct_answers': completed_test.correct_answers,
                'wrong_answers': completed_test.wrong_answers,
                'total_questions': completed_test.total_questions,
                'score_percentage': round(completed_test.score_percentage, 2)
            })
        return export_to_excel(all_statistics)

    # Paginate results for display
    paginator = Paginator(completed_tests, 50)  # Show 50 items per page
    page_obj = paginator.get_page(page)

    statistics = []
    for completed_test in page_obj:
        statistics.append({
            'completed_test': completed_test,
            'user': completed_test.user,
            'region': completed_test.user.region,
            'school': completed_test.user.school,
            'completed_date': completed_test.completed_date,
            'correct_answers': completed_test.correct_answers,
            'wrong_answers': completed_test.wrong_answers,
            'total_questions': completed_test.total_questions,
            'score_percentage': round(completed_test.score_percentage, 2)
        })

    # Get all regions for the filter dropdown
    regions = Region.objects.all()

    context = {
        'statistics': statistics,
        'page_obj': page_obj,
        'regions': regions,
        'selected_region': region_id,
        'selected_school': school,
        'start_date': start_date,
        'end_date': end_date,
    }

    return render(request, 'dashboard/test_statistics.html', context)

def export_to_excel(statistics):
    output = BytesIO()
    workbook = xlsxwriter.Workbook(output)
    worksheet = workbook.add_worksheet()

    # Add headers in Russian
    headers = [
        'Пользователь', 'Регион', 'Школа', 'Дата завершения',
        'Правильные ответы', 'Неправильные ответы', 'Всего вопросов', 'Результат (%)'
    ]
    for col, header in enumerate(headers):
        worksheet.write(0, col, header)

    # Add data
    for row, stat in enumerate(statistics, 1):
        worksheet.write(row, 0, f"{stat['user'].first_name} {stat['user'].last_name}")
        worksheet.write(row, 1, str(stat['region']))
        worksheet.write(row, 2, stat['school'])
        worksheet.write(row, 3, stat['completed_date'].strftime('%Y-%m-%d %H:%M'))
        worksheet.write(row, 4, stat['correct_answers'])
        worksheet.write(row, 5, stat['wrong_answers'])
        worksheet.write(row, 6, stat['total_questions'])
        worksheet.write(row, 7, stat['score_percentage'])

    workbook.close()
    output.seek(0)

    response = HttpResponse(
        output.read(),
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )
    response['Content-Disposition'] = 'attachment; filename=статистика_тестов.xlsx'
    return response

@login_required
def add_balance(request):
    # Only staff, superusers, or principals can add balance
    if not (request.user.is_staff or request.user.is_superuser or request.user.is_principal):
        messages.error(request, "У вас нет прав для доступа к этой странице.")
        return redirect('test_statistics')
    
    form = AddBalanceForm(request.POST or None)
    
    if request.method == 'POST' and form.is_valid():
        filter_type = form.cleaned_data['filter_type']
        amount = form.cleaned_data['amount']
        users_updated = 0
        
        try:
            if filter_type == 'all':
                # Add balance only to users with zero balance
                users = User.objects.filter(is_active=True, balance=0)
                for user in users:
                    user.balance += amount
                    user.save()
                    users_updated += 1
                
            elif filter_type == 'region':
                # Add balance to users in a specific region with zero balance
                region = form.cleaned_data['region']
                users = User.objects.filter(region=region, is_active=True, balance=0)
                for user in users:
                    user.balance += amount
                    user.save()
                    users_updated += 1
                
            elif filter_type == 'school':
                # Add balance to users in a specific school with zero balance
                school = form.cleaned_data['school']
                users = User.objects.filter(school__iexact=school, is_active=True, balance=0)
                for user in users:
                    user.balance += amount
                    user.save()
                    users_updated += 1
                
            elif filter_type == 'specific':
                # Add balance to a specific user only if they have zero balance
                username = form.cleaned_data['username']
                user = User.objects.get(username=username)
                if user.balance == 0:
                    user.balance += amount
                    user.save()
                    users_updated = 1
            
            messages.success(request, f"Успешно добавлено {amount} на баланс {users_updated} пользователя(ей) с нулевым балансом.")
            return redirect('add_balance2')
            
        except Exception as e:
            messages.error(request, f"Произошла ошибка: {str(e)}")
    
    # Get some statistics for the template
    total_users = User.objects.filter(is_active=True).count()
    zero_balance_users = User.objects.filter(is_active=True, balance=0).count()
    regions = Region.objects.all()
    region_stats = []
    
    for region in regions:
        region_stats.append({
            'name': region.name,
            'user_count': User.objects.filter(region=region, is_active=True).count(),
            'zero_balance_count': User.objects.filter(region=region, is_active=True, balance=0).count()
        })
    
    # Get unique schools and their user counts
    schools = User.objects.filter(is_active=True).values('school').distinct()
    school_stats = []
    
    for school_dict in schools:
        school = school_dict.get('school')
        if school:  # Skip None values
            school_stats.append({
                'name': school,
                'user_count': User.objects.filter(school=school, is_active=True).count(),
                'zero_balance_count': User.objects.filter(school=school, is_active=True, balance=0).count()
            })
    
    context = {
        'form': form,
        'total_users': total_users,
        'zero_balance_users': zero_balance_users,
        'region_stats': region_stats,
        'school_stats': school_stats
    }
    
    return render(request, 'dashboard/add_balance.html', context)