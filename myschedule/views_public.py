from datetime import date, timedelta
from django.shortcuts import render, get_object_or_404
from .models import Booking, Calendar

def calculate_free_time_slots(availability, busy_slots):
    """Oblicza wolne sloty czasowe"""
    from datetime import datetime, timedelta
    
    # Konwertuj na minuty od początku dnia dla łatwiejszych obliczeń
    start_minutes = availability.start_time.hour * 60 + availability.start_time.minute
    end_minutes = availability.end_time.hour * 60 + availability.end_time.minute
    
    # Zajęte minuty
    busy_minutes = set()
    for start_time, end_time in busy_slots:
        busy_start = start_time.hour * 60 + start_time.minute
        busy_end = end_time.hour * 60 + end_time.minute
        busy_minutes.update(range(busy_start, busy_end))
    
    # Wolne minuty
    free_minutes = []
    current_start = None
    
    for minute in range(start_minutes, end_minutes):
        if minute not in busy_minutes:
            if current_start is None:
                current_start = minute
        else:
            if current_start is not None:
                free_minutes.append((current_start, minute))
                current_start = None
    
    # Dodaj ostatni slot jeśli kończy się na końcu availability
    if current_start is not None:
        free_minutes.append((current_start, end_minutes))
    
    # Konwertuj z powrotem na godziny
    free_slots = []
    for start_min, end_min in free_minutes:
        start_hour = start_min // 60
        start_minute = start_min % 60
        end_hour = end_min // 60
        end_minute = end_min % 60
        
        start_time = f"{start_hour:02d}:{start_minute:02d}"
        end_time = f"{end_hour:02d}:{end_minute:02d}"
        free_slots.append((start_time, end_time))
    
    return free_slots



def public_calendar_week(request, token):
    calendar = get_object_or_404(Calendar, share_token=token)
    today = date.today()
    week_offset = int(request.GET.get('week', 0))
    start_of_week = today - timedelta(days=today.weekday()) + timedelta(weeks=week_offset)
    end_of_week = start_of_week + timedelta(days=6)
    week_days = [start_of_week + timedelta(days=i) for i in range(7)]
    
    availabilities = calendar.availabilities.filter(
        date__range=[start_of_week, end_of_week]
    ).order_by('date', 'start_time')
    
    # POPRAWKA: Filtruj tylko aktywne rezerwacje
    bookings = Booking.objects.filter(
        availability__in=availabilities,
        status='active'  # DODAJ TĘ LINIĘ
    ).select_related('service_type').order_by('start_datetime') 
    
    bookings_by_availability = {}
    for booking in bookings:
        slots = bookings_by_availability.setdefault(booking.availability_id, [])
        start = booking.start_datetime.time()
        end = (booking.start_datetime + timedelta(minutes=booking.service_type.duration_minutes)).time()
        slots.append((start, end))
    
    avail_by_day = {day: [] for day in week_days}
    for availability in availabilities:
        busy = bookings_by_availability.get(availability.id, [])
        avail_by_day[availability.date].append({
            "availability": availability,
            "busy_slots": busy
        })
        busy = bookings_by_availability.get(availability.id, [])
        free_slots = calculate_free_time_slots(availability, busy)

    
    context = {
        "week_days": week_days,
        "selected_week": start_of_week,
        "availabilities_by_day_items": [(d, avail_by_day[d]) for d in week_days],
        "calendar_owner": calendar.user,
        "week_offset": week_offset,
        "free_slots": free_slots,
    }
    return render(request, "myschedule/public_calendar_week.html", context)