from datetime import date, timedelta
from django.shortcuts import render, redirect, get_object_or_404
from .models import Booking, Calendar
from django.contrib.auth import get_user_model
from catalog.models import BusinessProfile


User = get_user_model()

def public_calendar_with_business(request, token=None, slug=None):
    """
    Publiczny kalendarz + wizytówka
    Działa z tokenem (URL: /myschedule/public/{token}/business/)
    i ze slugiem (URL: /catalog/{slug}/)
    """
    from catalog.models import BusinessProfile
    
    if slug:
        # Wersja dla katalogu
        business = get_object_or_404(BusinessProfile, slug=slug)
        calendar = business.calendar
    else:
        # Wersja dla publicznego kalendarza
        calendar = get_object_or_404(Calendar, share_token=token)
        business = BusinessProfile.objects.filter(calendar=calendar).first()
    
    if not calendar:
        context = {
            "business": business,
            "week_days": [],
            "availabilities_by_day_items": [],
            "calendar_owner": None,
            "selected_week": None,
            "week_offset": 0,
            "services": [],
        }
        return render(request, "myschedule/public_calendar_with_business.html", context)
    
    today = date.today()
    week_offset = int(request.GET.get('week', 0))
    start_of_week = today - timedelta(days=today.weekday()) + timedelta(weeks=week_offset)
    end_of_week = start_of_week + timedelta(days=6)
    week_days = [start_of_week + timedelta(days=i) for i in range(7)]

    availabilities = calendar.availabilities.filter(
        date__range=[start_of_week, end_of_week]
    ).order_by('date', 'start_time')

    avail_by_day = {day: [] for day in week_days}
    for availability in availabilities:
        free_slots = calculate_free_time_slots(availability)
        avail_by_day[availability.date].append({
            "availability": availability,
            "free_slots": free_slots
        })

    context = {
        "business": business,
        "week_days": week_days,
        "availabilities_by_day_items": [(d, avail_by_day[d]) for d in week_days],
        "calendar_owner": calendar.user,
        "selected_week": start_of_week,
        "week_offset": week_offset,
        "services": calendar.servicetype_set.all(),
    }
    return render(request, "myschedule/public_calendar_with_business.html", context)


def calculate_free_time_slots(availability, service_duration_minutes=15):
    """
    Wylicza wolne przedziały czasowe dla danej availability.
    Przyjmuje:
     - availability: obiekt Availability
     - service_duration_minutes: długość usługi w minutach
    Zwraca listę tupli (start_str, end_str).
    """
    from datetime import datetime, timedelta
    
    # Pobierz rezerwacje
    bookings = Booking.objects.filter(
        availability=availability,
        status='active'
    ).order_by('start_datetime')
    
    # Konwertuj availability na minuty
    start_min = availability.start_time.hour*60 + availability.start_time.minute
    end_min = availability.end_time.hour*60 + availability.end_time.minute
    
    # Zbierz zajęte przedziały
    busy = []
    for b in bookings:
        sm = b.start_datetime.time().hour*60 + b.start_datetime.time().minute
        em = sm + b.service_type.duration_minutes
        busy.append((sm, em))
    
    # Scal nakładające się busy
    busy.sort()
    merged = []
    for s, e in busy:
        if not merged or s > merged[-1][1]:
            merged.append((s, e))
        else:
            merged[-1] = (merged[-1][0], max(merged[-1][1], e))
    
    # Wylicz free
    free = []
    current = start_min
    for s, e in merged:
        if current < s:
            free.append((current, s))
        current = max(current, e)
    if current < end_min:
        free.append((current, end_min))
    
    # Konwersja na stringi i filtrowanie po długości usługi
    result = []
    for s, e in free:
        if e - s >= service_duration_minutes:
            sh, smi = divmod(s, 60)
            eh, emi = divmod(e, 60)
            result.append((f"{sh:02d}:{smi:02d}", f"{eh:02d}:{emi:02d}"))
    return result



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

    bookings = Booking.objects.filter(
        availability__in=availabilities,
        status='active'
    ).select_related('service_type').order_by('start_datetime')

    # Używaj free_slots zamiast busy_slots
    avail_by_day = {day: [] for day in week_days}
    for availability in availabilities:
        free_slots = calculate_free_time_slots(availability)
        avail_by_day[availability.date].append({
            "availability": availability,
            "free_slots": free_slots
        })

    context = {
        "week_days": week_days,
        "selected_week": start_of_week,
        "availabilities_by_day_items": [(d, avail_by_day[d]) for d in week_days],
        "calendar_owner": calendar.user,
        "week_offset": week_offset,
        "services": calendar.servicetype_set.all(), 
    }
    return render(request, "myschedule/public_calendar_week.html", context)


def redirect_username_to_token(request, username):
    """
    Przekierowuje z /<username>/ na /public/<share_token>/
    """
    
    user = get_object_or_404(User, username__iexact=username)
    calendar = get_object_or_404(Calendar, user=user)
    
    # Używamy pola share_token
    return redirect(
        'public_calendar_week',
        token=calendar.share_token,
        permanent=False
    )