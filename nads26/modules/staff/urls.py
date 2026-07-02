from django.urls import path, re_path
from . import views

urlpatterns = [
    path('profile/', views.profile_page, name='staff-profile'),
    path('password/', views.password_change_page, name='staff-password-change'),
    path('leaves/', views.leave_calendar_page, name='staff-leaves'),
    path('calendar/', views.church_calendar_page, name='staff-calendar'),
    path('expense-claims/', views.expense_claim_page, name='staff-expense-claims'),
    path('expense-claims/<str:claim_no>/voucher.pdf', views.expense_claim_voucher_pdf, name='staff-expense-claim-voucher'),
    re_path(r'^(?P<unused_path>.+)/?$', views.planned_page, name='staff-planned-catchall'),
]
