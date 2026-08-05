from django.db import migrations, models


PAGE_CATEGORY_MAP = {
    'staff-special-reserve': (
        '人事薪資', '全職同工', '董執團隊', '特別計畫', '預備金', '國度基金',
    ),
    'administration': ('行政部',),
    'worship': ('崇拜部',),
    'education': ('教育部',),
    'mission': ('宣教部',),
    'care': ('關懷部',),
    'counseling': ('輔導部',),
    'technology': ('科技服務部',),
    'gospel': ('重修舊好志工團', '伯利恆糧食之家\n(BLH)'),
    'pastoral-one': (
        '牧區處\nPA', '二魚', '多多牧區', '清一牧區', '清二牧區', '幸福牧區',
        '百合A區', '百合B區', '百合C區', '橄欖樹牧區', '青草地牧區',
        '青橄欖', '房角石牧區',
    ),
    'pastoral-two': (
        'young牧區', '兒童牧區', '百基拉牧區', '三一牧區', '蒙愛查經團契',
        '弟兄會', '加樂團契', '蒙恩團契',
    ),
}


def assign_existing_page_groups(apps, schema_editor):
    BudgetItem = apps.get_model('budget', 'BudgetItem')
    for page_group, categories in PAGE_CATEGORY_MAP.items():
        BudgetItem.objects.filter(category__in=categories).update(page_group=page_group)


def reset_page_groups(apps, schema_editor):
    BudgetItem = apps.get_model('budget', 'BudgetItem')
    BudgetItem.objects.update(page_group='staff-special-reserve')


class Migration(migrations.Migration):

    dependencies = [
        ('budget', '0005_annualoffering_monthlyoffering'),
    ]

    operations = [
        migrations.AddField(
            model_name='budgetitem',
            name='page_group',
            field=models.CharField(
                choices=[
                    ('staff-special-reserve', '同工-特別-預備'),
                    ('administration', '行政'),
                    ('worship', '崇拜'),
                    ('education', '教育'),
                    ('mission', '宣教'),
                    ('care', '關懷'),
                    ('counseling', '輔導'),
                    ('technology', '科技'),
                    ('gospel', '福音'),
                    ('pastoral-one', '牧區一'),
                    ('pastoral-two', '牧區二'),
                ],
                db_index=True,
                default='staff-special-reserve',
                max_length=40,
                verbose_name='所屬分頁',
            ),
        ),
        migrations.RunPython(assign_existing_page_groups, reset_page_groups),
    ]
