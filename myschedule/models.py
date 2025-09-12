from django.db import models
from django.conf import settings
from django.contrib.auth.models import User
from datetime import date, timedelta
import shortuuid

def default_valid_until():
    return date.today() + timedelta(days=730)

class Calendar(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="calendar")
    share_token = models.CharField(max_length=12, default=shortuuid.uuid, unique=True, editable=False)
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
        on_delete=models.CASCADE
    )
    booked_at = models.DateTimeField(auto_now_add=True)
    service_type = models.ForeignKey(ServiceType, on_delete=models.CASCADE, null=True, blank=True)
    start_datetime = models.DateTimeField()


    class Meta:
        unique_together = ('availability', 'user')    