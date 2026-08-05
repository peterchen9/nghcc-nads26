from django.db import migrations

def add_finance_menu_items(apps, schema_editor):
    MenuItem = apps.get_model('menu', 'MenuItem')
    try:
        parent = MenuItem.objects.get(title='財會', parent=None)
    except MenuItem.DoesNotExist:
        parent = MenuItem.objects.create(
            title='財會',
            route='',
            icon='💰',
            order=120,
            roles='*',
            is_active=True
        )

    items_to_add = [
        {'title': '預算表維護', 'route': '/finance/budget/', 'order': 1},
        {'title': '銀行帳戶結餘表', 'route': '/finance/bank-balances/', 'order': 2},
        {'title': '基金與團契款餘額', 'route': '/finance/fund-fellowship-balances/', 'order': 3},
        {'title': '奉獻金額與人數統計', 'route': '/finance/offering-statistics/', 'order': 4},
    ]

    for item in items_to_add:
        MenuItem.objects.get_or_create(
            title=item['title'],
            parent=parent,
            defaults={
                'route': item['route'],
                'order': item['order'],
                'roles': '*',
                'is_active': True
            }
        )

def remove_finance_menu_items(apps, schema_editor):
    MenuItem = apps.get_model('menu', 'MenuItem')
    MenuItem.objects.filter(
        title__in=['預算表維護', '銀行帳戶結餘表', '基金與團契款餘額', '奉獻金額與人數統計'],
        parent__title='財會'
    ).delete()

class Migration(migrations.Migration):

    dependencies = [
        ('menu', '0002_add_liturgy_menu_items'),
    ]

    operations = [
        migrations.RunPython(add_finance_menu_items, remove_finance_menu_items),
    ]
