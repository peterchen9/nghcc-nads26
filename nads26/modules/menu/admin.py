from django.contrib import admin
from .models import MenuItem

@admin.register(MenuItem)
class MenuItemAdmin(admin.ModelAdmin):
    list_display = ('title', 'parent', 'route', 'order', 'is_active')
    list_filter = ('parent', 'is_active')
    search_fields = ('title', 'route')
    ordering = ('parent__id', 'order')
