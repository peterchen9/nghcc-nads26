from django.urls import path, re_path
from . import views

urlpatterns = [
    path('planned/', views.planned_page, name='planned-feature'),
    path('booking/', views.booking_page, name='facility-booking'),
    path('rooms/', views.room_admin_page, name='facility-rooms'),
    path('maintenance/', views.maintenance_page, name='facility-maintenance'),
    path('booking/export/', views.export_bookings, name='facility-booking-export'),
    path('expense-claims/', views.expense_claim_page, name='facility-expense-claims'),
    path('expense-claims/<str:claim_no>/voucher.pdf', views.expense_claim_voucher_pdf, name='facility-expense-claim-voucher'),
    path('pastoral-reports/', views.pastoral_report_page, name='facility-pastoral-reports'),
    path('pastoral-reports/<str:report_no>/report.pdf', views.pastoral_report_pdf, name='facility-pastoral-report-pdf'),
    path('lan-hosts/', views.network_lan_hosts_page, name='facility-network-lan-hosts'),
    path('lan-hosts/scan/', views.network_lan_hosts_scan, name='facility-network-lan-hosts-scan'),
    path('lan-hosts/note/', views.network_lan_hosts_note, name='facility-network-lan-hosts-note'),
    path('lan-hosts/ping/', views.network_lan_hosts_ping, name='facility-network-lan-hosts-ping'),
    path('wlan-aps/', views.network_wlan_aps_page, name='facility-network-wlan-aps'),
    path('wlan-aps/scan/', views.network_wlan_aps_scan, name='facility-network-wlan-aps-scan'),
    re_path(r'^(?P<unused_path>.+)/?$', views.planned_page, name='facility-planned-catchall'),
]
