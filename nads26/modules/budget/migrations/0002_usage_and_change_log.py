# Generated for budget usage and audit log fields.
from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('budget', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='budgetitem',
            name='used_amount',
            field=models.DecimalField(blank=True, decimal_places=2, max_digits=14, null=True, verbose_name='已使用金額'),
        ),
        migrations.CreateModel(
            name='BudgetChangeLog',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('action', models.CharField(choices=[('create', '新增'), ('update', '修改'), ('import', '匯入'), ('delete', '刪除')], max_length=20, verbose_name='動作')),
                ('before_data', models.JSONField(blank=True, null=True, verbose_name='修改前內容')),
                ('after_data', models.JSONField(blank=True, null=True, verbose_name='修改後內容')),
                ('changed_by_code', models.CharField(blank=True, default='', max_length=150, verbose_name='修改者代號')),
                ('ip_address', models.GenericIPAddressField(blank=True, null=True, verbose_name='IP')),
                ('mac_address', models.CharField(blank=True, default='', max_length=32, verbose_name='MAC')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='修改日期時間')),
                ('budget_item', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='change_logs', to='budget.budgetitem')),
                ('changed_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'verbose_name': '預算修改紀錄',
                'verbose_name_plural': '預算修改紀錄',
                'db_table': 'budget_change_logs',
                'ordering': ['-created_at', '-id'],
            },
        ),
    ]
