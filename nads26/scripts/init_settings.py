import os
import sys
import django

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(BASE_DIR)

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'nads26.settings')
django.setup()

from modules.accounts.models import SystemSetting

settings = [
    {
        'key': 'site_name',
        'value': '北門',
        'description': '網站名稱 (顯示在側邊欄上方)',
    },
    {
        'key': 'home_title',
        'value': '歡迎回到 北門行政中心',
        'description': '首頁大標題',
    },
    {
        'key': 'home_desc',
        'value': '這是從 DjangoCMS 移植過來的新系統。我們保留了您熟悉的配色方案，並升級了介面細節，提供更流暢的使用體驗。',
        'description': '首頁描述內容',
    },
]

for s_data in settings:
    s, created = SystemSetting.objects.get_or_create(
        key=s_data['key'],
        defaults=s_data
    )
    if created:
        print(f"Created setting: {s.key}")
    else:
        # Update existing to match current view if they exist
        s.description = s_data['description']
        s.save()
        print(f"Setting already exists: {s.key}")
