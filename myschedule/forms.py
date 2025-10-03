from django import forms
from .models import Availability, ServiceType, Booking
from django.core.exceptions import ValidationError


class BookingForm(forms.ModelForm):
    service_type = forms.ModelChoiceField(
        queryset=ServiceType.objects.all(),
        empty_label="Wybierz rodzaj wizyty",
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    
    start_time = forms.TimeField(
        widget=forms.TimeInput(attrs={'type': 'time', 'class': 'form-control'}),
        help_text="Wybierz godzinę rozpoczęcia wizyty"
    )

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
    class Meta:
        model = Availability
        fields = ['date', 'start_time', 'end_time']
        widgets = {
            'date': forms.DateInput(attrs={'type': 'date'}),
            'start_time': forms.TimeInput(attrs={'type': 'time'}),
            'end_time': forms.TimeInput(attrs={'type': 'time'}),
        }
    
    def __init__(self, *args, **kwargs):
        self.calendar = kwargs.pop('calendar', None)
        super().__init__(*args, **kwargs)
    
    def clean(self):
        cleaned_data = super().clean()
        start_time = cleaned_data.get('start_time')
        end_time = cleaned_data.get('end_time')
        date = cleaned_data.get('date')
        
        # Sprawdź czy czas rozpoczęcia jest wcześniejszy niż zakończenia
        if start_time and end_time and start_time >= end_time:
            raise ValidationError("Czas rozpoczęcia musi być wcześniejszy niż czas zakończenia")
        
        # Sprawdź nakładanie tylko jeśli mamy wszystkie potrzebne dane
        if self.calendar and date and start_time and end_time:
            overlapping = Availability.objects.filter(
                calendar=self.calendar,
                date=date,
                start_time__lt=end_time,
                end_time__gt=start_time
            )
            
            # Jeśli edytujemy, wykluczamy aktualny rekord
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
    weekdays = forms.MultipleChoiceField(
        choices=WEEKDAY_CHOICES,  # Musisz mieć to zdefiniowane
        widget=forms.CheckboxSelectMultiple,
        help_text="Wybierz dni tygodnia"
    )
    start_time = forms.TimeField(widget=forms.TimeInput(attrs={'type': 'time'}))
    end_time = forms.TimeField(widget=forms.TimeInput(attrs={'type': 'time'}))
    
    def clean(self):
        cleaned_data = super().clean()
        start_time = cleaned_data.get('start_time')
        end_time = cleaned_data.get('end_time')
        
        if start_time and end_time and start_time >= end_time:
            raise ValidationError("Czas rozpoczęcia musi być wcześniejszy niż czas zakończenia")
        
        return cleaned_data