from django.urls import path
from . import views_offering

urlpatterns = [
    path('', views_offering.offering_dashboard, name='offering-dashboard'),
    path('save/', views_offering.save_monthly_offering, name='save-monthly-offering'),
    path('api/get-monthly/', views_offering.get_monthly_offering_data, name='get-monthly-offering'),
]
