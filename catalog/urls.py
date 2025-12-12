# catalog/urls.py

from django.urls import path, re_path
from . import views
from myschedule.views_public import public_calendar_with_business

app_name = 'catalog'

urlpatterns = [
    # PUBLIC
    path('', views.BusinessListView.as_view(), name='business_list'),
    
    # USER DASHBOARD - PRZED generic slug!
    path('my-businesses/', views.user_businesses, name='user_businesses'),
    
    # CREATE / EDIT / DELETE
    path('create/', views.BusinessCreateView.as_view(), name='business_create'),
    path('business/<int:pk>/edit/', views.BusinessUpdateView.as_view(), name='business_edit'),
    path('business/<int:pk>/delete/', views.BusinessDeleteView.as_view(), name='business_delete'),
    
    # SERVICES
    path('business/<int:profile_id>/service/add/', views.ServiceCreateView.as_view(), name='service_create'),
    path('service/<int:pk>/edit/', views.ServiceUpdateView.as_view(), name='service_edit'),
    path('service/<int:pk>/delete/', views.ServiceDeleteView.as_view(), name='service_delete'),
    
    # REVIEWS
    path('business/<int:profile_id>/review/add/', views.ReviewCreateView.as_view(), name='review_create'),
    
    # GENERIC - OSTATNI! (z unicode support dla polskich znaków)
    re_path(r'^(?P<slug>[\w-]+)/$', public_calendar_with_business, name='business_detail'),

]
