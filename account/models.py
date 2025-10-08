from django.contrib.auth.models import AbstractUser
from django.db import models
from django.conf import settings
from django.contrib.auth import get_user_model
from django.utils import timezone
from datetime import timedelta

class CustomUser(AbstractUser):
    email = models.EmailField('email address', unique=True)
    username = models.CharField(max_length=150, unique=True)
    phone_number = models.CharField(max_length=20, blank=True, null=True, verbose_name="Numer telefonu")  # NOWE POLE

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username']
    
User = get_user_model()

class UserNotificationSettings(models.Model):
    """Model przechowujący ustawienia powiadomień użytkownika"""
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,  # ✅ Używa AUTH_USER_MODEL z settings
        on_delete=models.CASCADE, 
        related_name='notification_settings'
    )
    
    # Opcje powiadomień
    booking_created_notifications = models.BooleanField(
        default=True, 
        verbose_name="Powiadomienia o nowych wizytach",
        help_text="Otrzymuj email gdy ktoś umawia wizytę w Twoim kalendarzu"
    )
    
    booking_cancelled_notifications = models.BooleanField(
        default=True,
        verbose_name="Powiadomienia o anulowanych wizytach", 
        help_text="Otrzymuj email gdy ktoś anuluje wizytę"
    )
    
    own_booking_confirmations = models.BooleanField(
        default=True,
        verbose_name="Potwierdzenia własnych wizyt",
        help_text="Otrzymuj email po umówieniu wizyty u kogoś"
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "Ustawienia powiadomień użytkownika"
        verbose_name_plural = "Ustawienia powiadomień użytkowników"
    
    def __str__(self):
        return f"Ustawienia powiadomień - {self.user.username}"


class Subscription(models.Model):
    SUBSCRIPTION_STATUS = [
        ('active', 'Aktywna'),
        ('expired', 'Wygasła'),
        ('cancelled', 'Anulowana'),
    ]
    
    # Użyj get_user_model() zamiast bezpośredniego importu User
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='subscription')
    start_date = models.DateTimeField(default=timezone.now)
    end_date = models.DateTimeField()
    status = models.CharField(max_length=20, choices=SUBSCRIPTION_STATUS, default='active')
    hotpay_transaction_id = models.CharField(max_length=100, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def is_active(self):
        return (
            self.status == 'active' and 
            timezone.now() <= self.end_date
        )
    
    def extend_subscription(self, days=30):
        if self.is_active():
            self.end_date += timedelta(days=days)
        else:
            self.start_date = timezone.now()
            self.end_date = timezone.now() + timedelta(days=days)
            self.status = 'active'
        self.save()
    
    def __str__(self):
        return f"{self.user.username} - {self.status}"
    

class FavoriteCalendar(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='favorite_calendars')
    calendar_url = models.URLField(help_text="Link do publicznego kalendarza")
    calendar_name = models.CharField(max_length=100, help_text="Nazwa kalendarza (opcjonalnie)")
    owner_name = models.CharField(max_length=100, blank=True, help_text="Nazwa właściciela")
    added_at = models.DateTimeField(auto_now_add=True)
    
    # Wyciągnij token z URL-a automatycznie przy zapisie
    calendar_token = models.CharField(max_length=12, blank=True, editable=False)
    
    class Meta:
        unique_together = ('user', 'calendar_token')  # użytkownik nie może dodać tego samego kalendarza dwukrotnie
        ordering = ['-added_at']
    
    def save(self, *args, **kwargs):
        # Wyciągnij token z URL-a (np. z https://twoja-domena.com/myschedule/public/abcd1234efgh/)
        import re
        if self.calendar_url:
            match = re.search(r'/public/([a-zA-Z0-9]+)/?', self.calendar_url)
            if match:
                self.calendar_token = match.group(1)
        super().save(*args, **kwargs)
    
    def get_calendar_object(self):
        """Zwraca obiekt Calendar na podstawie tokenu (jeśli istnieje)"""
        from myschedule.models import Calendar
        try:
            return Calendar.objects.get(share_token=self.calendar_token)
        except Calendar.DoesNotExist:
            return None
    
    def __str__(self):
        return f"{self.user.username} -> {self.calendar_name or self.calendar_token}"
    

class Payment(models.Model):
    PAYMENT_STATUS = [
        ('pending', 'Oczekująca'),
        ('completed', 'Zakończona'),
        ('failed', 'Nieudana'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='payments')
    subscription = models.ForeignKey(Subscription, on_delete=models.CASCADE, related_name='payments')
    amount = models.DecimalField(max_digits=10, decimal_places=2, default=20.00)
    payment_id = models.CharField(max_length=100, unique=True)
    hotpay_payment_id = models.CharField(max_length=100, blank=True, null=True)
    status = models.CharField(max_length=20, choices=PAYMENT_STATUS, default='pending')
    created_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(blank=True, null=True)
    hotpay_response = models.JSONField(blank=True, null=True)