from django.contrib.auth import authenticate, login
from django.http import HttpResponse
from django.shortcuts import render
from .forms import LoginForm, UserRegistrationForm, UserEditForm
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .models import *
from .forms import FavoriteCalendarForm
from myschedule.models import Calendar
from django.http import HttpResponse, JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from django.conf import settings
from django.utils import timezone
import hashlib
import uuid
import logging
from .forms import NotificationSettingsForm
from django.contrib.sites.shortcuts import get_current_site
from django.template.loader import render_to_string
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.utils.encoding import force_bytes, force_str
from django.core.mail import EmailMessage
from django.contrib.auth import get_user_model
from .tokens import account_activation_token


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
            # KLUCZOWA ZMIANA: ustaw is_active na False
            new_user.is_active = False
            # Save the User object
            new_user.save()
            
            # WYSYŁANIE EMAIL AKTYWACYJNEGO
            current_site = get_current_site(request)
            mail_subject = 'Aktywacja konta – UmowZdalnie.pl'
            message = render_to_string('account/activation_email.html', {
                'user': new_user,
                'domain': current_site.domain,
                'uid': urlsafe_base64_encode(force_bytes(new_user.pk)),
                'token': account_activation_token.make_token(new_user),
                'protocol': 'https' if request.is_secure() else 'http',
            })
            email = EmailMessage(mail_subject, message, to=[new_user.email])
            email.content_subtype = 'html'
            email.send()
            
            messages.success(request, 
                'Konto zostało utworzone! Sprawdź swoją skrzynkę pocztową i kliknij w link aktywacyjny.')
            return redirect('registration_pending')
    else:
        user_form = UserRegistrationForm()
    
    return render(request, 'account/register.html', {'user_form': user_form})

def register_done(request):
    return render(request, 'account/register_done.html')

@login_required
def edit(request):
    if request.method == 'POST':
        user_form = UserEditForm(
            instance=request.user,
            data=request.POST
        )
    
        if user_form.is_valid():
            user_form.save()
            messages.success(request, '✅ Profil został zaktualizowany.')
            return redirect('edit')  # lub inna strona
        else:
            messages.error(request, '❌ Popraw błędy w formularzu.')
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
def choose_plan(request):
    """Widok do wyboru planu subskrypcji"""
    
    # Pobierz dostępne plany
    plans = SubscriptionPlan.objects.filter(is_active=True).order_by('price_monthly')
    
    # Sprawdź czy user ma już subskrypcję
    current_subscription = None
    current_plan = None
    has_active_subscription = False
    
    try:
        current_subscription = request.user.subscription
        has_active_subscription = current_subscription.is_active()
        
        if has_active_subscription:
            # Pobierz plan - obsłuż przypadek gdy go nie ma
            current_plan = getattr(current_subscription, 'plan', None)
            
            # DEBUG - usuń to po naprawieniu
            logger.info(f"User: {request.user.username}, Subscription ID: {current_subscription.id}, Plan: {current_plan}")
            
    except Subscription.DoesNotExist:
        pass
    
    if request.method == 'POST':
        plan_id = request.POST.get('plan_id')
        action = request.POST.get('action', 'buy')
        
        try:
            selected_plan = SubscriptionPlan.objects.get(id=plan_id)
        except SubscriptionPlan.DoesNotExist:
            messages.error(request, 'Wybrany plan nie istnieje.')
            return redirect('choose_plan')
        
        # Przechowaj wybór planu w sesji
        request.session['selected_plan_id'] = str(selected_plan.id)
        request.session['selected_plan_name'] = selected_plan.display_name
        request.session['selected_plan_price'] = str(selected_plan.price_monthly)
        request.session['payment_action'] = action
        
        # Komunikaty informacyjne
        if action == 'extend':
            messages.info(request, f'Przedłużasz plan "{selected_plan.display_name}" o kolejne 30 dni.')
        elif action == 'change':
            messages.info(request, f'Zmieniasz plan na "{selected_plan.display_name}".')
        
        return redirect('create_payment')
    
    context = {
        'plans': plans,
        'current_subscription': current_subscription,
        'current_plan': current_plan,
        'has_active_subscription': has_active_subscription,
    }
    
    # DEBUG - usuń to później
    logger.info(f"Context: {context}")
    
    return render(request, 'account/choose_plan.html', context)

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
    
    # Pobierz wybrany plan z sesji
    plan_id = request.session.get('selected_plan_id')
    action = request.session.get('payment_action', 'buy')  # 'buy', 'extend', 'change'
    
    if not plan_id:
        messages.warning(request, 'Najpierw wybierz plan subskrypcji.')
        return redirect('choose_plan')
    
    try:
        selected_plan = SubscriptionPlan.objects.get(id=plan_id)
    except SubscriptionPlan.DoesNotExist:
        messages.error(request, 'Wybrany plan nie istnieje.')
        # Wyczyść sesję
        request.session.pop('selected_plan_id', None)
        request.session.pop('payment_action', None)
        return redirect('choose_plan')
    
    user = request.user
    
    # Sprawdź czy user ma już subskrypcję
    try:
        subscription = user.subscription
        
        if action == 'change' and subscription.plan != selected_plan:
            # Zmiana planu - ustaw nowy plan, ale przedłużenie nastąpi po obecnym okresie
            subscription.plan = selected_plan
            subscription.save()
            logger.info(f"User {user.username} changing plan to {selected_plan.display_name}")
        elif action == 'extend':
            # Przedłużenie - plan pozostaje ten sam
            logger.info(f"User {user.username} extending {selected_plan.display_name}")
        
    except Subscription.DoesNotExist:
        # Utwórz nową subskrypcję (dla nowych użytkowników)
        subscription = Subscription.objects.create(
            user=user,
            plan=selected_plan,
            end_date=timezone.now() + timezone.timedelta(days=30),
            status='active'
        )
        logger.info(f"Created new subscription for user {user.username} - {selected_plan.display_name}")
    
    # Generuj unikalny ID płatności
    payment_id = str(uuid.uuid4())
    amount = selected_plan.price_monthly
    
    # Utwórz rekord płatności
    payment = Payment.objects.create(
        user=user,
        subscription=subscription,
        amount=amount,
        payment_id=payment_id
    )
    
    logger.info(f"Created Payment: payment_id={payment.payment_id}, plan={selected_plan.display_name}, amount={amount}, action={action}")
    
    # Przygotuj nazwę usługi w zależności od akcji
    if action == 'extend':
        service_name = f'Przedłużenie subskrypcji - {selected_plan.display_name} (30 dni)'
    elif action == 'change':
        service_name = f'Zmiana planu na - {selected_plan.display_name} (30 dni)'
    else:
        service_name = f'Subskrypcja umowonline - {selected_plan.display_name} (30 dni)'
    
    # Przygotuj dane dla HotPay
    hotpay_data = {
        'SEKRET': settings.HOTPAY_SECRET_KEY,
        'KWOTA': f"{amount:.2f}",
        'NAZWA_USLUGI': service_name,
        'ADRES_WWW': request.build_absolute_uri('/'),
        'ID_ZAMOWIENIA': payment_id,
        'EMAIL': user.email,
        'NAZWA': f"{user.first_name} {user.last_name}" if user.first_name else user.username,
        'RETURN_URL': request.build_absolute_uri('/account/payment/success/'),
        'RETURN_URLC': request.build_absolute_uri('/account/payment/webhook/'),
    }
    
    # Wyczyść sesję
    request.session.pop('selected_plan_id', None)
    request.session.pop('selected_plan_name', None)
    request.session.pop('selected_plan_price', None)
    request.session.pop('payment_action', None)
    
    return render(request, 'account/payment/hotpay_form.html', {
        'hotpay_data': hotpay_data,
        'payment': payment,
        'subscription': subscription,
        'plan': selected_plan,
        'action': action,
        'HOTPAY_API_URL': settings.HOTPAY_API_URL,
    })




@csrf_exempt
def hotpay_webhook(request):
    try:
        # Pobierz dane z POST
        kwota = request.POST.get('KWOTA')
        id_platnosci = request.POST.get('ID_PLATNOSCI')
        id_zamowienia = request.POST.get('ID_ZAMOWIENIA', '')
        status = request.POST.get('STATUS')
        sekret = request.POST.get('SEKRET')
        received_hash = request.POST.get('HASH')
        
        notification_password = "dSvEhsMoBBGfPbfxBP8H"
        
        hash_string = f"{notification_password};{kwota};{id_platnosci};{id_zamowienia};{status};{sekret}"
        calculated_hash = hashlib.sha256(hash_string.encode('utf-8')).hexdigest()
        
        logger.info(f"Webhook data: KWOTA={kwota}, ID_PLATNOSCI={id_platnosci}, ID_ZAMOWIENIA='{id_zamowienia}', STATUS={status}")
        logger.info(f"Hash match: {calculated_hash == received_hash}")
        
        if calculated_hash != received_hash:
            logger.error("Hash mismatch!")
            return HttpResponse("Invalid hash", status=400)
        
        # Znajdź płatność
        try:
            payment = Payment.objects.get(payment_id=id_zamowienia)
        except Payment.DoesNotExist:
            logger.error(f"Payment not found: {id_zamowienia}")
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
            
            logger.info(f"Payment successful for user {payment.user.username} - {subscription.plan.display_name} subscription extended by 30 days")
            
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
    logger.info(f"Payment success reached via: {request.build_absolute_uri()}")

    return render(request, 'account/payment/success.html')

@login_required
def subscription_status(request):
    '''Status subskrypcji użytkownika'''
    try:
        subscription = request.user.subscription
    except Subscription.DoesNotExist:
        subscription = None
    
    # Pobierz informacje o SMS (jeśli plan to SMS)
    sms_usage = None
    sms_monthly_usage = 0
    sms_monthly_limit = 0
    
    if subscription and subscription.has_sms_plan():
        sms_monthly_usage = subscription.get_sms_monthly_usage()
        sms_monthly_limit = subscription.get_sms_monthly_limit()
        
        try:
            now = timezone.now()
            sms_usage = SMSUsage.objects.get(
                subscription=subscription,
                year=now.year,
                month=now.month
            )
        except SMSUsage.DoesNotExist:
            pass
    
    return render(request, 'account/subscription_status.html', {
        'subscription': subscription,
        'sms_usage': sms_usage,
        'sms_monthly_usage': sms_monthly_usage,
        'sms_monthly_limit': sms_monthly_limit,
    })

@login_required
def notification_settings(request):
    """Widok zarządzania ustawieniami powiadomień i statusu konta"""
    
    # Pobierz lub stwórz ustawienia powiadomień
    settings, created = UserNotificationSettings.objects.get_or_create(
        user=request.user
    )
    
    # Pobierz informacje o subskrypcji
    try:
        subscription = request.user.subscription
    except Subscription.DoesNotExist:
        subscription = None
    
    # Oblicz dni pozostałe
    days_left = 0
    is_trial = False
    if subscription and subscription.is_active():
        days_left = (subscription.end_date.date() - timezone.now().date()).days
        # Sprawdź czy to okres testowy (czy subskrypcja ma mniej niż 30 dni i nie ma płatności)
        is_trial = subscription.payments.filter(status='completed').count() == 0
    
    if request.method == 'POST':
        form = NotificationSettingsForm(request.POST, instance=settings)
        if form.is_valid():
            form.save()
            messages.success(request, 'Ustawienia zostały zaktualizowane.')
            return redirect('notification_settings')
    else:
        form = NotificationSettingsForm(instance=settings)
    
    return render(request, 'account/notification_settings.html', {
        'form': form,
        'settings': settings,
        'subscription': subscription,
        'days_left': days_left,
        'is_trial': is_trial
    })

def registration_pending(request):
    return render(request, 'account/register_done.html')  # Możesz użyć istniejącego szablonu

def activate(request, uidb64, token):
    try:
        uid = force_str(urlsafe_base64_decode(uidb64))
        user = get_user_model().objects.get(pk=uid)
    except (TypeError, ValueError, OverflowError, get_user_model().DoesNotExist):
        user = None

    if user and account_activation_token.check_token(user, token):
        user.is_active = True
        user.save()
        messages.success(request, 'Konto zostało pomyślnie aktywowane! Możesz się teraz zalogować.')
        return redirect('login')
    else:
        messages.error(request, 'Link aktywacyjny jest nieprawidłowy lub wygasł.')
        return render(request, 'account/activation_invalid.html')