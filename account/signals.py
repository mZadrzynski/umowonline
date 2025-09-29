from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth import get_user_model
from datetime import timedelta
from django.utils import timezone
from .models import Subscription
from myschedule.models import Calendar

User = get_user_model()

@receiver(post_save, sender=User)
def create_subscription_for_new_user(sender, instance, created, **kwargs):
    """Tworzy 30-dniową darmową subskrypcję dla nowego użytkownika"""
    if created:
        # 30-dniowy darmowy trial dla nowego użytkownika
        end_date = timezone.now() + timedelta(days=30)
        subscription = Subscription.objects.create(
            user=instance,
            end_date=end_date,
            status='active'
        )
        # Tworzy kalendarz
        Calendar.objects.create(user=instance)