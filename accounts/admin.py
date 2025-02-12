from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.forms import PasswordResetForm
from django.utils.html import format_html
from .models import User, Region
from .forms import UserCreationForm, UserChangeForm

class UserAdmin(BaseUserAdmin):
    form = UserChangeForm
    add_form = UserCreationForm

    list_display = ('username', 'balance', 'first_name', 'last_name', 'region', 'school', 'email', 'phone_number', 'is_student', 'is_teacher', 'is_principal', 'is_staff', 'is_active', 'is_superuser', 'password_reset_button')
    list_filter = ('is_student', 'is_teacher', 'is_principal', 'is_staff', 'is_active', 'is_superuser', 'region')
    fieldsets = (
        (None, {'fields': ('username', 'password')}),
        ('Personal info', {'fields': ('first_name', 'last_name', 'region', 'email', 'phone_number', 'school', 'balance', 'payment_id', 'test_is_started')}),
        ('Permissions', {'fields': ('is_active', 'is_student', 'is_teacher', 'is_principal', 'is_staff', 'is_superuser', 'groups', 'user_permissions')}),
    )
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('username', 'first_name', 'last_name', 'region', 'school', 'email', 'phone_number', 'password1', 'password2', 'is_student', 'is_teacher', 'is_principal')}
        ),
    )
    search_fields = ('username', 'first_name', 'last_name')
    ordering = ('username',)
    filter_horizontal = ('groups', 'user_permissions',)

    def password_reset_button(self, obj):
        return format_html(
            '<a class="button" href="{}?next={}" style="background-color: #447e9b; padding: 5px 10px; color: white; text-decoration: none; border-radius: 4px;">Reset Password</a>',
            f"/admin/password_reset/",
            f"/admin/accounts/user/{obj.pk}/change/"
        )
    password_reset_button.short_description = 'Reset Password'
    password_reset_button.allow_tags = True

    actions = ['send_password_reset_email']

    def send_password_reset_email(self, request, queryset):
        for user in queryset:
            form = PasswordResetForm({'email': user.email})
            if form.is_valid():
                form.save(
                    request=request,
                    use_https=request.is_secure(),
                    subject_template_name='registration/password_reset_subject.txt',
                    email_template_name='registration/password_reset_email.html',
                )
        self.message_user(request, f"Password reset emails sent to {queryset.count()} users")
    send_password_reset_email.short_description = "Send password reset email to selected users"

admin.site.register(User, UserAdmin)


@admin.register(Region)
class RegionAdmin(admin.ModelAdmin):
    list_display = ('name', 'region_type', 'description')
    search_fields = ('name',)
    list_filter = ('region_type',)
