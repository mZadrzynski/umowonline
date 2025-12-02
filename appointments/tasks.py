from celery import shared_task
from django.utils import timezone
from datetime import timedelta
from django.conf import settings
from .models import Appointment
import logging
from twilio.rest import Client

logger = logging.getLogger(__name__)

@shared_task
def send_appointment_reminders():
    """
    Wysyła SMS remindery do wizyt odbywających się za ~24h
    """
    now = timezone.now()
    hours_before = settings.SEND_REMINDER_HOURS_BEFORE
    
    tomorrow_start = now + timedelta(hours=hours_before - 2)
    tomorrow_end = now + timedelta(hours=hours_before + 2)
    
    appointments = Appointment.objects.filter(
        date_time__gte=tomorrow_start,
        date_time__lte=tomorrow_end,
        reminder_sent=False,
    )
    
    logger.info(f"Found {appointments.count()} appointments to send reminders")
    
    success_count = 0
    failed_count = 0
    
    for apt in appointments:
        try:
            send_sms_reminder(apt.phone_number, apt.client_name, apt.date_time)
            apt.reminder_sent = True
            apt.reminder_sent_at = now
            apt.save(update_fields=['reminder_sent', 'reminder_sent_at'])
            success_count += 1
            logger.info(f"✓ SMS sent for appointment {apt.id}")
        except Exception as e:
            failed_count += 1
            logger.error(f"✗ Failed for appointment {apt.id}: {str(e)}")
    
    return {'sent': success_count, 'failed': failed_count}


def send_sms_reminder(phone_number, client_name, appointment_time):
    """
    Wysyła SMS via Twilio z Messaging Service (z Alpha Sender 'umowzdalnie')
    """
    try:
        client = Client(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN)
        
        time_str = appointment_time.strftime('%H:%M')
        message = f"Wizyta jutro o {time_str}. Szczegoly i zmiana: www.umowzdalnie.pl. Pozdrawiamy!"
        
        msg = client.messages.create(
            body=message,
            messaging_service_sid=settings.TWILIO_MESSAGING_SERVICE_SID,  # ← Zmiana tutaj
            to=phone_number  # Format: +48501234567
        )
        
        logger.info(f"✓ SMS sent: {msg.sid}")
        return msg.sid
        
    except Exception as e:
        logger.error(f"✗ SMS error: {str(e)}")
        raise