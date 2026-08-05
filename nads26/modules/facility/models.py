from django.db import models
from django.utils import timezone

class PeriodicMaintenanceItem(models.Model):
    category = models.CharField("分類", max_length=100)
    name = models.CharField("設施名稱/維護項目", max_length=200)
    cycle = models.CharField("維護週期", max_length=100, blank=True, default="")
    description = models.TextField("說明", blank=True, default="")
    owner = models.CharField("主責同工", max_length=100, blank=True, default="")
    vendor = models.CharField("外包廠商", max_length=100, blank=True, default="")
    scheduled_weeks = models.TextField(
        "需維護週次(JSON)",
        default="[]",
        help_text="例如: [1, 13, 26, 39]"
    )
    order_num = models.IntegerField("排序", default=0)
    is_active = models.BooleanField("啟用狀態", default=True)
    created_at = models.DateTimeField("建立時間", auto_now_add=True)
    updated_at = models.DateTimeField("更新時間", auto_now=True)

    class Meta:
        verbose_name = "定期維護項目"
        verbose_name_plural = "定期維護項目"
        ordering = ["order_num", "id"]

    def __str__(self):
        return f"[{self.category}] {self.name}"


class PeriodicMaintenanceRecord(models.Model):
    item = models.ForeignKey(
        PeriodicMaintenanceItem,
        on_delete=models.CASCADE,
        related_name="records",
        verbose_name="維護項目"
    )
    year = models.IntegerField("年份")
    week_number = models.IntegerField("週次")
    maintenance_date = models.DateField("維護日期", default=timezone.now)
    status = models.CharField("狀態", max_length=20, default="completed") # completed / abnormal
    anomaly_note = models.TextField("狀況說明/備註", blank=True, default="")
    operator_name = models.CharField("登記人員", max_length=100, blank=True, default="")
    ip_address = models.CharField("IP位置", max_length=50, blank=True, default="")
    mac_address = models.CharField("MAC位置", max_length=255, blank=True, default="")
    gps_location = models.CharField("GPS座標", max_length=100, blank=True, default="")
    device_name = models.CharField("設備名稱", max_length=150, blank=True, default="")
    ssid = models.CharField("SSID/網路名稱", max_length=100, blank=True, default="")
    completed_at = models.DateTimeField("登記時間", auto_now_add=True)

    class Meta:
        verbose_name = "定期維護紀錄"
        verbose_name_plural = "定期維護紀錄"
        unique_together = ("item", "year", "week_number")
        ordering = ["-year", "-week_number", "id"]

    def __str__(self):
        return f"{self.item.name} - {self.maintenance_date} (W{self.week_number}) ({self.get_status_display()})"

    def get_status_display(self):
        return "發現異常" if self.status == "abnormal" else "維護完成"
