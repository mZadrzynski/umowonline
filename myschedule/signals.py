from django.db.models.signals import post_save, m2m_changed
from django.dispatch import receiver
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from .models import Calendar

User = get_user_model()

#sprawdza czy user jest premium jesli tak to tworzy kalendarz
@receiver(post_save, sender=User)
def create_calendar_for_premium(sender, instance, created, **kwargs):
    if created:
        try:
            premium_group = Group.objects.get(name="Premium")

            if premium_group in instance.groups.all():
                Calendar.objects.create(user=instance)
        except Group.DoesNotExist:
            pass


@receiver(m2m_changed, sender=User.groups.through)
def create_calendar_on_group_add(sender, instance, action, pk_set, **kwargs):
    if action == "post_add":
        try:
            premium_group = Group.objects.get(name="Premium")
            if premium_group.pk in pk_set:
                Calendar.objects.get_or_create(user=instance)
        except Group.DoesNotExist:
            pass