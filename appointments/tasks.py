# appointments/tasks.py

import re
from celery import shared_task
from django.utils import timezone
from datetime import timedelta
from django.conf import settings
from myschedule.models import Booking  # ← ZMIANA: używaj Booking
from account.models import Subscription, UserNotificationSettings
import logging
from twilio.rest import Client
from twilio.base.exceptions import TwilioRestException

logger = logging.getLogger(__name__)


def validate_polish_phone(phone_number):
    """
    Sprawdza czy numer jest z Polski: +48 i 9 cyfr
    Zwraca tuple (is_valid, normalized_number)
    """
    if not phone_number:
        return False, None
    
    # Usuń wszystkie znaki oprócz cyfr i +
    clean_number = re.sub(r'[^\d+]', '', phone_number)
    
    # Usuń + żeby policzyć cyfry
    digits_only = clean_number.lstrip('+')
    
    # Sprawdź format: 48 + 9 cyfr = 11 cyfr
    if digits_only.startswith('48') and len(digits_only) == 11:
        normalized = '+' + digits_only if not clean_number.startswith('+') else clean_number
        return True, normalized
    
    logger.warning(f"Invalid phone format: {phone_number} (cleaned: {clean_number})")
    return False, None


@shared_task
def send_appointment_reminders():
    """
    Wysyła SMS remindery do wizyt (Booking) odbywających się za ~24h
    """
    now = timezone.now()
    hours_before = settings.SEND_REMINDER_HOURS_BEFORE
    
    tomorrow_start = now + timedelta(hours=hours_before - 2)
    tomorrow_end = now + timedelta(hours=hours_before + 2)
    
    # ✅ DODAJ reminder_sent=False:
    bookings = Booking.objects.filter(
        start_datetime__gte=tomorrow_start,
        start_datetime__lte=tomorrow_end,
        status='active',
        reminder_sent=False  # ← DODAJ TO!
    ).select_related(
        'availability__calendar__user',
        'availability__calendar__user__subscription',
        'availability__calendar__user__notification_settings',
        'service_type'
    )
    
    logger.info(f"Found {bookings.count()} bookings to send reminders (reminder_sent=False)")
    
    success_count = 0
    failed_count = 0
    skipped_count = 0
    
    for booking in bookings:
        try:
            # Pobierz właściciela kalendarza
            owner = booking.availability.calendar.user
            
            if not owner:
                logger.warning(f"Booking {booking.id} has no calendar owner - skipping")
                skipped_count += 1
                continue
            
            # Sprawdź subskrypcję WŁAŚCICIELA
            try:
                subscription = owner.subscription
            except Subscription.DoesNotExist:
                logger.info(f"Owner {owner.username} (ID: {owner.id}) has no subscription - skipping booking {booking.id}")
                skipped_count += 1
                continue
            
            # Sprawdź czy subskrypcja jest aktywna
            if not subscription.is_active():
                logger.info(f"Owner {owner.username} has inactive subscription - skipping booking {booking.id}")
                skipped_count += 1
                continue
            
            # Sprawdź czy ma plan SMS
            if not subscription.has_sms_plan():
                logger.info(f"Owner {owner.username} has no SMS plan - skipping booking {booking.id}")
                skipped_count += 1
                continue
            
            # Sprawdź limit SMS
            if not subscription.can_send_sms():
                logger.warning(f"Owner {owner.username} exceeded SMS limit ({subscription.get_sms_monthly_usage()}/{subscription.get_sms_monthly_limit()}) - skipping booking {booking.id}")
                skipped_count += 1
                continue
            
            # Sprawdź ustawienia właściciela
            try:
                notification_settings = owner.notification_settings
                if not notification_settings.sms_reminders_enabled:
                    logger.info(f"Owner {owner.username} disabled SMS reminders - skipping booking {booking.id}")
                    skipped_count += 1
                    continue
            except UserNotificationSettings.DoesNotExist:
                pass  # Domyślnie włączone
            
            # Pobierz numer telefonu klienta
            client_phone = booking.client_phone
            if not client_phone:
                logger.warning(f"Booking {booking.id} has no client phone number - skipping")
                failed_count += 1
                continue
            
            # Walidacja numeru telefonu
            is_valid, normalized_phone = validate_polish_phone(client_phone)
            if not is_valid:
                logger.warning(f"Invalid phone number for booking {booking.id}: '{client_phone}' - skipping")
                failed_count += 1
                continue
            
            # Pobierz nazwę klienta
            client_name = booking.client_name if booking.client_name else (
                booking.user.get_full_name() if booking.user else "Klient"
            )
            
            # Wysyłaj SMS
            try:
                send_sms_reminder(normalized_phone, client_name, booking.start_datetime, booking.service_type.name)
                
                # Zaloguj użycie SMS (odliczane z konta właściciela)
                subscription.log_sms_usage(sms_count=1)
                
                # ✅ OZNACZ JAKO WYSŁANE (zapobiega duplikatom!):
                booking.reminder_sent = True
                booking.reminder_sent_at = now
                booking.save(update_fields=['reminder_sent', 'reminder_sent_at'])
                
                success_count += 1
                logger.info(f"✓ SMS sent for booking {booking.id} to {normalized_phone}, reminder_sent=True")
                
            except TwilioRestException as e:
                logger.error(f"✗ Twilio error for booking {booking.id} (phone: {normalized_phone}): {e.code} - {e.msg}")
                failed_count += 1
                
            except Exception as e:
                logger.error(f"✗ Unexpected error sending SMS for booking {booking.id}: {str(e)}")
                failed_count += 1
        
        except Exception as e:
            logger.error(f"✗ Unexpected error processing booking {booking.id}: {str(e)}", exc_info=True)
            failed_count += 1
    
    result = {
        'sent': success_count, 
        'failed': failed_count,
        'skipped': skipped_count,
        'total_processed': success_count + failed_count + skipped_count
    }
    
    logger.info(f"SMS reminder task completed: {result}")
    return result


def send_sms_reminder(phone_number, client_name, appointment_time, service_name):
    """
    Wysyła SMS via Twilio
    phone_number MUSI być w formacie +48XXXXXXXXX
    """
    try:
        client = Client(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN)
        
        # Upewnij się że ma +
        if not phone_number.startswith('+'):
            phone_number = '+' + phone_number
        
        # Format wiadomości
        time_str = appointment_time.strftime('%H:%M')
        date_str = appointment_time.strftime('%d.%m')
        message = f"Przypomnienie: Wizyta {service_name} {date_str} o {time_str}. Szczegoly: www.umowzdalnie.pl. Pozdrawiamy!"
        
        msg = client.messages.create(
            body=message,
            messaging_service_sid=settings.TWILIO_MESSAGING_SERVICE_SID,
            to=phone_number
        )
        
        logger.info(f"✓ SMS sent via Twilio: SID={msg.sid}, to={phone_number}, status={msg.status}")
        return msg.sid
        
    except TwilioRestException as e:
        logger.error(f"✗ Twilio API error: code={e.code}, msg={e.msg}, status={e.status}")
        raise
        
    except Exception as e:
        logger.error(f"✗ Unexpected error in send_sms_reminder: {str(e)}")
        raise
