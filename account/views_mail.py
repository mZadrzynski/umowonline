from django.core.mail import send_mail
from django.http import HttpResponse

def send_test_email(request):
    send_mail(
        subject='Testowy mail z Django',
        message='Cześć! Wysłano maila z widoku.',
        from_email=None,
        recipient_list=['e.zadrzynska@int.pl'],
        fail_silently=False,
    )
    return HttpResponse('Mail został wysłany!')