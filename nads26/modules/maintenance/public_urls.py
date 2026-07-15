from django.urls import path

from . import views


app_name = 'maintenance_public'

urlpatterns = [
    path('report/', views.public_report, name='report'),
]
