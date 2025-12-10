# catalog/models.py

from django.db import models
from django.conf import settings
from django.utils.text import slugify
from django.urls import reverse


class BusinessProfile(models.Model):
    """Profil firmy w katalogu"""
    
    # Relacja z użytkownikiem (FK - jeden user może mieć wiele profili)
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='business_profiles'
    )
    
    # Relacja z kalendarzem (opcjonalna - FK zamiast OneToOne!)
    # Jeden kalendarz może mieć kilka profili biznesowych
    calendar = models.ForeignKey(
        'myschedule.Calendar',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='business_profiles',
        help_text="Powiąż z kalendarzem aby pokazać dostępne terminy"
    )
    
    # Podstawowe info
    business_name = models.CharField(
        max_length=255,
        help_text="Nazwa firmy"
    )
    
    owner_name = models.CharField(
        max_length=255,
        help_text="Imię i nazwisko właściciela/menedżera"
    )
    
    slug = models.SlugField(
        unique=True,
        allow_unicode=True,
        help_text="URL-friendly nazwa (auto-generowana)"
    )
    
    description = models.TextField(
        help_text="Opis usług, doświadczenia, itp."
    )
    
    # Kontakt
    email = models.EmailField()
    
    phone = models.CharField(
        max_length=20,
        blank=True,
        help_text="Numer telefonu (opcjonalnie)"
    )
    
    website = models.URLField(
        blank=True,
        help_text="Link do strony internetowej (opcjonalnie)"
    )
    
    # Media
    logo = models.ImageField(
        upload_to='catalog/logos/',
        blank=True,
        null=True,
        help_text="Logo firmy (200x200 px)"
    )
    
    cover_image = models.ImageField(
        upload_to='catalog/covers/',
        blank=True,
        null=True,
        help_text="Zdjęcie na tle (1200x400 px)"
    )
    
    # Status
    is_active = models.BooleanField(
        default=True,
        help_text="Czy profil widoczny w katalogu?"
    )
    
    is_featured = models.BooleanField(
        default=False,
        help_text="Wyróżnij w katalogu?"
    )
    
    # Meta
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-is_featured', '-created_at']
        verbose_name = "Profil biznesowy"
        verbose_name_plural = "Profile biznesowe"
        indexes = [
            models.Index(fields=['owner', 'is_active']),
            models.Index(fields=['slug']),
        ]
    
    def save(self, *args, **kwargs):
        # Auto-generuj slug z business_name
        if not self.slug:
            self.slug = slugify(self.business_name, allow_unicode=True)
        super().save(*args, **kwargs)
    
    def get_absolute_url(self):
        """URL do szczegółów profilu"""
        return reverse('catalog:business_detail', kwargs={'slug': self.slug})
    
    def __str__(self):
        return f"{self.business_name} ({self.owner.username})"


class Service(models.Model):
    """Usługi oferowane przez firmę"""
    
    profile = models.ForeignKey(
        BusinessProfile,
        on_delete=models.CASCADE,
        related_name='services'
    )
    
    name = models.CharField(
        max_length=255,
        help_text="Nazwa usługi (np. Konsultacja, Trening)"
    )
    
    description = models.TextField(
        blank=True,
        help_text="Szczegółowy opis usługi"
    )
    
    duration_minutes = models.IntegerField(
        default=60,
        help_text="Czas trwania w minutach"
    )
    
    price = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        blank=True,
        null=True,
        help_text="Cena (PLN) - opcjonalnie"
    )
    
    is_active = models.BooleanField(
        default=True
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['name']
    
    def __str__(self):
        return f"{self.name} ({self.profile.business_name})"


class Review(models.Model):
    """Opinie o profilu"""
    
    profile = models.ForeignKey(
        BusinessProfile,
        on_delete=models.CASCADE,
        related_name='reviews'
    )
    
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='given_reviews'
    )
    
    rating = models.IntegerField(
        choices=[(i, f"{i} ⭐") for i in range(1, 6)],
        default=5
    )
    
    comment = models.TextField()
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']
        unique_together = ['profile', 'author']  # Jedno review na użytkownika
    
    def __str__(self):
        return f"Review: {self.profile.business_name} ({self.rating}⭐)"
