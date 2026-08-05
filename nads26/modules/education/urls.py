from django.urls import path
from . import views

app_name = 'education'

urlpatterns = [
    path('courses/', views.course_list_view, name='course-list'),
    path('courses/add/', views.course_create_view, name='course-add'),
    path('courses/<int:pk>/', views.course_detail_view, name='course-detail'),
    path('courses/<int:pk>/edit/', views.course_update_view, name='course-edit'),
    path('courses/<int:pk>/delete/', views.course_delete_view, name='course-delete'),
    
    # 討論版
    path('courses/<int:pk>/board/', views.course_board_view, name='course-board'),
    
    # 教師錄音
    path('classes/<int:class_id>/record/', views.class_record_view, name='class-record'),
    path('classes/<int:class_id>/upload-recording/', views.class_upload_recording_api, name='class-upload-recording'),
    
    # 安全音訊串流
    path('recordings/<int:recording_id>/audio/', views.serve_recording_audio_view, name='serve-recording-audio'),
    
    # 學員補課
    path('courses/<int:pk>/makeup/', views.course_makeup_view, name='course-makeup'),
    path('classes/<int:class_id>/makeup-complete/', views.class_makeup_complete_view, name='class-makeup-complete'),
    
    # 課程產出文件
    path('courses/<int:pk>/documents/', views.course_documents_view, name='course-documents'),
    path('courses/<int:pk>/doc/announcement/', views.doc_announcement_view, name='doc-announcement'),
    path('courses/<int:pk>/doc/doorsign/', views.doc_doorsign_view, name='doc-doorsign'),
    path('courses/<int:pk>/doc/feedback/', views.doc_feedback_view, name='doc-feedback'),
    path('courses/<int:pk>/doc/attendance/', views.doc_attendance_view, name='doc-attendance'),
    
    # 課程錄音網頁與 QR Code
    path('courses/<int:pk>/record/', views.course_record_view, name='course-record'),
    path('courses/<int:pk>/qrcode/', views.course_qrcode_view, name='course-qrcode'),
]
