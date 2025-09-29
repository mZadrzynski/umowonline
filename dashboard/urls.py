from django.contrib.auth import views 
from django.urls import path
from . import views


urlpatterns = [
    path("contact/", views.contact, name="contact"),
    path("help/", views.help, name="help"),
    path("rules/", views.rules, name="rules"),
    path("offert/", views.offert, name="offert"),


]


