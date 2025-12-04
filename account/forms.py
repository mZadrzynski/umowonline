from django import forms
from django.contrib.auth import get_user_model
from .models import FavoriteCalendar
from .models import UserNotificationSettings
from django.core.validators import RegexValidator 
import re




phone_validator = RegexValidator(
    regex=r'^\+?48\d{9}$',
    message='Numer telefonu musi być w formacie: +48501234567 (9 cyfr po 48)'
)

class LoginForm(forms.Form):
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
                'placeholder': 'Numer telefonu (opcjonalne)'
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
        cd = self.cleaned_data
        if cd['password'] != cd['password2']:
            raise forms.ValidationError("Hasła nie są identyczne.")
        return cd['password2']

class UserEditForm(forms.ModelForm):
    phone_number = forms.CharField(
        max_length=20,
        required=False,  # Opcjonalne
        validators=[phone_validator],
        label='Numer telefonu',
        help_text='Format: +48501234567 lub 48501234567',
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': '+48501234567'
        })
    )
    
    class Meta:
        model = get_user_model()
        fields = ['first_name', 'last_name', 'email', 'phone_number']
        widgets = {
            'first_name': forms.TextInput(attrs={'class': 'form-control'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={
                'class': 'form-control',
                'readonly': 'readonly',  # ← Email tylko do odczytu
                'disabled': 'disabled'   # ← Nie można edytować
            }),
        }
        labels = {
            'first_name': 'Imię',
            'last_name': 'Nazwisko',
            'email': 'Email',
            'phone_number': 'Numer telefonu',
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Email nie może być zmieniony
        self.fields['email'].disabled = True
        self.fields['email'].help_text = '🔒 Email nie może być zmieniony'
    
    def clean_phone_number(self):
        """Walidacja i normalizacja numeru telefonu"""
        phone = self.cleaned_data.get('phone_number', '').strip()
        
        if not phone:
            return ''  # Puste jest OK (opcjonalne)
        
        # Usuń wszystkie znaki oprócz cyfr i +
        clean_phone = re.sub(r'[^\d+]', '', phone)
        
        # Usuń + żeby sprawdzić cyfry
        digits_only = clean_phone.lstrip('+')
        
        # Sprawdź format: 48 + 9 cyfr = 11 cyfr
        if not digits_only.startswith('48') or len(digits_only) != 11:
            raise forms.ValidationError(
                'Numer telefonu musi zaczynać się od 48 i mieć 9 cyfr (np. +48501234567)'
            )
        
        # Zwróć znormalizowany format z +
        normalized = '+' + digits_only if not clean_phone.startswith('+') else clean_phone
        return normalized

class FavoriteCalendarForm(forms.ModelForm):
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
        url = self.cleaned_data['calendar_url']
        # Sprawdź czy URL zawiera prawidłowy token
        import re
        if not re.search(r'/public/[a-zA-Z0-9]+/?', url):
            raise forms.ValidationError("Nieprawidłowy link do kalendarza. URL powinien zawierać /public/TOKEN/")
        return url


class NotificationSettingsForm(forms.ModelForm):
    class Meta:
        model = UserNotificationSettings
        fields = [
            'booking_created_notifications',
            'booking_cancelled_notifications', 
            'own_booking_confirmations'
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
        }