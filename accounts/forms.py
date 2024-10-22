from django import forms
from django.contrib.auth.forms import ReadOnlyPasswordHashField, PasswordChangeForm
from .models import User, Region

class UserCreationForm(forms.ModelForm):
    """
    A form for creating new users. Includes all the required fields, plus a repeated password.
    """
    password1 = forms.CharField(label='Password', widget=forms.PasswordInput)
    password2 = forms.CharField(label='Password confirmation', widget=forms.PasswordInput)

    class Meta:
        model = User
        fields = ['username', 'first_name', 'last_name', 'region', 'school', 'email', 'phone_number',  'is_student', 'is_teacher', 'is_principal']

    def clean_password2(self):
        # Check that the two password entries match
        password1 = self.cleaned_data.get("password1")
        password2 = self.cleaned_data.get("password2")
        if password1 and password2 and password1 != password2:
            raise forms.ValidationError("Passwords don't match")
        return password2

    def save(self, commit=True):
        # Save the provided password in hashed format
        user = super().save(commit=False)
        user.set_password(self.cleaned_data["password1"])
        if commit:
            user.save()
        return user
    
class UserChangeFormCustom(forms.ModelForm):
    class Meta:
        model = User
        fields = ['email', 'phone_number', 'region', 'school']

    email = forms.EmailField(
        label="Электронный адрес",
        widget=forms.EmailInput(attrs={'class': 'form-control'}),
    )
    phone_number = forms.CharField(
        label="Контактный телефон",
        widget=forms.TextInput(attrs={'class': 'form-control'}),
    )
    region = forms.ModelChoiceField(
        queryset=Region.objects.all(),
        label="Регион",
        widget=forms.Select(attrs={'class': 'form-control'}),
    )
    school = forms.CharField(
        label="Образовательное учреждение",
        widget=forms.TextInput(attrs={'class': 'form-control'}),
    )    

class UserChangeForm(forms.ModelForm):
    """
    A form for updating users. Includes all the fields on the user, but replaces the password field
    with admin's password hash display field.
    """
    password = ReadOnlyPasswordHashField()

    class Meta:
        model = User
        fields = ['username', 'first_name', 'last_name', 'region', 'school', 'email', 'phone_number',  'password', 'is_active', 'is_student', 'is_teacher', 'is_principal', 'is_staff']

    def clean_password(self):
        # Regardless of what the user provides, return the initial value.
        # This is done here, rather than on the field, because the field does not have access to the initial value
        return self.initial["password"]

class CustomPasswordChangeForm(PasswordChangeForm):
    old_password = forms.CharField(
        label="Старый пароль",
        strip=False,
        widget=forms.PasswordInput(attrs={'autocomplete': 'current-password', 'class': 'form-control'}),
    )
    new_password1 = forms.CharField(
        label="Новый пароль",
        strip=False,
        widget=forms.PasswordInput(attrs={'autocomplete': 'new-password', 'class': 'form-control'}),
        help_text="Пароль должен содержать как минимум 8 символов, не должен быть слишком простым и должен отличаться от предыдущего.",
    )
    new_password2 = forms.CharField(
        label="Подтвердите новый пароль",
        strip=False,
        widget=forms.PasswordInput(attrs={'autocomplete': 'new-password', 'class': 'form-control'}),
    )

class BalanceTransferForm(forms.Form):
    recipient_username = forms.CharField(label="Recipient's IIN")
    amount = forms.DecimalField(max_digits=10, decimal_places=2)

    def clean_recipient_username(self):
        username = self.cleaned_data.get('recipient_username')
        try:
            recipient = User.objects.get(username=username)
        except User.DoesNotExist:
            raise forms.ValidationError("Recipient not found.")
        
        if not recipient.is_student:
            raise forms.ValidationError("Recipient must be a student.")
        
        return username