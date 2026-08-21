from datetime import date

from django.db import migrations, models


OPENING_USED_DAYS = {
    '林明月': 0,
    '董德官': 0,
    '羅明珠': 21,
    '周玉筍': 4,
    '何宜庭': 1,
    '鄭仲甫': 0.5,
    '張慕聖': 2.5,
    '趙沐恩': 2,
    '陳囿余': 0,
    '謝淑慧': 7.5,
    '林文正': 6.5,
    '黃美美': 5.5,
    '張惠萍': 4,
    '陳依蓮': 4,
    '楊宗英': 8.5,
    '施方正': 4,
    '郭慧芝': 3.5,
    '蔡文秀': 5,
    '陳潘傳': 0,
}

SHORT_NAMES = {
    '林明月': '明月', '董德官': '德官', '羅明珠': '明珠', '周玉筍': '玉筍',
    '何宜庭': '宜庭', '鄭仲甫': '仲甫', '張慕聖': '慕聖', '趙沐恩': '沐恩',
    '陳囿余': '囿余', '謝淑慧': '小慧', '林文正': '文正', '黃美美': '美美',
    '張惠萍': '惠萍', '陳依蓮': '依蓮', '楊宗英': '宗英', '施方正': '方正',
    '郭慧芝': '慧芝', '蔡文秀': '文秀', '陳潘傳': '彼得陳',
}


def load_opening_balances(apps, schema_editor):
    StaffInfo = apps.get_model('eureka', 'StaffInfo')
    for name, used_days in OPENING_USED_DAYS.items():
        StaffInfo.objects.filter(name__in=[name, SHORT_NAMES[name]]).update(
            annual_leave_used_base=used_days,
            annual_leave_used_base_year=2026,
            annual_leave_tracking_start=date(2026, 8, 14),
        )


def clear_opening_balances(apps, schema_editor):
    StaffInfo = apps.get_model('eureka', 'StaffInfo')
    StaffInfo.objects.filter(annual_leave_used_base_year=2026).update(
        annual_leave_used_base=0,
        annual_leave_used_base_year=None,
        annual_leave_tracking_start=None,
    )


class Migration(migrations.Migration):
    dependencies = [
        ('eureka', '0010_staffinfo_leave_summary_permission'),
    ]

    operations = [
        migrations.AddField(
            model_name='staffinfo',
            name='annual_leave_tracking_start',
            field=models.DateField(blank=True, null=True, verbose_name='特休續計起日'),
        ),
        migrations.AddField(
            model_name='staffinfo',
            name='annual_leave_used_base',
            field=models.FloatField(default=0.0, verbose_name='已休特休期初值'),
        ),
        migrations.AddField(
            model_name='staffinfo',
            name='annual_leave_used_base_year',
            field=models.PositiveIntegerField(blank=True, null=True, verbose_name='特休期初值年度'),
        ),
        migrations.RunPython(load_opening_balances, clear_opening_balances),
    ]
