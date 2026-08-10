from django.http import HttpResponse
from django.urls import include, path


urlpatterns = [
    path('', lambda request: HttpResponse('home'), name='home'),
    path('accounts/', include('modules.accounts.auth_urls')),
    path('eureka/', include('modules.eureka.urls')),
]
