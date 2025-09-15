from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.core.mail import EmailMessage

from django.conf import settings
from .forms import ContactForm



def contact(request):
    if request.method == 'POST':
        form = ContactForm(request.POST)
        if form.is_valid():
            email = EmailMessage(
                subject=form.cleaned_data['subject'],
                body=form.cleaned_data['message'],
                from_email=settings.DEFAULT_FROM_EMAIL,
                to=[settings.DEFAULT_FROM_EMAIL],
                reply_to=[form.cleaned_data['from_email']]
            )
            email.send(fail_silently=False)
            return render(request, 'dashboard/mail_send_success.html')
        # Jeśli formularz nie jest valid, renderuj z błędami
    else:
        form = ContactForm()  # Inicjalizuj pusty formularz dla GET
    
    return render(request, 'dashboard/contact.html', {'form': form})

def help(request):
    return render(request, 'dashboard/help.html')

def rules(request):
    return render(request, 'dashboard/rules.html')