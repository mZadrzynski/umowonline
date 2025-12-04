# appointments/tasks.py (fragment - tylko zmień validate_polish_phone)

import re
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

logger = logging.getLogger(__name__)


# ❌ USUŃ STARY validate_polish_phone() - już nie potrzebny!
# def validate_polish_phone(phone_number):
#     ...


@shared_task
def send_appointment_reminders():
    """
    Wysyła SMS remindery do wizyt (Booking) odbywających się za ~24h
    """
    now = timezone.now()
    hours_before = settings.SEND_REMINDER_HOURS_BEFORE
    
    tomorrow_start = now + timedelta(hours=hours_before - 2)
    tomorrow_end = now + timedelta(hours=hours_before + 2)
    
    bookings = Booking.objects.filter(
        start_datetime__gte=tomorrow_start,
        start_datetime__lte=tomorrow_end,
        status='active',
        reminder_sent=False
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
                logger.info(f"Owner {owner.username} has no subscription - skipping booking {booking.id}")
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
                logger.warning(f"Owner {owner.username} exceeded SMS limit - skipping booking {booking.id}")
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
                logger.warning(f"Booking {booking.id} has no client phone - skipping")
                failed_count += 1
                continue
            
            # ✅ WALIDACJA NUMERU TELEFONU (używa funkcji z utils.py)
            is_valid, normalized_phone, error = validate_and_normalize_polish_phone(client_phone)
            if not is_valid:
                logger.warning(f"Invalid phone for booking {booking.id}: '{client_phone}' - {error}")
                failed_count += 1
                continue
            
            # Pobierz nazwę klienta
            client_name = booking.client_name if booking.client_name else (
                booking.user.get_full_name() if booking.user else "Klient"
            )
            
            # Wysyłaj SMS
            try:
                send_sms_reminder(
                    normalized_phone, 
                    client_name, 
                    booking.start_datetime, 
                    booking.service_type.name
                )
                
                # Zaloguj użycie SMS
                subscription.log_sms_usage(sms_count=1)
                
                # Oznacz jako wysłane
                booking.reminder_sent = True
                booking.reminder_sent_at = now
                booking.save(update_fields=['reminder_sent', 'reminder_sent_at'])
                
                success_count += 1
                logger.info(f"✓ SMS sent for booking {booking.id} to {normalized_phone}")
                
            except TwilioRestException as e:
                logger.error(f"✗ Twilio error for booking {booking.id}: {e.code} - {e.msg}")
                failed_count += 1
                
            except Exception as e:
                logger.error(f"✗ Error sending SMS for booking {booking.id}: {str(e)}")
                failed_count += 1
        
        except Exception as e:
            logger.error(f"✗ Error processing booking {booking.id}: {str(e)}", exc_info=True)
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
    """Wysyła SMS via Twilio"""
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
        
        logger.info(f"✓ SMS sent: SID={msg.sid}, to={phone_number}, status={msg.status}")
        return msg.sid
        
    except TwilioRestException as e:
        logger.error(f"✗ Twilio error: code={e.code}, msg={e.msg}")
        raise
        
    except Exception as e:
        logger.error(f"✗ Error in send_sms_reminder: {str(e)}")
        raise
