from django.urls import path

from . import views

urlpatterns = [
    path('lan-hosts/', views.lan_hosts_page, name='network-lan-hosts'),
    path('lan-hosts/scan/', views.lan_hosts_scan, name='network-lan-hosts-scan'),
    path('lan-hosts/note/', views.lan_hosts_note, name='network-lan-hosts-note'),
    path('lan-hosts/ping/', views.lan_hosts_ping, name='network-lan-hosts-ping'),
    path('wlan-aps/', views.wlan_aps_page, name='network-wlan-aps'),
    path('wlan-aps/scan/', views.wlan_aps_scan, name='network-wlan-aps-scan'),
]
