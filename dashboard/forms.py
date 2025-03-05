from django import forms
from django.forms import ModelForm
from .models import AddStudent
from accounts.models import Region, User
from decimal import Decimal

class AddStudentForm(ModelForm):
    class Meta:
        model=AddStudent
        fields=['excel_file']

        widgets = {
        'excel_file': forms.FileInput(attrs={'class':'form-control'}),
    }

class AddBalanceForm(forms.Form):
    FILTER_CHOICES = [
        ('all', 'All Users'),
        ('region', 'By Region'),
        ('school', 'By School'),
        ('specific', 'Specific User')
    ]
    
    filter_type = forms.ChoiceField(
        choices=FILTER_CHOICES,
        widget=forms.Select(attrs={'class': 'form-control', 'id': 'filter-type'})
    )
    
    region = forms.ModelChoiceField(
        queryset=Region.objects.all(),
        required=False,
        widget=forms.Select(attrs={'class': 'form-control', 'id': 'region-select'})
    )
    
    school = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control', 'id': 'school-input'})
    )
    
    username = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control', 'id': 'username-input', 'placeholder': 'Enter IIN'})
    )
    
    amount = forms.DecimalField(
        max_digits=10,
        decimal_places=2,
        min_value=Decimal('0.01'),
        widget=forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'})
    )
    
    def clean(self):
        cleaned_data = super().clean()
        filter_type = cleaned_data.get('filter_type')
        region = cleaned_data.get('region')
        school = cleaned_data.get('school')
        username = cleaned_data.get('username')
        
        if filter_type == 'region' and not region:
            self.add_error('region', 'Region is required when filtering by region')
        
        if filter_type == 'school' and not school:
            self.add_error('school', 'School name is required when filtering by school')
        
        if filter_type == 'specific' and not username:
            self.add_error('username', 'Username (IIN) is required when selecting a specific user')
            
        if filter_type == 'specific' and username:
            try:
                User.objects.get(username=username)
            except User.DoesNotExist:
                self.add_error('username', 'User with this IIN does not exist')
                
        return cleaned_data