from django.shortcuts import render
from django.contrib.auth.decorators import login_required




def home(request):
    return render(request, 'home.html')

@login_required
def dashboard(request):
    return render(
        request,
            'account/dashboard.html',
            {'section': 'dashboard'}
            )

def contact(request):
    return render(request, "contact.html")