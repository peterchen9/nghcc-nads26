"""詩歌資料庫 — API URL 設定"""
from django.urls import path
from . import views

app_name = 'hymns'

urlpatterns = [
    path('', views.hymn_list, name='hymn-list'),
    path('<int:pk>/', views.hymn_detail, name='hymn-detail'),
    path('<int:pk>/upload/', views.hymn_upload, name='hymn-upload'),
]
