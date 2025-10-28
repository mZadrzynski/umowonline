from django.contrib import admin
from django.utils.html import format_html
from .models import Post

@admin.register(Post)
class PostAdmin(admin.ModelAdmin):
    # === LISTA POSTÓW ===
    list_display = ['title', 'author', 'status_badge', 'created_at', 'actions_links']
    list_filter = ['published', 'created_at', 'author']
    search_fields = ['title', 'content', 'excerpt']
    date_hierarchy = 'created_at'  # ← Super fajne - sortowanie po datach
    
    # === EDYCJA POSTA ===
    fieldsets = (
        ('Podstawowe informacje', {
            'fields': ('title', 'slug', 'author')
        }),
        ('Zawartość', {
            'fields': ('excerpt', 'content', 'featured_image'),
            'classes': ('wide',)  # Szersze pola
        }),
        ('SEO & Publikacja', {
            'fields': ('published', 'created_at', 'updated_at'),
            'classes': ('collapse',)  # ← Zwinięte na start
        }),
    )
    
    # === READONLY (nie można edytować) ===
    readonly_fields = ['created_at', 'updated_at', 'author']
    
    # === SLUG AUTO-GENERATE ===
    prepopulated_fields = {'slug': ('title',)}  # Slug auto-generuje się z tytułu
    
    # === AKCJE ===
    actions = ['publish_posts', 'unpublish_posts']
    
    # === AUTO-USTAWIANIE AUTORA ===
    def save_model(self, request, obj, form, change):
        if not obj.pk:  # Jeśli nowy post
            obj.author = request.user
        super().save_model(request, obj, form, change)
    
    # === STATUS BADGE (zielony/czerwony) ===
    def status_badge(self, obj):
        if obj.published:
            return format_html(
                '<span style="background-color: #28a745; color: white; padding: 3px 8px; border-radius: 3px; font-size: 11px;">Opublikowany</span>'
            )
        else:
            return format_html(
                '<span style="background-color: #dc3545; color: white; padding: 3px 8px; border-radius: 3px; font-size: 11px;">Szkic</span>'
            )
    status_badge.short_description = 'Status'
    
    # === LINKI DO AKCJI ===
    def actions_links(self, obj):
        if obj.published:
            view_url = f"/{obj.slug}/"  # Dostosuj do Twojego URLa
            return format_html(
                '<a class="button" href="{}" target="_blank">Podgląd</a>',
                view_url
            )
        return '-'
    actions_links.short_description = 'Akcje'
    
    # === AKCJE ZBIORCZE ===
    def publish_posts(self, request, queryset):
        updated = queryset.update(published=True)
        self.message_user(request, f'{updated} postów opublikowanych')
    publish_posts.short_description = "Opublikuj wybrane posty"
    
    def unpublish_posts(self, request, queryset):
        updated = queryset.update(published=False)
        self.message_user(request, f'{updated} postów ukryto')
    unpublish_posts.short_description = "Ukryj wybrane posty"