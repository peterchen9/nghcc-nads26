from django.urls import path
from . import views

urlpatterns = [
    path('', views.user_list, name='user-list'),
    path('routes/', views.app_routes, name='app-routes'),
    path('create/', views.user_create, name='user-create'),
    path('<int:pk>/', views.user_update, name='user-update'),
    path('<int:pk>/permissions/', views.user_set_permissions, name='user-permissions'),
    path('<int:pk>/delete/', views.user_delete, name='user-delete'),
]
