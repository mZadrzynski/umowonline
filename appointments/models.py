from django.db import models
from django.utils import timezone

class Appointment(models.Model):
    # ... istniejące pola ...
    phone_number = models.CharField(max_length=20, help_text="Numer telefonu bez spacji, np. 48501234567")
    client_name = models.CharField(max_length=100)
    date_time = models.DateTimeField()
    
    # Nowe pola dla SMS remindersów
    reminder_sent = models.BooleanField(default=False)
    reminder_sent_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        ordering = ['date_time']
        indexes = [
            models.Index(fields=['date_time', 'reminder_sent']),
        ]
    
    def __str__(self):
        return f"{self.client_name} - {self.date_time.strftime('%Y-%m-%d %H:%M')}"