from django.db import models
from django.conf import settings
from django.contrib.auth.models import User
from datetime import date, timedelta
from django.core.exceptions import ValidationError

import shortuuid

def default_valid_until():
    return date.today() + timedelta(days=730)

def generate_share_token():
    return shortuuid.uuid()[:12]

class Calendar(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="calendar")
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

    def __str__(self):
        return f"{self.name} ({self.duration_minutes} min)"
    

class Booking(models.Model):
    availability = models.ForeignKey(Availability, on_delete=models.CASCADE, related_name='bookings')
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        null=True, blank=True,  # ← pozwala na brak usera dla rezerwacji dodanych przez właściciela
    )
    booked_at = models.DateTimeField(auto_now_add=True)
    service_type = models.ForeignKey(ServiceType, on_delete=models.CASCADE, null=True, blank=True)
    start_datetime = models.DateTimeField()

    # DANE KLIENTA
    client_name = models.CharField(max_length=120, blank=True)  # ← NOWE, nazwa wpisywana przez właściciela
    client_phone = models.CharField(max_length=20, blank=True, verbose_name="Telefon klienta")
    client_email = models.EmailField(blank=True, verbose_name="Email klienta")
    client_note = models.TextField(blank=True, verbose_name="Notatka klienta", help_text="Dodatkowe informacje od klienta")

    status = models.CharField(
        max_length=20,
        choices=[('active', 'Aktywna'), ('cancelled', 'Anulowana')],
        default='active',
        verbose_name="Status wizyty"
    )

    # Kto dodał (właściciel lub sam klient)
    booked_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='bookings_created',
        null=True, blank=True,
        verbose_name="Dodane przez"
    )

    class Meta:
        # Usuń wcześniejsze unique_together ('availability','user').
        # Jeśli chcesz bronić przed nakładkami, i tak robimy check_time_collision.
        constraints = []

    @property
    def provider(self):
        return self.availability.calendar.user

    @property
    def client(self):
        # Jeśli to samodzielna rezerwacja – klient to user. Jeśli dodane przez właściciela – klient po nazwie.
        return self.user or self.client_name