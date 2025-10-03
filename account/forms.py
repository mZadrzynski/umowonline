from django import forms
from django.contrib.auth import get_user_model
from .models import FavoriteCalendar

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
    class Meta:
        model = get_user_model()
        fields = ['first_name', 'last_name', 'email', 'phone_number']  # DODANE phone_number
        widgets = {
            'first_name': forms.TextInput(attrs={'class': 'form-control'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
            'phone_number': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '+48 123 456 789'}),
        }
        labels = {
            'phone_number': 'Numer telefonu',
        }

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