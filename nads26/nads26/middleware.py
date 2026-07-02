class DisableCSRFMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        setattr(request, '_dont_enforce_csrf_checks', True)
        response = self.get_response(request)
        return response

from django.core.exceptions import PermissionDenied
from modules.menu.models import MenuItem

class MenuPermissionMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        path = request.path
        
        # 1. Skip system paths, static files, uploads, and admin panels
        if (path.startswith('/admin/') or 
            path.startswith('/ckeditor/') or 
            path.startswith('/static/') or 
            path.startswith('/media/')):
            if path.startswith('/admin/') and not path.startswith('/admin/login/') and not path.startswith('/admin/logout/') and request.user.is_authenticated and not request.user.is_superuser:
                from django.shortcuts import redirect
                return redirect('/')
            return self.get_response(request)

        # 2. Skip home page, accounts auth paths, and user management (handled inside views)
        if (path == '/' or 
            path.startswith('/users/') or 
            path.startswith('/accounts/')):
            return self.get_response(request)

        # 3. Restrict other app paths for authenticated, non-superuser users
        if request.user.is_authenticated:
            if request.user.is_superuser:
                return self.get_response(request)

            # Get all active MenuItems with routes
            menu_items = MenuItem.objects.filter(is_active=True).exclude(route='')
            
            # Match path against app routes
            # Sort routes descending by length so we match the most specific (longest) route first
            matched_item = None
            for item in sorted(menu_items, key=lambda x: len(x.route), reverse=True):
                route = item.route
                if not route.endswith('/'):
                    route += '/'
                test_path = path if path.endswith('/') else (path + '/')

                if test_path.startswith(route) or path == item.route:
                    matched_item = item
                    break

            if matched_item:
                allowed_ids = request.user.profile.allowed_menu_items.values_list('id', flat=True)
                if matched_item.id not in allowed_ids:
                    raise PermissionDenied("您無權存取此頁面。")

        return self.get_response(request)

