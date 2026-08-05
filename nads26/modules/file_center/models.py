from django.db import models
from django.contrib.auth.models import User

class FileAnnotation(models.Model):
    path = models.CharField("相對路徑", max_length=500, unique=True, help_text="相對於檔案中心根目錄的相對路徑")
    is_directory = models.BooleanField("是否為目錄", default=False)
    notes = models.TextField("註記內容", blank=True, default="")
    updated_at = models.DateTimeField("更新時間", auto_now=True)
    updated_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, verbose_name="更新者")

    class Meta:
        verbose_name = "檔案註記"
        verbose_name_plural = "檔案註記"

    def __str__(self):
        type_str = "目錄" if self.is_directory else "檔案"
        return f"[{type_str}] {self.path} — {self.notes[:20]}"

class FileActionLog(models.Model):
    ACTION_CHOICES = (
        ('download', '下載'),
        ('upload', '上傳'),
    )
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, verbose_name="使用者")
    action = models.CharField("操作類型", max_length=20, choices=ACTION_CHOICES)
    path = models.CharField("相對路徑", max_length=500)

    ip_address = models.CharField("IP 位址", max_length=50, blank=True, default="")
    mac_address = models.CharField("MAC 位址", max_length=50, blank=True, default="")
    latitude = models.DecimalField("緯度", max_digits=9, decimal_places=6, null=True, blank=True)
    longitude = models.DecimalField("經度", max_digits=9, decimal_places=6, null=True, blank=True)
    timestamp = models.DateTimeField("記錄時間", auto_now_add=True)

    class Meta:
        verbose_name = "檔案操作紀錄"
        verbose_name_plural = "檔案操作紀錄"
        ordering = ['-timestamp']

    def __str__(self):
        user_str = self.user.username if self.user else "Anonymous"
        return f"{user_str} — {self.get_action_display()} — {self.path} @ {self.timestamp}"
