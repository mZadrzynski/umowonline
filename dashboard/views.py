from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.core.mail import EmailMessage
from docx import Document
from django.conf import settings
from .forms import ContactForm, ContactFormPhone
import mammoth
from docx.shared import Inches
import os
import base64

def contact(request):
    form_email = ContactForm(request.POST if request.POST.get('form_type') == 'email' else None)
    form_phone = ContactFormPhone(request.POST if request.POST.get('form_type') == 'phone' else None)

    if request.method == 'POST':
        if request.POST.get('form_type') == 'email' and form_email.is_valid():
            email = EmailMessage(
                subject=form_email.cleaned_data['subject'],
                body=form_email.cleaned_data['message'],
                from_email=settings.DEFAULT_FROM_EMAIL,
                to=["kontakt@umowzdalnie.pl"],
                reply_to=[form_email.cleaned_data['from_email']]
            )
            email.send(fail_silently=False)
            return render(request, 'dashboard/mail_send_success.html')
        elif request.POST.get('form_type') == 'phone' and form_phone.is_valid():
            email = EmailMessage(
                subject="prośba o kontakt",
                body=form_phone.cleaned_data['phone'],
                from_email=settings.DEFAULT_FROM_EMAIL,
                to=["kontakt@umowzdalnie.pl"],
            )
            email.send(fail_silently=False)
            return render(request, 'dashboard/mail_send_success.html')

    return render(request, 'dashboard/contact.html', {
        'form_email': form_email,
        'form_phone': form_phone,
    })




def docx_to_html(path):
    with open(path, "rb") as docx_file:
        result = mammoth.convert_to_html(docx_file)
        html = result.value  # uzyskane html
    return html

def help(request):
    return render(request, 'dashboard/help.html')


def offert(request):
    return render(request, 'dashboard/offert.html')

def privacy_policy(request):
    path = 'dashboard/rules/privacy_policy.docx'
    html = docx_to_html(path)
    return render(request, 'dashboard/legal/privacy_policy.html', {'html': html})

def terms_of_service(request):
    path = 'dashboard/rules/terms_of_service.docx'
    html = docx_to_html(path)
    return render(request, 'dashboard/legal/terms_of_service.html', {'html': html})

def instructions(request):
    path = 'dashboard/rules/instructions.docx'
    html = docx_to_html(path)
    return render(request, 'dashboard/legal/instructions.html', {'html': html})