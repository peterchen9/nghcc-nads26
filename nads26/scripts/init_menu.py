import os
import sys
import django

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(BASE_DIR)

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'nads26.settings')
django.setup()

from modules.menu.models import MenuItem

# Clear existing items to avoid duplicates or order issues
MenuItem.objects.all().delete()

items = [
    {
        'title': '崇拜禮儀',
        'icon': '⛪',
        'order': 10,
        'children': [
            {'title': '詩歌資料庫', 'route': '/hymns/', 'order': 1},
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
            {'title': '出勤狀態', 'route': '/eureka/attendance/', 'order': 2},
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
            {'title': '場地登記', 'route': '/facility/booking/', 'order': 2},
            {'title': '場地資料維護', 'route': '/facility/rooms/', 'order': 3},
            {'title': '日常維護', 'route': '/facility/maintenance/', 'order': 4},
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
        ]
    },
    {'title': '財會', 'icon': '⚪', 'order': 120},
]

for item_data in items:
    children_data = item_data.pop('children', [])
    parent_item = MenuItem.objects.create(**item_data)
    print(f"Created parent menu: {parent_item.title}")
    for child_data in children_data:
        child_data['parent'] = parent_item
        child_item = MenuItem.objects.create(**child_data)
        print(f"  └── Created child menu: {child_item.title}")
