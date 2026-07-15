import uuid

from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import models


def attachment_upload_to(instance, filename):
    suffix = filename.rsplit('.', 1)[-1].lower() if '.' in filename else 'bin'
    date = instance.record.maintenance_date
    return f'maintenance/{date:%Y/%m}/{uuid.uuid4().hex}.{suffix}'


class MaintenanceCategory(models.Model):
    source_id = models.PositiveIntegerField(null=True, blank=True, unique=True)
    name = models.CharField(max_length=120, unique=True)
    notes = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ('name', 'id')
        verbose_name = '維護分類'
        verbose_name_plural = '維護分類'

    def __str__(self):
        return self.name


class MaintenanceLocation(models.Model):
    source_id = models.PositiveIntegerField(null=True, blank=True, unique=True)
    name = models.CharField(max_length=160)
    area = models.CharField(max_length=120, blank=True)
    floor = models.CharField(max_length=80, blank=True)
    notes = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ('name', 'floor', 'id')
        verbose_name = '維護地點'
        verbose_name_plural = '維護地點'
        constraints = [
            models.UniqueConstraint(fields=('name', 'area', 'floor'), name='uniq_maintenance_location'),
        ]

    def __str__(self):
        details = ' / '.join(part for part in (self.area, self.floor) if part)
        return f'{self.name}（{details}）' if details else self.name


class MaintenanceVendor(models.Model):
    source_id = models.PositiveIntegerField(null=True, blank=True, unique=True)
    name = models.CharField(max_length=200)
    category = models.CharField(max_length=120, blank=True)
    contact = models.CharField(max_length=120, blank=True)
    mobile_phone = models.CharField(max_length=60, blank=True)
    company_phone = models.CharField(max_length=60, blank=True)
    email = models.EmailField(blank=True)
    line = models.CharField(max_length=120, blank=True)
    address = models.CharField(max_length=300, blank=True)
    tax_id = models.CharField(max_length=30, blank=True)
    bank_name = models.CharField(max_length=120, blank=True)
    bank_branch = models.CharField(max_length=120, blank=True)
    bank_account_name = models.CharField(max_length=160, blank=True)
    bank_account_number = models.CharField(max_length=80, blank=True)
    notes = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ('name', 'id')
        verbose_name = '維護廠商'
        verbose_name_plural = '維護廠商'
        indexes = [models.Index(fields=('name',), name='maint_vendor_name_idx')]

    def __str__(self):
        return self.name


class MaintenanceRecord(models.Model):
    class Type(models.TextChoices):
        GENERAL = 'GENERAL', '一般維護'
        EMERGENCY = 'EMERGENCY', '緊急維護'
        SCHEDULED = 'SCHEDULED', '定期維護'

    class Status(models.TextChoices):
        PENDING = 'PENDING', '待處理'
        IN_PROGRESS = 'IN_PROGRESS', '處理中'
        COMPLETED = 'COMPLETED', '已完成'
        WAITING_QUOTE = 'WAITING_QUOTE', '待報價'
        WAITING_CONSTRUCTION = 'WAITING_CONSTRUCTION', '待施工'
        CANCELLED = 'CANCELLED', '取消'

    source_id = models.PositiveIntegerField(null=True, blank=True, unique=True)
    maintenance_date = models.DateField(db_index=True)
    type = models.CharField(max_length=30, choices=Type.choices, default=Type.GENERAL, db_index=True)
    category = models.ForeignKey(
        MaintenanceCategory, null=True, blank=True, on_delete=models.SET_NULL,
        related_name='records',
    )
    location = models.ForeignKey(
        MaintenanceLocation, null=True, blank=True, on_delete=models.SET_NULL,
        related_name='records',
    )
    handler = models.CharField(max_length=160)
    vendor = models.ForeignKey(
        MaintenanceVendor, null=True, blank=True, on_delete=models.SET_NULL,
        related_name='records',
    )
    vendor_representative = models.CharField(max_length=160, blank=True)
    issue = models.TextField()
    result = models.TextField(blank=True)
    status = models.CharField(max_length=40, choices=Status.choices, default=Status.PENDING, db_index=True)
    cost = models.DecimalField(max_digits=12, decimal_places=2, default=0, validators=[MinValueValidator(0)])
    notes = models.TextField(blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL,
        related_name='created_maintenance_records',
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ('-maintenance_date', '-id')
        verbose_name = '維護紀錄'
        verbose_name_plural = '維護紀錄'
        indexes = [
            models.Index(fields=('status', 'maintenance_date'), name='maint_status_date_idx'),
            models.Index(fields=('category', 'maintenance_date'), name='maint_cat_date_idx'),
        ]

    def __str__(self):
        return f'{self.maintenance_date} {self.issue[:40]}'

    @property
    def is_incomplete(self):
        return self.status not in {self.Status.COMPLETED, self.Status.CANCELLED}


class MaintenanceAttachment(models.Model):
    class Type(models.TextChoices):
        ONSITE = 'ONSITE', '現場照片'
        QUOTE = 'QUOTE', '報價單'
        RECEIPT = 'RECEIPT', '發票／收據'
        OTHER = 'OTHER', '其他附件'

    source_key = models.CharField(max_length=255, null=True, blank=True, unique=True)
    record = models.ForeignKey(MaintenanceRecord, on_delete=models.CASCADE, related_name='attachments')
    type = models.CharField(max_length=30, choices=Type.choices, default=Type.OTHER)
    file = models.FileField(upload_to=attachment_upload_to)
    original_name = models.CharField(max_length=255)
    mime_type = models.CharField(max_length=120, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ('type', 'id')
        verbose_name = '維護附件'
        verbose_name_plural = '維護附件'

    def __str__(self):
        return self.original_name
