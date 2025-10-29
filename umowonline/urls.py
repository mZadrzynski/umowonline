from django.contrib import admin
from django.urls import path, include
from . import views
from myschedule.views_public import redirect_username_to_token, public_calendar_week
from django.contrib.sitemaps.views import sitemap
from django.http import HttpResponse
from django.views.decorators.http import require_http_methods
from django.conf import settings
from django.conf.urls.static import static


# Importuj sitemaps
from sitemaps import StaticSitemap

# Sitemaps
sitemaps = {
    'static': StaticSitemap(),
}
# Robots.txt view
@require_http_methods(["GET"])
def robots_txt(request):
    """View do obsługi robots.txt"""
    content = """User-agent: *
Allow: /
Disallow: /admin/
Disallow: /account/
Disallow: /dashboard/
Disallow: /myschedule/
Disallow: /captcha/
Disallow: /social-auth/
Disallow: /api/

Sitemap: https://umowzdalnie.pl/sitemap.xml
"""
    return HttpResponse(content, content_type='text/plain')

urlpatterns = [
    path('admin/', admin.site.urls),
    path('blog/', include('blog.urls')),

    # SITEMAP I ROBOTS - DODAJ TUTAJ
    path('sitemap.xml', sitemap, {'sitemaps': sitemaps}, name='django.contrib.sitemaps.views.sitemap'),
    path('robots.txt', robots_txt, name='robots'),
    
    path('', views.home, name='home'),
    path('<str:username>/', redirect_username_to_token, name='public_calendar_username'),
    path('account/', include('account.urls')),
    path('dashboard/', include('dashboard.urls')),
    path("myschedule/", include("myschedule.urls")),
    path('captcha/', include('captcha.urls')),
    path('tinymce/', include('tinymce.urls')), 
    path(
        'social-auth/',
        include('social_django.urls', namespace='social')
    ),
]
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
