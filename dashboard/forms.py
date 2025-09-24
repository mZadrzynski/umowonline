from django import forms
from captcha.fields import CaptchaField




class ContactForm(forms.Form):
    from_email = forms.EmailField(required=True,
                    widget=forms.TextInput(attrs={'placeholder': 'Twój email'}))
    subject = forms.CharField(required=True,
                    widget=forms.TextInput(attrs={'placeholder': 'Temat wiadomośći'}))
    message = forms.CharField(
                    required=True,
                    widget=forms.Textarea(attrs={'placeholder': 'Treść wiadomości'}))
    captcha = CaptchaField()

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # CaptchaField używa MultiWidget -> jego input to zawsze [1]
        self.fields['captcha'].widget.widgets[1].attrs.update({
            'placeholder': 'Przepisz kod z obrazka'
        })

class ContactFormPhone(forms.Form):
    phone = forms.CharField(required=True,
                    widget=forms.TextInput(attrs={'placeholder': 'Wprowadz numer telefonu'}))
    captcha = CaptchaField()
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # CaptchaField używa MultiWidget -> jego input to zawsze [1]
        self.fields['captcha'].widget.widgets[1].attrs.update({
            'placeholder': 'Przepisz kod z obrazka'
        })