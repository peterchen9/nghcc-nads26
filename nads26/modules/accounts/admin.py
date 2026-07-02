from django.contrib import admin
from .models import UserProfile, SystemSetting

@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'display_name', 'worker_ename')
    search_fields = ('user__username', 'display_name', 'worker_ename')

@admin.register(SystemSetting)
class SystemSettingAdmin(admin.ModelAdmin):
    list_display = ('description', 'key', 'value')
    fields = ('description', 'key', 'value')
    readonly_fields = ('key',)  # Keep key read-only to avoid breaking logic
