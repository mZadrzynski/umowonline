import calendar
from datetime import date, datetime, timedelta, time
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from .forms import SingleAvailabilityForm, BulkAvailabilityForm, ServiceTypeForm, BookingForm, OwnerBookingForm
from datetime import timedelta
from django.shortcuts import get_object_or_404, redirect, render
from django.contrib.auth.decorators import login_required
from .models import Availability, Booking, ServiceType
from django.contrib import messages
from django.urls import reverse
from account.models import Subscription
import holidays



@login_required
def add_availability(request):
    if not hasattr(request.user, "calendar"):
        return HttpResponse("Nie masz kalendarza (tylko Premium może dodać dostępność)")
    
    single_form = SingleAvailabilityForm(prefix='single', calendar=request.user.calendar)
    bulk_form = BulkAvailabilityForm(prefix='bulk')
    
    if request.method == "POST":
        if 'submit_single' in request.POST:
            single_form = SingleAvailabilityForm(
                request.POST, 
                prefix='single', 
                calendar=request.user.calendar
            )
            if single_form.is_valid():
                availability = single_form.save(commit=False)
                availability.calendar = request.user.calendar
                availability.save()
                messages.success(request, "Dostępność została dodana.")
                return redirect("my_calendar")
                    
        elif 'submit_bulk' in request.POST:
            bulk_form = BulkAvailabilityForm(request.POST, prefix='bulk')
            if bulk_form.is_valid():
                cal = request.user.calendar
                start = bulk_form.cleaned_data["start_date"]
                end = bulk_form.cleaned_data["end_date"]
                days = [int(d) for d in bulk_form.cleaned_data["weekdays"]]
                start_time = bulk_form.cleaned_data["start_time"]
                end_time = bulk_form.cleaned_data["end_time"]
                
                pl_holidays = holidays.Poland(years=range(start.year, end.year + 1))
                
                current = start
                created_count = 0
                conflict_count = 0
                conflicts = []
                
                while current <= end:
                    if current.weekday() in days and current not in pl_holidays:
                        # Sprawdź nakładanie dla każdego dnia
                        overlapping = Availability.objects.filter(
                            calendar=cal,
                            date=current,
                            start_time__lt=end_time,
                            end_time__gt=start_time
                        )
                        
                        if not overlapping.exists():
                            Availability.objects.create(
                                calendar=cal,
                                date=current,
                                start_time=start_time,
                                end_time=end_time
                            )
                            created_count += 1
                        else:
                            existing = overlapping.first()
                            conflicts.append(
                                f"{current.strftime('%d.%m.%Y')} "
                                f"({existing.start_time.strftime('%H:%M')}-{existing.end_time.strftime('%H:%M')})"
                            )
                            conflict_count += 1
                    
                    current += timedelta(days=1)
                
                if created_count > 0:
                    messages.success(request, f"Dodano {created_count} dostępności.")
                
                if conflict_count > 0:
                    conflicts_str = ', '.join(conflicts[:5])
                    if len(conflicts) > 5:
                        conflicts_str += f" i {len(conflicts)-5} innych"
                    messages.warning(
                        request, 
                        f"Pominięto {conflict_count} nakładających się terminów: {conflicts_str}"
                    )
                
                return redirect("my_calendar_week")
    
    return render(request, "myschedule/add_availability.html", {
        "single_form": single_form,
        "bulk_form": bulk_form,
    })


@login_required
def delete_availability(request, availability_id):
    availability = get_object_or_404(
        Availability, 
        id=availability_id, 
        calendar=request.user.calendar
    )
    
    if request.method == 'POST':
        availability.delete()
        messages.success(request, "Dostępność została usunięta.")
        return redirect("my_calendar")
    
    return render(request, 'myschedule/confirm_delete.html', {
        'availability': availability
    })


@login_required
def add_service(request):
    if not hasattr(request.user, "calendar"):
        return HttpResponse("Nie masz kalendarza (tylko Premium może dodać wydarzenia)")
    
    if request.method == "POST":
        form = ServiceTypeForm(request.POST)
        if form.is_valid():
            service = form.save(commit=False)
            service.calendar = request.user.calendar
            service.save()
            return redirect("my_calendar_week")
    else:
        form = ServiceTypeForm()
    
    return render(request, "myschedule/add_service.html", {"form": form})



@login_required
def my_bookings(request):
    """Widok dla rezerwacji użytkownika - podzielony na dwie sekcje"""
    
    # Rezerwacje które użytkownik zrobił (rezerwacje u innych)
    my_bookings = Booking.objects.filter(
        user=request.user,
        status='active'
    ).select_related('availability__calendar__user', 'service_type').order_by('-booked_at')
    
    # Rezerwacje w kalendarzu użytkownika (rezerwacje innych u niego)
    calendar_bookings = []
    if hasattr(request.user, 'calendar'):
        calendar_bookings = Booking.objects.filter(
            availability__calendar=request.user.calendar,
            status='active'
        ).select_related('user', 'service_type').order_by('-booked_at')
    
    # Oblicz czasy zakończenia dla wszystkich rezerwacji
    for booking in my_bookings:
        start = booking.availability.start_time
        dummy_date = datetime(2000, 1, 1, start.hour, start.minute)
        duration = booking.service_type.duration_minutes
        end_time = (dummy_date + timedelta(minutes=duration)).time()
        booking.end_time = end_time
    
    for booking in calendar_bookings:
        start = booking.start_datetime
        duration = booking.service_type.duration_minutes
        booking.end_datetime = start + timedelta(minutes=duration)
    
    return render(request, "myschedule/my_bookings.html", {
        "my_bookings": my_bookings,  # Rezerwacje które użytkownik zrobił
        "calendar_bookings": calendar_bookings,  # Rezerwacje w kalendarzu użytkownika
    })

@login_required
def cancel_booking(request, booking_id):
    """Anulowanie rezerwacji przez użytkownika"""
    from account.signals import cancel_booking_with_notifications
    
    booking = get_object_or_404(
        Booking, 
        id=booking_id,
        user=request.user,
        status='active'
    )
    
    if request.method == 'POST':
        # Użyj funkcji z signals która wyśle powiadomienia
        cancel_booking_with_notifications(booking)
        messages.success(request, f'Wizyta {booking.service_type.name} została anulowana.')
        return redirect('my_bookings')
    
    return render(request, 'myschedule/confirm_cancel_booking.html', {
        'booking': booking
    })

@login_required
def cancel_calendar_booking(request, booking_id):
    """Anulowanie rezerwacji w kalendarzu właściciela"""
    from account.signals import cancel_booking_with_notifications
    
    # Sprawdź czy użytkownik jest właścicielem kalendarza
    booking = get_object_or_404(
        Booking, 
        id=booking_id,
        availability__calendar=request.user.calendar,
        status='active'
    )
    
    if request.method == 'POST':
        cancel_booking_with_notifications(booking)
        messages.success(request, f'Wizyta {booking.service_type.name} została anulowana.')
        return redirect('my_bookings')
    
    return render(request, 'myschedule/confirm_cancel_calendar_booking.html', {
        'booking': booking
    })

def generate_available_times(availability):
    """Generuje dostępne czasy w 15-minutowych interwałach"""
    times = []
    start_hour = availability.start_time.hour
    start_minute = availability.start_time.minute
    end_hour = availability.end_time.hour
    end_minute = availability.end_time.minute
    
    current_time = time(start_hour, start_minute)
    end_time = time(end_hour, end_minute)
    
    while current_time < end_time:
        times.append(current_time.strftime('%H:%M'))
        # Dodaj 15 minut
        current_datetime = datetime.combine(date.today(), current_time)
        current_datetime += timedelta(minutes=15)
        current_time = current_datetime.time()
    
    return times

def check_time_collision(availability, start_datetime, service_type):
    """Sprawdza czy nowy termin koliduje z istniejącymi rezerwacjami"""
    end_datetime = start_datetime + timedelta(minutes=service_type.duration_minutes)
    
    conflicting_bookings = Booking.objects.filter(
        availability=availability,
        status='active'
    )
    
    for booking in conflicting_bookings:
        existing_start = booking.start_datetime
        existing_end = existing_start + timedelta(minutes=booking.service_type.duration_minutes)
        
        # Sprawdź nakładanie
        if (start_datetime < existing_end and end_datetime > existing_start):
            return True  # Kolizja
    
    return False  # Brak kolizji


@login_required
def book_availability(request, availability_id):
    availability = get_object_or_404(Availability, id=availability_id)

    # Blokada przeszłości
    now = datetime.now()
    if datetime.combine(availability.date, availability.end_time) <= now:
        messages.error(request, "Nie można zarezerwować terminu w przeszłości.")
        return redirect("my_calendar_week")

    is_owner = hasattr(request.user, 'calendar') and request.user.calendar == availability.calendar

    if is_owner:
        return handle_owner_booking(request, availability)
    else:
        return handle_regular_booking(request, availability)

def handle_regular_booking(request, availability):
    # 1 rezerwacja per availability dla danego usera (zachowane)
    if Booking.objects.filter(availability=availability, user=request.user, status='active').exists():
        return render(request, "myschedule/already_booked.html", {"availability": availability})

    service_types = ServiceType.objects.filter(calendar=availability.calendar)

    if request.method == "POST":
        form = BookingForm(request.POST, user=request.user, availability=availability)
        form.fields['service_type'].queryset = service_types

        if form.is_valid():
            service_type = form.cleaned_data['service_type']
            start_time = datetime.strptime(form.cleaned_data['start_time'], '%H:%M').time()

            start_dt = datetime.combine(availability.date, start_time)
            end_dt = start_dt + timedelta(minutes=service_type.duration_minutes)

            if start_time < availability.start_time or end_dt.time() > availability.end_time:
                messages.error(request, "Godzina poza zakresem dostępności.")
                return render(request, "myschedule/book_availability.html", {"availability": availability, "form": form, "service_types": service_types})

            if check_time_collision(availability, start_dt, service_type):
                messages.error(request, "Ten termin jest już zajęty.")
                return render(request, "myschedule/book_availability.html", {"availability": availability, "form": form, "service_types": service_types})

            Booking.objects.create(
                availability=availability,
                user=request.user,              # ← zwykły user powiązany
                service_type=service_type,
                start_datetime=start_dt,
                client_phone=form.cleaned_data.get('client_phone', ''),
                client_note=form.cleaned_data.get('client_note', ''),
                booked_by=request.user,
                status='active'
            )
            messages.success(request, f"Zarezerwowano wizytę {service_type.name} na {start_time.strftime('%H:%M')}")
            return redirect("my_bookings")
    else:
        form = BookingForm(user=request.user, availability=availability)
        form.fields['service_type'].queryset = service_types

    return render(request, "myschedule/book_availability.html", {"availability": availability, "form": form, "service_types": service_types})

def handle_owner_booking(request, availability):
    service_types = ServiceType.objects.filter(calendar=availability.calendar)

    if request.method == "POST":
        form = OwnerBookingForm(request.POST)
        form.fields['service_type'].queryset = service_types
        # dostępne minuty/sloty
        form.fields['start_time'].choices = [(t, t) for t in generate_available_times(availability)]

        if form.is_valid():
            service_type = form.cleaned_data['service_type']
            start_time = datetime.strptime(form.cleaned_data['start_time'], '%H:%M').time()
            start_dt = datetime.combine(availability.date, start_time)

            # kolizje i zakres
            end_dt = start_dt + timedelta(minutes=service_type.duration_minutes)
            if start_time < availability.start_time or end_dt.time() > availability.end_time:
                messages.error(request, "Godzina poza zakresem dostępności.")
                return render(request, "myschedule/owner_book_availability.html", {"availability": availability, "form": form, "service_types": service_types})

            if check_time_collision(availability, start_dt, service_type):
                messages.error(request, "Ten termin jest już zajęty.")
                return render(request, "myschedule/owner_book_availability.html", {"availability": availability, "form": form, "service_types": service_types})

            Booking.objects.create(
                availability=availability,
                user=None,                                   # ← brak usera
                client_name=form.cleaned_data['client_name'],# ← nazwa klienta wpisana przez właściciela
                service_type=service_type,
                start_datetime=start_dt,
                client_phone=form.cleaned_data.get('client_phone', ''),
                client_note=form.cleaned_data.get('client_note', ''),
                booked_by=request.user,
                status='active'
            )
            messages.success(request, f"Dodano wizytę dla {form.cleaned_data['client_name']} na {start_time.strftime('%H:%M')}")
            return redirect("my_calendar_week")
    else:
        form = OwnerBookingForm()
        form.fields['service_type'].queryset = service_types
        form.fields['start_time'].choices = [(t, t) for t in generate_available_times(availability)]

    return render(request, "myschedule/owner_book_availability.html", {
        "availability": availability,
        "form": form,
        "service_types": service_types,
        "is_owner": True
    })

@login_required
def my_calendar(request):
    if not hasattr(request.user, "calendar"):
            return render(request, "no_calendar.html")
    
    # miesiąc
    month_offset = int(request.GET.get("month", 0))
    today = date.today().replace(day=1)
    year = today.year + (today.month - 1 + month_offset) // 12
    month = (today.month - 1 + month_offset) % 12 + 1
    start_of_month = date(year, month, 1)
    last_day = calendar.monthrange(year, month)[1]
    end_of_month = date(year, month, last_day)
    
    # siatka dni
    first_weekday = start_of_month.weekday()
    grid_start = start_of_month - timedelta(days=first_weekday)
    total_cells = ((first_weekday + last_day - 1) // 7 + 1) * 7
    all_days = [grid_start + timedelta(days=i) for i in range(total_cells)]
    
    # oblicz start aktualnego tygodnia
    current_week_start = date.today() - timedelta(days=date.today().weekday())
    
    # zbuduj listę tygodni z offsetem
    weeks_with_offset = []
    for i in range(0, len(all_days), 7):
        week_days = all_days[i:i+7]
        week_start = week_days[0]
        week_offset = (week_start - current_week_start).days // 7
        weeks_with_offset.append((week_days, week_offset))
    
    # publiczny URL
    public_path = reverse('public_calendar_week', args=[request.user.calendar.share_token])
    public_url = request.build_absolute_uri(public_path)
    
    # dostępności i zajęcia
    avail_qs = request.user.calendar.availabilities.filter(
        date__range=[start_of_month, end_of_month]
    ).order_by('date', 'start_time')
    bookings = Booking.objects.filter(availability__in=avail_qs).select_related('service_type')
    
    bookings_by_av = {}
    for b in bookings:
        slots = bookings_by_av.setdefault(b.availability_id, [])
        start = b.start_datetime.time()
        end = (b.start_datetime + timedelta(minutes=b.service_type.duration_minutes)).time()
        slots.append((start, end))
    
    av_by_day = {}
    for av in avail_qs:
        av_by_day.setdefault(av.date, []).append({
            "availability": av,
            "busy_slots": bookings_by_av.get(av.id, [])
        })

    visits_by_day = {}
    for b in bookings:
        booking_date = b.availability.date
        visits_by_day[booking_date] = visits_by_day.get(booking_date, 0) + 1

    POLISH_MONTHS = [
    "",  # placeholder for 0-indexing
    "styczeń", "luty", "marzec", "kwiecień", "maj", "czerwiec",
    "lipiec", "sierpień", "wrzesień", "październik", "listopad", "grudzień"
    ]


    return render(request, "myschedule/calendar.html", {
        "weeks_with_offset": weeks_with_offset,
        "start_of_month": start_of_month,
        "month_offset": month_offset,
        "public_calendar_url": public_url,
        "av_by_day": av_by_day,
        "month_name": POLISH_MONTHS[month],
        "year": year,
        "visits_by_day": visits_by_day, 
    })


@login_required 
def my_calendar_week(request):
    #jezeli user nie ma kalandarza to nie zobaczy widoku tylko napis(sprawdzanie grupy premium w signals)
    try:
        subscription = request.user.subscription
        if not subscription.is_active():
            return render(request, "dashboard/subscription_expired.html")
            
        # Sprawdź czy kalendarz istnieje (twój oryginalny kod)
        if not hasattr(request.user, "calendar"):
            return render(request, "dashboard/no_calendar.html")
        today = date.today()
        week_offset = int(request.GET.get("week", 0))
        start_of_week = today - timedelta(days=today.weekday()) + timedelta(weeks=week_offset)
        end_of_week = start_of_week + timedelta(days=6)
        week_days = [start_of_week + timedelta(days=i) for i in range(7)]
        now = datetime.now()
  

        public_path = reverse('public_calendar_week', args=[request.user.calendar.share_token])
        public_url = request.build_absolute_uri(public_path)
        #wyszukuje wszystkie dostepnosci w danym tygodsniu
        availabilities = request.user.calendar.availabilities.filter(
            date__range=[start_of_week, end_of_week]
        ).order_by('date', 'start_time')

        # Pobierz wszystkie Bookingi przypisane do tych Availability
        bookings = Booking.objects.filter(
            availability__in=availabilities,
            status='active'  # Tylko aktywne rezerwacje
        ).select_related('service_type', 'user')


        # Przygotuj strukturę mapującą Availability na zajęte sloty z Booking
        bookings_by_availability = {}
        for booking in bookings:
            booking_list = bookings_by_availability.setdefault(booking.availability_id, [])
            # Oblicz czas zakończenia
            start = booking.start_datetime
            duration = booking.service_type.duration_minutes
            booking.end_datetime = start + timedelta(minutes=duration)
            booking_list.append(booking)

        # Przydziel Availability z informacją o zajętych slotach do dni
        availabilities_by_day = {day: [] for day in week_days}

        for availability in availabilities:
            busy_slots = bookings_by_availability.get(availability.id, [])
            info = {
                "availability": availability,
                "busy_slots": busy_slots,
                "bookings": bookings_by_availability.get(availability.id, [])  # DODAJ to
            }

            if availability.date in availabilities_by_day:
                availabilities_by_day[availability.date].append(info)

        availabilities_by_day_items = [(day, availabilities_by_day.get(day, [])) for day in week_days]

        return render(request, "myschedule/calendar_week.html", {
            "week_days": week_days,
            "selected_week": start_of_week,
            "availabilities_by_day_items": availabilities_by_day_items,
            "public_calendar_url": public_url,
            "week_offset": week_offset,
            "now_time": now.time(),
        })
    
    except Subscription.DoesNotExist:
        return render(request, "dashboard/subscription_expired.html")

def subscription_expired(request):
    """Widok dla użytkowników z wygasłą subskrypcją"""
    context = {
        'hotpay_form_url': 'https://panel.hotpay.pl/twoj_link_do_formularza'
    }
    return render(request, "dashboard/subscription_expired.html", context)

