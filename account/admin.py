from django.contrib import admin
from django.contrib.auth import get_user_model
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin

User = get_user_model()

@admin.register(User)
class CustomUserAdmin(BaseUserAdmin):
    # Wyświetlaj kolumnę z grupami na liście użytkowników
    list_display = ['username', 'email', 'is_staff', 'is_active']
    # Pozwól przy tworzeniu i edytowaniu użytkowników wybierać grupy
    filter_horizontal = ('groups', 'user_permissions')