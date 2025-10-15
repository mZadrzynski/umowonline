from django.contrib.auth import views as auth_views
from django.urls import path, include
from . import views
from . import views_mail

urlpatterns = [
    path('', include('django.contrib.auth.urls')),
    path('register/', views.register, name='register'),
    path('edit/', views.edit, name='edit'),
    path('send-mail/', views_mail.send_test_email, name='send_mail'),
    path('favorites/', views.favorite_calendars, name='favorite_calendars'),
    path('favorites/add/', views.add_favorite_calendar, name='add_favorite_calendar'),
    path('favorites/remove/<int:favorite_id>/', views.remove_favorite_calendar, name='remove_favorite_calendar'),
    path('settings/', views.notification_settings, name='notification_settings'),
    path('register/done/', views.register_done, name='register_done'),
    path('registration-pending/', views.registration_pending, name='registration_pending'),
    path('activate/<uidb64>/<token>/', views.activate, name='activate'),

    #URL-E PŁATNOŚCI
    path('payment/create/', views.create_payment, name='create_payment'),
    path('payment/webhook/', views.hotpay_webhook, name='hotpay_webhook'),
    path('payment/success/', views.payment_success, name='payment_success'),
    path('subscription/', views.subscription_status, name='subscription_status'),
]  