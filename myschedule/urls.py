from django.urls import path
from . import views
from . import views_public

urlpatterns = [
    path("calendar/", views.my_calendar, name="my_calendar"),
    path("calendar_week/", views.my_calendar_week, name="my_calendar_week"),
    path("calendar/add/", views.add_availability, name="add_availability"),
    path('calendar/add-service/', views.add_service, name='add_service'),
    path('book/<int:availability_id>/', views.book_availability, name='book_availability'),
    path('my-bookings/', views.my_bookings, name='my_bookings'),
    path('public/<str:token>/', views_public.public_calendar_week, name='public_calendar_week'),
    path('availability/delete/<int:availability_id>/', views.delete_availability, name='delete_availability'),
    path('subscription/expired/', views.subscription_expired, name='subscription_expired'),

]