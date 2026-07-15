class DisableCSRFMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        setattr(request, '_dont_enforce_csrf_checks', True)
        response = self.get_response(request)
        return response

from django.core.exceptions import PermissionDenied
from modules.menu.permissions import find_menu_item_for_path, user_can_access_menu_item

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

            matched_item = find_menu_item_for_path(path)

            if matched_item and not user_can_access_menu_item(request.user, matched_item):
                raise PermissionDenied("您無權存取此頁面。")

        return self.get_response(request)
