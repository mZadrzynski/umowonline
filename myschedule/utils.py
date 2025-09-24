from .models import Availability

def check_time_overlap(start1, end1, start2, end2):
    """
    Sprawdza czy dwa przedziały czasowe się nakładają
    Zwraca True jeśli się nakładają, False jeśli nie
    
    Logika: start1 < end2 AND end1 > start2
    """
    return start1 < end2 and end1 > start2

def get_overlapping_availabilities(calendar, date, start_time, end_time, exclude_id=None):
    """
    Zwraca dostępności które nakładają się z podanym przedziałem
    """
    queryset = Availability.objects.filter(
        calendar=calendar,
        date=date,
        start_time__lt=end_time,
        end_time__gt=start_time
    )
    
    if exclude_id:
        queryset = queryset.exclude(pk=exclude_id)
    
    return queryset