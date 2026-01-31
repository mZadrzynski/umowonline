from django.urls import path
from . import views
from . import views_public

urlpatterns = [
    # ZARZĄDZANIE KALENDARZAMI
    path('calendars/', views.calendar_list, name='calendar_list'),
    path('calendars/create/', views.calendar_create, name='calendar_create'),
    path('calendars/<int:calendar_id>/set-active/', views.calendar_set_active, name='calendar_set_active'),
    
    path("calendar/", views.my_calendar, name="my_calendar"),
    path("calendar_week/", views.my_calendar_week, name="my_calendar_week"),
    path("calendar/add/", views.add_availability, name="add_availability"),
    path('calendar/add-service/', views.add_service, name='add_service'),
    path('book/<int:availability_id>/', views.book_availability, name='book_availability'),
    
    path('my-bookings/', views.my_bookings, name='my_bookings'),
    path('calendar-bookings/', views.calendar_bookings, name='calendar_bookings'),
    
    path('calendars/<int:calendar_id>/set-active/', views.calendar_set_active, name='calendar_set_active'),
    path('calendars/<int:calendar_id>/edit/', views.calendar_edit, name='calendar_edit'),  # ✅ DODAJ


    # ✅ Services PRZED username_slug
    path('services/', views.service_types_list, name='service_types_list'),
    path('services/add/', views.add_service, name='add_service'),
    path('services/<int:pk>/edit/', views.service_type_edit, name='service_type_edit'),
    path('services/<int:pk>/delete/', views.service_type_delete, name='service_type_delete'),
    
    # ✅ Inne ścieżki PRZED username_slug
    path('availability/delete/<int:availability_id>/', views.delete_availability, name='delete_availability'),
    path('subscription/expired/', views.subscription_expired, name='subscription_expired'),
    path('booking/<int:booking_id>/cancel/', views.cancel_booking, name='cancel_booking'),
    path('calendar-booking/<int:booking_id>/cancel/', views.cancel_calendar_booking, name='cancel_calendar_booking'),
    
    # ✅ Username slug NA KOŃCU
    path('<str:username_slug>/', views_public.public_calendar_by_username, name='public_calendar_by_username'),
    path('public/<str:token>/business/', views_public.public_calendar_with_business, name='public_calendar_with_business'),
    path('public/<str:token>/', views_public.public_calendar_with_business, name='public_calendar_week'),

]