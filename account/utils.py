import re
from django.core.exceptions import ValidationError

def validate_and_normalize_polish_phone(phone_number):
    """
    Sprawdza czy numer jest polski (48 + 9 cyfr)
    Zwraca tuple (is_valid, normalized_number, error_message)
    
    Przykłady:
    >>> validate_and_normalize_polish_phone('+48501234567')
    (True, '+48501234567', None)
    
    >>> validate_and_normalize_polish_phone('501234567')
    (False, None, 'Numer telefonu musi zaczynać się od 48')
    """
    if not phone_number:
        return True, '', None  # Puste jest OK
    
    # Usuń wszystkie znaki oprócz cyfr i +
    clean_phone = re.sub(r'[^\d+]', '', phone_number)
    
    # Usuń + żeby sprawdzić cyfry
    digits_only = clean_phone.lstrip('+')
    
    # Sprawdź format: 48 + 9 cyfr = 11 cyfr
    if not digits_only.startswith('48'):
        return False, None, 'Numer telefonu musi zaczynać się od 48'
    
    if len(digits_only) != 11:
        return False, None, f'Numer telefonu musi mieć 9 cyfr po 48 (podano {len(digits_only) - 2})'
    
    # Zwróć znormalizowany format z +
    normalized = '+' + digits_only if not clean_phone.startswith('+') else clean_phone
    return True, normalized, None
