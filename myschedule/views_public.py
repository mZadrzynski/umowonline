from datetime import date, timedelta
from django.shortcuts import render, redirect, get_object_or_404
from .models import Booking, Calendar
from django.contrib.auth import get_user_model
from myschedule.models import CalendarAlias
from catalog.models import BusinessProfile

User = get_user_model()

def public_calendar_with_business(request, token=None, slug=None):
    """
    Publiczny kalendarz + wizytówka
    Działa z tokenem (URL: /myschedule/public/{token}/business/)
    i ze slugiem (URL: /catalog/{slug}/)
    ✅ OBSŁUGUJE WIELE KALENDARZY!
    """
    
    if slug:
        # Wersja dla katalogu
        business = get_object_or_404(BusinessProfile, slug=slug)
        if not business.calendar:
            context = {
                "business": business,
                "week_days": [],
                "availabilities_by_day_items": [],
                "calendar_owner": None,
                "selected_week": None,
                "week_offset": 0,
                "services": [],
                "available_calendars": [],
                "selected_calendar": None,
                "no_calendar_message": "Ta firma nie ma jeszcze przydzielonego kalendarza."
            }
            return render(request, "myschedule/public_calendar_with_business.html", context)
        
        # ✅ OBSŁUGA WIELU KALENDARZY
        calendar_owner = business.calendar.user
        user_calendars = calendar_owner.calendars.all().order_by('id')
        
        # Sprawdź czy użytkownik wybrał konkretny kalendarz z URL (?calendar_id=X)
        selected_calendar_id = request.GET.get('calendar_id')
        if selected_calendar_id:
            try:
                calendar = Calendar.objects.get(id=selected_calendar_id, user=calendar_owner)
            except Calendar.DoesNotExist:
                calendar = business.calendar
        else:
            calendar = business.calendar
    else:
        # Wersja dla publicznego kalendarza (token)
        calendar = get_object_or_404(Calendar, share_token=token)
        business = BusinessProfile.objects.filter(calendar=calendar).first()
        calendar_owner = calendar.user
        user_calendars = calendar_owner.calendars.all().order_by('id')
    
    # ✅ DANE KALENDARZA
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
        "available_calendars": user_calendars,
        "selected_calendar": calendar,
    }
    
    # 🐛 DEBUG
    print("=" * 50)
    print(f"🔍 Function: public_calendar_with_business")
    print(f"🔍 Business: {business.business_name if business else 'None'}")
    print(f"🔍 Calendar owner: {calendar_owner.username}")
    print(f"🔍 User calendars count: {user_calendars.count()}")
    print(f"🔍 Available calendars: {list(user_calendars.values_list('name', 'id'))}")
    print(f"🔍 Selected calendar: {calendar.name} (ID: {calendar.id})")
    print(f"🔍 Services count: {len(context['services'])}")
    print("=" * 50)
    
    return render(request, "myschedule/public_calendar_with_business.html", context)



def calculate_free_time_slots(availability, service_duration_minutes=15):
    """
    Wylicza wolne przedziały czasowe dla danej availability.
    ✅ NAPRAWIONO: Konwersja UTC -> lokalny timezone!
    
    Przyjmuje:
     - availability: obiekt Availability
     - service_duration_minutes: długość usługi w minutach
    Zwraca listę tupli (start_str, end_str).
    """
    from datetime import datetime, timedelta
    from django.utils import timezone as django_tz
    
    # Pobierz rezerwacje
    bookings = Booking.objects.filter(
        availability=availability,
        status='active'
    ).order_by('start_datetime')
    
    # Konwertuj availability na minuty
    start_min = availability.start_time.hour*60 + availability.start_time.minute
    end_min = availability.end_time.hour*60 + availability.end_time.minute
    
    # ✅ NAPRAWA: Zbierz zajęte przedziały z konwersją timezone
    busy = []
    for b in bookings:
        # Konwertuj AWARE datetime (UTC) na lokalny timezone
        local_dt = django_tz.localtime(b.start_datetime)
        sm = local_dt.hour * 60 + local_dt.minute
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
    Przekierowuje z /<username>/ do publicznego kalendarza
    ✅ Wybiera PIERWSZY kalendarz użytkownika (główny)
    """
    
    user = get_object_or_404(User, username__iexact=username)
    
    # ✅ POPRAWKA: Wybierz pierwszy kalendarz (główny)
    calendar = user.calendars.order_by('id').first()
    
    if not calendar:
        from django.http import Http404
        raise Http404(f"Użytkownik {username} nie ma żadnego kalendarza")
    
    # Przekieruj do widoku z kalendarzem
    return public_calendar_with_business(request, token=calendar.share_token)


def public_calendar_by_username(request, username_slug: str):
    """
    Publiczny widok po username/alias.
    
    /marcin       -> alias.index=1 -> alias.calendar.share_token -> istniejąca logika
    /marcin2      -> alias.index=2 -> drugi kalendarz
    /marcin3      -> alias.index=3 -> trzeci kalendarz
    
    Przekazuje do istniejącej funkcji public_calendar_with_business,
    używając share_token z kalendarza.
    """
    # Znajdź alias po slug
    alias = get_object_or_404(CalendarAlias, slug=username_slug)
    
    # Pobierz token z kalendarza
    token = alias.calendar.share_token
    
    # Deleguj do istniejącej funkcji (bezpośrednio, bez re-redirectu)
    # To jakby direct call do public_calendar_with_business(request, token)
    return public_calendar_with_business(request, token=token)