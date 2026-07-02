from django.urls import path
from . import views

urlpatterns = [
    path('info/', views.video_info, name='humnos-info'),
    path('download/', views.video_download, name='humnos-download'),
]
