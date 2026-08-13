import os
import sys
import django
from django.db import transaction

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(BASE_DIR)

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'nads26.settings')
django.setup()

from modules.menu.models import MenuItem

items = [
    {
        'title': '崇拜禮儀',
        'icon': '⛪',
        'order': 10,
        'children': [
            {'title': '詩歌資料庫', 'route': '/hymns/', 'order': 1},
            {'title': '洗禮', 'route': '/worship/baptism/', 'order': 2},
            {'title': '聖餐禮', 'route': '/worship/communion/', 'order': 3},
            {'title': '婚禮', 'route': '/worship/wedding/', 'order': 4},
            {'title': '安息禮拜', 'route': '/worship/funeral/', 'order': 5},
        ]
    },
    {
        'title': '關懷',
        'icon': '⚪',
        'order': 30,
        'children': [
            {'title': 'Eureka!找人', 'route': '/eureka/', 'order': 1},
            {'title': '牧區小組', 'route': '/eureka/pastoral/', 'order': 2},
            {'title': '新朋友登記', 'route': '/eureka/add/', 'order': 3},
            {'title': '搜名單', 'route': '/eureka/modify/', 'order': 4},
            {'title': '牧養報告', 'route': '/facility/pastoral-reports/', 'order': 5},
        ]
    },
    {
        'title': '同工',
        'icon': '💼',
        'order': 40,
        'children': [
            {'title': '休假表', 'route': '/staff/leaves/', 'order': 1},
            {'title': '場地登記', 'route': '/facility/booking/', 'order': 2},
            {'title': '辦公室座位', 'route': '/eureka/seats/', 'order': 3},
            {'title': '請款單', 'route': '/staff/expense-claims/', 'order': 4},
            {'title': '行事曆', 'route': '/staff/calendar/', 'order': 5},
        ]
    },
    {
        'title': '場地設施',
        'icon': '🏢',
        'order': 70,
        'children': [
            {'title': '用電監測', 'route': '/facility/power/', 'order': 1},
            {'title': '場地資料維護', 'route': '/facility/rooms/', 'order': 2},
            {'title': '日常維護', 'route': '/facility/maintenance/', 'order': 3},
            {'title': '定期維護', 'route': '/facility/periodic-maintenance/', 'order': 4},
            {'title': '定期維護回報', 'route': '/facility/periodic-maintenance/report/', 'order': 5},
            {'title': '教室檢查', 'route': '/facility/classroom-inspection/', 'order': 6},
        ],
    },
    {
        'title': '工具',
        'icon': '🔧',
        'order': 80,
        'children': [
            {'title': '網路影音下載', 'route': '/webav/', 'order': 1},
        ]
    },
    {
        'title': '檔案中心',
        'icon': '📁',
        'order': 85,
        'children': [
            {'title': '同工參考資料', 'route': '/file-center/staff-reference/', 'order': 1},
        ]
    },
    {
        'title': '資訊網路',
        'icon': '⚪',
        'order': 90,
        'children': [
            {'title': '區網Hosts', 'route': '/facility/lan-hosts/', 'order': 1},
            {'title': '無線網路', 'route': '/facility/wlan-aps/', 'order': 2},
        ],
    },
    {
        'title': '管理員',
        'icon': '🛡️',
        'order': 110,
        'children': [
            {'title': '使用者管理', 'route': '/users/', 'order': 1},
            {'title': '同工資料', 'route': '/eureka/staff/', 'order': 2},
            {'title': '出勤狀態', 'route': '/eureka/attendance/', 'order': 3},
        ]
    },
    {
        'title': '財會',
        'icon': '💰',
        'order': 120,
        'children': [
            {'title': '預算表維護', 'route': '/finance/budget/', 'order': 1},
            {'title': '銀行帳戶結餘表', 'route': '/finance/bank-balances/', 'order': 2},
            {'title': '基金與團契款餘額', 'route': '/finance/fund-fellowship-balances/', 'order': 3},
            {'title': '奉獻金額與人數統計', 'route': '/finance/offering-statistics/', 'order': 4},
            {'title': '請款/自動扣繳單', 'route': '/finance/auto-debit-claims/', 'order': 5},
        ]
    },
]

@transaction.atomic
def sync_menu(menu_items=items):
    """Synchronize declared menus without deleting permission relations."""
    for item in menu_items:
        parent_defaults = {
            key: value for key, value in item.items() if key != 'children'
        }
        parent_title = parent_defaults.pop('title')
        parent_item, parent_created = MenuItem.objects.update_or_create(
            title=parent_title,
            parent=None,
            defaults=parent_defaults,
        )
        action = 'Created' if parent_created else 'Updated'
        print(f"{action} parent menu: {parent_item.title}")

        for child in item.get('children', []):
            child_defaults = dict(child)
            route = child_defaults.pop('route')
            child_defaults['parent'] = parent_item
            child_item, child_created = MenuItem.objects.update_or_create(
                route=route,
                defaults=child_defaults,
            )
            action = 'Created' if child_created else 'Updated'
            print(f"  └── {action} child menu: {child_item.title}")


if __name__ == '__main__':
    sync_menu()
