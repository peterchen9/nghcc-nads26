from django.urls import path
from . import views

app_name = 'eureka'

urlpatterns = [
    path('', views.eureka_view, name='eureka'),
    path('photo/<str:filename>', views.serve_photo, name='eureka-photo'),
    path('melos/<int:church_id>', views.melos_view, name='eureka-melos'),
    path('neos', views.neos_view, name='eureka-neos'),
    path('pastoral/', views.pastoral_view, name='pastoral'),
    path('add/', views.add_view, name='add'),
    path('add/download/', views.download_add_view, name='add-download'),
    path('modify/', views.modify_view, name='modify'),
    path('modify/download/', views.download_all_view, name='modify-download'),
    path('modify/duplicates/', views.duplicates_view, name='modify-duplicates'),
    path('modify/delete/<int:church_id>/', views.delete_view, name='modify-delete'),
    path('attendance/', views.attendance_view, name='attendance'),
    path('vacation/', views.vacation_view, name='vacation'),
    path('vacation/sync/', views.sync_vacation_view, name='vacation-sync'),
    path('staff/', views.staff_list_view, name='staff-list'),
    path('staff/edit/<int:staff_id>/', views.edit_staff_view, name='staff-edit'),
    path('seats/', views.seat_map_view, name='seats'),
    path('seats/save/', views.save_seat_map_view, name='seats-save'),
]
