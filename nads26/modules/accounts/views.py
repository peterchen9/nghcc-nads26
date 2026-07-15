import json
from django.shortcuts import render, get_object_or_404
from django.contrib.auth.models import User
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from modules.menu.models import MenuItem
from modules.menu.permissions import expand_menu_ids, user_can_access_route

def has_user_mgmt_permission(user):
    if not user.is_authenticated:
        return False
    if user.is_superuser:
        return True
    try:
        return user_can_access_route(user, '/users/')
    except Exception:
        return False

def admin_required(view_func):
    def _wrapped_view(request, *args, **kwargs):
        if not has_user_mgmt_permission(request.user):
            raise PermissionDenied("您無權進行此操作。")
        return view_func(request, *args, **kwargs)
    return _wrapped_view

@login_required
@admin_required
def user_list(request):
    users = User.objects.all().select_related('profile').prefetch_related('profile__allowed_menu_items').order_by('id')
    return render(request, 'accounts/user_list.html', {'users': users})

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def app_routes(request):
    if not has_user_mgmt_permission(request.user):
        return Response({'detail': 'Permission denied.'}, status=403)
        
    roots = MenuItem.objects.filter(parent=None, is_active=True).prefetch_related('children').order_by('order', 'id')
    data = []
    for r in roots:
        children_data = []
        for c in r.children.filter(is_active=True).order_by('order', 'id'):
            children_data.append({
                'id': c.id,
                'title': c.title,
                'route': c.route,
            })
        data.append({
            'id': r.id,
            'title': r.title,
            'route': r.route,
            'children': children_data
        })
    return Response(data)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def user_create(request):
    if not has_user_mgmt_permission(request.user):
        return Response({'detail': 'Permission denied.'}, status=403)
        
    username = request.data.get('username', '').strip()
    password = request.data.get('password', '').strip()
    display_name = request.data.get('display_name', '').strip()
    email = request.data.get('email', '').strip()
    department = request.data.get('department', '').strip()
    role = request.data.get('role', '').strip()
    is_active = request.data.get('is_active', True)

    if not username or not password:
        return Response({'error': '帳號與密碼為必填欄位'}, status=400)

    if User.objects.filter(username=username).exists():
        return Response({'error': '此帳號已存在'}, status=400)

    user = User.objects.create_user(
        username=username,
        password=password,
        email=email,
        is_active=is_active,
        is_staff=True
    )
    
    profile = user.profile
    profile.display_name = display_name
    profile.department = department
    profile.role = role
    profile.save()

    return Response({'status': 'success', 'user_id': user.id})

@api_view(['PUT', 'POST'])
@permission_classes([IsAuthenticated])
def user_update(request, pk):
    if not has_user_mgmt_permission(request.user):
        return Response({'detail': 'Permission denied.'}, status=403)
        
    user = get_object_or_404(User, pk=pk)
    
    username = request.data.get('username', '').strip()
    password = request.data.get('password', '').strip()
    display_name = request.data.get('display_name', '').strip()
    email = request.data.get('email', '').strip()
    department = request.data.get('department', '').strip()
    role = request.data.get('role', '').strip()
    is_active = request.data.get('is_active', True)

    if username and username != user.username:
        if User.objects.filter(username=username).exclude(pk=pk).exists():
            return Response({'error': '此帳號已存在'}, status=400)
        user.username = username

    if password:
        user.set_password(password)

    user.email = email
    user.is_active = is_active
    user.is_staff = True
    user.save()

    profile = user.profile
    profile.display_name = display_name
    profile.department = department
    profile.role = role
    profile.save()

    return Response({'status': 'success'})

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def user_set_permissions(request, pk):
    if not has_user_mgmt_permission(request.user):
        return Response({'detail': 'Permission denied.'}, status=403)
        
    user = get_object_or_404(User, pk=pk)
    menu_ids = request.data.get('menu_ids', [])
    
    profile = user.profile
    valid_menu_items = MenuItem.objects.filter(id__in=expand_menu_ids(menu_ids), is_active=True)
    profile.allowed_menu_items.set(valid_menu_items)
    profile.save()

    return Response({
        'status': 'success',
        'menu_ids': list(valid_menu_items.values_list('id', flat=True)),
    })

@api_view(['DELETE', 'POST'])
@permission_classes([IsAuthenticated])
def user_delete(request, pk):
    if not has_user_mgmt_permission(request.user):
        return Response({'detail': 'Permission denied.'}, status=403)
        
    user = get_object_or_404(User, pk=pk)
    if user == request.user:
        return Response({'error': '您不能刪除自己！'}, status=400)
        
    user.delete()
    return Response({'status': 'success'})

# Custom auth views
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.views import (
    PasswordResetView, PasswordResetDoneView,
    PasswordResetConfirmView, PasswordResetCompleteView
)
from django.urls import reverse_lazy
from django.shortcuts import redirect

def custom_login(request):
    if request.user.is_authenticated:
        return redirect('/')
        
    next_url = request.GET.get('next', '/')
    error_msg = None
    
    if request.method == 'POST':
        username = request.POST.get('username', '').strip()
        password = request.POST.get('password', '')
        remember_me = request.POST.get('remember_me') == 'on'
        
        user = authenticate(request, username=username, password=password)
        if user is not None:
            if user.is_active:
                login(request, user)
                if remember_me:
                    request.session.set_expiry(1209600)  # 2 weeks
                else:
                    request.session.set_expiry(0)  # Browser session cookie
                return redirect(next_url)
            else:
                error_msg = "此帳號已被停用。"
        else:
            error_msg = "帳號或密碼錯誤。"
            
    return render(request, 'accounts/login.html', {
        'error_msg': error_msg,
        'next': next_url,
    })

def custom_logout(request):
    logout(request)
    return render(request, 'accounts/logged_out.html')

class CustomPasswordResetView(PasswordResetView):
    template_name = 'accounts/password_reset_form.html'
    success_url = reverse_lazy('password_reset_done')

class CustomPasswordResetDoneView(PasswordResetDoneView):
    template_name = 'accounts/password_reset_done.html'

class CustomPasswordResetConfirmView(PasswordResetConfirmView):
    template_name = 'accounts/password_reset_confirm.html'
    success_url = reverse_lazy('password_reset_complete')

class CustomPasswordResetCompleteView(PasswordResetCompleteView):
    template_name = 'accounts/password_reset_complete.html'
