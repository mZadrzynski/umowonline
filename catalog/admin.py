from django.contrib import admin

# Register your models here.
# catalog/admin.py

from django.contrib import admin
from django.utils.html import format_html
from .models import BusinessProfile, Service, Review


@admin.register(BusinessProfile)
class BusinessProfileAdmin(admin.ModelAdmin):
    list_display = ['business_name', 'owner', 'is_active', 'is_featured', 'created_at']
    list_filter = ['is_active', 'is_featured', 'created_at']
    search_fields = ['business_name', 'owner__username', 'description']
    prepopulated_fields = {'slug': ('business_name',)}
    readonly_fields = ['created_at', 'updated_at', 'logo_preview', 'cover_preview']
    
    fieldsets = (
        ('Podstawowe Info', {
            'fields': ('owner', 'business_name', 'owner_name', 'slug')
        }),
        ('Opis', {
            'fields': ('description',)
        }),
        ('Kontakt', {
            'fields': ('email', 'phone', 'website')
        }),
        ('Media', {
            'fields': ('logo', 'logo_preview', 'cover_image', 'cover_preview')
        }),
        ('Powiązania', {
            'fields': ('calendar',)
        }),
        ('Status', {
            'fields': ('is_active', 'is_featured')
        }),
        ('Meta', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def logo_preview(self, obj):
        if obj.logo:
            return format_html('<img src="{}" width="100" />', obj.logo.url)
        return "Brak"
    logo_preview.short_description = "Podgląd logo"
    
    def cover_preview(self, obj):
        if obj.cover_image:
            return format_html('<img src="{}" width="200" />', obj.cover_image.url)
        return "Brak"
    cover_preview.short_description = "Podgląd okładki"


@admin.register(Service)
class ServiceAdmin(admin.ModelAdmin):
    list_display = ['name', 'profile', 'duration_minutes', 'price', 'is_active']
    list_filter = ['is_active', 'created_at']
    search_fields = ['name', 'profile__business_name']


@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    list_display = ['profile', 'author', 'rating', 'created_at']
    list_filter = ['rating', 'created_at']
    search_fields = ['profile__business_name', 'author__username']
    readonly_fields = ['created_at']
