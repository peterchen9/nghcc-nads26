from django.urls import path
from . import views

urlpatterns = [
    path('planned/', views.planned_feature, name='planned-feature'),
    path('', views.page_detail, name='home'),
    path('pages/edit-home/', views.edit_home, name='edit-home'),
    path('tools/qr-generator/', views.qr_generator, name='qr-generator'),
    path('reference/media-collection/', views.media_collection, name='media-collection'),
    path('reference/media-collection/<int:pk>/download/', views.media_download, name='media-download'),
    path('reference/media-collection/<int:pk>/edit-download/', views.media_edit_download, name='media-edit-download'),
    path('p/<slug:slug>/', views.page_detail, name='page-detail'),
]
