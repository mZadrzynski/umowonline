from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django.contrib.auth import get_user_model
from datetime import timedelta
from django.utils import timezone
from .models import Subscription
from myschedule.models import Calendar, Booking
from django.core.mail import send_mail
from django.conf import settings
from django.template.loader import render_to_string

User = get_user_model()

def send_booking_notification_email(recipient, booking, email_type):
    """
    Wysyła emailowe powiadomienie w zależności od typu:
      - 'new_booking_provider'
      - 'booking_confirmation_client'
      - 'booking_cancelled_provider'
      - 'booking_cancelled_client'
    """
    # Konfiguracja dostępnych typów i szablonów
    email_templates = {
        'new_booking_provider': {
            'subject': 'Nowa wizyta została umówiona',
            'template': 'emails/new_booking_provider.html',
        },
        'booking_confirmation_client': {
            'subject': 'Potwierdzenie umówienia wizyty',
            'template': 'emails/booking_confirmation_client.html',
        },
        'booking_cancelled_provider': {
            'subject': 'Wizyta została anulowana',
            'template': 'emails/booking_cancelled_provider.html',
        },
        'booking_cancelled_client': {
            'subject': 'Twoja wizyta została anulowana',
            'template': 'emails/booking_cancelled_client.html',
        },
    }

    # Sprawdź czy typ istnieje
    config = email_templates.get(email_type)
    if not config:
        return

    # Przygotuj kontekst do szablonu
    context = {
        'recipient': recipient,
        'booking': booking,
        'site_name': 'UmówZdalnie.pl',
    }

    # Renderuj HTML
    html_message = render_to_string(config['template'], context)

    # Wyślij email
    send_mail(
        subject=config['subject'],
        message='',  # pusta część tekstowa
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[recipient.email],
        html_message=html_message,
        fail_silently=False
    )

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


@receiver(post_save, sender=Booking)
def send_booking_notifications(sender, instance, created, **kwargs):
    """Wysyła powiadomienia o nowej wizycie"""
    if created:  # Tylko dla nowych booking
        # Powiadomienie dla właściciela kalendarza (provider)
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

# USUŃ signal post_delete i zamień na funkcję:
def cancel_booking_with_notifications(booking_instance):
    """Anuluje booking i wysyła powiadomienia"""
    # Powiadomienie dla właściciela kalendarza
    provider_settings = getattr(booking_instance.provider, 'notification_settings', None)
    if provider_settings and provider_settings.booking_cancelled_notifications:
        send_booking_notification_email(
            recipient=booking_instance.provider,
            booking=booking_instance,
            email_type='booking_cancelled_provider'
        )
    
    # Powiadomienie dla klienta  
    client_settings = getattr(booking_instance.client, 'notification_settings', None)
    if client_settings and client_settings.own_booking_confirmations:
        send_booking_notification_email(
            recipient=booking_instance.client,
            booking=booking_instance,
            email_type='booking_cancelled_client'
        )
    
    # Ustaw status na cancelled zamiast usuwać
    booking_instance.status = 'cancelled'
    booking_instance.save()