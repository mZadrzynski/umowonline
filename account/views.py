from django.contrib.auth import authenticate, login
from django.http import HttpResponse
from django.shortcuts import render
from .forms import LoginForm, UserRegistrationForm, UserEditForm
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .models import FavoriteCalendar
from .forms import FavoriteCalendarForm
from myschedule.models import Calendar


def user_login(request):
    if request.method == 'POST':
        form = LoginForm(request.POST)
        if form.is_valid():
            cd = form.cleaned_data
            # Użyj email zamiast username
            user = authenticate(
                request,
                username=cd['email'],  # Django będzie używać email jako username
                password=cd['password']
            )
            if user is not None:
                if user.is_active:
                    login(request, user)
                    return redirect('/')  # lub przekieruj gdzie chcesz
                else:
                    messages.error(request, 'Konto zostało wyłączone.')
            else:
                messages.error(request, 'Nieprawidłowy email lub hasło.')
    else:
        form = LoginForm()
    return render(request, 'registration/login.html', {'form': form})

def register(request):
    if request.method == 'POST':
        user_form = UserRegistrationForm(request.POST)
        if user_form.is_valid():
            # Create a new user object but avoid saving it yet
            new_user = user_form.save(commit=False)
            # Set the chosen password
            new_user.set_password(user_form.cleaned_data['password'])
            # Save the User object
            new_user.save()
            
            messages.success(request, 'Konto zostało utworzone pomyślnie!')
            return redirect('login')
    else:
        user_form = UserRegistrationForm()
    
    return render(request, 'account/register.html', {'user_form': user_form})

@login_required
def edit(request):
    if request.method == 'POST':
        user_form = UserEditForm(
            instance=request.user,
            data=request.POST
        )
    
        if user_form.is_valid():
            user_form.save()
    else:
        user_form = UserEditForm(instance=request.user)

    return render(
            request,
            'account/edit.html',
            {
            'user_form': user_form,
            }
        )


@login_required
def favorite_calendars(request):
    """Lista ulubionych kalendarzy użytkownika"""
    favorites = FavoriteCalendar.objects.filter(user=request.user)
    
    # Sprawdź które kalendarze nadal istnieją
    for favorite in favorites:
        calendar_obj = favorite.get_calendar_object()
        favorite.is_active = calendar_obj is not None
        if calendar_obj:
            favorite.real_owner = calendar_obj.user.username
    
    return render(request, 'account/favorite_calendars.html', {
        'favorites': favorites
    })

@login_required
def add_favorite_calendar(request):
    import logging
    logger = logging.getLogger(__name__)
    logger.debug("ENTER add_favorite_calendar, method=%s", request.method)
    if request.method == 'POST':
        form = FavoriteCalendarForm(request.POST)
        logger.debug("POST data: %s", request.POST)
        logger.debug("Form valid: %s, errors: %s", form.is_valid(), form.errors)
        if form.is_valid():
            favorite = form.save(commit=False)
            favorite.user = request.user
            logger.debug("Saving favorite: %s", favorite)
            favorite.save()
            logger.debug("Saved favorite id: %s", favorite.id)
            messages.success(request, 'Dodano kalendarz do ulubionych.')
            return redirect('favorite_calendars')
    else:
        form = FavoriteCalendarForm()
    return render(request, 'account/add_favorite_calendar.html', {'form': form})


@login_required
def remove_favorite_calendar(request, favorite_id):
    """Usuń kalendarz z ulubionych"""
    favorite = get_object_or_404(FavoriteCalendar, id=favorite_id, user=request.user)
    
    if request.method == 'POST':
        calendar_name = favorite.calendar_name
        favorite.delete()
        messages.success(request, f'Usunięto "{calendar_name}" z ulubionych.')
        return redirect('favorite_calendars')
    
    return render(request, 'account/confirm_remove_favorite.html', {'favorite': favorite})