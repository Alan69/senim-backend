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
        'user__region',
        'product'
    ).prefetch_related(
        'completed_questions',
        'completed_questions__question',
        'completed_questions__selected_option',
        'completed_questions__test'
    )

    # Apply filters
    if region_id and region_id != '':
        completed_tests = completed_tests.filter(user__region_id=region_id)
    if school:
        completed_tests = completed_tests.filter(user__school__icontains=school)
    if start_date:
        completed_tests = completed_tests.filter(completed_date__gte=start_date)
    if end_date:
        completed_tests = completed_tests.filter(completed_date__lte=end_date)

    # Order by completed date
    completed_tests = completed_tests.order_by('-completed_date')

    # Handle Excel export before pagination
    if request.GET.get('export') == 'excel':
        return export_to_excel(completed_tests)

    # Paginate the queryset first
    paginator = Paginator(completed_tests, 50)
    page_obj = paginator.get_page(page)

    # Process only the current page's results
    statistics = []
    for completed_test in page_obj:
        # Dictionary to store test-specific statistics
        test_stats = {}
        correct_answers = 0
        wrong_answers = 0
        
        # Get all completed questions for this test in one query
        completed_questions = completed_test.completed_questions.all()
        
        for question in completed_questions:
            test = question.test
            test_title = test.title
            
            # Initialize test stats if not already present
            if test_title not in test_stats:
                test_stats[test_title] = {
                    'correct': 0,
                    'incorrect': 0,
                    'total': 0
                }
            
            # Check if any selected option is correct
            selected_options = list(question.selected_option.all())  # Convert to list to avoid multiple queries
            has_correct = any(option.is_correct for option in selected_options)
            
            # Update statistics
            if has_correct:
                correct_answers += 1
                test_stats[test_title]['correct'] += 1
            else:
                wrong_answers += 1
                test_stats[test_title]['incorrect'] += 1
            
            test_stats[test_title]['total'] += 1
        
        total_questions = correct_answers + wrong_answers
        score_percentage = round((correct_answers / total_questions) * 100, 2) if total_questions > 0 else 0
        
        # Convert test_stats dictionary to a list
        test_statistics = [
            {
                'name': test_name,
                'correct': stats['correct'],
                'incorrect': stats['incorrect'],
                'total': stats['total'],
                'percentage': round((stats['correct'] / stats['total']) * 100, 2) if stats['total'] > 0 else 0
            }
            for test_name, stats in test_stats.items()
        ]
        
        statistics.append({
            'completed_test': completed_test,
            'user': completed_test.user,
            'region': completed_test.user.region,
            'school': completed_test.user.school,
            'completed_date': completed_test.completed_date,
            'correct_answers': correct_answers,
            'wrong_answers': wrong_answers,
            'total_questions': total_questions,
            'score_percentage': score_percentage,
            'test_statistics': test_statistics
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

def export_to_excel(completed_tests):
    output = BytesIO()
    workbook = xlsxwriter.Workbook(output, {'constant_memory': True})
    
    # Create formats
    header_format = workbook.add_format({
        'bold': True,
        'align': 'center',
        'valign': 'vcenter',
        'bg_color': '#f0f0f0'
    })
    
    # Create worksheet with basic structure first
    worksheet = workbook.add_worksheet('Общая статистика')
    
    # Define base headers
    base_headers = [
        'Пользователь', 'Регион', 'Школа', 'Дата завершения',
        'Тест', 'Правильных', 'Неправильных', 'Всего вопросов', 'Результат (%)',
        'Всего правильных', 'Всего неправильных', 'Всего вопросов', 'Общий результат (%)'
    ]
    
    # Set column widths for better readability
    worksheet.set_column(0, 0, 30)  # User name
    worksheet.set_column(1, 1, 20)  # Region
    worksheet.set_column(2, 2, 20)  # School
    worksheet.set_column(3, 3, 20)  # Date
    worksheet.set_column(4, 4, 30)  # Test name
    worksheet.set_column(5, 12, 15)  # Other columns
    
    # Write headers
    for col, header in enumerate(base_headers):
        worksheet.write(0, col, header, header_format)
    
    # Process and write data in chunks
    row = 1
    for completed_test in completed_tests.iterator():
        try:
            # Get all completed questions for this test in one query
            completed_questions = list(completed_test.completed_questions.all().select_related('test'))
            
            if not completed_questions:  # Skip if no questions
                continue
            
            # Group questions by test
            test_stats = {}
            total_correct = 0
            total_wrong = 0
            
            for question in completed_questions:
                try:
                    # Get test ID and title safely
                    test_id = question.test_id
                    test_title = question.test.title if hasattr(question.test, 'title') else f"Test {test_id}"
                    
                    # Initialize test stats if not already present
                    if test_id not in test_stats:
                        test_stats[test_id] = {
                            'title': test_title,
                            'correct': 0,
                            'wrong': 0,
                            'total': 0
                        }
                    
                    # Check if any selected option is correct
                    selected_options = list(question.selected_option.all())
                    has_correct = any(option.is_correct for option in selected_options)
                    
                    # Update statistics
                    if has_correct:
                        test_stats[test_id]['correct'] += 1
                        total_correct += 1
                    else:
                        test_stats[test_id]['wrong'] += 1
                        total_wrong += 1
                    
                    test_stats[test_id]['total'] += 1
                    
                except Exception as e:
                    print(f"Error processing question {question.id}: {str(e)}")
                    continue
            
            # Calculate totals
            total_questions = total_correct + total_wrong
            overall_percentage = round((total_correct / total_questions) * 100, 2) if total_questions > 0 else 0
            
            # Write one row per test for this user
            user_name = f"{completed_test.user.first_name} {completed_test.user.last_name}"
            region = str(completed_test.user.region)
            school = completed_test.user.school
            date = completed_test.completed_date.strftime('%Y-%m-%d %H:%M')
            
            # Sort tests by title for consistent ordering
            sorted_tests = sorted(test_stats.values(), key=lambda x: x['title'])
            
            for test_stat in sorted_tests:
                # Calculate test-specific percentage
                test_percentage = round((test_stat['correct'] / test_stat['total']) * 100, 2) if test_stat['total'] > 0 else 0
                
                # Write data
                worksheet.write(row, 0, user_name)
                worksheet.write(row, 1, region)
                worksheet.write(row, 2, school)
                worksheet.write(row, 3, date)
                worksheet.write(row, 4, test_stat['title'])
                worksheet.write(row, 5, test_stat['correct'])
                worksheet.write(row, 6, test_stat['wrong'])
                worksheet.write(row, 7, test_stat['total'])
                worksheet.write(row, 8, test_percentage)
                worksheet.write(row, 9, total_correct)
                worksheet.write(row, 10, total_wrong)
                worksheet.write(row, 11, total_questions)
                worksheet.write(row, 12, overall_percentage)
                
                row += 1
                
        except Exception as e:
            # Log the error but continue processing other records
            print(f"Error processing completed test {completed_test.id}: {str(e)}")
            continue
    
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