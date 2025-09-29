from django.shortcuts import redirect
from django.urls import reverse
from django.utils.deprecation import MiddlewareMixin
from .models import Subscription

class SubscriptionMiddleware(MiddlewareMixin):
    """Middleware sprawdzający status subskrypcji użytkownika"""
    
    # URLs dostępne bez aktywnej subskrypcji
    ALLOWED_URLS = [
        '/accounts/login/',
        '/accounts/logout/',
        '/accounts/register/',
        '/payment/',
        '/subscription/expired/',
        '/admin/',
        '/static/',
        '/media/',
    ]
    
    def process_request(self, request):
        # Pomiń dla nieuwierzytelnionych użytkowników
        if not request.user.is_authenticated:
            return None
            
        # Pomiń dla administratorów
        if request.user.is_superuser:
            return None
            
        # Sprawdź czy URL jest na liście dozwolonych
        for allowed_url in self.ALLOWED_URLS:
            if request.path.startswith(allowed_url):
                return None
                
        # Sprawdź status subskrypcji
        try:
            subscription = request.user.subscription
            if not subscription.is_active():
                # Zaktualizuj status jeśli wygasła
                if subscription.status == 'active':
                    subscription.status = 'expired'
                    subscription.save()
                return redirect('subscription_expired')
        except Subscription.DoesNotExist:
            # Użytkownik nie ma subskrypcji - stwórz ją (dla starych użytkowników)
            return redirect('subscription_expired')
            
        return None