from django.urls import path
from . import views

app_name = 'eureka'

urlpatterns = [
    path('', views.eureka_view, name='eureka'),
    path('photo/<str:filename>', views.serve_photo, name='eureka-photo'),
    path('melos/<int:church_id>', views.melos_view, name='eureka-melos'),
    path('neos', views.neos_view, name='eureka-neos'),
    path('pastoral/', views.pastoral_view, name='pastoral'),
    path('pastoral/overseer/edit/<int:pk>/', views.edit_overseer_view, name='pastoral-overseer-edit'),
    path('pastoral/section/add/', views.add_section_view, name='pastoral-section-add'),
    path('pastoral/section/edit/<int:pk>/', views.edit_section_view, name='pastoral-section-edit'),
    path('pastoral/group/add/', views.add_group_view, name='pastoral-group-add'),
    path('pastoral/group/edit/<int:pk>/', views.edit_group_view, name='pastoral-group-edit'),
    path('pastoral/group/<int:pk>/members/', views.group_members_api, name='pastoral-group-members'),
    path('pastoral/group/<int:pk>/member/add/', views.add_group_member_api, name='pastoral-group-member-add'),
    path('pastoral/group/<int:pk>/member/remove/', views.remove_group_member_api, name='pastoral-group-member-remove'),
    path('pastoral/unassigned-members/', views.unassigned_members_api, name='pastoral-unassigned-members'),
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
    path('staff/delete/<int:staff_id>/', views.delete_staff_view, name='staff-delete'),
    path('seats/', views.seat_map_view, name='seats'),
    path('seats/save/', views.save_seat_map_view, name='seats-save'),
    path('meeting-attendance/', views.meeting_attendance_view, name='meeting-attendance'),
    path('shifts/', views.shift_list_view, name='shift-list'),
    path('shift/', views.shift_list_view),
    path('shifts/create/', views.shift_create_view, name='shift-create'),
    path('shifts/edit/<int:shift_id>/', views.shift_edit_view, name='shift-edit'),
    path('shifts/delete/<int:shift_id>/', views.shift_delete_view, name='shift-delete'),
]

