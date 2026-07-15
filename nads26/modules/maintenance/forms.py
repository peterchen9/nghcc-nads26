from pathlib import Path

from django import forms
from django.core.exceptions import ValidationError

from .models import (
    MaintenanceCategory,
    MaintenanceLocation,
    MaintenanceRecord,
    MaintenanceVendor,
)


ALLOWED_UPLOAD_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.webp', '.pdf'}
ALLOWED_UPLOAD_MIME_TYPES = {'image/jpeg', 'image/png', 'image/webp', 'application/pdf'}
MAX_UPLOAD_BYTES = 10 * 1024 * 1024


def validate_maintenance_upload(uploaded):
    if not uploaded:
        return uploaded
    suffix = Path(uploaded.name).suffix.lower()
    mime_type = getattr(uploaded, 'content_type', '') or ''
    if suffix not in ALLOWED_UPLOAD_EXTENSIONS or mime_type not in ALLOWED_UPLOAD_MIME_TYPES:
        raise ValidationError('只允許上傳 JPG、PNG、WEBP 或 PDF。')
    if uploaded.size > MAX_UPLOAD_BYTES:
        raise ValidationError('單一附件不可超過 10 MB。')
    return uploaded


class StyledModelForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs.setdefault('class', 'maint-field')


class MaintenanceRecordForm(StyledModelForm):
    onsite_file = forms.FileField(label='現場照片', required=False, validators=[validate_maintenance_upload])
    quote_file = forms.FileField(label='報價單照片／PDF', required=False, validators=[validate_maintenance_upload])
    receipt_file = forms.FileField(label='發票收據照片／PDF', required=False, validators=[validate_maintenance_upload])

    class Meta:
        model = MaintenanceRecord
        fields = (
            'maintenance_date', 'type', 'category', 'location', 'handler', 'vendor',
            'vendor_representative', 'status', 'cost', 'issue', 'result', 'notes',
        )
        labels = {
            'maintenance_date': '維護日期', 'type': '維護類型', 'category': '維護分類',
            'location': '維護地點', 'handler': '經手人', 'vendor': '廠商',
            'vendor_representative': '廠商代表', 'status': '維護狀態', 'cost': '費用',
            'issue': '需維護問題', 'result': '維護結果', 'notes': '備註',
        }
        widgets = {
            'maintenance_date': forms.DateInput(attrs={'type': 'date'}),
            'cost': forms.NumberInput(attrs={'min': '0', 'step': '1'}),
            'issue': forms.Textarea(attrs={'rows': 5}),
            'result': forms.Textarea(attrs={'rows': 4}),
            'notes': forms.Textarea(attrs={'rows': 3}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['category'].queryset = MaintenanceCategory.objects.filter(is_active=True)
        self.fields['location'].queryset = MaintenanceLocation.objects.filter(is_active=True)
        self.fields['vendor'].queryset = MaintenanceVendor.objects.filter(is_active=True)


class PublicMaintenanceReportForm(forms.ModelForm):
    onsite_file = forms.FileField(label='現場照片', required=False, validators=[validate_maintenance_upload])
    website = forms.CharField(required=False, widget=forms.HiddenInput)

    class Meta:
        model = MaintenanceRecord
        fields = ('maintenance_date', 'type', 'category', 'location', 'handler', 'issue')
        labels = {
            'maintenance_date': '日期', 'type': '類型', 'category': '分類',
            'location': '地點', 'handler': '申請人', 'issue': '需維護問題',
        }
        widgets = {
            'maintenance_date': forms.DateInput(attrs={'type': 'date'}),
            'issue': forms.Textarea(attrs={'rows': 6}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs.setdefault('class', 'public-field')
        self.fields['category'].queryset = MaintenanceCategory.objects.filter(is_active=True)
        self.fields['location'].queryset = MaintenanceLocation.objects.filter(is_active=True)

    def clean_website(self):
        if self.cleaned_data.get('website'):
            raise ValidationError('無效的送出內容。')
        return ''


class MaintenanceVendorForm(StyledModelForm):
    class Meta:
        model = MaintenanceVendor
        exclude = ('source_id', 'created_at', 'updated_at')
        labels = {
            'name': '廠商名稱', 'category': '廠商類別', 'contact': '聯絡人',
            'mobile_phone': '行動電話', 'company_phone': '公司電話', 'email': 'Email',
            'line': 'LINE', 'address': '地址', 'tax_id': '統一編號', 'bank_name': '銀行',
            'bank_branch': '分行', 'bank_account_name': '戶名',
            'bank_account_number': '帳號', 'notes': '備註', 'is_active': '是否啟用',
        }
        widgets = {'notes': forms.Textarea(attrs={'rows': 3})}


class MaintenanceCategoryForm(StyledModelForm):
    class Meta:
        model = MaintenanceCategory
        fields = ('name', 'notes', 'is_active')
        labels = {'name': '分類名稱', 'notes': '備註', 'is_active': '是否啟用'}
        widgets = {'notes': forms.Textarea(attrs={'rows': 2})}

class MaintenanceLocationForm(StyledModelForm):
    class Meta:
        model = MaintenanceLocation
        fields = ('name', 'area', 'floor', 'notes', 'is_active')
        labels = {
            'name': '地點名稱', 'area': '區域', 'floor': '樓層',
            'notes': '備註', 'is_active': '是否啟用',
        }
        widgets = {'notes': forms.Textarea(attrs={'rows': 2})}
