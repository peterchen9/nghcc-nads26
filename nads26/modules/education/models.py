import datetime
import os
from django.db import models, transaction
from django.conf import settings
from django.core.files.storage import FileSystemStorage
from django.contrib.auth.models import User

private_storage = FileSystemStorage(
    location=getattr(settings, 'PRIVATE_MEDIA_ROOT', os.path.join(settings.BASE_DIR, 'private_media'))
)

class Course(models.Model):
    code = models.CharField(
        "課程代號", 
        max_length=20, 
        unique=True, 
        db_index=True,
        blank=True,
        help_text="自動產生，例如: RS2026001"
    )
    subject = models.CharField("課程主題", max_length=255)
    introduction = models.TextField("簡介", blank=True, default="")
    teachers = models.CharField("師資", max_length=255, help_text="多位老師可用逗號分隔")
    class_leader = models.CharField("班長", max_length=255, blank=True, default="")
    total_classes = models.PositiveIntegerField("課程次數", default=1)
    hours_per_class = models.PositiveIntegerField("每次上課時數(分鐘)", default=60)
    class_time = models.CharField("上課時間", max_length=255, help_text="例如: 每週六早上 09:00 - 11:00")
    classroom_id = models.IntegerField("教室ID", null=True, blank=True)
    classroom_name = models.CharField("教室名稱", max_length=100, blank=True, default="")
    makeup_required = models.BooleanField("是否補課？", default=False)
    created_at = models.DateTimeField("建立時間", auto_now_add=True)
    updated_at = models.DateTimeField("更新時間", auto_now=True)

    class Meta:
        verbose_name = "課程規劃"
        verbose_name_plural = "課程規劃"
        ordering = ["-code"]

    def __str__(self):
        return f"{self.code} - {self.subject}"

    def save(self, *args, **kwargs):
        if not self.code:
            current_year = datetime.datetime.now().year
            prefix = f"RS{current_year}"
            
            # atomic block for code generation
            with transaction.atomic():
                # select_for_update to handle concurrency safely
                last_course = Course.objects.select_for_update().filter(
                    code__startswith=prefix
                ).order_by('-code').first()
                
                if last_course:
                    try:
                        # Extract suffix from code, e.g. "RS2026001" -> "001"
                        last_serial = int(last_course.code[6:])
                        next_serial = last_serial + 1
                    except (ValueError, IndexError):
                        next_serial = 1
                else:
                    next_serial = 1
                
                self.code = f"{prefix}{next_serial:03d}"
        
        super().save(*args, **kwargs)


class CourseClass(models.Model):
    course = models.ForeignKey(
        Course, 
        on_delete=models.CASCADE, 
        related_name="classes", 
        verbose_name="課程"
    )
    class_number = models.PositiveIntegerField("堂次", help_text="第幾堂課")
    date = models.DateField("上課日期", null=True, blank=True)
    subject = models.CharField("課堂主題", max_length=255, blank=True, default="")
    teacher = models.CharField("授課老師", max_length=255, blank=True, default="")

    class Meta:
        verbose_name = "課程表單堂"
        verbose_name_plural = "課程表單堂"
        ordering = ["class_number"]

    def __str__(self):
        return f"{self.course.code} - 第{self.class_number}堂: {self.subject or '未設定'}"


class CoursePost(models.Model):
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name="posts")
    author = models.ForeignKey(User, on_delete=models.CASCADE)
    title = models.CharField("標題", max_length=255)
    content = models.TextField("內容")
    created_at = models.DateTimeField("發佈時間", auto_now_add=True)

    class Meta:
        verbose_name = "課程討論版公告"
        verbose_name_plural = "課程討論版公告"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.course.code} - {self.title}"


class CourseClassRecording(models.Model):
    course_class = models.OneToOneField(
        CourseClass, 
        on_delete=models.CASCADE, 
        related_name="recording",
        verbose_name="課堂"
    )
    audio_file = models.FileField("錄音檔案", storage=private_storage, upload_to="education/recordings/")
    filename = models.CharField("原始檔名", max_length=255)
    file_size = models.PositiveIntegerField("檔案大小(Bytes)", default=0)
    uploaded_at = models.DateTimeField("上傳時間", auto_now_add=True)

    class Meta:
        verbose_name = "課堂錄音"
        verbose_name_plural = "課堂錄音"

    def __str__(self):
        return f"{self.course_class} 錄音"


class MakeUpRecord(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="makeup_records", verbose_name="學員")
    course_class = models.ForeignKey(CourseClass, on_delete=models.CASCADE, related_name="makeup_records", verbose_name="課堂")
    completed_at = models.DateTimeField("完成登記時間", auto_now_add=True)

    class Meta:
        verbose_name = "學員補課紀錄"
        verbose_name_plural = "學員補課紀錄"
        unique_together = ("user", "course_class")

    def __str__(self):
        return f"{self.user.username} - {self.course_class} (補課完成)"
