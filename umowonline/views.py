from django.shortcuts import render
from django.db.models import Q
from catalog.models import BusinessProfile
import random



def home(request):

    all_businesses = BusinessProfile.objects.filter(is_active=True)
    random_businesses = random.sample(
        list(all_businesses), 
        min(3, len(all_businesses))  # max 3 lub mniej jeśli jest mniej profilów
    )
    
    context = {

        'random_businesses': random_businesses,
    }
    return render(request, 'home.html', context)