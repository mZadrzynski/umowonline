from django import forms
from django.forms.widgets import TimeInput

class FifteenMinuteTimeWidget(forms.TimeInput):
    """Widget czasu ograniczony do 15-minutowych przedziałów"""
    
    def __init__(self, attrs=None):
        default_attrs = {
            'type': 'time',
            'step': '900',  # 15 minut w sekundach (15 * 60 = 900)
            'class': 'form-control'
        }
        if attrs:
            default_attrs.update(attrs)
        super().__init__(attrs=default_attrs)

class FifteenMinuteTimeField(forms.TimeField):
    """Pole czasu z walidacją 15-minutowych przedziałów"""
    widget = FifteenMinuteTimeWidget
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
    
    def validate(self, value):
        super().validate(value)
        if value is not None:
            # Sprawdzenie czy minuty to 0, 15, 30 lub 45
            if value.minute not in [0, 15, 30, 45]:
                raise forms.ValidationError(
                    'Czas musi być ustawiony na jeden z przedziałów: :00, :15, :30, :45'
                )

# Alternatywne rozwiązanie używające choices
TIME_CHOICES = []
for hour in range(24):
    for minute in [0, 15, 30, 45]:
        time_str = f"{hour:02d}:{minute:02d}"
        TIME_CHOICES.append((time_str, time_str))

class FifteenMinuteChoiceWidget(forms.Select):
    """Widget wyboru czasu z gotowymi opcjami co 15 minut"""
    
    def __init__(self, attrs=None):
        super().__init__(attrs=attrs)
        self.choices = TIME_CHOICES