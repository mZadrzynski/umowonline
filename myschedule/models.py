from django.db import models
from django.conf import settings
from django.contrib.auth.models import User
from datetime import date, timedelta
from django.core.exceptions import ValidationError
from django.utils.text import slugify
import uuid

def default_valid_until():
    return date.today() + timedelta(days=730)

def generate_share_token():
    return str(uuid.uuid4())[:12]

class Calendar(models.Model):
    user = models.ForeignKey(  # ← było: OneToOneField
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="calendars",
    )
    name = models.CharField(max_length=100, null=True, blank=True)
    share_token = models.CharField(max_length=12, default=generate_share_token, unique=True, editable=False)
    valid_from = models.DateField(default=date.today)  # od kiedy kalendarz aktywny
    valid_until = models.DateField(default=default_valid_until, null=True, blank=True)
 # do kiedy (opcjonalne)
    is_active = models.BooleanField(default=True)  # czy aktywny

    def __str__(self):
        return f"Kalendarz {self.user.username}"
    
    

class Availability(models.Model):
    calendar = models.ForeignKey(Calendar, on_delete=models.CASCADE, related_name="availabilities")
    title = models.CharField(max_length=100, blank=True)  # opcjonalne - nazwa wizyty
    date = models.DateField()  
    start_time = models.TimeField()
    end_time = models.TimeField()
        
    class Meta:
        ordering = ['date', 'start_time']
        # Możesz dodać podstawowe ograniczenie unikalności
        constraints = [
            models.CheckConstraint(
                check=models.Q(start_time__lt=models.F('end_time')),
                name='start_time_before_end_time'
            )
        ]

    def __str__(self):
        return f"{self.start_time.date()} {self.start_time.time()} - {self.end_time.time()}"
    


class ServiceType(models.Model):
    calendar = models.ForeignKey('Calendar', on_delete=models.CASCADE)
    name = models.CharField(max_length=100)        # np. "Naprawa auta"
    duration_minutes = models.PositiveIntegerField()  # np. 60
    description = models.TextField(blank=True)
    price = models.DecimalField(
        max_digits=8, 
        decimal_places=2, 
        null=True, 
        blank=True,  # Opcjonalne
        help_text="Cena usługi w PLN"
    )
    def __str__(self):
        return f"{self.name} ({self.duration_minutes} min)"
    

class Booking(models.Model):
    availability = models.ForeignKey(Availability, on_delete=models.CASCADE, related_name='bookings')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, null=True, blank=True)
    booked_at = models.DateTimeField(auto_now_add=True)
    service_type = models.ForeignKey(ServiceType, on_delete=models.CASCADE, null=True, blank=True)
    start_datetime = models.DateTimeField()
    
    client_name = models.CharField(max_length=120, blank=True)
    client_phone = models.CharField(max_length=20, blank=True, verbose_name="Telefon klienta")
    client_email = models.EmailField(blank=True, verbose_name="Email klienta")
    client_note = models.TextField(blank=True, verbose_name="Notatka klienta")
    
    status = models.CharField(
        max_length=20,
        choices=[('active', 'Aktywna'), ('cancelled', 'Anulowana')],
        default='active',
        verbose_name="Status wizyty"
    )
    
    booked_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='bookings_created',
        null=True, blank=True,
        verbose_name="Dodane przez"
    )
    
    reminder_sent = models.BooleanField(
        default=False,
        verbose_name="SMS reminder wysłany"
    )
    reminder_sent_at = models.DateTimeField(
        null=True, 
        blank=True,
        verbose_name="Kiedy wysłano SMS"
    )
    
    class Meta:
        ordering = ['-start_datetime']
        
    
    @property
    def provider(self):
        return self.availability.calendar.user
    
    @property
    def client(self):
        return self.user or self.client_name


class CalendarAlias(models.Model):
    """
    Alias slugowy dla kalendarza użytkownika.
    Pozwala na: /marcin (index=1), /marcin2 (index=2), /marcin3 (index=3)
    
    Przykład:
      user=marcin, calendar=user.calendar, index=1, slug='marcin'
      user=marcin, calendar=drugi_kalendarz, index=2, slug='marcin2'
    """
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="calendar_aliases",
    )
    calendar = models.ForeignKey(
        Calendar,
        on_delete=models.CASCADE,
        related_name="aliases",
    )
    index = models.PositiveIntegerField(
        default=1,
        help_text="Numer aliasu: 1=główny (/marcin), 2=(/marcin2), 3=(/marcin3) itp",
    )
    slug = models.SlugField(
        max_length=150,
        unique=True,
        db_index=True,
        help_text="Slug URL-owy: marcin, marcin2, marcin3 itp",
    )
    created_at = models.DateTimeField(auto_now_add=True, null=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["user", "index"],
                name="unique_user_calendar_index",
            ),
        ]
        ordering = ["user_id", "index"]
        verbose_name = "Alias kalendarza"
        verbose_name_plural = "Aliasy kalendarza"

    def __str__(self):
        return f"{self.user.username}/{self.slug} → {self.calendar.id}"

    @staticmethod
    def build_slug(username: str, index: int) -> str:
        """
        Generuje slug na podstawie username i index:
          build_slug('marcin', 1) -> 'marcin'
          build_slug('marcin', 2) -> 'marcin2'
          build_slug('marcin', 3) -> 'marcin3'
        """
        base = slugify(username)
        return base if index == 1 else f"{base}{index}"