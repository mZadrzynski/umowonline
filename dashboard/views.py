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


def instructions(request):
    """Ładuje instrukcję z pliku DOCX i konwertuje na HTML"""
    
    docx_path = os.path.join(settings.BASE_DIR, 'static', 'docs', 'instrukcja.docx')
    
    try:
        doc = Document(docx_path)
        html_content = ""
        
        # Iteruj przez elementy dokumentu w kolejności
        for element in doc.element.body:
            if element.tag.endswith('p'):  # Paragraf
                # Znajdź odpowiedni paragraf
                for paragraph in doc.paragraphs:
                    if paragraph._element == element:
                        if paragraph.text.strip():
                            # Sprawdź style
                            if paragraph.style.name.startswith('Heading'):
                                level = paragraph.style.name[-1] if paragraph.style.name[-1].isdigit() else '1'
                                html_content += f"<h{level}>{paragraph.text}</h{level}>"
                            else:
                                html_content += f"<p>{paragraph.text}</p>"
                        
                        # Sprawdź obrazy w paragrafie
                        for run in paragraph.runs:
                            for drawing in run._element.xpath('.//a:blip'):
                                try:
                                    # Pobierz obraz
                                    embed_id = drawing.get('{http://schemas.openxmlformats.org/officeDocument/2006/relationships}embed')
                                    if embed_id:
                                        image_part = doc.part.related_parts[embed_id]
                                        image_data = image_part.blob
                                        image_base64 = base64.b64encode(image_data).decode()
                                        content_type = image_part.content_type
                                        img_html = f'<img src="data:{content_type};base64,{image_base64}" class="img-fluid mb-3" alt="Instrukcja">'
                                        html_content += img_html
                                except Exception as e:
                                    print(f"Błąd obrazka: {e}")
                        break
                        
    except FileNotFoundError:
        html_content = "<p>Plik instrukcji nie został znaleziony. Umieść plik 'instrukcja.docx' w folderze 'static/docs/'.</p>"
    except Exception as e:
        html_content = f"<p>Błąd przy wczytywaniu instrukcji: {str(e)}</p>"
    
    return render(request, 'dashboard/legal/instructions.html', {
        'html': html_content
    })


def docx_to_html(path):
    with open(path, "rb") as docx_file:
        result = mammoth.convert_to_html(docx_file)
        html = result.value  # uzyskane html
    return html

def help(request):
    return render(request, 'dashboard/help.html')

def terms_of_service(request):
    return render(request, 'dashboard/legal/terms_of_service.html')

def offert(request):
    return render(request, 'dashboard/offert.html')

def privacy_policy(request):
    path = 'dashboard/rules/privacy_policy.docx'
    html = docx_to_html(path)
    return render(request, 'dashboard/legal/privacy_policy.html', {'html': html})
