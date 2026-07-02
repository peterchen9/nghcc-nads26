from .models import SystemSetting

def settings_processor(request):
    settings_dict = {}
    for s in SystemSetting.objects.all():
        settings_dict[s.key] = s.value
    
    # Defaults if not in DB
    return {
        'site_name': settings_dict.get('site_name', '北門'),
        'home_title': settings_dict.get('home_title', '歡迎回到 北門行政中心'),
        'home_desc': settings_dict.get('home_desc', '這是從 DjangoCMS 移植過來的新系統。我們保留了您熟悉的配色方案，並升級了介面細節，提供更流暢的使用體驗。'),
    }
