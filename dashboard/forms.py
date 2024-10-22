from django import forms
from django.forms import ModelForm
from .models import AddStudent

class AddStudentForm(ModelForm):
    class Meta:
        model=AddStudent
        fields=['excel_file']

        widgets = {
        'excel_file': forms.FileInput(attrs={'class':'form-control'}),
    }