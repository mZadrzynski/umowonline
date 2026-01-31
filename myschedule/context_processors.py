from myschedule.views import get_active_calendar

def calendar_context(request):
    """Dodaj aktywny kalendarz do każdego template"""
    if request.user.is_authenticated:
        return {
            'current_calendar': get_active_calendar(request),
        }
    return {}