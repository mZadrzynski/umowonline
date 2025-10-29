from django.contrib import admin
from django.utils.html import format_html
from tinymce.widgets import TinyMCE
from django import forms
from .models import Post

class PostAdminForm(forms.ModelForm):
    class Meta:
        model = Post
        fields = '__all__'
        widgets = {
            'content': TinyMCE(),  # ← TINYMCE W TREŚCI
        }

@admin.register(Post)
class PostAdmin(admin.ModelAdmin):
    form = PostAdminForm  # ← UŻYJ FORMY Z TINYMCE
    
    list_display = ['title', 'author', 'status_badge', 'created_at']
    list_filter = ['published', 'created_at', 'author']
    search_fields = ['title', 'content', 'excerpt']
    date_hierarchy = 'created_at'
    
    fieldsets = (
        ('Podstawowe informacje', {
            'fields': ('title', 'slug', 'author')
        }),
        ('Zawartość', {
            'fields': ('excerpt', 'content', 'featured_image'),
            'classes': ('wide',)
        }),
        ('SEO & Publikacja', {
            'fields': ('published', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    readonly_fields = ['created_at', 'updated_at', 'author']
    prepopulated_fields = {'slug': ('title',)}
    
    def save_model(self, request, obj, form, change):
        if not obj.pk:
            obj.author = request.user
        super().save_model(request, obj, form, change)
    
    def status_badge(self, obj):
        if obj.published:
            return format_html(
                '<span style="background-color: #28a745; color: white; padding: 3px 8px; border-radius: 3px;">Opublikowany</span>'
            )
        else:
            return format_html(
                '<span style="background-color: #dc3545; color: white; padding: 3px 8px; border-radius: 3px;">Szkic</span>'
            )
    status_badge.short_description = 'Status'