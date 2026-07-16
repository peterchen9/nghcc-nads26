from django.urls import path
from . import views_fund_fellowship

urlpatterns = [
    path('', views_fund_fellowship.fund_fellowship_dashboard, name='fund-fellowship-dashboard'),
    path('manage-funds/', views_fund_fellowship.manage_funds, name='manage-funds'),
    path('manage-fellowships/', views_fund_fellowship.manage_fellowships, name='manage-fellowships'),
]
