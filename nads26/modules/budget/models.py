from decimal import Decimal

from django.conf import settings
from django.db import models


class BudgetItem(models.Model):
    category = models.CharField('分類', max_length=120, blank=True, default='')
    budget_code = models.CharField('2026預算代號', max_length=60, blank=True, default='', db_index=True)
    ministry = models.CharField('事工', max_length=200, blank=True, default='')
    annual_goal = models.TextField('年度目標', blank=True, default='')
    strategy_plan = models.TextField('策略&執行計畫', blank=True, default='')
    activity_budget = models.TextField('活動與預算', blank=True, default='')
    lead_pastor = models.CharField('主責牧者', max_length=120, blank=True, default='')
    budget_2026 = models.DecimalField('2026預算', max_digits=14, decimal_places=2, null=True, blank=True)
    used_amount = models.DecimalField('已使用金額', max_digits=14, decimal_places=2, null=True, blank=True)
    accounting_subject = models.CharField('會計科目', max_length=120, blank=True, default='')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'budget_items'
        ordering = ['id']
        verbose_name = '預算項目'
        verbose_name_plural = '預算項目'

    @property
    def usage_ratio(self):
        if not self.budget_2026:
            return None
        used = self.used_amount or Decimal('0')
        return (used / self.budget_2026) * Decimal('100')

    @property
    def balance(self):
        return (self.budget_2026 or Decimal('0')) - (self.used_amount or Decimal('0'))

    @property
    def row_status(self):
        ratio = self.usage_ratio
        if ratio is None:
            return ''
        if ratio > 90:
            return 'over-pink'
        if ratio > 70:
            return 'over-yellow'
        return ''

    def __str__(self):
        return f'{self.budget_code} {self.ministry}'.strip()


class BudgetChangeLog(models.Model):
    ACTION_CHOICES = [
        ('create', '新增'),
        ('update', '修改'),
        ('import', '匯入'),
        ('delete', '刪除'),
    ]

    budget_item = models.ForeignKey(BudgetItem, null=True, blank=True, on_delete=models.SET_NULL, related_name='change_logs')
    action = models.CharField('動作', max_length=20, choices=ACTION_CHOICES)
    before_data = models.JSONField('修改前內容', null=True, blank=True)
    after_data = models.JSONField('修改後內容', null=True, blank=True)
    changed_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL)
    changed_by_code = models.CharField('修改者代號', max_length=150, blank=True, default='')
    ip_address = models.GenericIPAddressField('IP', null=True, blank=True)
    mac_address = models.CharField('MAC', max_length=32, blank=True, default='')
    created_at = models.DateTimeField('修改日期時間', auto_now_add=True)

    class Meta:
        db_table = 'budget_change_logs'
        ordering = ['-created_at', '-id']
        verbose_name = '預算修改紀錄'
        verbose_name_plural = '預算修改紀錄'
