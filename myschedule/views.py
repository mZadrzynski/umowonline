import calendar as py_calendar
from datetime import date, datetime, timedelta, time
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from django.utils import timezone
from django.contrib import messages
from django.urls import reverse
from django.views.decorators.http import require_http_methods
from django.db.models import Count
from django.db import transaction, IntegrityError
import holidays

from .forms import SingleAvailabilityForm, BulkAvailabilityForm, ServiceTypeForm, BookingForm, OwnerBookingForm
from .models import Availability, Booking, ServiceType, Calendar, CalendarAlias
from account.models import Subscription



@login_required
def calendar_list(request):
    """
    Lista wszystkich kalendarzy użytkownika
    """
    
    storage = messages.get_messages(request)
    storage.used = True 
    calendars = request.user.calendars.all().annotate(
        bookings_count=Count('availabilities__bookings', distinct=True)
    ).order_by('id')
    
    return render(request, 'myschedule/calendar_list.html', {
        'calendars': calendars,
    })


@login_required
def calendar_create(request):
    MAX_CALENDARS = 20
    current_count = request.user.calendars.count()
    
    if current_count >= MAX_CALENDARS:
        messages.error(request, 
            f'❌ Osiągnąłeś limit {MAX_CALENDARS} kalendarzy. '
            f'Usuń niepotrzebne kalendarze, aby dodać nowy.')
        return redirect('calendar_list')
    
    if request.method == 'POST':
        name = request.POST.get('name', 'Nowy kalendarz')
        calendar = Calendar.objects.create(
            user=request.user,
            name=name,
            share_token=f"token_{request.user.id}_{Calendar.objects.filter(user=request.user).count() + 1}"
        )
        index = request.user.calendars.count()
        slug = CalendarAlias.build_slug(request.user.username, index)
        CalendarAlias.objects.create(user=request.user, calendar=calendar, index=index, slug=slug)
        messages.success(request, f"Kalendarz '{name}' został utworzony!")
        return redirect('calendar_list')
    return render(request, 'myschedule/calendar_create.html')


@login_required
def calendar_edit(request, calendar_id):
    """
    Edytuj kalendarz (zmiana nazwy)
    """
    calendar = get_object_or_404(Calendar, id=calendar_id, user=request.user)
    
    if request.method == 'POST':
        new_name = request.POST.get('name', '').strip()
        
        if not new_name:
            messages.error(request, "Nazwa kalendarza nie może być pusta")
        else:
            calendar.name = new_name
            calendar.save()
            messages.success(request, f"Zmieniono nazwę na: {new_name}")
            return redirect('calendar_list')
    
    return render(request, 'myschedule/calendar_edit.html', {
        'calendar': calendar
    })

@login_required
def calendar_set_active(request, calendar_id):
    """
    Ustaw kalendarz jako aktywny w sesji
    """
    calendar = get_object_or_404(Calendar, id=calendar_id, user=request.user)
    request.session['active_calendar_id'] = calendar.id
    
    messages.success(request, f"Przełączono na kalendarz: {calendar.name}")
    
    # ✅ Przekieruj na stronę z której przyszedł request
    referer = request.META.get('HTTP_REFERER')
    if referer and 'calendar_week' in referer:
        return redirect('my_calendar_week')
    elif referer and 'calendar/' in referer:
        return redirect('my_calendar')
    else:
        return redirect('calendar_list')

def get_active_calendar(request):
    if not request.user.is_authenticated:
        return None
    calendar_id = request.session.get('active_calendar_id')
    if calendar_id:
        calendar = Calendar.objects.filter(id=calendar_id, user=request.user).first()
        if calendar:
            return calendar
    return request.user.calendars.first()

@login_required
def add_availability(request):
    calendar = get_active_calendar(request)
    if not calendar:
        messages.error(request, "Nie masz kalendarza")
        return redirect("my_calendar_week")
    
    single_form = SingleAvailabilityForm(prefix='single', calendar=calendar)
    bulk_form = BulkAvailabilityForm(prefix='bulk')
    
    if request.method == "POST":
        if 'submit_single' in request.POST:
            single_form = SingleAvailabilityForm(request.POST, prefix='single', calendar=calendar)
            if single_form.is_valid():
                availability = single_form.save(commit=False)
                availability.calendar = calendar
                availability.save()
                messages.success(request, "Dostępność została dodana.")
                return redirect("my_calendar")
                    
        elif 'submit_bulk' in request.POST:
            bulk_form = BulkAvailabilityForm(request.POST, prefix='bulk')
            if bulk_form.is_valid():
                cal = calendar
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
                        overlapping = Availability.objects.filter(calendar=cal, date=current, start_time__lt=end_time, end_time__gt=start_time)
                        
                        if not overlapping.exists():
                            Availability.objects.create(calendar=cal, date=current, start_time=start_time, end_time=end_time)
                            created_count += 1
                        else:
                            existing = overlapping.first()
                            conflicts.append(f"{current.strftime('%d.%m.%Y')} ({existing.start_time.strftime('%H:%M')}-{existing.end_time.strftime('%H:%M')})")
                            conflict_count += 1
                    
                    current += timedelta(days=1)
                
                if created_count > 0:
                    messages.success(request, f"Dodano {created_count} dostępności.")
                
                if conflict_count > 0:
                    conflicts_str = ', '.join(conflicts[:5])
                    if len(conflicts) > 5:
                        conflicts_str += f" i {len(conflicts)-5} innych"
                    messages.warning(request, f"Pominięto {conflict_count} nakładających się terminów: {conflicts_str}")
                
                return redirect("my_calendar_week")
    
    return render(request, "myschedule/add_availability.html", {"single_form": single_form, "bulk_form": bulk_form, 'current_calendar': calendar, 'user_calendars': request.user.calendars.all(),})

@login_required
def delete_availability(request, availability_id):
    calendar = get_active_calendar(request)
    if not calendar:
        messages.error(request, "Nie masz kalendarza")
        return redirect("my_calendar_week")
    
    availability = get_object_or_404(Availability, id=availability_id, calendar=calendar)
    
    if request.method == 'POST':
        availability.delete()
        messages.success(request, "Dostępność została usunięta.")
        return redirect("my_calendar")
    
    return render(request, 'myschedule/confirm_delete.html', {'availability': availability})

@login_required
def add_service(request):
    calendar = get_active_calendar(request)
    if not calendar:
        messages.error(request, "Nie masz kalendarza")
        return redirect("my_calendar_week")
    
    if request.method == "POST":
        form = ServiceTypeForm(request.POST)
        if form.is_valid():
            service = form.save(commit=False)
            service.calendar = calendar
            service.save()
            return redirect("my_calendar_week")
    else:
        form = ServiceTypeForm()
    
    return render(request, "myschedule/service_type_form.html", {"form": form, "current_calendar": calendar, 'user_calendars': request.user.calendars.all(),})

@login_required
def service_type_edit(request, pk):
    calendar = get_active_calendar(request)
    if not calendar:
        messages.error(request, "Nie masz kalendarza")
        return redirect("my_calendar_week")
    
    service_type = get_object_or_404(ServiceType, pk=pk, calendar=calendar)
    
    if request.method == 'POST':
        name = request.POST.get('name', '').strip()
        duration_minutes = request.POST.get('duration_minutes', '')
        description = request.POST.get('description', '').strip()
        price = request.POST.get('price', '')
        
        if not name:
            messages.error(request, "Nazwa serwisu jest wymagana")
            return render(request, 'myschedule/service_type_form.html', {'service_type': service_type, 'calendar': calendar})
        
        if not duration_minutes or int(duration_minutes) <= 0:
            messages.error(request, "Czas trwania musi być większy od 0")
            return render(request, 'myschedule/service_type_form.html', {'service_type': service_type, 'calendar': calendar})
        
        service_type.name = name
        service_type.duration_minutes = int(duration_minutes)
        service_type.description = description
        service_type.price = price if price else None
        service_type.save()
        
        messages.success(request, f"Serwis '{name}' został zaktualizowany")
        return redirect('service_types_list')
    
    return render(request, 'myschedule/service_type_form.html', {'service_type': service_type, 'calendar': calendar})

@login_required
def service_types_list(request):
    calendar = get_active_calendar(request)
    if not calendar:
        messages.error(request, "Nie masz kalendarza")
        return redirect("my_calendar_week")
    
    service_types = ServiceType.objects.filter(calendar=calendar).order_by('-id')
    return render(request, 'myschedule/service_types_list.html', {'service_types': service_types, 'calendar': calendar, 'current_calendar': calendar, 'user_calendars': request.user.calendars.all(),})

@login_required
@require_http_methods(["GET", "POST"])
def service_type_delete(request, pk):
    calendar = get_active_calendar(request)
    if not calendar:
        messages.error(request, "Nie masz kalendarza")
        return redirect("my_calendar_week")
    
    service_type = get_object_or_404(ServiceType, pk=pk, calendar=calendar)
    
    if request.method == 'POST':
        service_name = service_type.name
        service_type.delete()
        messages.success(request, f"Serwis '{service_name}' został usunięty")
        return redirect('service_types_list')
    
    return render(request, 'myschedule/service_type_confirm_delete.html', {'service_type': service_type})

@login_required
def calendar_bookings(request):
    calendar = get_active_calendar(request)
    if not calendar:
        return render(request, "dashboard/no_calendar.html")
    
    calendar_bookings = Booking.objects.filter(availability__calendar=calendar, status='active').select_related('user', 'service_type').order_by('-booked_at')
    
    for booking in calendar_bookings:
        start = booking.start_datetime
        duration = booking.service_type.duration_minutes
        booking.end_datetime = start + timedelta(minutes=duration)
    
    return render(request, "myschedule/calendar_bookings.html", {"bookings": calendar_bookings, "current_calendar": calendar, 'user_calendars': request.user.calendars.all(),})

@login_required
def my_bookings(request):
    my_bookings = Booking.objects.filter(user=request.user, status='active').select_related('availability__calendar__user', 'service_type').order_by('-booked_at')
    
    for booking in my_bookings:
        if booking.start_datetime:
            start = booking.start_datetime
            duration = booking.service_type.duration_minutes
            booking.end_datetime = start + timedelta(minutes=duration)

    return render(request, "myschedule/my_bookings.html", {"my_bookings": my_bookings,})

@login_required
def cancel_booking(request, booking_id):
    from account.signals import cancel_booking_with_notifications
    
    booking = get_object_or_404(Booking, id=booking_id, user=request.user, status='active')
    
    if request.method == 'POST':
        cancel_booking_with_notifications(booking)
        messages.success(request, f'Wizyta {booking.service_type.name} została anulowana.')
        return redirect('my_bookings')
    
    return render(request, 'myschedule/confirm_cancel_booking.html', {'booking': booking})

@login_required
def cancel_calendar_booking(request, booking_id):
    from account.signals import cancel_booking_with_notifications
    
    calendar = get_active_calendar(request)
    if not calendar:
        messages.error(request, "Nie masz kalendarza")
        return redirect("my_calendar_week")
    
    booking = get_object_or_404(Booking, id=booking_id, availability__calendar=calendar, status='active')
    
    if request.method == 'POST':
        cancel_booking_with_notifications(booking)
        messages.success(request, f'Wizyta {booking.service_type.name} została anulowana.')
        return redirect('my_bookings')
    
    return render(request, 'myschedule/confirm_cancel_calendar_booking.html', {'booking': booking})

def generate_available_times(availability):
    times = []
    start_hour = availability.start_time.hour
    start_minute = availability.start_time.minute
    end_hour = availability.end_time.hour
    end_minute = availability.end_time.minute
    
    current_time = time(start_hour, start_minute)
    end_time = time(end_hour, end_minute)
    
    while current_time < end_time:
        times.append(current_time.strftime('%H:%M'))
        current_datetime = datetime.combine(date.today(), current_time)
        current_datetime += timedelta(minutes=15)
        current_time = current_datetime.time()
    
    return times

def check_time_collision(availability, start_datetime, service_type):
    
    if timezone.is_naive(start_datetime):
        start_datetime = timezone.make_aware(start_datetime)
    
    end_datetime = start_datetime + timedelta(minutes=service_type.duration_minutes)
    
    conflicting_bookings = Booking.objects.filter(availability=availability, status='active')
    
    for booking in conflicting_bookings:
        existing_start = booking.start_datetime
        existing_end = existing_start + timedelta(minutes=booking.service_type.duration_minutes)
        
        if (start_datetime < existing_end and end_datetime > existing_start):
            return True
    
    return False

@login_required
def my_calendar(request):
    calendar = get_active_calendar(request)
    if not calendar:
        return render(request, "dashboard/no_calendar.html")
    
    month_offset = int(request.GET.get("month", 0))
    today = date.today().replace(day=1)
    year = today.year + (today.month - 1 + month_offset) // 12
    month = (today.month - 1 + month_offset) % 12 + 1
    start_of_month = date(year, month, 1)
    last_day = py_calendar.monthrange(year, month)[1]
    end_of_month = date(year, month, last_day)
    
    first_weekday = start_of_month.weekday()
    grid_start = start_of_month - timedelta(days=first_weekday)
    total_cells = ((first_weekday + last_day - 1) // 7 + 1) * 7
    all_days = [grid_start + timedelta(days=i) for i in range(total_cells)]
    
    current_week_start = date.today() - timedelta(days=date.today().weekday())
    
    weeks_with_offset = []
    for i in range(0, len(all_days), 7):
        week_days = all_days[i:i+7]
        week_start = week_days[0]
        week_offset = (week_start - current_week_start).days // 7
        weeks_with_offset.append((week_days, week_offset))
    
    public_path = reverse('public_calendar_week', args=[calendar.share_token])
    public_url = request.build_absolute_uri(public_path)
    
    avail_qs = calendar.availabilities.filter(date__range=[start_of_month, end_of_month]).order_by('date', 'start_time')
    bookings = Booking.objects.filter(availability__in=avail_qs).select_related('service_type')
    
    bookings_by_av = {}
    for b in bookings:
        slots = bookings_by_av.setdefault(b.availability_id, [])
        start = b.start_datetime.time()
        end = (b.start_datetime + timedelta(minutes=b.service_type.duration_minutes)).time()
        slots.append((start, end))
    
    av_by_day = {}
    for av in avail_qs:
        av_by_day.setdefault(av.date, []).append({"availability": av, "busy_slots": bookings_by_av.get(av.id, [])})

    visits_by_day = {}
    for b in bookings:
        booking_date = b.availability.date
        visits_by_day[booking_date] = visits_by_day.get(booking_date, 0) + 1

    POLISH_MONTHS = ["", "styczeń", "luty", "marzec", "kwiecień", "maj", "czerwiec", "lipiec", "sierpień", "wrzesień", "październik", "listopad", "grudzień"]

    return render(request, "myschedule/calendar.html", {"weeks_with_offset": weeks_with_offset, "start_of_month": start_of_month, "month_offset": month_offset, "public_calendar_url": public_url, "av_by_day": av_by_day, "month_name": POLISH_MONTHS[month], "year": year, "visits_by_day": visits_by_day, "current_calendar": calendar, 'user_calendars': request.user.calendars.all(),})

@login_required 
def my_calendar_week(request):
    try:
        subscription = request.user.subscription
        if not subscription.is_active():
            return render(request, "dashboard/subscription_expired.html")
    
        calendar = get_active_calendar(request)
        if not calendar:
            return render(request, "dashboard/no_calendar.html")
        
        today = date.today()
        week_offset = int(request.GET.get("week", 0))
        start_of_week = today - timedelta(days=today.weekday()) + timedelta(weeks=week_offset)
        end_of_week = start_of_week + timedelta(days=6)
        week_days = [start_of_week + timedelta(days=i) for i in range(7)]
        now = timezone.now()
  
        public_path = reverse('public_calendar_week', args=[calendar.share_token])
        public_url = request.build_absolute_uri(public_path)
        
        availabilities = calendar.availabilities.filter(date__range=[start_of_week, end_of_week]).order_by('date', 'start_time')

        bookings = Booking.objects.filter(availability__in=availabilities, status='active').select_related('service_type', 'user').order_by('start_datetime')
  
        bookings_by_availability = {}
        for booking in bookings:
            booking_list = bookings_by_availability.setdefault(booking.availability_id, [])
            start = booking.start_datetime
            duration = booking.service_type.duration_minutes
            booking.end_datetime = start + timedelta(minutes=duration)
            booking_list.append(booking)

        availabilities_by_day = {day: [] for day in week_days}

        for availability in availabilities:
            busy_slots = bookings_by_availability.get(availability.id, [])
            info = {"availability": availability, "busy_slots": busy_slots, "bookings": bookings_by_availability.get(availability.id, [])}

            if availability.date in availabilities_by_day:
                availabilities_by_day[availability.date].append(info)

        availabilities_by_day_items = [(day, availabilities_by_day.get(day, [])) for day in week_days]

        return render(request, "myschedule/calendar_week.html", {"week_days": week_days, "selected_week": start_of_week, "availabilities_by_day_items": availabilities_by_day_items, "public_calendar_url": public_url, "week_offset": week_offset, "now_time": now.time(), "today": now.date(), "current_calendar": calendar, "user_calendars": request.user.calendars.all(),})
    
    except Subscription.DoesNotExist:
        return render(request, "dashboard/subscription_expired.html")

def subscription_expired(request):
    context = {'hotpay_form_url': 'https://panel.hotpay.pl/twoj_link_do_formularza'}
    return render(request, "dashboard/subscription_expired.html", context)

def calculate_free_time_slots(availability, service_duration_minutes=15):

    
    bookings = Booking.objects.filter(availability=availability, status='active').order_by('start_datetime')
    
    avail_start_minutes = availability.start_time.hour * 60 + availability.start_time.minute
    avail_end_minutes = availability.end_time.hour * 60 + availability.end_time.minute
    
    busy_intervals = []
    for booking in bookings:
        start_minutes = booking.start_datetime.time().hour * 60 + booking.start_datetime.time().minute
        end_minutes = start_minutes + booking.service_type.duration_minutes
        busy_intervals.append((start_minutes, end_minutes))
    
    if busy_intervals:
        busy_intervals.sort()
        merged_busy = [busy_intervals[0]]
        for current_start, current_end in busy_intervals[1:]:
            last_start, last_end = merged_busy[-1]
            if current_start <= last_end:
                merged_busy[-1] = (last_start, max(last_end, current_end))
            else:
                merged_busy.append((current_start, current_end))
    else:
        merged_busy = []
    
    free_intervals = []
    current_minute = avail_start_minutes
    
    for busy_start, busy_end in merged_busy:
        if current_minute < busy_start:
            free_intervals.append((current_minute, busy_start))
        current_minute = max(current_minute, busy_end)
    
    if current_minute < avail_end_minutes:
        free_intervals.append((current_minute, avail_end_minutes))
    
    free_slots = []
    for start_minutes, end_minutes in free_intervals:
        if end_minutes - start_minutes >= service_duration_minutes:
            start_hour = start_minutes // 60
            start_min = start_minutes % 60
            end_hour = end_minutes // 60
            end_min = end_minutes % 60
            
            start_time_str = f"{start_hour:02d}:{start_min:02d}"
            end_time_str = f"{end_hour:02d}:{end_min:02d}"
            free_slots.append((start_time_str, end_time_str))
    
    return free_slots

def generate_available_start_times(availability, duration_minutes):
    now = timezone.now()
    
    availability_end_dt = timezone.make_aware(datetime.combine(availability.date, availability.end_time))
    if availability_end_dt <= now:
        return []
    
    available_times = []
    current_time = availability.start_time
    
    while current_time < availability.end_time:
        slot_dt = timezone.make_aware(datetime.combine(availability.date, current_time))
        slot_end_dt = slot_dt + timedelta(minutes=duration_minutes)
        
        if slot_dt <= now:
            current_time = (datetime.combine(availability.date, current_time) + timedelta(minutes=15)).time()
            continue
        
        if slot_end_dt > timezone.make_aware(datetime.combine(availability.date, availability.end_time)):
            break
        
        conflict = Booking.objects.filter(availability=availability, status='active', start_datetime__lt=slot_end_dt, start_datetime__gte=slot_dt).exists()
        
        if not conflict:
            available_times.append((current_time.strftime('%H:%M'), current_time.strftime('%H:%M')))
        
        current_time = (datetime.combine(availability.date, current_time) + timedelta(minutes=15)).time()
    
    return available_times

@login_required
def book_availability(request, availability_id):

    
    availability = get_object_or_404(Availability, id=availability_id)
    now = timezone.now()
    
    availability_end_dt = timezone.make_aware(datetime.combine(availability.date, availability.end_time))
    storage = messages.get_messages(request)
    storage.used = True
    
    if availability_end_dt <= now:
            messages.error(request, "❌ Ten termin już minął. Nie można rezerwować.")
            return redirect(request.META.get('HTTP_REFERER', 'my_calendar_week'))
    
    is_owner = hasattr(request.user, 'calendars') and availability.calendar in request.user.calendars.all()
    
    if is_owner:
        return handle_owner_booking(request, availability)
    else:
        return handle_regular_booking(request, availability)

@login_required
def handle_regular_booking(request, availability):
    from django.contrib import messages
    from django.db import transaction, IntegrityError
    
    storage = messages.get_messages(request)
    storage.used = True

    now = timezone.now()
    availability_end_dt = timezone.make_aware(datetime.combine(availability.date, availability.end_time))
    
    if availability_end_dt <= now:
        messages.error(request, "❌ Ten termin już minął.")
        return redirect("my_calendar_week")

    if Booking.objects.filter(availability=availability, user=request.user, status='active').exists():
        return render(request, "myschedule/already_booked.html", {"availability": availability})

    service_types = ServiceType.objects.filter(calendar=availability.calendar)

    if request.method == "POST":
        form = BookingForm(request.POST, user=request.user, availability=availability, service_types=service_types)
        
        service_type_id = form.data.get('service_type')
        if service_type_id:
            try:
                service_obj = ServiceType.objects.get(id=service_type_id)
                available_times = generate_available_start_times(availability, service_obj.duration_minutes)
                if available_times:
                    form.fields['start_time'].choices = available_times
                else:
                    form.fields['start_time'].choices = [('', 'Brak dostępnych godzin')]
            except ServiceType.DoesNotExist:
                available_times = generate_available_start_times(availability, 15)
                form.fields['start_time'].choices = available_times
        else:
            available_times = generate_available_start_times(availability, 15)
            form.fields['start_time'].choices = available_times

        if form.is_valid():
            service_type = form.cleaned_data.get('service_type')
            if not service_type:
                form.add_error('service_type', "Wybierz rodzaj usługi.")
            else:
                start_time_str = form.cleaned_data.get('start_time')
                if not start_time_str:
                    form.add_error('start_time', "Wybierz godzinę rozpoczęcia.")
                else:
                    start_time = datetime.strptime(start_time_str, '%H:%M').time()
                    start_dt = timezone.make_aware(datetime.combine(availability.date, start_time))
                    
                    if start_dt <= now:
                        form.add_error('start_time', "❌ Ten termin już minął.")
                    else:
                        try:
                            with transaction.atomic():
                                end_dt = start_dt + timedelta(minutes=service_type.duration_minutes)
                                
                                has_conflict = False
                                conflicting_bookings = Booking.objects.filter(availability=availability, status='active')
                                        
                                for existing_booking in conflicting_bookings:
                                    existing_end = existing_booking.start_datetime + timedelta(minutes=existing_booking.service_type.duration_minutes)
                                    
                                    if start_dt < existing_end and end_dt > existing_booking.start_datetime:
                                        has_conflict = True
                                        form.add_error('start_time', f"❌ Ten termin nakłada się z wizytą {existing_booking.start_datetime.strftime('%H:%M')}-{existing_end.strftime('%H:%M')}")
                                        break
                                
                                if not has_conflict:
                                    Booking.objects.create(availability=availability, user=request.user, service_type=service_type, start_datetime=start_dt, client_phone=form.cleaned_data.get('client_phone', ''), client_note=form.cleaned_data.get('client_note', ''), booked_by=request.user, status='active')
                                    messages.success(request, f"✅ Zarezerwowano wizytę {service_type.name} na {start_time.strftime('%H:%M')}")
                                    return redirect("my_bookings")
                                    
                        except IntegrityError:
                            form.add_error('start_time', "❌ Ten slot został właśnie zarezerwowany. Spróbuj ponownie.")
    else:
        form = BookingForm(user=request.user, availability=availability, service_types=service_types)
        
        available_times = generate_available_start_times(availability, 15)
        if available_times:
            form.fields['start_time'].choices = available_times
        else:
            form.fields['start_time'].choices = [('', 'Brak dostępnych godzin')]

    return render(request, "myschedule/book_availability.html", {"availability": availability, "form": form, "service_types": service_types})

@login_required
def handle_owner_booking(request, availability):
    from django.db import transaction, IntegrityError

    service_types = ServiceType.objects.filter(calendar=availability.calendar)
    
    if request.method == "POST":
        form = OwnerBookingForm(request.POST)
        form.fields['service_type'].queryset = service_types
        
        service_type_id = form.data.get('service_type')
        if service_type_id:
            try:
                service_obj = ServiceType.objects.get(id=service_type_id)
                form.update_available_times(availability, service_obj.duration_minutes)
            except ServiceType.DoesNotExist:
                form.update_available_times(availability, 15)
        else:
            form.update_available_times(availability, 15)
        
        if form.is_valid():
            service_type = form.cleaned_data.get('service_type')
            if not service_type:
                form.add_error('service_type', "Wybierz rodzaj usługi.")
            else:

                start_time = datetime.strptime(form.cleaned_data['start_time'], '%H:%M').time()
                start_dt = timezone.make_aware(datetime.combine(availability.date, start_time))
                try:
                    with transaction.atomic():
                        end_dt = start_dt + timedelta(minutes=service_type.duration_minutes)
                        
                        has_conflict = False
                        conflicting_bookings = Booking.objects.filter(availability=availability, status='active')
                        
                        for existing_booking in conflicting_bookings:
                            existing_end = existing_booking.start_datetime + timedelta(minutes=existing_booking.service_type.duration_minutes)
                            
                            if start_dt < existing_end and end_dt > existing_booking.start_datetime:
                                has_conflict = True
                                form.add_error('start_time', f"❌ Ten termin nakłada się z wizytą {existing_booking.start_datetime.strftime('%H:%M')}-{existing_end.strftime('%H:%M')}")
                                break
                        
                        if not has_conflict:
                            Booking.objects.create(availability=availability, user=None, client_name=form.cleaned_data['client_name'], service_type=service_type, start_datetime=start_dt, client_phone=form.cleaned_data.get('client_phone', ''), client_note=form.cleaned_data.get('client_note', ''), booked_by=request.user, status='active')
                            messages.success(request, f"✅ Dodano wizytę dla {form.cleaned_data['client_name']} na {start_time.strftime('%H:%M')}")
                            return redirect("my_calendar_week")
                            
                except IntegrityError:
                    form.add_error('start_time', "❌ Ten slot został właśnie zarezerwowany. Spróbuj ponownie.")
                    
    else:
        form = OwnerBookingForm()
        form.fields['service_type'].queryset = service_types
        form.update_available_times(availability, 15)
    
    return render(request, "myschedule/owner_book_availability.html", {"availability": availability, "form": form, "service_types": service_types, "is_owner": True})


@login_required
def calendar_delete(request, calendar_id):
    """Usuń kalendarz (zawsze zostaw minimum 1)"""
    calendar = get_object_or_404(Calendar, id=calendar_id, user=request.user)
    
    # Sprawdź czy to nie jedyny kalendarz
    user_calendars_count = request.user.calendars.count()
    
    if user_calendars_count <= 1:
        messages.error(request, '❌ Nie możesz usunąć ostatniego kalendarza! Musisz mieć przynajmniej jeden.')
        return redirect('calendar_list')
    
    if request.method == 'POST':
        calendar_name = calendar.name
        
        # Sprawdź czy to główny kalendarz (przypisany do BusinessProfile)
        business_profiles = calendar.businessprofile_set.all()
        if business_profiles.exists():
            messages.warning(request, 
                f'⚠️ Kalendarz "{calendar_name}" jest przypisany do profilu biznesowego. '
                f'Najpierw zmień kalendarz w profilu, a potem usuń ten kalendarz.')
            return redirect('calendar_list')
        
        calendar.delete()
        messages.success(request, f'✅ Kalendarz "{calendar_name}" został usunięty.')
        return redirect('calendar_list')
    
    return render(request, 'myschedule/calendar_confirm_delete.html', {
        'calendar': calendar
    })