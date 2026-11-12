from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import User


@admin.register(User)
class CustomUserAdmin(UserAdmin):
    list_display = ('username', 'display_name', 'phone', 'email', 'role', 'gender', 'is_suspended', 'is_staff')
    list_filter = ('role', 'gender', 'is_suspended', 'is_staff', 'is_superuser')
    search_fields = ('username', 'first_name', 'last_name', 'phone', 'email')
    ordering = ('-date_joined',)
    
    fieldsets = UserAdmin.fieldsets + (
        ('معلومات إضافية', {
            'fields': ('phone', 'gender', 'role', 'avatar', 'bio', 'is_suspended')
        }),
    )
    add_fieldsets = UserAdmin.add_fieldsets + (
        ('معلومات إضافية', {
            'fields': ('phone', 'email', 'first_name', 'last_name', 'gender', 'role', 'bio')
        }),
    )
