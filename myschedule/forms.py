from django import forms
from .models import Availability, ServiceType, Booking
from django.core.exceptions import ValidationError
from datetime import time, timedelta, datetime
from django.contrib.auth.models import User

def generate_time_choices():
    """Generuje wybory czasu co 15 minut z zabezpieczeniem przed błędami"""
    times = []
    try:
        current = datetime.strptime('00:00', '%H:%M')
        end = datetime.strptime('23:45', '%H:%M')
        delta = timedelta(minutes=15)
        
        while current <= end:
            t_str = current.strftime('%H:%M')
            times.append((t_str, t_str))
            current += delta
            
        # Sprawdź czy lista nie jest pusta
        if not times:
            raise ValueError("Lista czasów jest pusta")
            
        return times
    except Exception as e:
        # Fallback - zwróć podstawowe opcje
        print(f"Błąd w generate_time_choices: {e}")
        return [
            ('08:00', '08:00'), ('08:15', '08:15'), ('08:30', '08:30'), ('08:45', '08:45'),
            ('09:00', '09:00'), ('09:15', '09:15'), ('09:30', '09:30'), ('09:45', '09:45'),
            ('10:00', '10:00'), ('10:15', '10:15'), ('10:30', '10:30'), ('10:45', '10:45'),
            ('11:00', '11:00'), ('11:15', '11:15'), ('11:30', '11:30'), ('11:45', '11:45'),
            ('12:00', '12:00'), ('12:15', '12:15'), ('12:30', '12:30'), ('12:45', '12:45'),
            ('13:00', '13:00'), ('13:15', '13:15'), ('13:30', '13:30'), ('13:45', '13:45'),
            ('14:00', '14:00'), ('14:15', '14:15'), ('14:30', '14:30'), ('14:45', '14:45'),
            ('15:00', '15:00'), ('15:15', '15:15'), ('15:30', '15:30'), ('15:45', '15:45'),
            ('16:00', '16:00'), ('16:15', '16:15'), ('16:30', '16:30'), ('16:45', '16:45'),
            ('17:00', '17:00'), ('17:15', '17:15'), ('17:30', '17:30'), ('17:45', '17:45'),
            ('18:00', '18:00'), ('18:15', '18:15'), ('18:30', '18:30'), ('18:45', '18:45'),
        ]
    

def generate_available_times(availability, service_duration_minutes=15):
    '''Generuje czasy dostępne w danej availability z uwzględnieniem czasu trwania usługi'''
    times = []
    
    try:
        # Start i koniec availability
        avail_start = availability.start_time
        avail_end = availability.end_time
        
        # Konwertuj na datetime dla obliczeń
        today = datetime.today().date()
        current = datetime.combine(today, avail_start)
        end = datetime.combine(today, avail_end)
        
        # Odejmij czas trwania usługi od końca
        service_duration = timedelta(minutes=service_duration_minutes)
        last_possible_start = end - service_duration
        
        # Generuj co 15 minut
        delta = timedelta(minutes=15)
        
        while current <= last_possible_start:
            t_str = current.strftime('%H:%M')
            times.append((t_str, t_str))
            current += delta
        
        if not times:
            return [('', 'Brak dostępnych godzin dla tej usługi')]
            
        return times
    
    except Exception as e:
        print(f"Błąd w generate_available_times: {e}")
        return [('', 'Błąd przy generowaniu czasów')]
    



class ServiceTypeForm(forms.ModelForm):
    class Meta:
        model = ServiceType
        fields = ['name', 'duration_minutes', 'description']
        labels = {
            'name': 'Nazwa',
            'duration_minutes': 'Czas trwania uslugi (minuty)',
            'description': 'Opis uslugi',
        }
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
        labels = {
            'date': 'Data',
        }
        widgets = {
            'date': forms.DateInput(attrs={'type': 'date'})
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
    start_date = forms.DateField(
        widget=forms.DateInput(attrs={'type': 'date'}),
        label="Data rozpoczęcia"
    )
    end_date = forms.DateField(
        widget=forms.DateInput(attrs={'type': 'date'}),
        label="Data zakończenia"
    )
    start_time = forms.ChoiceField(choices=generate_time_choices(), label="Godzina rozpoczęcia")
    end_time = forms.ChoiceField(choices=generate_time_choices(), label="Godzina zakończenia")
    weekdays = forms.MultipleChoiceField(
        choices=WEEKDAY_CHOICES,
        widget=forms.CheckboxSelectMultiple,
        label="Wybierz dni tygodnia"
    )

    
    def clean(self):
        cleaned_data = super().clean()
        start_time = cleaned_data.get('start_time')
        end_time = cleaned_data.get('end_time')
        
        if start_time and end_time and start_time >= end_time:
            raise ValidationError("Czas rozpoczęcia musi być wcześniejszy niż czas zakończenia")
        
        return cleaned_data


class BookingForm(forms.ModelForm):
    service_type = forms.ModelChoiceField(
        queryset=ServiceType.objects.all(),
        empty_label="Wybierz rodzaj wizyty",
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    
    start_time = forms.ChoiceField(
        choices=[],  # Będzie wypełnione dynamicznie
        label="Godzina rozpoczęcia"
    )
    
    # ... reszta pól bez zmian
    
    def __init__(self, *args, **kwargs):
        self.availability = kwargs.pop('availability', None)
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        
        # Automatycznie uzupełnij telefon z profilu użytkownika
        if user and hasattr(user, 'phone_number') and user.phone_number:
            self.fields['client_phone'].initial = user.phone_number
        
        # NOWE: Ustaw dostępne czasy na podstawie availability i service_type
        if self.availability:
            # Domyślnie użyj 15 minut, może być później zaktualizowane przez JavaScript
            from .views import generate_available_start_times
            available_times = generate_available_start_times(self.availability, 15)
            if available_times:
                self.fields['start_time'].choices = available_times
            else:
                self.fields['start_time'].choices = [('', 'Brak dostępnych godzin')]
        
        # Dodaj JavaScript do dynamicznej aktualizacji czasów gdy zmieni się service_type
        self.fields['service_type'].widget.attrs.update({
            'onchange': 'updateAvailableTimes(this.value)'
        })

class OwnerBookingForm(forms.ModelForm):
    start_time = forms.ChoiceField(
        choices=[],
        label="Godzina rozpoczęcia",
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    
    # ... reszta pól bez zmian
    
    def update_available_times(self, availability, service_duration=15):
        """Aktualizuje dostępne czasy dla danej usługi"""
        from .views import generate_available_start_times
        available_times = generate_available_start_times(availability, service_duration)
        if available_times:
            self.fields['start_time'].choices = available_times
        else:
            self.fields['start_time'].choices = [('', 'Brak dostępnych godzin')]
