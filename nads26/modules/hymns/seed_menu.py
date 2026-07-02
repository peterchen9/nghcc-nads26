"""
新增詩歌資料庫選單項目

使用方式:
    python3 manage.py shell < modules/hymns/seed_menu.py
"""
import os
import sys
import django

# 確保 Django 設定載入
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'mysite.settings')

# 如果尚未 setup
try:
    from modules.menu.models import MenuItem
except:
    django.setup()
    from modules.menu.models import MenuItem


def seed_menu():
    """在崇拜禮儀底下新增詩歌資料庫選單"""

    # 找到「崇拜禮儀」父選單，或建立新的
    worship_parent = MenuItem.objects.filter(title__contains='崇拜').first()

    if not worship_parent:
        # 如果沒有崇拜禮儀的父選單，建一個
        worship_parent, created = MenuItem.objects.get_or_create(
            title='崇拜禮儀',
            defaults={
                'route': '',
                'icon': '⛪',
                'order': 10,
                'roles': '*',
            }
        )
        if created:
            print(f'✅ 建立父選單: {worship_parent.title}')
        else:
            print(f'📌 已存在父選單: {worship_parent.title}')

    # 新增或取得詩歌資料庫選單
    hymns_menu, created = MenuItem.objects.get_or_create(
        title='詩歌資料庫',
        defaults={
            'route': '/worship/hymns',
            'icon': '🎵',
            'parent': worship_parent,
            'order': 50,
            'roles': '*',
        }
    )

    if created:
        print(f'✅ 新增選單項目: {hymns_menu.title} (route={hymns_menu.route})')
    else:
        print(f'📌 選單項目已存在: {hymns_menu.title}')
        # 確保路由正確
        if hymns_menu.route != '/worship/hymns':
            hymns_menu.route = '/worship/hymns'
            hymns_menu.save()
            print(f'   已更新路由為: /worship/hymns')


if __name__ == '__main__':
    seed_menu()
else:
    seed_menu()
