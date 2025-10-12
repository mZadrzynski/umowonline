from django.contrib.auth import views 
from django.urls import path
from . import views


urlpatterns = [
    path("contact/", views.contact, name="contact"),
    path("help/", views.help, name="help"),
    path('terms/', views.terms_of_service, name='terms_of_service'),
    path("offert/", views.offert, name="offert"),
    path('privacy/', views.privacy_policy, name='privacy_policy'),
    path('instructions/', views.instructions, name='instructions'),
]