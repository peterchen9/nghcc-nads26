from django.db import models
from django.contrib.auth.models import User


class Member(models.Model):
    """會員/人員主檔 — 對應 members 表"""

    church_id = models.BigIntegerField('Church ID', primary_key=True)
    name = models.CharField('姓名', max_length=255, default='')
    address = models.CharField('地址', max_length=255, blank=True, default='')
    mobile1 = models.CharField('手機', max_length=50, blank=True, default='')
    email1 = models.CharField('Email', max_length=255, blank=True, default='')
    note = models.TextField('備註', blank=True, default='')
    family_id = models.BigIntegerField('Family ID', null=True, blank=True)
    section = models.CharField('牧區', max_length=100, blank=True, default='')
    family1 = models.CharField('小組', max_length=255, blank=True, default='')
    
    # 額外出席與其它資訊欄位
    dataindate = models.DateField('資料輸入日期', null=True, blank=True)
    att_y = models.CharField('出席總覽年份/代碼', max_length=255, blank=True, default='')
    att_12m = models.IntegerField('近12個月出席', null=True, blank=True)
    att_str = models.TextField('出席詳情', blank=True, default='')
    percent_year = models.CharField('年度出席率', max_length=255, blank=True, default='')
    data_str = models.TextField('出席詳情圖', blank=True, default='')
    percent_12_month = models.CharField('近12月出席率', max_length=255, blank=True, default='')
    first_daka = models.CharField('首次打卡', max_length=50, blank=True, default='')

    # 其它既有資料庫欄位 (可選，防寫入/讀取對不齊，設為 blank/null 即可)
    gender = models.CharField('性別', max_length=10, blank=True, default='')
    birthday = models.DateField('生日', null=True, blank=True)
    join_date = models.DateField('加入日期', null=True, blank=True)
    baptized = models.CharField('已洗禮', max_length=10, blank=True, default='')
    presence = models.IntegerField('在場/現況', default=0)
    marriage = models.CharField('婚姻狀況', max_length=50, blank=True, default='')
    phone_h = models.CharField('住家電話', max_length=50, blank=True, default='')
    phone_o = models.CharField('辦公電話', max_length=50, blank=True, default='')
    visitor_info = models.CharField('訪客資訊', max_length=255, blank=True, default='')
    car_number = models.CharField('車牌號碼', max_length=50, blank=True, default='')
    line_id = models.CharField('Line ID', max_length=100, blank=True, default='')
    photo_base64 = models.TextField('照片 Base64', blank=True, default='')

    class Meta:
        db_table = 'members'
        managed = False  # 已由外部 mysqldump 匯入，不由 Django 控管 schema
        verbose_name = '人員'
        verbose_name_plural = '人員'

    def __str__(self):
        return f'[{self.church_id}] {self.name}'


class StaffAttendance(models.Model):
    """員工打卡記錄"""
    employee_no = models.CharField("員工編號", max_length=50)
    name = models.CharField("姓名", max_length=100)
    card_no = models.CharField("卡號", max_length=50, blank=True, default="")
    timestamp = models.DateTimeField("打卡時間")
    serial_no = models.IntegerField("設備流水號", unique=True)

    class Meta:
        db_table = 'staff_attendance'
        verbose_name = "員工打卡記錄"
        verbose_name_plural = "員工打卡記錄"
        ordering = ['-timestamp']

    def __str__(self):
        return f"{self.name} ({self.employee_no}) - {self.timestamp.strftime('%Y-%m-%d %H:%M:%S')}"


class StaffLeave(models.Model):
    """同工休假紀錄"""
    member = models.ForeignKey(
        'Member', 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name='leaves'
    )
    staff_name = models.CharField("同工姓名", max_length=100)
    date = models.DateField("日期")
    time_slot = models.CharField("時段", max_length=10, choices=[('AM', '上午'), ('PM', '下午')])
    leave_type = models.CharField("假別", max_length=50, blank=True, default="")

    class Meta:
        db_table = 'staff_leaves'
        verbose_name = "同工休假記錄"
        verbose_name_plural = "同工休假記錄"
        unique_together = ('staff_name', 'date', 'time_slot')
        ordering = ['-date', 'staff_name', 'time_slot']

    def __str__(self):
        return f"{self.staff_name} - {self.date} {self.time_slot}: {self.leave_type or '上班'}"


class DailyDutyNote(models.Model):
    """每日行政與活動備註"""
    date = models.DateField("日期", unique=True)
    note = models.CharField("行政備註", max_length=255, blank=True, default="")

    class Meta:
        db_table = 'daily_duty_notes'
        verbose_name = "每日行政備註"
        verbose_name_plural = "每日行政備註"
        ordering = ['-date']

    def __str__(self):
        return f"{self.date}: {self.note}"


class StaffShift(models.Model):
    """同工排班表"""
    shift_code = models.CharField("班表代號", max_length=50, unique=True)
    description = models.CharField("班表名稱/描述", max_length=100, blank=True, default="")
    
    # Monday to Sunday daily work times
    mon_start = models.TimeField("週一上班時間", null=True, blank=True)
    mon_end = models.TimeField("週一下班時間", null=True, blank=True)
    tue_start = models.TimeField("週二上班時間", null=True, blank=True)
    tue_end = models.TimeField("週二下班時間", null=True, blank=True)
    wed_start = models.TimeField("週三上班時間", null=True, blank=True)
    wed_end = models.TimeField("週三下班時間", null=True, blank=True)
    thu_start = models.TimeField("週四上班時間", null=True, blank=True)
    thu_end = models.TimeField("週四下班時間", null=True, blank=True)
    fri_start = models.TimeField("週五上班時間", null=True, blank=True)
    fri_end = models.TimeField("週五下班時間", null=True, blank=True)
    sat_start = models.TimeField("週六上班時間", null=True, blank=True)
    sat_end = models.TimeField("週六下班時間", null=True, blank=True)
    sun_start = models.TimeField("週日上班時間", null=True, blank=True)
    sun_end = models.TimeField("週日下班時間", null=True, blank=True)

    class Meta:
        db_table = 'staff_shifts'
        verbose_name = "同工班表"
        verbose_name_plural = "同工班表"

    def __str__(self):
        return f"{self.shift_code} ({self.description or '無描述'})"


class StaffInfo(models.Model):
    """同工基本資料與特休額度"""
    staff_id = models.IntegerField("同工編號", primary_key=True)
    name = models.CharField("姓名", max_length=100)
    identity_code = models.CharField("身分代碼", max_length=50, blank=True, default="")
    is_active = models.BooleanField("在職狀態", default=True)
    email = models.EmailField("本人Email", blank=True, default="")
    cc_email = models.EmailField("CC Email", blank=True, default="")
    onboard_date = models.DateField("到職日期", null=True, blank=True)
    
    # New fields requested by user
    employee_no = models.CharField("工號", max_length=50, blank=True, default="")
    mobile = models.CharField("手機號碼", max_length=50, blank=True, default="")
    seat = models.CharField("座位", max_length=50, blank=True, default="")
    locker_no = models.CharField("櫃號", max_length=50, blank=True, default="")
    bank_branch = models.CharField("??(??)", max_length=120, blank=True, default="")
    bank_account = models.CharField("????", max_length=120, blank=True, default="")
    user = models.ForeignKey(User, verbose_name="user", null=True, blank=True, on_delete=models.SET_NULL, related_name="staff_infos")
    shift = models.ForeignKey(StaffShift, on_delete=models.SET_NULL, null=True, blank=True, related_name='staff_infos', verbose_name='班表')
    annual_leave_quota = models.FloatField("年度特休", default=0.0)

    leave_quotas = models.JSONField("歷年休假額度", default=dict, blank=True)

    class Meta:
        db_table = 'staff_info'
        verbose_name = "同工資料"
        verbose_name_plural = "同工資料"
        ordering = ['staff_id']

    def __str__(self):
        return f"[{self.staff_id}] {self.name} ({self.identity_code})"


class SeatMap(models.Model):
    """辦公室座位配置圖"""
    name = models.CharField("配置名稱", max_length=100, default="預設座位圖")
    layout_data = models.JSONField("配置JSON資料", default=dict, blank=True)
    updated_at = models.DateTimeField("更新時間", auto_now=True)

    class Meta:
        db_table = 'seat_maps'
        verbose_name = "座位配置圖"
        verbose_name_plural = "座位配置圖"

    def __str__(self):
        return f"{self.name} ({self.updated_at.strftime('%Y-%m-%d %H:%M')})"


class YearlyAttendance(models.Model):
    year = models.IntegerField("年", primary_key=True)
    attendance = models.IntegerField("聚會人數", default=0)
    baptized = models.IntegerField("受洗", default=0)
    remark = models.TextField("備註", blank=True, default="")

    class Meta:
        db_table = 'yearly_attendance'
        verbose_name = "歷年人數統計"
        verbose_name_plural = "歷年人數統計"
        ordering = ['year']

    def __str__(self):
        return f"{self.year}: {self.attendance}人"


class WeeklyAttendance(models.Model):
    date = models.DateField("週(主日日期)", primary_key=True)
    first_service = models.IntegerField("第一堂", null=True, blank=True)
    second_service = models.IntegerField("第二堂", null=True, blank=True)
    evening_service = models.IntegerField("晚堂", null=True, blank=True)
    online = models.IntegerField("線上", null=True, blank=True)
    children = models.IntegerField("兒主", null=True, blank=True)
    youth = models.IntegerField("青少", null=True, blank=True)
    total = models.IntegerField("總計", null=True, blank=True)
    new_friends = models.IntegerField("主日新朋友", null=True, blank=True)
    remark = models.TextField("註記(不含新朋友)", blank=True, default="")

    class Meta:
        db_table = 'weekly_attendance'
        verbose_name = "每週聚會人數"
        verbose_name_plural = "每週聚會人數"
        ordering = ['-date']

    def save(self, *args, **kwargs):
        # Recalculate total if individual counts are present
        if (self.first_service is not None or 
            self.second_service is not None or 
            self.evening_service is not None or 
            self.online is not None):
            self.total = (self.first_service or 0) + (self.second_service or 0) + (self.evening_service or 0) + (self.online or 0)
        
        # Ensure total is saved when update_fields is specified
        if 'update_fields' in kwargs and kwargs['update_fields'] is not None:
            update_fields = set(kwargs['update_fields'])
            update_fields.add('total')
            kwargs['update_fields'] = update_fields

        super().save(*args, **kwargs)


    def __str__(self):
        return f"{self.date} - 總計: {self.total or 0}人"


class PrayerMeetingAttendance(models.Model):
    date = models.DateField("週(週四日期)", primary_key=True)
    attendance = models.IntegerField("人數", default=0)

    class Meta:
        db_table = 'prayer_meeting_attendance'
        verbose_name = "禱告會人數"
        verbose_name_plural = "禱告會人數"
        ordering = ['-date']

    def __str__(self):
        return f"{self.date} - 禱告會: {self.attendance}人"


class PastoralOverseer(models.Model):
    name = models.CharField("區牧名字", max_length=255, unique=True)

    class Meta:
        db_table = 'pastoral_overseers'
        verbose_name = "區牧"
        verbose_name_plural = "區牧"

    def __str__(self):
        return self.name


class PastoralSection(models.Model):
    name = models.CharField("牧區名稱", max_length=255, unique=True)
    overseer = models.ForeignKey(PastoralOverseer, on_delete=models.CASCADE, related_name='sections')
    counselor = models.CharField("輔導", max_length=255, blank=True, default='')
    leader = models.CharField("區長", max_length=255, blank=True, default='')

    class Meta:
        db_table = 'pastoral_sections'
        verbose_name = "牧區"
        verbose_name_plural = "牧區"

    def __str__(self):
        return self.name


class PastoralGroup(models.Model):
    name = models.CharField("小組名稱", max_length=255, unique=True)
    section = models.ForeignKey(PastoralSection, on_delete=models.CASCADE, related_name='groups')
    meeting_time = models.CharField("聚會時間", max_length=255, blank=True, default='')
    location = models.CharField("地點", max_length=255, blank=True, default='')
    target = models.CharField("對象", max_length=255, blank=True, default='')
    topic = models.CharField("近期聚會主題", max_length=255, blank=True, default='')
    photo = models.ImageField("小組照片", upload_to='groups/', blank=True, null=True)

    class Meta:
        db_table = 'pastoral_groups'
        verbose_name = "小組"
        verbose_name_plural = "小組"

    def __str__(self):
        return self.name





