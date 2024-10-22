from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import User, Region
from .forms import UserCreationForm, UserChangeForm

class UserAdmin(BaseUserAdmin):
    form = UserChangeForm
    add_form = UserCreationForm

    list_display = ('username', 'first_name', 'last_name', 'region', 'school', 'email', 'phone_number', 'is_student', 'is_teacher', 'is_principal', 'is_staff', 'is_active', 'is_superuser')
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

admin.site.register(User, UserAdmin)


@admin.register(Region)
class RegionAdmin(admin.ModelAdmin):
    list_display = ('name', 'region_type', 'description')
    search_fields = ('name',)
    list_filter = ('region_type',)
