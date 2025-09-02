import calendar
from datetime import date
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from .forms import AvailabilityForm

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