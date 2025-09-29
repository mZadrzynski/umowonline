from django import forms
from django.contrib.auth import get_user_model
from .models import FavoriteCalendar

class LoginForm(forms.Form):
    username = forms.CharField()
    password = forms.CharField(widget=forms.PasswordInput)


class UserRegistrationForm(forms.ModelForm):
    password = forms.CharField(
        label='Password',
        widget=forms.PasswordInput
    )
    password2 = forms.CharField(
        label='Repeat password',
        widget=forms.PasswordInput
    )
    class Meta:
        model = get_user_model()
        fields = ['username', 'first_name', 'email']
        

    def clean_password2(self):
        cd = self.cleaned_data
        if cd['password'] != cd['password2']:
            raise forms.ValidationError("Passwords don't match.")
        return cd['password2']
    
class UserEditForm(forms.ModelForm):
    class Meta:
        model = get_user_model()
        fields = ['first_name', 'last_name', 'email']



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