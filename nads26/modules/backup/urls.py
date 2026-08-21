from django.urls import path
from . import views

urlpatterns = [
    path('', views.backup_dashboard, name='backup-dashboard'),
    path('save-config/', views.save_config, name='backup-save-config'),
    path('run/', views.run_backup, name='backup-run'),
    path('download/<int:pk>/', views.download_backup, name='backup-download'),
    path('comment/<int:pk>/', views.update_comment, name='backup-comment'),
    path('delete/<int:pk>/', views.delete_backup, name='backup-delete'),
    path('view-log/<int:pk>/', views.view_log, name='backup-view-log'),
]
