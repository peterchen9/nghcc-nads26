from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from .models import Page

def page_detail(request, slug='home'):
    # Default to 'home' if no slug is provided
    page = Page.objects.filter(slug=slug, is_active=True).first()
    return render(request, 'pages/page_detail.html', {'page': page, 'slug': slug})

@login_required
def edit_home(request):
    if not request.user.is_superuser:
        raise PermissionDenied("您無權進行此操作。")
    page, created = Page.objects.get_or_create(
        slug='home',
        defaults={
            'title': '首頁',
            'content': '<h1>歡迎使用北門行政平台</h1>',
            'is_active': True
        }
    )
    return redirect(f'/admin/pages/page/{page.id}/change/')

@login_required
def qr_generator(request):
    return render(request, 'pages/qr_generator.html')

from .models import MediaCollection
import paramiko
import mimetypes
import tempfile
import subprocess
import os
from django.http import FileResponse, Http404

class SFTPFileWrapper:
    def __init__(self, sftp_file, sftp_client, transport):
        self.sftp_file = sftp_file
        self.sftp_client = sftp_client
        self.transport = transport
        
    def read(self, *args, **kwargs):
        return self.sftp_file.read(*args, **kwargs)
        
    def seek(self, *args, **kwargs):
        return self.sftp_file.seek(*args, **kwargs)
        
    def tell(self):
        return self.sftp_file.tell()
        
    def close(self):
        try:
            self.sftp_file.close()
        finally:
            try:
                self.sftp_client.close()
            finally:
                self.transport.close()

@login_required
def media_collection(request):
    query = request.GET.get('q', '').strip()
    files = MediaCollection.objects.all()
    if query:
        from django.db.models import Q
        files = files.filter(Q(filename__icontains=query) | Q(path__icontains=query))
    files = files.order_by('path')
    for f in files:
        gb = f.size / 1073741824.0
        if gb == 0:
            f.size_gb_str = "0.000 GB"
        elif gb < 0.001:
            f.size_gb_str = f"{gb:.4f} GB"
        else:
            f.size_gb_str = f"{gb:.3f} GB"
        f.size_gb = gb
    return render(request, 'pages/media_collection.html', {'files': files, 'query': query})

@login_required
def media_download(request, pk):
    media = get_object_or_404(MediaCollection, pk=pk)
    try:
        transport = paramiko.Transport(('192.168.16.127', 22))
        transport.connect(username='peter', password='Gala1051#')
        sftp = paramiko.SFTPClient.from_transport(transport)
        sftp_file = sftp.open(media.path, 'rb')
        wrapped_file = SFTPFileWrapper(sftp_file, sftp, transport)
        
        content_type = mimetypes.guess_type(media.filename)[0] or 'application/octet-stream'
        response = FileResponse(
            wrapped_file,
            content_type=content_type,
            as_attachment=True,
            filename=media.filename
        )
        return response
    except Exception as e:
        raise Http404(f"無法從 NAS 取得檔案: {e}")

@login_required
def media_edit_download(request, pk):
    media = get_object_or_404(MediaCollection, pk=pk)
    start_time = request.GET.get('start', '00:00:00').strip()
    end_time = request.GET.get('end', '').strip()
    custom_name = request.GET.get('name', '').strip()
    
    if not custom_name:
        custom_name = media.filename
    else:
        orig_ext = os.path.splitext(media.filename)[1]
        if not custom_name.endswith(orig_ext):
            custom_name += orig_ext

    try:
        transport = paramiko.Transport(('192.168.16.127', 22))
        transport.connect(username='peter', password='Gala1051#')
        sftp = paramiko.SFTPClient.from_transport(transport)
        
        temp_dir = tempfile.mkdtemp()
        temp_input = os.path.join(temp_dir, 'input' + os.path.splitext(media.filename)[1])
        temp_output = os.path.join(temp_dir, 'output' + os.path.splitext(media.filename)[1])
        
        sftp.get(media.path, temp_input)
        sftp.close()
        transport.close()
        
        cmd = ['ffmpeg', '-y', '-ss', start_time]
        if end_time:
            cmd.extend(['-to', end_time])
        cmd.extend(['-i', temp_input, '-c', 'copy', temp_output])
        
        p = subprocess.Popen(cmd, stderr=subprocess.PIPE, stdout=subprocess.PIPE)
        p.communicate()
        
        if p.returncode != 0 or not os.path.exists(temp_output) or os.path.getsize(temp_output) == 0:
            cmd_fallback = ['ffmpeg', '-y', '-ss', start_time]
            if end_time:
                cmd_fallback.extend(['-to', end_time])
            cmd_fallback.extend(['-i', temp_input, temp_output])
            p_fallback = subprocess.Popen(cmd_fallback, stderr=subprocess.PIPE, stdout=subprocess.PIPE)
            p_fallback.communicate()
            
        if not os.path.exists(temp_output):
            raise Http404("剪輯處理失敗，無法產生輸出檔案。")
            
        content_type = mimetypes.guess_type(custom_name)[0] or 'application/octet-stream'
        response = FileResponse(
            open(temp_output, 'rb'),
            content_type=content_type,
            as_attachment=True,
            filename=custom_name
        )
        
        original_streaming = response.streaming_content
        def cleanup():
            try:
                yield from original_streaming
            finally:
                try:
                    if os.path.exists(temp_input): os.remove(temp_input)
                    if os.path.exists(temp_output): os.remove(temp_output)
                    if os.path.exists(temp_dir): os.rmdir(temp_dir)
                except Exception:
                    pass
        response.streaming_content = cleanup()
        return response
    except Exception as e:
        raise Http404(f"剪輯下載發生錯誤: {e}")


@login_required
def planned_feature(request):
    return render(request, 'planned.html')
