from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import DailyPowerReportViewSet

router = DefaultRouter()
router.register('reports', DailyPowerReportViewSet, basename='power-reports')

urlpatterns = [
    path('', include(router.urls)),
]
