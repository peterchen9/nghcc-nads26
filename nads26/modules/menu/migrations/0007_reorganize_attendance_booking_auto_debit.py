from django.db import migrations


ATTENDANCE_ROUTE = '/eureka/attendance/'
BOOKING_ROUTE = '/facility/booking/'
AUTO_DEBIT_ROUTE = '/finance/auto-debit-claims/'


def reorganize_menu_items(apps, schema_editor):
    MenuItem = apps.get_model('menu', 'MenuItem')
    parent_specs = {
        '同工': ('💼', 40),
        '管理員': ('🛡️', 110),
        '場地設施': ('🏢', 70),
        '財會': ('💰', 120),
    }
    parents = {}
    for title, (icon, order) in parent_specs.items():
        parents[title], _ = MenuItem.objects.get_or_create(
            title=title,
            parent=None,
            defaults={
                'route': '', 'icon': icon, 'order': order,
                'roles': '*', 'is_active': True,
            },
        )
    MenuItem.objects.update_or_create(
        route=ATTENDANCE_ROUTE,
        defaults={
            'title': '出勤狀態', 'parent': parents['管理員'], 'order': 3,
            'roles': '*', 'is_active': True,
        },
    )
    MenuItem.objects.update_or_create(
        route=BOOKING_ROUTE,
        defaults={
            'title': '場地登記', 'parent': parents['同工'], 'order': 2,
            'roles': '*', 'is_active': True,
        },
    )
    MenuItem.objects.update_or_create(
        route=AUTO_DEBIT_ROUTE,
        defaults={
            'title': '請款/自動扣繳單', 'parent': parents['財會'], 'order': 5,
            'roles': '*', 'is_active': True,
        },
    )


def restore_previous_menu_layout(apps, schema_editor):
    MenuItem = apps.get_model('menu', 'MenuItem')
    parents = {title: MenuItem.objects.get(title=title, parent=None)
               for title in ('同工', '場地設施', '財會')}
    MenuItem.objects.filter(route=ATTENDANCE_ROUTE).update(
        parent=parents['同工'], order=2
    )
    MenuItem.objects.filter(route=BOOKING_ROUTE).update(
        parent=parents['場地設施'], order=2
    )
    MenuItem.objects.filter(route=AUTO_DEBIT_ROUTE).update(
        title='自動扣繳單', parent=parents['財會'], order=5
    )


class Migration(migrations.Migration):
    dependencies = [
        ('menu', '0006_add_auto_debit_claim_menu'),
    ]

    operations = [
        migrations.RunPython(reorganize_menu_items, restore_previous_menu_layout),
    ]
