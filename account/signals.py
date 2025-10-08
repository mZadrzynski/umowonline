from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django.contrib.auth import get_user_model
from datetime import timedelta
from django.utils import timezone
from .models import Subscription
from myschedule.models import Calendar, Booking
from .models import UserNotificationSettings
from django.core.mail import send_mail
from django.conf import settings
from django.template.loader import render_to_string

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


@receiver(post_save, sender=User)  # ✅ Używa custom user
def create_notification_settings(sender, instance, created, **kwargs):
    """Automatycznie tworzy ustawienia powiadomień dla nowego użytkownika"""
    if created:
        UserNotificationSettings.objects.create(user=instance)

@receiver(post_save, sender=User) 
def save_notification_settings(sender, instance, **kwargs):
    """Zapisuje ustawienia powiadomień przy zapisie użytkownika"""
    if hasattr(instance, 'notification_settings'):
        instance.notification_settings.save()

#Jeśli masz model Booking, odkomentuj poniższe signals:
@receiver(post_save, sender=Booking)
def send_booking_notifications(sender, instance, created, **kwargs):
    """Wysyła powiadomienia o nowej wizycie"""
    if created and instance.status == 'active':
        # Powiadomienie dla właściciela kalendarza
        provider_settings = getattr(instance.provider, 'notification_settings', None)
        if provider_settings and provider_settings.booking_created_notifications:
            send_booking_notification_email(
                recipient=instance.provider,
                booking=instance,
                email_type='new_booking_provider'
            )
        
        # Potwierdzenie dla klienta
        client_settings = getattr(instance.client, 'notification_settings', None) 
        if client_settings and client_settings.own_booking_confirmations:
            send_booking_notification_email(
                recipient=instance.client,
                booking=instance,
                email_type='booking_confirmation_client'
            )
@receiver(post_delete, sender=Booking)
def send_cancellation_notifications(sender, instance, **kwargs):
    """Wysyła powiadomienia o anulowaniu wizyty"""
    # Powiadomienie dla właściciela kalendarza
    provider_settings = getattr(instance.provider, 'notification_settings', None)
    if provider_settings and provider_settings.booking_cancelled_notifications:
        send_booking_notification_email(
            recipient=instance.provider,
            booking=instance,
            email_type='booking_cancelled_provider'
        )
    
    # Powiadomienie dla klienta
    client_settings = getattr(instance.client, 'notification_settings', None)
    if client_settings and client_settings.own_booking_confirmations:
        send_booking_notification_email(
            recipient=instance.client, 
            booking=instance,
            email_type='booking_cancelled_client'
        )
def send_booking_notification_email(recipient, booking, email_type):
   """Funkcja wysyłająca email z powiadomieniem"""
   
   email_templates = {
       'new_booking_provider': {
           'subject': 'Nowa wizyta została umówiona',
           'template': 'emails/new_booking_provider.html'
       },
       'booking_confirmation_client': {
           'subject': 'Potwierdzenie umówienia wizyty',
           'template': 'emails/booking_confirmation_client.html'
       },
       'booking_cancelled_provider': {
           'subject': 'Wizyta została anulowana', 
           'template': 'emails/booking_cancelled_provider.html'
       },
       'booking_cancelled_client': {
           'subject': 'Twoja wizyta została anulowana',
           'template': 'emails/booking_cancelled_client.html'
       }
   }
   
   if email_type not in email_templates:
       return
       
   template_config = email_templates[email_type]
   
   try:
       # Kontekst dla szablonu email
       context = {
           'recipient': recipient,
           'booking': booking,
           'site_name': 'UmówZdalnie.pl'
       }
       
       # Renderowanie HTML wiadomości 
       html_message = render_to_string(template_config['template'], context)
       
       # Wysłanie emaila
       send_mail(
           subject=template_config['subject'],
           message='',  # pusta wiadomość tekstowa
           from_email=settings.DEFAULT_FROM_EMAIL,
           recipient_list=[recipient.email],
           html_message=html_message,
           fail_silently=False,
       )
       
   except Exception as e:
       # Logowanie błędów (opcjonalne)
       print(f"Błąd wysyłania emaila: {e}")