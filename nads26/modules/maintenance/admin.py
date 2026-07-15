from django.contrib import admin

from .models import (
    MaintenanceAttachment,
    MaintenanceCategory,
    MaintenanceLocation,
    MaintenanceRecord,
    MaintenanceVendor,
)


class MaintenanceAttachmentInline(admin.TabularInline):
    model = MaintenanceAttachment
    extra = 0


@admin.register(MaintenanceRecord)
class MaintenanceRecordAdmin(admin.ModelAdmin):
    list_display = ('maintenance_date', 'issue', 'category', 'location', 'vendor', 'status', 'cost')
    list_filter = ('type', 'status', 'category', 'location')
    search_fields = ('issue', 'result', 'notes', 'handler')
    inlines = (MaintenanceAttachmentInline,)


@admin.register(MaintenanceVendor)
class MaintenanceVendorAdmin(admin.ModelAdmin):
    list_display = ('name', 'category', 'contact', 'mobile_phone', 'tax_id', 'is_active')
    search_fields = ('name', 'contact', 'tax_id')


admin.site.register(MaintenanceCategory)
admin.site.register(MaintenanceLocation)
