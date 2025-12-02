from django.contrib import admin
from django.contrib.auth import get_user_model
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import SubscriptionPlan, Subscription, SMSUsage, Payment, UserNotificationSettings, FavoriteCalendar

User = get_user_model()

@admin.register(User)
class CustomUserAdmin(BaseUserAdmin):
    # Wyświetlaj kolumnę z grupami na liście użytkowników
    list_display = ['username', 'email', 'is_staff', 'is_active']
    # Pozwól przy tworzeniu i edytowaniu użytkowników wybierać grupy
    filter_horizontal = ('groups', 'user_permissions')


@admin.register(SubscriptionPlan)
class SubscriptionPlanAdmin(admin.ModelAdmin):
    list_display = ['display_name', 'name', 'price_monthly', 'sms_included', 'is_active']
    list_filter = ['is_active', 'name']
    search_fields = ['display_name', 'name']
    readonly_fields = ['created_at', 'updated_at']
    
    fieldsets = (
        ('Podstawowe informacje', {
            'fields': ('name', 'display_name', 'description', 'is_active')
        }),
        ('Cena', {
            'fields': ('price_monthly',)
        }),
        ('SMS', {
            'fields': ('sms_included', 'sms_price_per_extra')
        }),
        ('Metadane', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(Subscription)
class SubscriptionAdmin(admin.ModelAdmin):
    list_display = ['user', 'plan', 'status', 'start_date', 'end_date', 'is_active_display']
    list_filter = ['status', 'plan', 'start_date']
    search_fields = ['user__username', 'user__email']
    readonly_fields = ['created_at', 'updated_at', 'start_date']
    
    fieldsets = (
        ('Użytkownik', {
            'fields': ('user', 'plan')
        }),
        ('Okresy', {
            'fields': ('start_date', 'end_date', 'status')
        }),
        ('Integracja HotPay', {
            'fields': ('hotpay_transaction_id',),
            'classes': ('collapse',)
        }),
        ('Metadane', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def is_active_display(self, obj):
        return '✓' if obj.is_active() else '✗'
    is_active_display.short_description = 'Aktywna'


@admin.register(SMSUsage)
class SMSUsageAdmin(admin.ModelAdmin):
    list_display = ['subscription', 'month', 'year', 'sms_count', 'extra_sms_cost']
    list_filter = ['year', 'month', 'subscription__plan']
    search_fields = ['subscription__user__username']
    readonly_fields = ['created_at', 'updated_at']
    
    fieldsets = (
        ('Subskrypcja', {
            'fields': ('subscription',)
        }),
        ('Okres', {
            'fields': ('year', 'month')
        }),
        ('SMS', {
            'fields': ('sms_count', 'extra_sms_cost')
        }),
        ('Metadane', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ['payment_id', 'user', 'amount', 'status', 'created_at']
    list_filter = ['status', 'created_at']
    search_fields = ['payment_id', 'user__username', 'user__email']
    readonly_fields = ['payment_id', 'created_at', 'completed_at', 'hotpay_response']
    
    fieldsets = (
        ('Płatność', {
            'fields': ('payment_id', 'status', 'amount')
        }),
        ('Użytkownik i Subskrypcja', {
            'fields': ('user', 'subscription')
        }),
        ('HotPay', {
            'fields': ('hotpay_payment_id', 'hotpay_response'),
            'classes': ('collapse',)
        }),
        ('Okresy', {
            'fields': ('created_at', 'completed_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(UserNotificationSettings)
class UserNotificationSettingsAdmin(admin.ModelAdmin):
    list_display = ['user', 'booking_created_notifications', 'sms_reminders_enabled']
    search_fields = ['user__username', 'user__email']
    readonly_fields = ['created_at', 'updated_at']
    
    fieldsets = (
        ('Użytkownik', {
            'fields': ('user',)
        }),
        ('Powiadomienia', {
            'fields': (
                'booking_created_notifications',
                'booking_cancelled_notifications',
                'own_booking_confirmations',
                'sms_reminders_enabled'
            )
        }),
        ('Metadane', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(FavoriteCalendar)
class FavoriteCalendarAdmin(admin.ModelAdmin):
    list_display = ['user', 'calendar_name', 'calendar_token', 'added_at']
    list_filter = ['added_at']
    search_fields = ['user__username', 'calendar_name']
    readonly_fields = ['calendar_token', 'added_at']