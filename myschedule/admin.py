from django.contrib import admin
from .models import Booking

@admin.register(Booking)
class BookingAdmin(admin.ModelAdmin):
    list_display = ['id', 'client_name', 'client_phone', 'start_datetime', 'status', 'reminder_sent', 'reminder_sent_at']
    list_filter = ['status', 'reminder_sent', 'start_datetime']
    search_fields = ['client_name', 'client_phone', 'client_email']
    readonly_fields = ['booked_at', 'reminder_sent_at']
    
    fieldsets = (
        ('Informacje o wizycie', {
            'fields': ('availability', 'service_type', 'start_datetime', 'status')
        }),
        ('Dane klienta', {
            'fields': ('client_name', 'client_phone', 'client_email', 'client_note')
        }),
        ('SMS Reminder', {
            'fields': ('reminder_sent', 'reminder_sent_at'),
            'classes': ('collapse',)
        }),
        ('Metadane', {
            'fields': ('booked_at', 'booked_by'),
            'classes': ('collapse',)
        }),
    )