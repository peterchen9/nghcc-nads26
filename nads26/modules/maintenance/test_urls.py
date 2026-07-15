from django.http import HttpResponse
from django.urls import include, path


urlpatterns = [
    path('', lambda request: HttpResponse('home'), name='home'),
    path('accounts/logout/', lambda request: HttpResponse('logout'), name='logout'),
    path('facility/maintenance/', lambda request: HttpResponse('legacy maintenance'), name='facility-maintenance'),
    path('facility/maintenance/manage/', include('modules.maintenance.urls')),
    path('maintenance/', include('modules.maintenance.public_urls')),
]
