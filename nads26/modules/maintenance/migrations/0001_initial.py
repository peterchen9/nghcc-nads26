import django.core.validators
import django.db.models.deletion
import modules.maintenance.models
from decimal import Decimal
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True

    dependencies = [migrations.swappable_dependency(settings.AUTH_USER_MODEL)]

    operations = [
        migrations.CreateModel(
            name='MaintenanceCategory',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('source_id', models.PositiveIntegerField(blank=True, null=True, unique=True)),
                ('name', models.CharField(max_length=120, unique=True)),
                ('notes', models.TextField(blank=True)),
                ('is_active', models.BooleanField(default=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
            ],
            options={'verbose_name': '維護分類', 'verbose_name_plural': '維護分類', 'ordering': ('name', 'id')},
        ),
        migrations.CreateModel(
            name='MaintenanceLocation',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('source_id', models.PositiveIntegerField(blank=True, null=True, unique=True)),
                ('name', models.CharField(max_length=160)),
                ('area', models.CharField(blank=True, max_length=120)),
                ('floor', models.CharField(blank=True, max_length=80)),
                ('notes', models.TextField(blank=True)),
                ('is_active', models.BooleanField(default=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
            ],
            options={'verbose_name': '維護地點', 'verbose_name_plural': '維護地點', 'ordering': ('name', 'floor', 'id')},
        ),
        migrations.CreateModel(
            name='MaintenanceVendor',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('source_id', models.PositiveIntegerField(blank=True, null=True, unique=True)),
                ('name', models.CharField(max_length=200)),
                ('category', models.CharField(blank=True, max_length=120)),
                ('contact', models.CharField(blank=True, max_length=120)),
                ('mobile_phone', models.CharField(blank=True, max_length=60)),
                ('company_phone', models.CharField(blank=True, max_length=60)),
                ('email', models.EmailField(blank=True, max_length=254)),
                ('line', models.CharField(blank=True, max_length=120)),
                ('address', models.CharField(blank=True, max_length=300)),
                ('tax_id', models.CharField(blank=True, max_length=30)),
                ('bank_name', models.CharField(blank=True, max_length=120)),
                ('bank_branch', models.CharField(blank=True, max_length=120)),
                ('bank_account_name', models.CharField(blank=True, max_length=160)),
                ('bank_account_number', models.CharField(blank=True, max_length=80)),
                ('notes', models.TextField(blank=True)),
                ('is_active', models.BooleanField(default=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
            ],
            options={'verbose_name': '維護廠商', 'verbose_name_plural': '維護廠商', 'ordering': ('name', 'id')},
        ),
        migrations.CreateModel(
            name='MaintenanceRecord',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('source_id', models.PositiveIntegerField(blank=True, null=True, unique=True)),
                ('maintenance_date', models.DateField(db_index=True)),
                ('type', models.CharField(choices=[('GENERAL', '一般維護'), ('EMERGENCY', '緊急維護'), ('SCHEDULED', '定期維護')], db_index=True, default='GENERAL', max_length=30)),
                ('handler', models.CharField(max_length=160)),
                ('vendor_representative', models.CharField(blank=True, max_length=160)),
                ('issue', models.TextField()),
                ('result', models.TextField(blank=True)),
                ('status', models.CharField(choices=[('PENDING', '待處理'), ('IN_PROGRESS', '處理中'), ('COMPLETED', '已完成'), ('WAITING_QUOTE', '待報價'), ('WAITING_CONSTRUCTION', '待施工'), ('CANCELLED', '取消')], db_index=True, default='PENDING', max_length=40)),
                ('cost', models.DecimalField(decimal_places=2, default=0, max_digits=12, validators=[django.core.validators.MinValueValidator(0)])),
                ('notes', models.TextField(blank=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('category', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='records', to='maintenance.maintenancecategory')),
                ('created_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='created_maintenance_records', to=settings.AUTH_USER_MODEL)),
                ('location', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='records', to='maintenance.maintenancelocation')),
                ('vendor', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='records', to='maintenance.maintenancevendor')),
            ],
            options={'verbose_name': '維護紀錄', 'verbose_name_plural': '維護紀錄', 'ordering': ('-maintenance_date', '-id')},
        ),
        migrations.CreateModel(
            name='MaintenanceAttachment',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('source_key', models.CharField(blank=True, max_length=255, null=True, unique=True)),
                ('type', models.CharField(choices=[('ONSITE', '現場照片'), ('QUOTE', '報價單'), ('RECEIPT', '發票／收據'), ('OTHER', '其他附件')], default='OTHER', max_length=30)),
                ('file', models.FileField(upload_to=modules.maintenance.models.attachment_upload_to)),
                ('original_name', models.CharField(max_length=255)),
                ('mime_type', models.CharField(blank=True, max_length=120)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('record', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='attachments', to='maintenance.maintenancerecord')),
            ],
            options={'verbose_name': '維護附件', 'verbose_name_plural': '維護附件', 'ordering': ('type', 'id')},
        ),
        migrations.AddConstraint(
            model_name='maintenancelocation',
            constraint=models.UniqueConstraint(fields=('name', 'area', 'floor'), name='uniq_maintenance_location'),
        ),
        migrations.AddIndex(
            model_name='maintenancevendor',
            index=models.Index(fields=['name'], name='maint_vendor_name_idx'),
        ),
        migrations.AddIndex(
            model_name='maintenancerecord',
            index=models.Index(fields=['status', 'maintenance_date'], name='maint_status_date_idx'),
        ),
        migrations.AddIndex(
            model_name='maintenancerecord',
            index=models.Index(fields=['category', 'maintenance_date'], name='maint_cat_date_idx'),
        ),
    ]
