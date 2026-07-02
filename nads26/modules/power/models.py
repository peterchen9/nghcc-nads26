from django.db import models


class DailyPowerReport(models.Model):
    meter_id = models.CharField(max_length=20, null=True, blank=True)
    usage_date = models.DateField(null=True, blank=True)
    total_usage = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    peak_ratio = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        managed = True
        db_table = 'daily_power_report'
        ordering = ['usage_date']
        verbose_name = '每日用電報告'
        verbose_name_plural = '每日用電報告'

    def __str__(self):
        return f'{self.usage_date} - {self.total_usage} kWh'
