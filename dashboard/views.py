from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required
from test_logic.models import Test, Result, Option, Product, CompletedTest, CompletedQuestion
from django.http import HttpResponse
from accounts.models import User, Region
from openpyxl import load_workbook
from django.db.models import Count, Q, F, FloatField, ExpressionWrapper
import xlsxwriter
from io import BytesIO
from django.db.models import Avg
from datetime import datetime
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger

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

    # Use select_related and prefetch_related to reduce queries
    completed_tests = CompletedTest.objects.select_related(
        'user', 
        'user__region', 
        'product'
    ).prefetch_related(
        'completed_questions',
        'completed_questions__selected_option'
    )

    # Apply filters
    if region_id:
        completed_tests = completed_tests.filter(user__region_id=region_id)
    if school:
        completed_tests = completed_tests.filter(user__school__icontains=school)
    if start_date:
        completed_tests = completed_tests.filter(completed_date__gte=start_date)
    if end_date:
        completed_tests = completed_tests.filter(completed_date__lte=end_date)

    # Use annotation to calculate statistics in the database
    statistics = completed_tests.annotate(
        correct_answers=Count(
            'completed_questions',
            filter=Q(completed_questions__selected_option__is_correct=True)
        ),
        total_questions=Count('completed_questions'),
    ).values(
        'id', 'user__username', 'user__first_name', 'user__last_name',
        'user__school', 'user__region__name', 'completed_date', 
        'time_spent', 'correct_answers', 'total_questions'
    ).order_by('-completed_date')  # Sort by most recent first

    # Pagination
    page = request.GET.get('page', 1)
    paginator = Paginator(statistics, 25)  # Show 25 entries per page
    
    try:
        statistics_page = paginator.page(page)
    except PageNotAnInteger:
        statistics_page = paginator.page(1)
    except EmptyPage:
        statistics_page = paginator.page(paginator.num_pages)

    context = {
        'statistics': statistics_page,
        'regions': Region.objects.all(),
        'selected_region': region_id,
        'selected_school': school,
        'start_date': start_date,
        'end_date': end_date,
    }

    # Handle Excel export
    if request.GET.get('export') == 'excel':
        return export_to_excel(statistics)

    return render(request, 'dashboard/test_statistics.html', context)

def export_to_excel(statistics):
    output = BytesIO()
    workbook = xlsxwriter.Workbook(output)
    worksheet = workbook.add_worksheet()

    # Add headers in Russian
    headers = [
        'Пользователь', 'Регион', 'Школа', 'Дата завершения', 'Затраченное время (мин)',
        'Правильные ответы', 'Неправильные ответы', 'Всего вопросов', 'Результат (%)'
    ]
    for col, header in enumerate(headers):
        worksheet.write(0, col, header)

    # Add data
    for row, stat in enumerate(statistics, 1):
        worksheet.write(row, 0, f"{stat['user__username']}")
        worksheet.write(row, 1, str(stat['user__region__name']))
        worksheet.write(row, 2, stat['user__school'])
        worksheet.write(row, 3, stat['completed_date'].strftime('%Y-%m-%d %H:%M'))
        worksheet.write(row, 4, stat['time_spent'])
        worksheet.write(row, 5, stat['correct_answers'])
        worksheet.write(row, 6, stat['total_questions'] - stat['correct_answers'])
        worksheet.write(row, 7, stat['total_questions'])
        worksheet.write(row, 8, (stat['correct_answers'] / stat['total_questions']) * 100)

    workbook.close()
    output.seek(0)

    response = HttpResponse(
        output.read(),
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )
    response['Content-Disposition'] = 'attachment; filename=статистика_тестов.xlsx'
    return response