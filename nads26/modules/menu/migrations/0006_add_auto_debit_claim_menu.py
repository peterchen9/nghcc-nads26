from django.db import migrations


AUTO_DEBIT_ROUTE = '/finance/auto-debit-claims/'


def add_auto_debit_claim_menu(apps, schema_editor):
    MenuItem = apps.get_model('menu', 'MenuItem')
    finance_parent, _ = MenuItem.objects.get_or_create(
        title='財會',
        parent=None,
        defaults={
            'route': '',
            'icon': '💰',
            'order': 120,
            'roles': '*',
            'is_active': True,
        },
    )
    MenuItem.objects.update_or_create(
        route=AUTO_DEBIT_ROUTE,
        defaults={
            'title': '自動扣繳單',
            'parent': finance_parent,
            'order': 5,
            'roles': '*',
            'is_active': True,
        },
    )


def preserve_auto_debit_claim_menu(apps, schema_editor):
    # MenuItem IDs are permission relations. Reversing this migration must not
    # delete or recreate the row and accidentally remove user access grants.
    return None


class Migration(migrations.Migration):
    dependencies = [
        ('menu', '0005_add_education_menu_items'),
    ]

    operations = [
        migrations.RunPython(
            add_auto_debit_claim_menu,
            preserve_auto_debit_claim_menu,
        ),
    ]
