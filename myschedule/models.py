from django.db import models
from django.conf import settings

class Calendar(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="calendar")

    def __str__(self):
        return f"Kalendarz {self.user.username}"

class Availability(models.Model):
    calendar = models.ForeignKey(Calendar, on_delete=models.CASCADE, related_name="availabilities")
    date = models.DateField()
    start_time = models.TimeField()
    end_time = models.TimeField()

    def __str__(self):
        return f"{self.date} {self.start_time}-{self.end_time}"