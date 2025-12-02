from django.contrib.auth.models import AbstractUser
from django.db import models
from django.conf import settings
from django.contrib.auth import get_user_model
from django.utils import timezone
from datetime import timedelta

from django.contrib.auth.models import AbstractUser
from django.core.validators import RegexValidator


username_validator = RegexValidator(
    regex=r'^[a-zA-Z0-9_.-]+$',
    message='Username może zawierać tylko litery, cyfry, kropki, myślniki i podkreślenia.'
)


class CustomUser(AbstractUser):
    email = models.EmailField('email address', unique=True)
    username = models.CharField(
        max_length=150,
        unique=True,  # To jest kluczowe!
        validators=[username_validator],
        help_text='Tylko alfanumeryczne znaki, kropki, myślniki i podkreślenia',
        error_messages={
            'unique': "Użytkownik z taką nazwą już istnieje.",
        },
    )
    phone_number = models.CharField(max_length=20, blank=True, null=True, verbose_name="Numer telefonu")  # NOWE POLE

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username']
    
User = get_user_model()


class SubscriptionPlan(models.Model):
    """Model opisujący dostępne plany subskrypcji"""
    PLAN_CHOICES = [
        ('basic', 'Podstawowy'),
        ('sms', 'SMS'),
    ]
    
    name = models.CharField(max_length=50, choices=PLAN_CHOICES, unique=True)
    display_name = models.CharField(max_length=100, help_text="Nazwa wyświetlana na stronie")
    description = models.TextField(help_text="Opis planu")
    price_monthly = models.DecimalField(max_digits=6, decimal_places=2, help_text="Cena za miesiąc w PLN")
    
    # SMS specific
    sms_included = models.IntegerField(default=0, help_text="Liczba SMS-ów w planie (0 = brak)")
    sms_price_per_extra = models.DecimalField(max_digits=4, decimal_places=2, default=0.10, help_text="Cena za dodatkowy SMS")
    
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "Plan subskrypcji"
        verbose_name_plural = "Plany subskrypcji"
        ordering = ['price_monthly']
    
    def __str__(self):
        return f"{self.display_name} ({self.price_monthly} PLN)"


# ========== NOWY MODEL: SMSUsage ==========
class SMSUsage(models.Model):
    """Śledzenie liczby SMS-ów wysłanych w danym miesiącu"""
    subscription = models.ForeignKey('Subscription', on_delete=models.CASCADE, related_name='sms_usage')
    year = models.IntegerField()
    month = models.IntegerField()
    sms_count = models.IntegerField(default=0)
    extra_sms_cost = models.DecimalField(max_digits=6, decimal_places=2, default=0.00, help_text="Koszt SMS-ów poza planem")
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "Użycie SMS"
        verbose_name_plural = "Użycie SMS"
        unique_together = ('subscription', 'year', 'month')
        ordering = ['-year', '-month']
    
    def __str__(self):
        return f"{self.subscription.user.username} - {self.month}/{self.year} ({self.sms_count} SMS)"
    

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

    sms_reminders_enabled = models.BooleanField(
        default=True,
        verbose_name="Powiadomienia SMS",
        help_text="Wysyłaj SMS-y przed wizytami (wymaga planu SMS)"
    )
    
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
    plan = models.ForeignKey(SubscriptionPlan, on_delete=models.SET_NULL, null=True, related_name='subscriptions')
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
    
    def has_sms_plan(self):
        """Sprawdź czy user ma plan z SMS"""
        return self.plan and self.plan.name == 'sms'
    
    def get_sms_monthly_usage(self):
        """Pobierz bieżące użycie SMS w tym miesiącu"""
        now = timezone.now()
        try:
            usage = SMSUsage.objects.get(
                subscription=self,
                year=now.year,
                month=now.month
            )
            return usage.sms_count
        except SMSUsage.DoesNotExist:
            return 0
    
    def get_sms_monthly_limit(self):
        """Pobierz limit SMS dla tego planu w tym miesiącu"""
        if self.has_sms_plan():
            return self.plan.sms_included
        return 0
    
    def can_send_sms(self):
        """Sprawdź czy można wysłać SMS (czy limit nie został przekroczony)"""
        if not self.has_sms_plan():
            return False
        current_usage = self.get_sms_monthly_usage()
        limit = self.get_sms_monthly_limit()
        return current_usage < limit

    def extend_subscription(self, days=30):
        if self.is_active():
            self.end_date += timedelta(days=days)
        else:
            self.start_date = timezone.now()
            self.end_date = timezone.now() + timedelta(days=days)
            self.status = 'active'
        self.save()
    
    def log_sms_usage(self, sms_count=1):
        """Zaloguj wysłanie SMS-ów"""
        if not self.has_sms_plan():
            return False
        
        now = timezone.now()
        usage, created = SMSUsage.objects.get_or_create(
            subscription=self,
            year=now.year,
            month=now.month,
            defaults={'sms_count': 0, 'extra_sms_cost': 0.00}
        )
        
        included = self.plan.sms_included
        current_total = usage.sms_count + sms_count
        
        # Oblicz koszt SMS-ów poza planem
        if current_total > included:
            extra_sms = current_total - included
            usage.extra_sms_cost = extra_sms * self.plan.sms_price_per_extra
        
        usage.sms_count = current_total
        usage.save()
        
        return True

    def __str__(self):
        plan_name = self.plan.display_name if self.plan else "Brak planu"
        return f"{self.user.username} - {plan_name} - {self.status}"
    

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