from django.shortcuts import render
from .forms import RequestTestForm
from django.http import HttpResponse
from accounts.models import User

def create_custom_user(username, password, user_school, user_region, first_name, last_name):
    user = User.objects.create_user(
        username=username,
        password=password,
        first_name=first_name,  # Get the first word as first_name
        last_name=last_name,   # Get the second word as last_name
    )
    user.school = user_school
    user.region = user_region
    user.is_teacher = True
    user.is_staff = True
    user.save()
    return user

def request_page(request):
    if request.method == 'POST':
        form = RequestTestForm(request.POST, request.FILES)
        if form.is_valid():
            # Create a custom user
            iin = form.cleaned_data['iin']
            school = form.cleaned_data['school']
            region = form.cleaned_data['region']
            name = form.cleaned_data['name']
            
            user = create_custom_user(
                username=iin,
                password=iin,
                user_school=school,
                user_region=region,
                first_name=name.split()[0],
                last_name=name.split()[1],
            )
            form.save()
            # TODO render template
            return HttpResponse("Запрос отправлен")
    else:
        form = RequestTestForm()
    return render(request, 'test_request/request.html', {'form': form})