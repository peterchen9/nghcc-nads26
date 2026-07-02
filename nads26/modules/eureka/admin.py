from django.contrib import admin
from .models import Member

@admin.register(Member)
class MemberAdmin(admin.ModelAdmin):
    list_display = ('church_id', 'name', 'section', 'family1', 'mobile1', 'email1')
    list_filter = ('section', 'family1')
    search_fields = ('church_id', 'name', 'section', 'family1', 'mobile1', 'email1')
    ordering = ('church_id',)
