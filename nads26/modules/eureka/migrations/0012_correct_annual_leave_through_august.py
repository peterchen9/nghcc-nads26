from datetime import date

from django.db import migrations


USED_DAYS_THROUGH_AUGUST = {
    '林明月': 0,
    '董德官': 0,
    '羅明珠': 25,
    '周玉筍': 0,
    '何宜庭': 1,
    '鄭仲甫': 0,
    '張慕聖': 3.5,
    '趙沐恩': 2,
    '陳囿余': 0,
    '謝淑慧': 7.5,
    '林文正': 6.5,
    '黃美美': 5.5,
    '張惠萍': 4,
    '陳依蓮': 3,
    '楊宗英': 3,
    '施方正': 8.5,
    '郭慧芝': 3.5,
    '蔡文秀': 4,
    '陳潘傳': 0,
}

PREVIOUS_USED_DAYS = {
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


def set_balances(apps, values, tracking_start):
    StaffInfo = apps.get_model('eureka', 'StaffInfo')
    existing_names = set(
        StaffInfo.objects.filter(name__in=values).values_list('name', flat=True)
    )
    if not existing_names:
        return
    if existing_names != set(values):
        missing = sorted(set(values) - existing_names)
        raise RuntimeError(f'Missing StaffInfo rows: {missing}')
    for name, used_days in values.items():
        matches = StaffInfo.objects.filter(name=name)
        if matches.count() != 1:
            raise RuntimeError(f'Expected exactly one StaffInfo row for {name}')
        matches.update(
            annual_leave_used_base=used_days,
            annual_leave_used_base_year=2026,
            annual_leave_tracking_start=tracking_start,
        )


def apply_correction(apps, schema_editor):
    set_balances(apps, USED_DAYS_THROUGH_AUGUST, date(2026, 8, 31))


def reverse_correction(apps, schema_editor):
    set_balances(apps, PREVIOUS_USED_DAYS, date(2026, 8, 14))


class Migration(migrations.Migration):
    dependencies = [
        ('eureka', '0011_staffinfo_annual_leave_opening_balance'),
    ]

    operations = [
        migrations.RunPython(apply_correction, reverse_correction),
    ]
