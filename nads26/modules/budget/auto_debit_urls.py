from django.urls import path

from . import views


urlpatterns = [
    path('', views.auto_debit_claim_page, name='auto-debit-claims'),
    path(
        '<str:claim_no>/voucher.pdf',
        views.auto_debit_claim_voucher_pdf,
        name='auto-debit-claim-voucher',
    ),
]
