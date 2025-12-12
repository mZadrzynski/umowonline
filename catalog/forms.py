from django import forms
from .models import BusinessProfile, Review


class BusinessProfileForm(forms.ModelForm):
    """Formularz do tworzenia/edytowania profilu"""
    
    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        
        # ✅ SECURITY: Filter calendars to only user's own calendars
        if user:
            from myschedule.models import Calendar
            # Znajdź kalendarze przypisane do zalogowanego użytkownika
            self.fields['calendar'].queryset = Calendar.objects.filter(user=user)
            # Ale BusinessProfile ma pole 'owner', nie 'user'
        
        # Apply form-control class to all fields
        for field_name, field in self.fields.items():
            if field_name != 'is_active':  # Skip checkbox
                if 'class' not in field.widget.attrs:
                    field.widget.attrs['class'] = 'form-control'
    
    class Meta:
        model = BusinessProfile
        fields = [
            'business_name', 'owner_name', 'description',
            'address', 'postal_code', 'city',
            'email', 'phone', 'website',
            'logo', 'cover_image', 
            'calendar',
            'is_active'
        ]
        widgets = {
            'business_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Nazwa firmy'
            }),
            'owner_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Imię i nazwisko'
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 5,
                'placeholder': 'Opisz swoją działalność...'
            }),
            'address': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Ulica i numer domu, np. ul. Mariacka 5'
            }),
            'postal_code': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': '31-999'
            }),
            'city': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Kraków'
            }),
            'email': forms.EmailInput(attrs={
                'class': 'form-control',
                'placeholder': 'email@example.com'
            }),
            'phone': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': '+48 123 456 789'
            }),
            'website': forms.URLInput(attrs={
                'class': 'form-control',
                'placeholder': 'https://example.com'
            }),
            'calendar': forms.Select(attrs={
                'class': 'form-control'
            }),
            'logo': forms.FileInput(attrs={
                'class': 'form-control'
            }),
            'cover_image': forms.FileInput(attrs={
                'class': 'form-control'
            }),
            'is_active': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
        }

class ReviewForm(forms.ModelForm):
    """Formularz do opini"""
    
    class Meta:
        model = Review
        fields = ['rating', 'comment']
        widgets = {
            'rating': forms.RadioSelect(choices=[(i, f"{i} ⭐") for i in range(1, 6)]),
            'comment': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 4,
                'placeholder': 'Podziel się swoją opinią...'
            }),
        }
