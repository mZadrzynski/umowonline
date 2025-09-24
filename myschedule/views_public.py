
from datetime import date, timedelta
from django.shortcuts import render
from datetime import timedelta
from django.shortcuts import get_object_or_404, redirect, render
from .models import Booking, Calendar



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
        availability__in=availabilities
    ).select_related('service_type')

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

    context = {
        "week_days": week_days,
        "selected_week": start_of_week,
        "availabilities_by_day_items": [(d, avail_by_day[d]) for d in week_days],
        "calendar_owner": calendar.user,
    }
    return render(request, "myschedule/public_calendar_week.html", context)