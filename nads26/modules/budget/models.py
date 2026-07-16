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


class BankAccount(models.Model):
    category = models.CharField('帳戶類別', max_length=100)
    bank = models.CharField('銀行', max_length=100, blank=True, default='')
    account_no = models.CharField('帳號', max_length=100, blank=True, default='')
    is_active = models.BooleanField('是否啟用', default=True)
    order = models.PositiveSmallIntegerField('排序', default=0)

    class Meta:
        db_table = 'bank_accounts'
        ordering = ['order', 'id']
        verbose_name = '銀行帳戶'
        verbose_name_plural = '銀行帳戶'

    def __str__(self):
        parts = [self.category]
        if self.bank:
            parts.append(self.bank)
        if self.account_no:
            parts.append(self.account_no)
        return ' - '.join(parts)


class AccountBalance(models.Model):
    account = models.ForeignKey(BankAccount, on_delete=models.CASCADE, related_name='balances', verbose_name='銀行帳戶')
    month = models.DateField('月份', db_index=True)
    balance = models.DecimalField('餘額', max_digits=16, decimal_places=2)

    class Meta:
        db_table = 'account_balances'
        ordering = ['-month', 'account__order']
        constraints = [
            models.UniqueConstraint(fields=['account', 'month'], name='unique_account_month')
        ]
        verbose_name = '帳戶餘額'
        verbose_name_plural = '帳戶餘額'

    def __str__(self):
        return f'{self.month.strftime("%Y-%m")} - {self.account}: {self.balance}'


class TimeDeposit(models.Model):
    category = models.CharField('帳戶類別', max_length=100)
    duration = models.CharField('存單期間', max_length=100, blank=True, default='')
    period = models.CharField('期別', max_length=50, blank=True, default='')
    deposit_type = models.CharField('存單類別', max_length=50, blank=True, default='')
    deposit_no = models.CharField('存單編號', max_length=100, blank=True, default='')
    interest_rate = models.DecimalField('利率%', max_digits=8, decimal_places=5, null=True, blank=True)
    rate_type = models.CharField('固定/機動', max_length=20, blank=True, default='')
    amount = models.DecimalField('金額', max_digits=16, decimal_places=2)
    is_active = models.BooleanField('是否啟用', default=True)
    order = models.PositiveSmallIntegerField('排序', default=0)

    class Meta:
        db_table = 'time_deposits'
        ordering = ['order', 'id']
        verbose_name = '定期存單'
        verbose_name_plural = '定期存單'

    def __str__(self):
        return f'{self.category} - {self.deposit_no} ({self.amount})'


class Fund(models.Model):
    name = models.CharField('基金名稱', max_length=100, unique=True)
    note = models.TextField('備註', blank=True, default='')
    is_active = models.BooleanField('是否啟用', default=True)
    order = models.PositiveSmallIntegerField('排序', default=0)

    class Meta:
        db_table = 'funds'
        ordering = ['order', 'id']
        verbose_name = '基金'
        verbose_name_plural = '基金'

    def __str__(self):
        return self.name


class FundBalance(models.Model):
    fund = models.ForeignKey(Fund, on_delete=models.CASCADE, related_name='balances', verbose_name='基金')
    month = models.DateField('月份', db_index=True)
    balance = models.DecimalField('餘額', max_digits=16, decimal_places=2)

    class Meta:
        db_table = 'fund_balances'
        ordering = ['-month', 'fund__order']
        constraints = [
            models.UniqueConstraint(fields=['fund', 'month'], name='unique_fund_month')
        ]
        verbose_name = '基金餘額'
        verbose_name_plural = '基金餘額'

    def __str__(self):
        return f'{self.month.strftime("%Y-%m")} - {self.fund}: {self.balance}'


class Fellowship(models.Model):
    name = models.CharField('團契名稱', max_length=100, unique=True)
    note = models.TextField('備註', blank=True, default='')
    is_active = models.BooleanField('是否啟用', default=True)
    order = models.PositiveSmallIntegerField('排序', default=0)

    class Meta:
        db_table = 'fellowships'
        ordering = ['order', 'id']
        verbose_name = '團契'
        verbose_name_plural = '團契'

    def __str__(self):
        return self.name


class FellowshipBalance(models.Model):
    fellowship = models.ForeignKey(Fellowship, on_delete=models.CASCADE, related_name='balances', verbose_name='團契')
    month = models.DateField('月份', db_index=True)
    balance = models.DecimalField('餘額', max_digits=16, decimal_places=2)

    class Meta:
        db_table = 'fellowship_balances'
        ordering = ['-month', 'fellowship__order']
        constraints = [
            models.UniqueConstraint(fields=['fellowship', 'month'], name='unique_fellowship_month')
        ]
        verbose_name = '團契餘額'
        verbose_name_plural = '團契餘額'

    def __str__(self):
        return f'{self.month.strftime("%Y-%m")} - {self.fellowship}: {self.balance}'


class MonthlyOffering(models.Model):
    month = models.DateField('月份', unique=True, db_index=True)
    pledge_people_count = models.IntegerField('月定人數', null=True, blank=True)
    sunday = models.DecimalField('主日奉獻', max_digits=16, decimal_places=2, default=0.0)
    pledge = models.DecimalField('月定奉獻', max_digits=16, decimal_places=2, default=0.0)
    thanksgiving = models.DecimalField('感恩奉獻', max_digits=16, decimal_places=2, default=0.0)
    building = models.DecimalField('建築奉獻', max_digits=16, decimal_places=2, default=0.0)
    planting = models.DecimalField('植堂奉獻', max_digits=16, decimal_places=2, default=0.0)
    designated = models.DecimalField('指定奉獻', max_digits=16, decimal_places=2, default=0.0)
    mission = models.DecimalField('宣教&大陸奉獻', max_digits=16, decimal_places=2, default=0.0)
    galilee = models.DecimalField('加利利基金', max_digits=16, decimal_places=2, default=0.0)
    timothy = models.DecimalField('提摩太基金', max_digits=16, decimal_places=2, default=0.0)
    kingdom = models.DecimalField('國度基金', max_digits=16, decimal_places=2, default=0.0)
    venue = models.DecimalField('場地費收入', max_digits=16, decimal_places=2, default=0.0)
    total = models.DecimalField('合計', max_digits=16, decimal_places=2, default=0.0)

    class Meta:
        db_table = 'monthly_offerings'
        ordering = ['-month']
        verbose_name = '每月奉獻統計'
        verbose_name_plural = '每月奉獻統計'

    def save(self, *args, **kwargs):
        self.total = (
            (self.sunday or Decimal('0.0')) +
            (self.pledge or Decimal('0.0')) +
            (self.thanksgiving or Decimal('0.0')) +
            (self.building or Decimal('0.0')) +
            (self.planting or Decimal('0.0')) +
            (self.designated or Decimal('0.0')) +
            (self.mission or Decimal('0.0')) +
            (self.galilee or Decimal('0.0')) +
            (self.timothy or Decimal('0.0')) +
            (self.kingdom or Decimal('0.0')) +
            (self.venue or Decimal('0.0'))
        )
        super().save(*args, **kwargs)
        self.update_annual_offering()

    def update_annual_offering(self):
        year = self.month.year
        siblings = MonthlyOffering.objects.filter(month__year=year)

        sums = siblings.aggregate(
            agg_sunday=models.Sum('sunday'),
            agg_pledge=models.Sum('pledge'),
            agg_thanksgiving=models.Sum('thanksgiving'),
            agg_building=models.Sum('building'),
            agg_planting=models.Sum('planting'),
            agg_designated=models.Sum('designated'),
            agg_mission=models.Sum('mission'),
            agg_galilee=models.Sum('galilee'),
            agg_timothy=models.Sum('timothy'),
            agg_kingdom=models.Sum('kingdom'),
            agg_venue=models.Sum('venue'),
            agg_total=models.Sum('total'),
            agg_max_people=models.Max('pledge_people_count')
        )

        people_count = None
        if sums['agg_max_people'] is not None:
            people_count = int(round(sums['agg_max_people']))

        ann, created = AnnualOffering.objects.get_or_create(year=year)
        ann.pledge_people_count = people_count
        ann.sunday = sums['agg_sunday'] or Decimal('0.0')
        ann.pledge = sums['agg_pledge'] or Decimal('0.0')
        ann.thanksgiving = sums['agg_thanksgiving'] or Decimal('0.0')
        ann.building = sums['agg_building'] or Decimal('0.0')
        ann.planting = sums['agg_planting'] or Decimal('0.0')
        ann.designated = sums['agg_designated'] or Decimal('0.0')
        ann.mission = sums['agg_mission'] or Decimal('0.0')
        ann.galilee = sums['agg_galilee'] or Decimal('0.0')
        ann.timothy = sums['agg_timothy'] or Decimal('0.0')
        ann.kingdom = sums['agg_kingdom'] or Decimal('0.0')
        ann.venue = sums['agg_venue'] or Decimal('0.0')

        ann.total = (
            ann.sunday + ann.pledge + ann.thanksgiving + ann.building +
            ann.planting + ann.designated + ann.mission + ann.galilee +
            ann.timothy + ann.kingdom + ann.venue +
            (ann.spring or Decimal('0.0')) +
            (ann.other or Decimal('0.0')) +
            (ann.project or Decimal('0.0'))
        )
        ann.save()

    def __str__(self):
        return f'{self.month.strftime("%Y-%m")} - 奉獻總計: {self.total}'


class AnnualOffering(models.Model):
    year = models.IntegerField('年度', unique=True, db_index=True)
    pledge_people_count = models.IntegerField('月定人數', null=True, blank=True)
    sunday = models.DecimalField('主日奉獻', max_digits=16, decimal_places=2, default=0.0)
    pledge = models.DecimalField('月定奉獻', max_digits=16, decimal_places=2, default=0.0)
    thanksgiving = models.DecimalField('感恩奉獻', max_digits=16, decimal_places=2, default=0.0)
    building = models.DecimalField('建築奉獻', max_digits=16, decimal_places=2, default=0.0)
    planting = models.DecimalField('植堂奉獻', max_digits=16, decimal_places=2, default=0.0)
    designated = models.DecimalField('指定奉獻', max_digits=16, decimal_places=2, default=0.0)
    mission = models.DecimalField('宣教&大陸奉獻', max_digits=16, decimal_places=2, default=0.0)
    galilee = models.DecimalField('加利利基金', max_digits=16, decimal_places=2, default=0.0)
    timothy = models.DecimalField('提摩太基金', max_digits=16, decimal_places=2, default=0.0)
    kingdom = models.DecimalField('國度基金', max_digits=16, decimal_places=2, default=0.0)
    venue = models.DecimalField('場地費收入', max_digits=16, decimal_places=2, default=0.0)
    spring = models.DecimalField('新春(免填)', max_digits=16, decimal_places=2, default=0.0)
    other = models.DecimalField('其他', max_digits=16, decimal_places=2, default=0.0)
    project = models.DecimalField('專案(免填)', max_digits=16, decimal_places=2, default=0.0)
    total = models.DecimalField('合計', max_digits=16, decimal_places=2, default=0.0)

    class Meta:
        db_table = 'annual_offerings'
        ordering = ['-year']
        verbose_name = '年度奉獻統計'
        verbose_name_plural = '年度奉獻統計'

    def __str__(self):
        return f'{self.year}年 - 奉獻總計: {self.total}'
