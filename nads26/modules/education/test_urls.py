from django.urls import path, include

urlpatterns = [
    path('', lambda r: None, name='home'),
    path('accounts/', include('modules.accounts.auth_urls')),
    path('education/', include('modules.education.urls')),
]
