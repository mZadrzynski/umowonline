from django.contrib.sitemaps import Sitemap
from django.urls import reverse

class StaticSitemap(Sitemap):
    """Sitemap dla stron publicznych umowzdalnie.pl"""
    changefreq = "weekly"
    priority = 0.8

    def items(self):
        """
        Tutaj wymieniamy WSZYSTKIE stany URL-y które chcemy w sitemapie.
        Na podstawie Twojego urlpatterns:
        """
        return [
            'home',                      # strona główna
            'register',                  # rejestracja
            'contact',                   # kontakt
            'help',                      # pomoc
            'terms_of_service',          # regulamin
            'privacy_policy',            # polityka prywatności
            'offert',                    # oferta
            'instructions',              # instrukcje
        ]
    
    def location(self, item):
        """Zwraca URL dla każdego itemu"""
        return reverse(item)