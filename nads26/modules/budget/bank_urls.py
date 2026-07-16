from django.urls import path
from . import views_bank

urlpatterns = [
    path('', views_bank.bank_balances_dashboard, name='bank-balances-dashboard'),
    path('manage-balances/', views_bank.manage_balances, name='manage-balances'),
    path('manage-deposits/', views_bank.manage_deposits, name='manage-deposits'),
]
