from django.urls import path
from . import views

urlpatterns = [
    path('staff-reference/', views.reference_data_page, name='reference-data-page'),
    path('api/list/', views.api_list_directory, name='api-list-directory'),
    path('download/', views.file_download, name='file-download'),
    path('upload/', views.file_upload, name='file-upload'),
    path('annotation/', views.save_annotation, name='save-annotation'),
]
