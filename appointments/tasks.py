# appointments/tasks.py (fragment - tylko zmień validate_polish_phone)


from celery import shared_task
from django.utils import timezone
from datetime import timedelta
from django.conf import settings
from myschedule.models import Booking
from account.models import Subscription, UserNotificationSettings
from account.utils import validate_and_normalize_polish_phone  # ← IMPORT Z UTILS
import logging
from twilio.rest import Client
from twilio.base.exceptions import TwilioRestException
import pytz

logger = logging.getLogger(__name__)


@shared_task
def send_appointment_reminders():
    """
    Wysyła SMS remindery do wizyt.
    Uruchamia się co 30 min.
    Szuka wizyt w szerszym oknie, żeby nic nie zgubić przy przesunięciach czasu.
    """
    # 1. Ustal czas 'TERAZ'
    now = timezone.now() # To jest zawsze UTC w Django jeśli USE_TZ=True
    
    # 2. Godziny z ustawień (np. 24)
    hours_before = getattr(settings, 'SEND_REMINDER_HOURS_BEFORE', 24)
    
    # 3. SZEROKIE OKNO CZASOWE (np. od 20h do 28h do przodu)
    # Dzięki temu złapiemy wizyty nawet jak Celery się spóźni albo strefa czasowa zeświruje o godzinę
    window_start = now + timedelta(hours=hours_before - 4) 
    window_end = now + timedelta(hours=hours_before + 4)
    
    # Logowanie dla Ciebie (żebyś widział w logach polski czas)
    pl_tz = pytz.timezone('Europe/Warsaw')
    now_pl = now.astimezone(pl_tz)
    logger.info(f"🚀 RUNNING TASK: {now_pl.strftime('%H:%M:%S')} (PL Time)")
    logger.info(f"🔎 Szukam wizyt w oknie UTC: {window_start.strftime('%d.%m %H:%M')} - {window_end.strftime('%d.%m %H:%M')}")

    bookings = Booking.objects.filter(
        start_datetime__gte=window_start,
        start_datetime__lte=window_end,
        status='active',
        reminder_sent=False
    ).select_related(
        'availability__calendar__user__subscription',
        'availability__calendar__user__notification_settings',
        'service_type'
    )
    
    count = bookings.count()
    if count == 0:
        logger.info("brak wizyt do wysłania SMS w tym oknie.")
        return "No bookings found"

    logger.info(f"Znaleziono {count} wizyt do przetworzenia.")
    
    success_count = 0
    
    for booking in bookings:
        try:
            # --- Logika biznesowa (taka sama jak miałeś, tylko uporządkowana) ---
            owner = booking.availability.calendar.user
            
            # Walidacje (subskrypcja, limity itp.)
            if not hasattr(owner, 'subscription') or not owner.subscription.is_active():
                continue
            if not owner.subscription.has_sms_plan():
                continue
            if not owner.subscription.can_send_sms():
                logger.warning(f"Limit SMS wyczerpany dla {owner.username}")
                continue

            # Sprawdź czy user chce wysyłać (domyślnie True)
            try:
                if not owner.notification_settings.sms_reminders_enabled:
                    continue
            except UserNotificationSettings.DoesNotExist:
                pass 

            # Walidacja numeru
            client_phone = booking.client_phone
            is_valid, normalized_phone, error = validate_and_normalize_polish_phone(client_phone)
            
            if not is_valid:
                logger.warning(f"Zły numer w wizycie {booking.id}: {error}")
                continue

            # --- WYSYŁKA ---
            client_name = booking.client_name or "Klient"
            service_name = booking.service_type.name if booking.service_type else "Wizyta"
            
                      # --- KONWERSJA CZASU (POPRAWKA) ---
            # Pobieramy czas z bazy
            dt = booking.start_datetime
            
            # Jeśli czas nie ma strefy (jest 'naive'), uznajemy że to UTC
            if timezone.is_naive(dt):
                dt = timezone.make_aware(dt, timezone.utc)
            
            # Konwertujemy na Warsaw
            booking_time_pl = dt.astimezone(pl_tz)

            # DEBUG: Wypisz w logach co wysyłamy
            logger.info(f"DEBUG CZASU: Baza={booking.start_datetime} -> PL={booking_time_pl}")

            send_sms_reminder(
                normalized_phone, 
                client_name, 
                booking_time_pl, 
                service_name
            )
            
            # --- SUKCES ---
            # Oznaczamy OD RAZU, żeby nie wysłać drugi raz za 30 min
            owner.subscription.log_sms_usage(1)
            booking.reminder_sent = True
            booking.reminder_sent_at = now
            booking.save(update_fields=['reminder_sent', 'reminder_sent_at'])
            
            success_count += 1
            logger.info(f"✅ SMS wysłany do {normalized_phone} (Wizyta ID: {booking.id})")

        except Exception as e:
            logger.error(f"❌ Błąd przy wizycie {booking.id}: {e}")

    return f"Przetworzono: {count}, Wysłano: {success_count}"

def send_sms_reminder(phone_number, client_name, appointment_time, service_name):
    """Wysyła SMS via Twilio"""
    client = Client(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN)
    
    # Formatowanie daty do treści SMS (np. 16.12 14:30)
    date_str = appointment_time.strftime('%d.%m')
    time_str = appointment_time.strftime('%H:%M')
    
    message_body = (
        f"Przypomnienie: {service_name}, {date_str} godz. {time_str}. "
        f"Do zobaczenia! www.umowzdalnie.pl"
    )
    
    client.messages.create(
        body=message_body,
        messaging_service_sid=settings.TWILIO_MESSAGING_SERVICE_SID,
        to=phone_number
    )