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


class BaptismSession(models.Model):
    date = models.DateField("洗禮日期")
    location = models.CharField("洗禮場次/地點", max_length=200)
    pastor = models.CharField("主領牧師", max_length=100)

    class Meta:
        verbose_name = "洗禮場次"
        verbose_name_plural = "洗禮場次"
        ordering = ["-date", "-id"]

    def __str__(self):
        return f"{self.date} {self.location} ({self.pastor})"


class BaptismPerson(models.Model):
    date = models.DateField("洗禮日期")
    pastor = models.CharField("主禮牧師", max_length=100)
    name = models.CharField("姓名", max_length=100)
    gender = models.CharField("性別", max_length=10)
    category = models.CharField("洗禮類別", max_length=50) # 成人 / 嬰兒洗 / 堅信禮
    note = models.TextField("註記", blank=True, default="")
    
    session = models.ForeignKey(
        BaptismSession,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name="洗禮場次",
        related_name="participants"
    )
    interview_pastor = models.CharField("受洗約談牧者", max_length=100, blank=True, default="")
    gift_bible = models.CharField("贈送聖經", max_length=100, blank=True, default="")
    verse = models.CharField("受洗經文", max_length=255, blank=True, default="")
    is_completed = models.BooleanField("受洗完成", default=True)


    class Meta:
        verbose_name = "受洗者"
        verbose_name_plural = "受洗者"
        ordering = ["-date", "id"]

    def __str__(self):
        return f"{self.name} ({self.date})"


class FuneralService(models.Model):
    # Deceased Details
    deceased_name = models.CharField("故人姓名", max_length=100)
    deceased_date_of_birth = models.DateField("生日", null=True, blank=True)
    deceased_date_of_death = models.DateField("安息日期", null=True, blank=True)
    deceased_age = models.IntegerField("安息年齡", null=True, blank=True)
    
    # Family Contact Details
    family_contact = models.CharField("家屬聯絡人", max_length=100, blank=True, default="")
    family_relationship = models.CharField("關係", max_length=50, blank=True, default="")
    family_phone = models.CharField("聯絡電話", max_length=50, blank=True, default="")
    
    # Service Schedule
    service_date = models.DateField("禮拜日期")
    service_time = models.CharField("禮拜時間", max_length=50, blank=True, default="")
    location = models.CharField("禮拜地點", max_length=255, blank=True, default="")
    note = models.TextField("備註/備忘錄", blank=True, default="")
    
    # Serving Staff
    pastor = models.CharField("主禮牧師", max_length=100, blank=True, default="")
    preacher = models.CharField("證道人員", max_length=100, blank=True, default="")
    leader = models.CharField("司會人員", max_length=100, blank=True, default="")
    pianist = models.CharField("司琴人員", max_length=100, blank=True, default="")
    sound = models.CharField("司音/音控", max_length=100, blank=True, default="")
    projection = models.CharField("投影/簡報", max_length=100, blank=True, default="")
    ushers = models.CharField("招待人員", max_length=255, blank=True, default="")
    choir = models.CharField("獻詩/詩班", max_length=255, blank=True, default="")
    traffic = models.CharField("交通指引", max_length=255, blank=True, default="")
    
    # New requested columns
    coffining = models.CharField("入殮人員", max_length=100, blank=True, default="")
    cremation = models.CharField("火化人員", max_length=100, blank=True, default="")
    scripture = models.CharField("讀經人員", max_length=100, blank=True, default="")
    prayer = models.CharField("禱告人員", max_length=100, blank=True, default="")
    burial = models.CharField("安厝人員", max_length=100, blank=True, default="")
    
    is_completed = models.BooleanField("禮拜已完成", default=False)
    
    class Meta:
        verbose_name = "安息禮拜"
        verbose_name_plural = "安息禮拜"
        ordering = ["-service_date", "id"]
        
    def __str__(self):
        return f"{self.deceased_name} 安息禮拜 ({self.service_date})"


class FuneralShift(models.Model):
    group_no = models.IntegerField("組別", unique=True)
    preacher = models.CharField("講道(主理)", max_length=100, blank=True, default="")
    leader = models.CharField("司會", max_length=100, blank=True, default="")
    scripture_prayer = models.CharField("讀經+禱告", max_length=100, blank=True, default="")

    class Meta:
        verbose_name = "安息服事班表"
        verbose_name_plural = "安息服事班表"
        ordering = ["group_no"]

    def __str__(self):
        return f"第 {self.group_no} 組"


class DeaconBoardMinutes(models.Model):
    title = models.CharField("會議名稱", max_length=200)
    meeting_date = models.DateField("會議日期")
    summary = models.TextField("會議摘要", blank=True, default="")
    attachment = models.FileField("會議紀錄檔案", upload_to="board_minutes/", blank=True, null=True)
    created_at = models.DateTimeField("建立時間", auto_now_add=True)
    updated_at = models.DateTimeField("更新時間", auto_now=True)

    class Meta:
        verbose_name = "執事會會議紀錄"
        verbose_name_plural = "執事會會議紀錄"
        ordering = ["-meeting_date", "-id"]

    def __str__(self):
        return f"{self.title} ({self.meeting_date})"

