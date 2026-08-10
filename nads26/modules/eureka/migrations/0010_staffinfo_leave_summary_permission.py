from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ('eureka', '0009_pastoraloverseer_pastoralsection_pastoralgroup'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='staffinfo',
            options={
                'db_table': 'staff_info',
                'ordering': ['staff_id'],
                'permissions': [
                    ('view_staff_leave_summary', '可查看人事休假總覽'),
                ],
                'verbose_name': '同工資料',
                'verbose_name_plural': '同工資料',
            },
        ),
    ]
