from django import forms
from .models import Availability, ServiceType, Booking
 

class AvailabilityForm(forms.ModelForm):
    class Meta:
        model = Availability
        fields = ["date", "start_time", "end_time", "title"]
        widgets = {
            'date': forms.DateInput(attrs={'type': 'date'}),
            'start_time': forms.TimeInput(attrs={'type': 'time'}),
            'end_time': forms.TimeInput(attrs={'type': 'time'}),
        }

class ServiceTypeForm(forms.ModelForm):
    class Meta:
        model = ServiceType
        fields = ['calendar', 'name', 'duration_minutes', 'description']


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
    
    class Meta:
        model = Booking
        fields = ['service_type', 'start_time']