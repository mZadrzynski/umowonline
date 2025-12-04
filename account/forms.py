from django import forms
from django.contrib.auth import get_user_model
from .models import FavoriteCalendar, UserNotificationSettings
from .utils import validate_and_normalize_polish_phone


class LoginForm(forms.Form):
    """Formularz logowania użytkownika"""
    email = forms.EmailField(
        widget=forms.EmailInput(attrs={
            'class': 'form-control form-control-lg',
            'placeholder': 'Wprowadź email'
        })
    )
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'form-control form-control-lg',
            'placeholder': 'Wprowadź hasło'
        })
    )


class UserRegistrationForm(forms.ModelForm):
    """Formularz rejestracji nowego użytkownika"""
    password = forms.CharField(
        label='Hasło',
        widget=forms.PasswordInput(attrs={
            'class': 'form-control form-control-lg',
            'placeholder': 'Wprowadź hasło'
        })
    )
    password2 = forms.CharField(
        label='Powtórz hasło',
        widget=forms.PasswordInput(attrs={
            'class': 'form-control form-control-lg',
            'placeholder': 'Powtórz hasło'
        })
    )
    
    class Meta:
        model = get_user_model()
        fields = ['username', 'first_name', 'last_name', 'email', 'phone_number']
        widgets = {
            'username': forms.TextInput(attrs={
                'class': 'form-control form-control-lg',
                'placeholder': 'Nazwa użytkownika'
            }),
            'first_name': forms.TextInput(attrs={
                'class': 'form-control form-control-lg',
                'placeholder': 'Imię'
            }),
            'last_name': forms.TextInput(attrs={
                'class': 'form-control form-control-lg',
                'placeholder': 'Drugie imię/Nazwisko (opcjonalne)'
            }),
            'email': forms.EmailInput(attrs={
                'class': 'form-control form-control-lg',
                'placeholder': 'Adres email'
            }),
            'phone_number': forms.TextInput(attrs={
                'class': 'form-control form-control-lg',
                'placeholder': '+48501234567 (opcjonalne)'
            }),
        }
        labels = {
            'username': 'Nazwa użytkownika',
            'first_name': 'Imię',
            'last_name': 'Drugie imię/Nazwisko',
            'email': 'Email',
            'phone_number': 'Numer telefonu',
        }

    def clean_password2(self):
        """Sprawdź czy hasła są identyczne"""
        cd = self.cleaned_data
        if cd['password'] != cd['password2']:
            raise forms.ValidationError("Hasła nie są identyczne.")
        return cd['password2']
    
    def clean_phone_number(self):
        """Walidacja i normalizacja numeru telefonu"""
        phone = self.cleaned_data.get('phone_number', '').strip()
        is_valid, normalized, error = validate_and_normalize_polish_phone(phone)
        
        if not is_valid:
            raise forms.ValidationError(error)
        
        return normalized


class UserEditForm(forms.ModelForm):
    """Formularz edycji profilu użytkownika"""
    
    class Meta:
        model = get_user_model()
        fields = ['first_name', 'last_name', 'email', 'phone_number']
        widgets = {
            'first_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Imię'
            }),
            'last_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Nazwisko'
            }),
            'email': forms.EmailInput(attrs={
                'class': 'form-control',
                'readonly': 'readonly',
                'disabled': 'disabled'
            }),
            'phone_number': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': '+48501234567'
            }),
        }
        labels = {
            'first_name': 'Imię',
            'last_name': 'Nazwisko',
            'email': 'Email',
            'phone_number': 'Numer telefonu',
        }
        help_texts = {
            'phone_number': 'Format: +48501234567 lub 48501234567 (opcjonalne)',
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Email nie może być zmieniony
        self.fields['email'].disabled = True
        self.fields['email'].help_text = '🔒 Email nie może być zmieniony'
        # Phone number jest opcjonalne
        self.fields['phone_number'].required = False
    
    def clean_phone_number(self):
        """Walidacja i normalizacja numeru telefonu"""
        phone = self.cleaned_data.get('phone_number', '').strip()
        is_valid, normalized, error = validate_and_normalize_polish_phone(phone)
        
        if not is_valid:
            raise forms.ValidationError(error)
        
        return normalized


class FavoriteCalendarForm(forms.ModelForm):
    """Formularz dodawania ulubionego kalendarza"""
    class Meta:
        model = FavoriteCalendar
        fields = ['calendar_url', 'calendar_name', 'owner_name']
        widgets = {
            'calendar_url': forms.URLInput(attrs={
                'class': 'form-control',
                'placeholder': 'https://umowzdalnie.pl/myschedule/public/abcd1234efgh/',
                'required': True
            }),
            'calendar_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Nazwa kalendarza (opcjonalnie)'
            }),
            'owner_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Nazwa właściciela (opcjonalnie)'
            })
        }
        
    def clean_calendar_url(self):
        """Sprawdź czy URL zawiera prawidłowy token"""
        url = self.cleaned_data['calendar_url']
        import re
        if not re.search(r'/public/[a-zA-Z0-9]+/?', url):
            raise forms.ValidationError(
                "Nieprawidłowy link do kalendarza. URL powinien zawierać /public/TOKEN/"
            )
        return url


class NotificationSettingsForm(forms.ModelForm):
    """Formularz ustawień powiadomień użytkownika"""
    class Meta:
        model = UserNotificationSettings
        fields = [
            'booking_created_notifications',
            'booking_cancelled_notifications', 
            'own_booking_confirmations',
            'sms_reminders_enabled'  # Dodaj jeśli masz to pole w modelu
        ]
        widgets = {
            'booking_created_notifications': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
            'booking_cancelled_notifications': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
            'own_booking_confirmations': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
            'sms_reminders_enabled': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
        }
        labels = {
            'booking_created_notifications': 'Powiadomienia o nowych wizytach',
            'booking_cancelled_notifications': 'Powiadomienia o anulowanych wizytach',
            'own_booking_confirmations': 'Potwierdzenia moich wizyt',
            'sms_reminders_enabled': 'Wysyłaj przypomnienia SMS do klientów',
        }
