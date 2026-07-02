"""
用電監測 API 視圖
"""
from rest_framework import viewsets
from rest_framework.permissions import AllowAny
from .models import DailyPowerReport
from .serializers import DailyPowerReportSerializer

from django.shortcuts import render
from django.contrib.auth.decorators import login_required

DB = 'default'


@login_required
def power_page_view(request):
    """渲染用電監測前端網頁"""
    return render(request, 'power/power_page.html')



class DailyPowerReportViewSet(viewsets.ReadOnlyModelViewSet):
    """
    每日用電報告（唯讀）
    篩選參數:
      - year: 年份
      - month: 月份
      - meter_id: 電表編號
      - days: 最近 N 天（預設 30）
    """
    serializer_class = DailyPowerReportSerializer
    permission_classes = [AllowAny]

    def get_queryset(self):
        qs = DailyPowerReport.objects.using(DB).all()

        meter_id = self.request.query_params.get('meter_id')
        year = self.request.query_params.get('year')
        month = self.request.query_params.get('month')
        days = self.request.query_params.get('days')

        if meter_id:
            qs = qs.filter(meter_id=meter_id)
        if year:
            qs = qs.filter(usage_date__year=int(year))
        if month:
            qs = qs.filter(usage_date__month=int(month))
        if days:
            from datetime import date, timedelta
            cutoff = date.today() - timedelta(days=int(days))
            qs = qs.filter(usage_date__gte=cutoff)

        return qs.order_by('usage_date')
