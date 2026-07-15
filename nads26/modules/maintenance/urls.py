from django.urls import path

from . import views


app_name = 'maintenance'

urlpatterns = [
    path('', views.dashboard, name='dashboard'),
    path('records/', views.record_list, name='record-list'),
    path('records/new/', views.record_create, name='record-create'),
    path('records/<int:pk>/', views.record_detail, name='record-detail'),
    path('records/<int:pk>/edit/', views.record_update, name='record-update'),
    path('records/<int:pk>/delete/', views.record_delete, name='record-delete'),
    path('attachments/<int:pk>/delete/', views.attachment_delete, name='attachment-delete'),
    path('vendors/', views.vendor_list, name='vendor-list'),
    path('categories/', views.category_list, name='category-list'),
    path('locations/', views.location_list, name='location-list'),
    path('statistics/', views.statistics, name='statistics'),
    path('unfinished/', views.unfinished, name='unfinished'),
]
