"""
影音下載 API
整合 yt-dlp，提供影片資訊查詢與下載功能
"""
import os
import re
import tempfile
import mimetypes

from django.http import FileResponse, JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

import yt_dlp


# 暫存下載目錄
DOWNLOAD_DIR = os.path.join(tempfile.gettempdir(), 'humnos_downloads')
os.makedirs(DOWNLOAD_DIR, exist_ok=True)


def _safe_filename(name: str) -> str:
    """移除非法字元並截斷至 100 字元"""
    safe = re.sub(r'[\\/*?:"<>|]', '', name)
    return safe[:100]


def _resolve_facebook_url(url: str) -> tuple[str, str | None]:
    """
    解析 Facebook 網址。如果是分享連結，嘗試追蹤重導向。
    如果重導向後的網址是貼文而非直接影片連結，則返回建議說明。
    """
    if 'facebook.com' not in url:
        return url, None

    import requests
    redirected_url = url
    if '/share/' in url:
        try:
            # 追蹤重導向，不帶 User-Agent 瀏覽器頭以防被 Facebook 阻擋重導向
            r = requests.get(url, allow_redirects=True, timeout=5)
            if r.status_code == 200:
                redirected_url = r.url
        except Exception:
            pass

    # 檢查是否為貼文連結而非影片直接連結
    if any(k in redirected_url for k in ['/posts/', '/share/p/', 'permalink.php', 'pfbid']):
        return redirected_url, (
            "您輸入的是 Facebook 貼文分享連結。Facebook 的安全限制導致下載器無法直接解析貼文頁面。\n"
            "【解決方法】：請在該影片上點擊右鍵複製『影片網址』，或是點選影片的『發布時間』（如：1小時前/5月20日），"
            "複製網址列中以『/watch/?v=』或『/videos/』開頭的影片直接連結，貼回上方輸入框後重新查詢與下載。"
        )

    return redirected_url, None


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def video_info(request):
    """
    取得影片資訊（標題、時長、縮圖等）
    POST body: { "url": "https://..." }
    """
    url = request.data.get('url', '').strip()
    if not url:
        return Response({'error': '請提供影片網址'}, status=400)

    # 針對 Facebook 網址進行重導向解析與貼文限制防範
    resolved_url, fb_error = _resolve_facebook_url(url)
    if fb_error:
        return Response({'error': fb_error}, status=400)

    # 清除 playlist 參數
    clean_url = re.sub(r'&list=[^&]+', '', resolved_url)

    ydl_opts = {
        'noplaylist': True,
        'skip_download': True,
        'quiet': True,
        'user_agent': (
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
            'AppleWebKit/537.36 (KHTML, like Gecko) '
            'Chrome/120.0.0.0 Safari/537.36'
        ),
        'extractor_args': {
            'youtube': {
                'player_client': ['ios', 'android'],
            }
        },
        'nocheckcertificate': True,
        'ffmpeg_location': '/usr/bin/ffmpeg',
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(clean_url, download=False)
            return Response({
                'title': info.get('title', ''),
                'duration': info.get('duration', 0),
                'thumbnail': info.get('thumbnail', ''),
                'uploader': info.get('uploader', ''),
                'url': clean_url,
            })
    except Exception as e:
        err_msg = str(e)
        if 'facebook.com' in clean_url or '[facebook]' in err_msg:
            return Response({
                'error': (
                    "無法解析該 Facebook 連結。這通常是因為該網址是貼文分享連結、私密社團內容或需要登入的限制影片。\n"
                    "【解決方法】：請在影片上點擊右鍵複製『影片網址』，或是點選影片的『發布時間』（如：1小時前），"
                    "複製網址列中以『/watch/?v=』或『/videos/』開頭的『直接影片網址』重新貼上查詢。"
                )
            }, status=400)
        return Response({'error': f'無法取得影片資訊: {err_msg}'}, status=400)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def video_download(request):
    """
    下載影片/音檔並回傳檔案
    POST body: {
        "url": "https://...",
        "format": "mp4" | "mp3",
        "quality": "1080" | "720" | "480" | "360",
        "bitrate": "320k" | "256k" | "128k",
        "filename": "自訂檔名（選填）"
    }
    """
    url = request.data.get('url', '').strip()
    format_choice = request.data.get('format', 'mp4')
    quality = request.data.get('quality', '720')
    audio_bitrate = request.data.get('bitrate', '256k')
    custom_name = request.data.get('filename', '').strip()

    if not url:
        return Response({'error': '請提供影片網址'}, status=400)

    # 針對 Facebook 網址進行重導向解析與貼文限制防範
    resolved_url, fb_error = _resolve_facebook_url(url)
    if fb_error:
        return Response({'error': fb_error}, status=400)

    clean_url = re.sub(r'&list=[^&]+', '', resolved_url)

    # 檔名模板
    if custom_name:
        outtmpl = os.path.join(DOWNLOAD_DIR, f'{_safe_filename(custom_name)}.%(ext)s')
    else:
        outtmpl = os.path.join(DOWNLOAD_DIR, '%(title).100s.%(ext)s')

    ydl_opts = {
        'noplaylist': True,
        'outtmpl': outtmpl,
        'user_agent': (
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
            'AppleWebKit/537.36 (KHTML, like Gecko) '
            'Chrome/120.0.0.0 Safari/537.36'
        ),
        'extractor_args': {
            'youtube': {
                'player_client': ['ios', 'android'],
            }
        },
        'nocheckcertificate': True,
        'rm_cache_dir': True,
        'ffmpeg_location': '/usr/bin/ffmpeg',
    }

    if format_choice == 'mp3':
        ydl_opts.update({
            'format': 'bestaudio/best',
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': audio_bitrate.replace('k', ''),
            }],
        })
    else:
        target_q = quality or '720'
        ydl_opts.update({
            'format': (
                f'bestvideo[height<={target_q}][ext=mp4]'
                f'+bestaudio[ext=m4a]'
                f'/best[height<={target_q}]/best'
            ),
            'merge_output_format': 'mp4',
        })

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(clean_url, download=True)
            file_path = ydl.prepare_filename(info)

            if format_choice == 'mp3':
                file_path = os.path.splitext(file_path)[0] + '.mp3'

        if not os.path.exists(file_path):
            return Response({'error': '下載的檔案不存在'}, status=500)

        # 設定 Content-Type
        content_type = 'audio/mpeg' if format_choice == 'mp3' else 'video/mp4'
        filename = os.path.basename(file_path)

        response = FileResponse(
            open(file_path, 'rb'),
            content_type=content_type,
            as_attachment=True,
            filename=filename,
        )

        # 下載完成後刪除暫存檔案（透過 streaming_content wrapper）
        original_streaming = response.streaming_content

        def cleanup_streaming():
            try:
                yield from original_streaming
            finally:
                if os.path.exists(file_path):
                    os.remove(file_path)

        response.streaming_content = cleanup_streaming()
        return response

    except Exception as e:
        err_msg = str(e)
        if 'facebook.com' in clean_url or '[facebook]' in err_msg:
            return Response({
                'error': (
                    "無法下載該 Facebook 連結。這通常是因為該網址是貼文分享連結、私密社團內容或需要登入的限制影片。\n"
                    "【解決方法】：請在影片上點擊右鍵複製『影片網址』，或是點選影片的『發布時間』（如：1小時前），"
                    "複製網址列中以『/watch/?v=』或『/videos/』開頭的『直接影片網址』重新貼上進行下載。"
                )
            }, status=400)
        return Response({'error': f'下載發生錯誤: {err_msg}'}, status=500)


from django.shortcuts import render
from django.contrib.auth.decorators import login_required

@login_required
def humnos_page_view(request):
    return render(request, 'humnos/humnos_page.html')

