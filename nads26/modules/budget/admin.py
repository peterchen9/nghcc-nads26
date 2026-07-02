from django.contrib import admin

from .models import BudgetChangeLog, BudgetItem


@admin.register(BudgetItem)
class BudgetItemAdmin(admin.ModelAdmin):
    list_display = ('budget_code', 'category', 'ministry', 'lead_pastor', 'budget_2026', 'accounting_subject')
    search_fields = ('category', 'budget_code', 'ministry', 'lead_pastor', 'accounting_subject')
    list_filter = ('category', 'lead_pastor', 'accounting_subject')


@admin.register(BudgetChangeLog)
class BudgetChangeLogAdmin(admin.ModelAdmin):
    list_display = ('created_at', 'action', 'changed_by_code', 'ip_address', 'mac_address', 'budget_item')
    list_filter = ('action', 'changed_by_code')
    search_fields = ('changed_by_code', 'ip_address', 'mac_address', 'budget_item__budget_code')
    readonly_fields = ('created_at',)
