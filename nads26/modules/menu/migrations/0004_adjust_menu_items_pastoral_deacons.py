from django.db import migrations

def adjust_menu_items(apps, schema_editor):
    MenuItem = apps.get_model('menu', 'MenuItem')

    # 1. Create root menu '牧者'
    pastoral_parent, _ = MenuItem.objects.get_or_create(
        title='牧者',
        parent=None,
        defaults={
            'route': '',
            'icon': '⛪',
            'order': 35,
            'roles': '*',
            'is_active': True
        }
    )

    # 2. Move '牧養報告', '定期維護', '日常維護' under '牧者'
    MenuItem.objects.filter(route='/facility/pastoral-reports/').update(
        parent=pastoral_parent,
        order=1
    )
    MenuItem.objects.filter(route='/facility/periodic-maintenance/').update(
        parent=pastoral_parent,
        order=2
    )
    MenuItem.objects.filter(route='/facility/maintenance/').update(
        parent=pastoral_parent,
        order=3
    )

    # 3. Create root menu '執事會'
    deacons_parent, _ = MenuItem.objects.get_or_create(
        title='執事會',
        parent=None,
        defaults={
            'route': '',
            'icon': '👥',
            'order': 45,
            'roles': '*',
            'is_active': True
        }
    )

    # 4. Create sub-menu items under '執事會'
    MenuItem.objects.get_or_create(
        title='會議紀錄',
        parent=deacons_parent,
        defaults={
            'route': '/board/minutes/',
            'order': 1,
            'roles': '*',
            'is_active': True
        }
    )
    MenuItem.objects.get_or_create(
        title='歷屆執事名單',
        parent=deacons_parent,
        defaults={
            'route': '/board/deacons/',
            'order': 2,
            'roles': '*',
            'is_active': True
        }
    )

def reverse_adjust_menu_items(apps, schema_editor):
    MenuItem = apps.get_model('menu', 'MenuItem')

    # 1. Restore '牧養報告' to parent '關懷'
    try:
        care_parent = MenuItem.objects.get(title='關懷', parent=None)
        MenuItem.objects.filter(route='/facility/pastoral-reports/').update(
            parent=care_parent,
            order=5
        )
    except MenuItem.DoesNotExist:
        pass

    # 2. Restore '定期維護' and '日常維護' to parent '場地設施'
    try:
        facility_parent = MenuItem.objects.get(title='場地設施', parent=None)
        MenuItem.objects.filter(route='/facility/periodic-maintenance/').update(
            parent=facility_parent,
            order=5
        )
        MenuItem.objects.filter(route='/facility/maintenance/').update(
            parent=facility_parent,
            order=4
        )
    except MenuItem.DoesNotExist:
        pass

    # 3. Delete '會議紀錄' and '歷屆執事名單'
    MenuItem.objects.filter(route__in=['/board/minutes/', '/board/deacons/']).delete()

    # 4. Delete '牧者' and '執事會' root menus
    MenuItem.objects.filter(title__in=['牧者', '執事會'], parent=None).delete()


class Migration(migrations.Migration):

    dependencies = [
        ('menu', '0003_add_finance_menu_items'),
    ]

    operations = [
        migrations.RunPython(adjust_menu_items, reverse_adjust_menu_items),
    ]
