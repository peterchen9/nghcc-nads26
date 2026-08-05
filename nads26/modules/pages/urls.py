from django.urls import path
from . import views

urlpatterns = [
    path('planned/', views.planned_feature, name='planned-feature'),
    path('worship/baptism/', views.baptism_list_view, name='worship-baptism'),
    path('worship/baptism/edit/<int:pk>/', views.baptism_edit_view, name='worship-baptism-edit'),
    path('worship/baptism/session/new/', views.baptism_new_session_view, name='worship-baptism-session-new'),
    path('worship/baptism/register/', views.baptism_register_view, name='worship-baptism-register'),
    path('worship/baptism/batch-complete/', views.baptism_batch_complete_view, name='worship-baptism-batch-complete'),
    path('worship/baptism/member-profile/<str:name>/', views.baptism_member_profile_view, name='worship-baptism-member-profile'),
    path('worship/communion/', views.under_construction, {'title': '聖餐禮'}, name='worship-communion'),
    path('worship/wedding/', views.under_construction, {'title': '婚禮'}, name='worship-wedding'),
    path('worship/funeral/', views.funeral_list_view, name='worship-funeral'),
    path('board/minutes/', views.board_minutes_view, name='board-minutes'),
    path('board/deacons/', views.under_construction, {'title': '歷屆執事名單 (功能撰寫中)'}, name='board-deacons'),
    path('worship/funeral/new/', views.funeral_new_view, name='worship-funeral-new'),
    path('worship/funeral/edit/<int:pk>/', views.funeral_edit_view, name='worship-funeral-edit'),
    path('worship/funeral/batch-complete/', views.funeral_batch_complete_view, name='worship-funeral-batch-complete'),
    path('worship/funeral/shifts/', views.funeral_shifts_view, name='worship-funeral-shifts'),
    path('', views.page_detail, name='home'),
    path('pages/edit-home/', views.edit_home, name='edit-home'),
    path('tools/qr-generator/', views.qr_generator, name='qr-generator'),
    path('reference/media-collection/', views.media_collection, name='media-collection'),
    path('reference/media-collection/<int:pk>/download/', views.media_download, name='media-download'),
    path('reference/media-collection/<int:pk>/edit-download/', views.media_edit_download, name='media-edit-download'),
    path('p/<slug:slug>/', views.page_detail, name='page-detail'),
]
