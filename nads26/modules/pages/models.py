from django.db import models
from ckeditor_uploader.fields import RichTextUploadingField

class Page(models.Model):
    title = models.CharField("標題", max_length=200)
    slug = models.SlugField("網址路徑", max_length=200, unique=True, help_text="例如：home, contact")
    content = RichTextUploadingField("網頁內容", blank=True, default="")
    is_active = models.BooleanField("是否啟用", default=True)
    created_at = models.DateTimeField("建立時間", auto_now_add=True)
    updated_at = models.DateTimeField("更新時間", auto_now=True)

    class Meta:
        verbose_name = "網頁內容"
        verbose_name_plural = "網頁內容"

    def __str__(self):
        return self.title

class MediaCollection(models.Model):
    filename = models.CharField("檔名", max_length=255)
    path = models.TextField("路徑")
    duration = models.CharField("時長", max_length=50, default="未知")
    file_type = models.CharField("類型", max_length=10, default="")
    size = models.BigIntegerField("檔案大小", default=0)
    last_scanned = models.DateTimeField("掃描時間", auto_now=True)

    class Meta:
        verbose_name = "影音收藏"
        verbose_name_plural = "影音收藏"

    def __str__(self):
        return self.filename
