# Generated for budget maintenance feature.
from decimal import Decimal

from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name='BudgetItem',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('category', models.CharField(blank=True, default='', max_length=120, verbose_name='分類')),
                ('budget_code', models.CharField(blank=True, db_index=True, default='', max_length=60, verbose_name='2026預算代號')),
                ('ministry', models.CharField(blank=True, default='', max_length=200, verbose_name='事工')),
                ('annual_goal', models.TextField(blank=True, default='', verbose_name='年度目標')),
                ('strategy_plan', models.TextField(blank=True, default='', verbose_name='策略&執行計畫')),
                ('activity_budget', models.TextField(blank=True, default='', verbose_name='活動與預算')),
                ('lead_pastor', models.CharField(blank=True, default='', max_length=120, verbose_name='主責牧者')),
                ('budget_2026', models.DecimalField(blank=True, decimal_places=2, max_digits=14, null=True, verbose_name='2026預算')),
                ('accounting_subject', models.CharField(blank=True, default='', max_length=120, verbose_name='會計科目')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
            ],
            options={
                'verbose_name': '預算項目',
                'verbose_name_plural': '預算項目',
                'db_table': 'budget_items',
                'ordering': ['id'],
            },
        ),
    ]
