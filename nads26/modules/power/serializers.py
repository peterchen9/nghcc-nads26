from rest_framework import serializers
from .models import DailyPowerReport


class DailyPowerReportSerializer(serializers.ModelSerializer):
    class Meta:
        model = DailyPowerReport
        fields = ['id', 'meter_id', 'usage_date', 'total_usage', 'peak_ratio', 'created_at']
