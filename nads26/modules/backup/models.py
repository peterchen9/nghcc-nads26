from django.db import models
from datetime import time

class BackupConfig(models.Model):
    DEST_CHOICES = [
        ('local', '本機目錄'),
        ('sftp', 'SFTP (遠端主機/NAS)'),
    ]

    RETENTION_CHOICES = [
        ('count', '保留最新份數'),
        ('days', '保留天數'),
    ]

    backup_path = models.CharField("備份路徑", max_length=500, default="/app/backups")
    dest_type = models.CharField("備份目的地類型", max_length=20, choices=DEST_CHOICES, default='local')
    sftp_host = models.CharField("遠端主機/NAS IP", max_length=255, blank=True, default='')
    sftp_port = models.IntegerField("遠端主機 Port", default=22)
    sftp_username = models.CharField("遠端使用者名稱", max_length=100, blank=True, default='')
    sftp_password = models.CharField("遠端密碼", max_length=255, blank=True, default='')

    schedule_enabled = models.BooleanField("啟用定期備份", default=False)
    backup_time = models.TimeField("備份時間", default=time(2, 0))

    retention_type = models.CharField("保留規則", max_length=20, choices=RETENTION_CHOICES, default='count')
    retention_value = models.IntegerField("保留數量/天數", default=10)

    class Meta:
        verbose_name = "備份設定"
        verbose_name_plural = "備份設定"

    def __str__(self):
        return f"備份設定 ({self.get_dest_type_display()})"

    @classmethod
    def get_solo(cls):
        """Get the singleton config instance, or create one with defaults."""
        obj, created = cls.objects.get_or_create(id=1)
        return obj


class BackupHistory(models.Model):
    STATUS_CHOICES = [
        ('pending', '備份中'),
        ('success', '成功'),
        ('failed', '失敗'),
    ]

    TRIGGER_CHOICES = [
        ('manual', '手動'),
        ('scheduled', '排程'),
    ]

    filename = models.CharField("備份檔名", max_length=255)
    filepath = models.CharField("備份路徑", max_length=500)
    filesize = models.BigIntegerField("檔案大小 (Bytes)", default=0)
    created_at = models.DateTimeField("備份時間", auto_now_add=True)
    status = models.CharField("備份狀態", max_length=20, choices=STATUS_CHOICES, default='pending')
    log = models.TextField("備份記錄/過程", blank=True, default='')
    comment = models.TextField("備份註解", blank=True, default='')
    trigger_type = models.CharField("觸發類型", max_length=20, choices=TRIGGER_CHOICES, default='manual')

    class Meta:
        verbose_name = "備份紀錄"
        verbose_name_plural = "備份紀錄"
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.filename} ({self.get_status_display()})"
