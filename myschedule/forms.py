from django import forms
from .models import Availability, ServiceType, Booking
from django.core.exceptions import ValidationError
from datetime import time, timedelta, datetime

def generate_time_choices():
    times = []
    current = datetime.strptime('00:00', '%H:%M')
    end = datetime.strptime('23:45', '%H:%M')
    delta = timedelta(minutes=15)
    while current <= end:
        t_str = current.strftime('%H:%M')
        times.append((t_str, t_str))
        current += delta

class BookingForm(forms.ModelForm):
    service_type = forms.ModelChoiceField(
        queryset=ServiceType.objects.all(),
        empty_label="Wybierz rodzaj wizyty",
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    
    start_time = forms.ChoiceField(choices=generate_time_choices(), label="Godzina rozpoczęcia")
    
    client_phone = forms.CharField(
        max_length=20,
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': '+48 123 456 789'}),
        label="Numer telefonu",
        help_text="Podaj numer telefonu kontaktowy"
    )
    
    client_note = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Dodatkowe informacje...'}),
        label="Notatka",
        help_text="Możesz dodać dodatkowe informacje lub uwagi"
    )

    class Meta:
        model = Booking
        fields = ['service_type', 'start_time', 'client_phone', 'client_note']
     
    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)  # Pobierz użytkownika z kwargs
        super().__init__(*args, **kwargs)
        
        # Automatycznie uzupełnij telefon z profilu użytkownika jeśli dostępny
        if user and hasattr(user, 'phone_number') and user.phone_number:
            self.fields['client_phone'].initial = user.phone_number
            

class ServiceTypeForm(forms.ModelForm):
    class Meta:
        model = ServiceType
        fields = ['name', 'duration_minutes', 'description']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'duration_minutes': forms.NumberInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control'}),
        }
        
WEEKDAY_CHOICES = [
    (0, "Poniedziałek"), (1, "Wtorek"), (2, "Środa"), 
    (3, "Czwartek"), (4, "Piątek"), (5, "Sobota"), (6, "Niedziela")
]


class SingleAvailabilityForm(forms.ModelForm):
    start_time = forms.ChoiceField(choices=generate_time_choices(), label="Godzina rozpoczęcia")
    end_time = forms.ChoiceField(choices=generate_time_choices(), label="Godzina zakończenia")

    class Meta:
        model = Availability
        fields = ['date', 'start_time', 'end_time']
        widgets = {
            'date': forms.DateInput(attrs={'type': 'date'}),
        }

    def __init__(self, *args, **kwargs):
        self.calendar = kwargs.pop('calendar', None)
        super().__init__(*args, **kwargs)

    def clean(self):
        cleaned_data = super().clean()
        start_time = cleaned_data.get('start_time')
        end_time = cleaned_data.get('end_time')
        date = cleaned_data.get('date')

        # Zamiana stringów z ChoiceField na obiekty czasu
        from datetime import datetime
        if start_time:
            start_time = datetime.strptime(start_time, '%H:%M').time()
            cleaned_data['start_time'] = start_time
        if end_time:
            end_time = datetime.strptime(end_time, '%H:%M').time()
            cleaned_data['end_time'] = end_time

        # Walidacja kolejności
        if start_time and end_time and start_time >= end_time:
            raise ValidationError("Czas rozpoczęcia musi być wcześniejszy niż czas zakończenia")

        # Sprawdzenie nakładania
        if self.calendar and date and start_time and end_time:
            overlapping = Availability.objects.filter(
                calendar=self.calendar,
                date=date,
                start_time__lt=end_time,
                end_time__gt=start_time
            )

            if self.instance and self.instance.pk:
                overlapping = overlapping.exclude(pk=self.instance.pk)

            if overlapping.exists():
                existing = overlapping.first()
                raise ValidationError(
                    f"Nakładanie z istniejącą dostępnością: "
                    f"{existing.start_time.strftime('%H:%M')} - {existing.end_time.strftime('%H:%M')}"
                )

        return cleaned_data

class BulkAvailabilityForm(forms.Form):
    start_date = forms.DateField(widget=forms.DateInput(attrs={'type': 'date'}))
    end_date = forms.DateField(widget=forms.DateInput(attrs={'type': 'date'}))
    start_time = forms.ChoiceField(choices=generate_time_choices(), label="Godzina rozpoczęcia")
    end_time = forms.ChoiceField(choices=generate_time_choices(), label="Godzina zakończenia")
    weekdays = forms.MultipleChoiceField(
        choices=WEEKDAY_CHOICES,  # Musisz mieć to zdefiniowane
        widget=forms.CheckboxSelectMultiple,
        help_text="Wybierz dni tygodnia"
    )

    
    def clean(self):
        cleaned_data = super().clean()
        start_time = cleaned_data.get('start_time')
        end_time = cleaned_data.get('end_time')
        
        if start_time and end_time and start_time >= end_time:
            raise ValidationError("Czas rozpoczęcia musi być wcześniejszy niż czas zakończenia")
        
        return cleaned_data