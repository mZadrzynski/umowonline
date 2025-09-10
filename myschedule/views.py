import calendar
from datetime import date, datetime, timedelta
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from .forms import AvailabilityForm, ServiceTypeForm, BookingForm
from datetime import timedelta
from django.shortcuts import get_object_or_404, redirect, render
from django.contrib.auth.decorators import login_required
from .models import Availability, Booking, ServiceType
from django.contrib import messages



@login_required
def my_calendar(request):
    if not hasattr(request.user, "calendar"):
        return HttpResponse("Nie masz kalendarza (tylko Premium ma dostęp)")

    today = date.today()
    cal = calendar.Calendar()
    month_days = cal.itermonthdates(today.year, today.month)

    return render(request, "myschedule/calendar.html", {
        "month_days": month_days,
        "today": today,
        "availabilities": request.user.calendar.availabilities.all(),
    })


def my_calendar_week(request):
    if not hasattr(request.user, "calendar"):
        return HttpResponse("Nie masz kalendarza (tylko Premium ma dostęp)")

    today = date.today()
    week_offset = int(request.GET.get("week", 0))
    start_of_week = today - timedelta(days=today.weekday()) + timedelta(weeks=week_offset)
    end_of_week = start_of_week + timedelta(days=6)
    week_days = [start_of_week + timedelta(days=i) for i in range(7)]

    availabilities = request.user.calendar.availabilities.filter(
        date__range=[start_of_week, end_of_week]
    ).order_by('date', 'start_time')

    # Pobierz wszystkie Bookingi przypisane do tych Availability
    bookings = Booking.objects.filter(
        availability__in=availabilities
    ).select_related('service_type')

    # Przygotuj strukturę mapującą Availability na zajęte sloty z Booking
    bookings_by_availability = {}
    for booking in bookings:
        slots = bookings_by_availability.setdefault(booking.availability_id, [])
        start = booking.start_datetime.time()
        end = (booking.start_datetime + timedelta(minutes=booking.service_type.duration_minutes)).time()
        slots.append((start, end))

    # Przydziel Availability z informacją o zajętych slotach do dni
    availabilities_by_day = {day: [] for day in week_days}

    for availability in availabilities:
        busy_slots = bookings_by_availability.get(availability.id, [])
        info = {
            "availability": availability,
            "busy_slots": busy_slots  # lista tuple (start, end) zajętych godzin
        }
        if availability.date in availabilities_by_day:
            availabilities_by_day[availability.date].append(info)

    availabilities_by_day_items = [(day, availabilities_by_day.get(day, [])) for day in week_days]

    return render(request, "myschedule/calendar_week.html", {
        "week_days": week_days,
        "selected_week": start_of_week,
        "availabilities_by_day_items": availabilities_by_day_items,
    })



@login_required
def add_availability(request):
    if not hasattr(request.user, "calendar"):
        return HttpResponse("Nie masz kalendarza (tylko Premium może dodać dostępność)")

    if request.method == "POST":
        form = AvailabilityForm(request.POST)
        if form.is_valid():
            availability = form.save(commit=False)
            availability.calendar = request.user.calendar
            availability.save()
            return redirect("my_calendar")
    else:
        form = AvailabilityForm()

    return render(request, "myschedule/add_availability.html", {"form": form})


@login_required
def add_service(request):
    if not hasattr(request.user, "calendar"):
        return HttpResponse("Nie masz kalendarza (tylko Premium może dodać wydarzenia)")
    if request.method == "POST":
        form = ServiceTypeForm(request.POST)
        if form.is_valid():
            event = form.save(commit=False)
            event.calendar = request.user.calendar
            event.save()
            return redirect("my_calendar")
    else:
        form = ServiceTypeForm()
    return render(request, "myschedule/add_service.html", {"form": form})



@login_required
def my_bookings(request):
    bookings = Booking.objects.filter(user=request.user).order_by('booked_at')

    for booking in bookings:
        start = booking.availability.start_time
        dummy_date = datetime(2000, 1, 1, start.hour, start.minute)
        duration = booking.service_type.duration_minutes  # zakładamy, że Booking ma pole service_type

        end_time = (dummy_date + timedelta(minutes=duration)).time()
        booking.end_time = end_time  # dynamiczne dodanie pola do obiektu

    return render(request, "myschedule/my_bookings.html", {"bookings": bookings})


@login_required
def book_availability(request, availability_id):
    availability = get_object_or_404(Availability, id=availability_id)
    
    if Booking.objects.filter(availability=availability, user=request.user).exists():
        return render(request, "myschedule/already_booked.html", {"availability": availability})
    
    service_types = ServiceType.objects.filter(calendar=availability.calendar)
    
    if request.method == "POST":
        form = BookingForm(request.POST)
        form.fields['service_type'].queryset = service_types
        
        if form.is_valid():
            service_type = form.cleaned_data['service_type']
            start_time = form.cleaned_data['start_time']
            
            # Połącz datę z Availability z wybraną godziną
            start_datetime = datetime.combine(availability.date, start_time)
            
            # Oblicz czas końca wizyty (POPRAWKA)
            end_datetime = start_datetime + timedelta(minutes=service_type.duration_minutes)
            end_time = end_datetime.time()
            
            # POPRAWIONE SPRAWDZENIE - porównuj tylko obiekty time
            availability_start = availability.start_time
            availability_end = availability.end_time
            
            print(f"Debug: start_time={start_time}, end_time={end_time}")
            print(f"Debug: availability start={availability_start}, end={availability_end}")
            print(f"Debug: start_time >= availability_start: {start_time >= availability_start}")
            print(f"Debug: end_time <= availability_end: {end_time <= availability_end}")
            
            # Sprawdź czy wizyta mieści się w ramach dostępności
            if start_time < availability_start or end_time > availability_end:
                messages.error(request, f"Wybrana godzina {start_time}-{end_time} nie mieści się w dostępnym czasie {availability_start}-{availability_end}!")
                return render(request, "myschedule/book_availability.html", {
                    "availability": availability, 
                    "form": form, 
                    "service_types": service_types
                })
            
            # Reszta kodu bez zmian...
            conflicting_bookings = Booking.objects.filter(
                availability=availability,
                start_datetime__date=availability.date
            ).exclude(user=request.user)
            
            # Sprawdź kolizje czasowe
            for booking in conflicting_bookings:
                existing_start = booking.start_datetime.time()
                existing_end = (booking.start_datetime + timedelta(minutes=booking.service_type.duration_minutes)).time()
                
                # Sprawdź czy zakresy się pokrywają
                if (start_time < existing_end and end_time > existing_start):
                    messages.error(request, "Ten termin jest już zajęty!")
                    return render(request, "myschedule/book_availability.html", {
                        "availability": availability, 
                        "form": form, 
                        "service_types": service_types
                    })
            
            # Stwórz rezerwację
            Booking.objects.create(
                availability=availability,
                user=request.user,
                service_type=service_type,
                start_datetime=start_datetime
            )
            
            messages.success(request, f"Zarezerwowano wizytę {service_type.name} na {start_time}")
            return redirect("my_bookings")
    else:
        form = BookingForm()
        form.fields['service_type'].queryset = service_types
    
    return render(request, "myschedule/book_availability.html", {
        "availability": availability, 
        "form": form, 
        "service_types": service_types
    })