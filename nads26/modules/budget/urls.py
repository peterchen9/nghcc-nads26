from django.urls import path

from . import views

urlpatterns = [
    path('', views.budget_list, name='budget-list'),
    path('export/', views.budget_export, name='budget-export'),
    path('<int:pk>/edit/', views.budget_edit, name='budget-edit'),
    path('<int:pk>/delete/', views.budget_delete, name='budget-delete'),
]
