from django.contrib.sitemaps import Sitemap
from django.urls import reverse
from blog.models import Post  # zmień na swoją nazwę modelu


class StaticSitemap(Sitemap):
    """Sitemap dla stron statycznych umowzdalnie.pl"""
    changefreq = "weekly"
    priority = 0.8

    def items(self):
        """Lista wszystkich stron statycznych"""
        return [
            'home',
            'register',
            'contact',
            'help',
            'terms_of_service',
            'privacy_policy',
            'offert',
            'instructions',
            'blog:post_list',   # główna strona bloga
        ]

    def location(self, item):
        """Zwraca URL dla każdego itemu"""
        return reverse(item)


class BlogPostSitemap(Sitemap):
    """Sitemap dla postów bloga - dynamiczny"""
    changefreq = "weekly"
    priority = 0.9

    def items(self):
        """Zwraca tylko opublikowane posty"""
        return Post.objects.filter(published=True).order_by('-created_at')

    def lastmod(self, obj):
        """Data ostatniej modyfikacji"""
        return obj.updated_at

    def location(self, obj):
        """URL posta"""
        return obj.get_absolute_url()