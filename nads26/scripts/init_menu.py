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
    {'title': '聚會活動', 'icon': '🎵', 'order': 20},
    {
        'title': '關懷',
        'icon': '⚪',
        'order': 30,
        'children': [
            {'title': 'Eureka!找人', 'route': '/eureka/', 'order': 1},
            {'title': '牧區小組', 'route': '/eureka/pastoral/', 'order': 2},
            {'title': '新朋友登記', 'route': '/eureka/add/', 'order': 3},
            {'title': '搜名單', 'route': '/eureka/modify/', 'order': 4},
        ]
    },
    {
        'title': '同工',
        'icon': '💼',
        'order': 40,
        'children': [
            {'title': '出勤狀態', 'route': '/eureka/attendance/', 'order': 1},
            {'title': '辦公室座位', 'route': '/eureka/seats/', 'order': 2},
        ]
    },
    {'title': '交通', 'icon': '🚗', 'order': 50},
    {'title': '教育', 'icon': '🎓', 'order': 60},
    {'title': '場地設施', 'icon': '🏢', 'order': 70},
    {
        'title': '工具',
        'icon': '🔧',
        'order': 80,
        'children': [
            {'title': '網路影音下載', 'route': '/webav/', 'order': 1},
        ]
    },
    {'title': '資訊網路', 'icon': '⚪', 'order': 90},
    {'title': '報到系統', 'icon': '📅', 'order': 100},
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
    {'title': '參考資料', 'icon': '📱', 'order': 130},
    {'title': '奉獻', 'icon': '⚪', 'order': 140},
]

for item_data in items:
    children_data = item_data.pop('children', [])
    parent_item = MenuItem.objects.create(**item_data)
    print(f"Created parent menu: {parent_item.title}")
    for child_data in children_data:
        child_data['parent'] = parent_item
        child_item = MenuItem.objects.create(**child_data)
        print(f"  └── Created child menu: {child_item.title}")
