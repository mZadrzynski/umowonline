from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from .models import Calendar

User = get_user_model()

@receiver(post_save, sender=User)
def create_calendar_for_premium(sender, instance, created, **kwargs):
    if created:
        try:
            premium_group = Group.objects.get(name="Premium")
            if premium_group in instance.groups.all():
                Calendar.objects.create(user=instance)
        except Group.DoesNotExist:
            pass