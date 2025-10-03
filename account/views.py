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
from django.http import HttpResponse, JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from django.conf import settings
from django.utils import timezone
from .models import Subscription, Payment
import hashlib
import json
import uuid
import logging

logger = logging.getLogger('hotpay')


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



@login_required
def create_payment(request):
    '''Widok do tworzenia nowej płatności za subskrypcję'''
    user = request.user
    
    # Sprawdź czy user ma już subskrypcję
    try:
        subscription = user.subscription
    except Subscription.DoesNotExist:
        # Utwórz nową subskrypcję z trial period
        subscription = Subscription.objects.create(
            user=user,
            end_date=timezone.now() + timezone.timedelta(days=30),
            status='active'
        )
    
    # Sprawdź czy subskrypcja nie jest już aktywna na długo
    #if subscription.is_active() and subscription.end_date > timezone.now() + timezone.timedelta(days=25):
    #    messages.info(request, 'Twoja subskrypcja jest już aktywna!')
    #    return redirect('my_calendar_week')
    
    # Generuj unikalny ID płatności
    payment_id = str(uuid.uuid4())
    amount = 20.00  # 20 PLN za miesiąc
    
    # Utwórz rekord płatności
    payment = Payment.objects.create(
        user=user,
        subscription=subscription,
        amount=amount,
        payment_id=payment_id
    )
    
    # Przygotuj dane dla HotPay
    hotpay_data = {
        'SEKRET': settings.HOTPAY_SECRET_KEY,
        'KWOTA': f"{amount:.2f}",
        'NAZWA_USLUGI': 'Subskrypcja umowonline - 30 dni',
        'ADRES_WWW': request.build_absolute_uri('/'),
        'ID_PLATNOSCI': payment_id,
        'EMAIL': user.email,
        'NAZWA': f"{user.first_name} {user.last_name}" if user.first_name else user.username,
        'RETURN_URL': request.build_absolute_uri('/ac/payment/success/'),
        'RETURN_URLC': request.build_absolute_uri('/account/payment/webhook/'),
    }
    
    return render(request, 'account/payment/hotpay_form.html', {
        'hotpay_data': hotpay_data,
        'payment': payment,
        'subscription': subscription,
        'HOTPAY_API_URL': settings.HOTPAY_API_URL,
    })

@csrf_exempt
#@require_POST test czy zadziala
def hotpay_webhook(request):
    '''Webhook do obsługi powiadomień z HotPay'''
    try:
    # Pobierz wszystkie wartości
        kwota = request.POST.get('KWOTA', '')
        id_platnosci = request.POST.get('ID_PLATNOSCI', '')
        id_zamowienia = request.POST.get('ID_ZAMOWIENIA', '')
        status = request.POST.get('STATUS', '')
        secure = request.POST.get('SECURE', '')      # <— dodaj
        sekret = request.POST.get('SEKRET', '').rstrip(',')
        
        # Logowanie dla debugowania
        logger.info(f"HotPay webhook received: {dict(request.POST)}")
        
        # Weryfikacja hash
        hash_string = ";".join([
            settings.HOTPAY_NOTIFICATION_PASSWORD,
            kwota,
            id_platnosci,
            id_zamowienia,
            status,
            secure,
            sekret
        ])


        logger.info("hash_string repr: %r", hash_string)

        logger.info("kwota = %r", kwota)
        logger.info("id_platnosci = %r", id_platnosci)
        logger.info("id_zamowienia = %r", id_zamowienia)
        logger.info("status = %r", status)
        logger.info("secure = %r", secure)
        logger.info("sekret = %r", sekret)
        logger.info("notification_password = %r", settings.HOTPAY_NOTIFICATION_PASSWORD)
                
        calculated_hash = hashlib.sha256(hash_string.encode('utf-8')).hexdigest()
        logger.info(f"Calculated SHA256 = {calculated_hash}")
        

        received_hash = request.POST.get('HASH', '')
        if calculated_hash != received_hash:
            logger.error(f"Invalid hash. Received: {received_hash}, Calculated: {calculated_hash}")
            return HttpResponse('Invalid hash', status=400)
            
        # Znajdź płatność
        try:
            payment = Payment.objects.get(payment_id=id_platnosci)
        except Payment.DoesNotExist:
            logger.error(f"Payment not found: {id_platnosci}")
            return HttpResponse('Payment not found', status=404)
        
        # Aktualizuj status płatności
        payment.hotpay_response = dict(request.POST)
        
        if status == 'SUCCESS':
            payment.status = 'completed'
            payment.completed_at = timezone.now()
            payment.hotpay_payment_id = request.POST.get('ID_PLATNOSCI_HOTPAY', '')
            payment.save()
            
            # KLUCZOWE: Przedłuż subskrypcję o 30 dni
            subscription = payment.subscription
            subscription.extend_subscription(days=30)
            subscription.hotpay_transaction_id = payment.hotpay_payment_id
            subscription.save()
            
            logger.info(f"Payment successful for user {payment.user.username} - subscription extended by 30 days")
            
        elif status == 'FAILED':
            payment.status = 'failed'
            payment.save()
            logger.warning(f"Payment failed for user {payment.user.username}")
        
        return HttpResponse('OK')
        
    except Exception as e:
        logger.error(f"Webhook processing error: {str(e)}")
        return HttpResponse(f'Error: {str(e)}', status=500)

@login_required
def payment_success(request):
    '''Strona potwierdzenia płatności'''
    return render(request, 'account/payment/success.html')

@login_required
def subscription_status(request):
    '''Status subskrypcji użytkownika'''
    try:
        subscription = request.user.subscription
    except Subscription.DoesNotExist:
        subscription = None
    
    return render(request, 'account/subscription_status.html', {
        'subscription': subscription
    })