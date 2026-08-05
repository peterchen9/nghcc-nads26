import os
import re
import subprocess
from decimal import Decimal
from django.shortcuts import render
from django.http import JsonResponse, FileResponse, HttpResponseBadRequest
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from django.conf import settings
from django.core.exceptions import PermissionDenied
from django.utils import timezone
from .models import FileAnnotation, FileActionLog

def safe_join(base_dir, *paths):
    """
    Safely joins paths ensuring that the result is strictly within base_dir.
    Prevents directory traversal attacks.
    """
    base_path = os.path.abspath(base_dir)
    # If paths is empty or first item is empty, return base_path
    if not paths or not paths[0]:
        return base_path
    
    # Strip leading slashes to prevent absolute path joining
    cleaned_paths = [p.lstrip('/') for p in paths]
    joined_path = os.path.abspath(os.path.join(base_path, *cleaned_paths))
    
    if os.path.commonpath([base_path, joined_path]) != base_path:
        raise PermissionDenied("無權存取此路徑。")
    return joined_path

def get_client_ip(request):
    forwarded = request.META.get('HTTP_X_FORWARDED_FOR', '')
    if forwarded:
        return forwarded.split(',')[0].strip()
    return request.META.get('REMOTE_ADDR', '')

def get_client_mac(ip_address):
    if not ip_address:
        return ''
    commands = [
        ['ip', 'neigh', 'show', ip_address],
        ['arp', '-n', ip_address],
    ]
    for command in commands:
        try:
            result = subprocess.run(command, capture_output=True, text=True, timeout=2)
            match = re.search(r'([0-9a-fA-F]{2}(?::[0-9a-fA-F]{2}){5})', result.stdout)
            if match:
                return match.group(1).lower()
        except Exception:
            continue
    return ''

@login_required
def reference_data_page(request):
    """
    Renders the main Child Labor Reference Data tree page.
    """
    return render(request, 'file_center/reference_data.html')

@login_required
def api_list_directory(request):
    """
    API endpoint to list subdirectories and files under a given path.
    Used for tree lazy loading and displaying right pane file lists.
    """
    relative_path = request.GET.get('path', '').strip()
    root_path = settings.NAS_ROOT_PATH
    
    # Ensure root path exists
    if not os.path.exists(root_path):
        try:
            os.makedirs(root_path, exist_ok=True)
        except Exception as e:
            return JsonResponse({'error': f'無法建立或存取根目錄: {str(e)}'}, status=500)
            
    try:
        target_dir = safe_join(root_path, relative_path)
    except PermissionDenied as e:
        return JsonResponse({'error': str(e)}, status=403)
        
    if not os.path.exists(target_dir):
        return JsonResponse({'error': '目錄不存在。'}, status=404)
        
    if not os.path.isdir(target_dir):
        return JsonResponse({'error': '指定路徑不是一個目錄。'}, status=400)
        
    try:
        entries = os.listdir(target_dir)
    except Exception as e:
        return JsonResponse({'error': f'無法讀取目錄: {str(e)}'}, status=500)
        
    dirs_list = []
    files_list = []
    
    # Read annotations for current sub-items to minimize database queries
    # Build list of relative paths of child entries
    child_rel_paths = []
    for entry in entries:
        child_rel_path = os.path.join(relative_path, entry).replace('\\', '/')
        child_rel_paths.append(child_rel_path)
        
    annotations_map = {
        ann.path: ann.notes 
        for ann in FileAnnotation.objects.filter(path__in=child_rel_paths)
    }
    
    for entry in entries:
        # Skip hidden files
        if entry.startswith('.'):
            continue
            
        full_entry_path = os.path.join(target_dir, entry)
        child_rel_path = os.path.join(relative_path, entry).replace('\\', '/')
        notes = annotations_map.get(child_rel_path, '')
        
        stat = os.stat(full_entry_path)
        mtime = timezone.datetime.fromtimestamp(stat.st_mtime, tz=timezone.get_current_timezone())
        
        item_data = {
            'name': entry,
            'path': child_rel_path,
            'notes': notes,
            'updated_at': mtime.strftime('%Y-%m-%d %H:%M:%S'),
        }
        
        if os.path.isdir(full_entry_path):
            dirs_list.append(item_data)
        else:
            item_data['size'] = stat.st_size
            files_list.append(item_data)
            
    # Sort alphabetically
    dirs_list.sort(key=lambda x: x['name'].lower())
    files_list.sort(key=lambda x: x['name'].lower())
    
    return JsonResponse({
        'path': relative_path,
        'directories': dirs_list,
        'files': files_list
    })

@login_required
def file_download(request):
    """
    Downloads a file and logs the event (user, IP, MAC, GPS coords).
    """
    relative_path = request.GET.get('path', '').strip()
    lat_str = request.GET.get('lat', '').strip()
    lng_str = request.GET.get('lng', '').strip()
    
    if not relative_path:
        return HttpResponseBadRequest("未指定下載路徑。")
        
    root_path = settings.NAS_ROOT_PATH
    try:
        file_path = safe_join(root_path, relative_path)
    except PermissionDenied as e:
        return HttpResponseBadRequest(str(e))
        
    if not os.path.exists(file_path) or not os.path.isfile(file_path):
        return HttpResponseBadRequest("檔案不存在或不是檔案。")
        
    # Get IP and MAC
    ip = get_client_ip(request)
    mac = get_client_mac(ip)
    
    # Get GPS coordinates
    lat = None
    lng = None
    try:
        if lat_str:
            lat = Decimal(lat_str)
        if lng_str:
            lng = Decimal(lng_str)
    except Exception:
        pass
        
    # Log the download action
    FileActionLog.objects.create(
        user=request.user,
        action='download',
        path=relative_path,
        ip_address=ip,
        mac_address=mac,
        latitude=lat,
        longitude=lng
    )
    
    # Serve the file
    response = FileResponse(open(file_path, 'rb'))
    # Set Content-Disposition to download file with original filename
    response['Content-Disposition'] = f'attachment; filename="{os.path.basename(file_path)}"'
    return response

@login_required
@require_POST
def file_upload(request):
    """
    Uploads a file to a directory and logs the event.
    """
    parent_path = request.POST.get('path', '').strip()
    uploaded_file = request.FILES.get('file')
    lat_str = request.POST.get('lat', '').strip()
    lng_str = request.POST.get('lng', '').strip()
    
    if not uploaded_file:
        return JsonResponse({'error': '未提供上傳檔案。'}, status=400)
        
    root_path = settings.NAS_ROOT_PATH
    try:
        target_dir = safe_join(root_path, parent_path)
    except PermissionDenied as e:
        return JsonResponse({'error': str(e)}, status=403)
        
    if not os.path.exists(target_dir) or not os.path.isdir(target_dir):
        return JsonResponse({'error': '目標上傳目錄不存在。'}, status=404)
        
    # Clean filename to avoid path traversal in upload
    filename = os.path.basename(uploaded_file.name)
    target_file_path = os.path.join(target_dir, filename)
    relative_file_path = os.path.join(parent_path, filename).replace('\\', '/')
    
    try:
        with open(target_file_path, 'wb+') as destination:
            for chunk in uploaded_file.chunks():
                destination.write(chunk)
    except Exception as e:
        return JsonResponse({'error': f'儲存檔案失敗: {str(e)}'}, status=500)
        
    # Get IP and MAC
    ip = get_client_ip(request)
    mac = get_client_mac(ip)
    
    # Get GPS coordinates
    lat = None
    lng = None
    try:
        if lat_str:
            lat = Decimal(lat_str)
        if lng_str:
            lng = Decimal(lng_str)
    except Exception:
        pass
        
    # Log the upload action
    FileActionLog.objects.create(
        user=request.user,
        action='upload',
        path=relative_file_path,
        ip_address=ip,
        mac_address=mac,
        latitude=lat,
        longitude=lng
    )
    
    return JsonResponse({'success': True, 'path': relative_file_path})

@login_required
@require_POST
def save_annotation(request):
    """
    Creates or updates notes for a directory or file.
    """
    path = request.POST.get('path', '').strip()
    is_dir_str = request.POST.get('is_directory', '').strip()
    notes = request.POST.get('notes', '').strip()
    
    if not path:
        return JsonResponse({'error': '路徑不能為空。'}, status=400)
        
    is_directory = is_dir_str.lower() in ('true', '1', 'yes')
    
    # Quick sanity check on path traversal
    root_path = settings.NAS_ROOT_PATH
    try:
        safe_join(root_path, path)
    except PermissionDenied as e:
        return JsonResponse({'error': str(e)}, status=403)
        
    annotation, created = FileAnnotation.objects.update_or_create(
        path=path,
        defaults={
            'is_directory': is_directory,
            'notes': notes,
            'updated_by': request.user
        }
    )
    
    return JsonResponse({'success': True, 'path': path, 'notes': notes})
