from django.http import HttpResponse
from django.urls import include, path


urlpatterns = [
    path('', lambda request: HttpResponse('home'), name='home'),
    path('accounts/login/', lambda request: HttpResponse('login'), name='login'),
    path('accounts/logout/', lambda request: HttpResponse('logout'), name='logout'),
    path('facility/', include('modules.facility.urls')),
]
