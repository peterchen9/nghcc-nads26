"""
詩歌資料庫 — API 視圖

端點：
  GET  /api/hymns/              → 列表（支援搜尋 hymntitle、tune、beat，分頁）
  GET  /api/hymns/<id>/         → 詳情
  POST /api/hymns/<id>/upload/  → 上傳 mp3/htm/pdf 檔案
"""
import os
import re

from django.db.models import Q
from rest_framework.decorators import api_view, permission_classes, parser_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.parsers import MultiPartParser
from rest_framework.response import Response

from .models import Hymn
from .serializers import HymnListSerializer, HymnDetailSerializer

from django.conf import settings
from django.contrib.auth.decorators import login_required


# 檔案儲存目錄
HTM_DIR = os.path.join(settings.MEDIA_ROOT, 'hymns', 'html')
MP3_DIR = os.path.join(settings.MEDIA_ROOT, 'hymns', 'mp3')
SCORE_DIR = os.path.join(settings.MEDIA_ROOT, 'hymns', 'pdf')
MIDI_DIR = os.path.join(settings.MEDIA_ROOT, 'hymns', 'midi')


@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])
def hymn_list(request):
    """
    GET /api/hymns/
    查詢參數：
      q          — 關鍵字搜尋（曲名 hymntitle 模糊比對）
      tune       — 調性篩選（完全比對或模糊比對）
      beat       — 日期篩選（YYYY-MM-DD 或 YYYY）
      page       — 頁碼（預設 1）
      page_size  — 每頁筆數（預設 50，最大 200）

    POST /api/hymns/
    新增詩歌
    """
    if request.method == 'GET':
        qs = Hymn.objects.all()

        # 關鍵字搜尋（曲名、來源）
        q = request.GET.get('q', '').strip()
        if q:
            qs = qs.filter(
                Q(hymntitle__icontains=q) |
                Q(source__icontains=q) |
                Q(stroke_id__icontains=q)
            )

        # 調性篩選
        tune = request.GET.get('tune', '').strip()
        if tune:
            qs = qs.filter(tune_mark__icontains=tune)

        # 日期篩選
        beat = request.GET.get('beat', '').strip()
        if beat:
            if len(beat) == 4 and beat.isdigit():
                # 僅年份
                qs = qs.filter(beat_mark__year=int(beat))
            else:
                # 完整日期
                qs = qs.filter(beat_mark=beat)

        # 分頁
        try:
            page = max(1, int(request.GET.get('page', 1)))
        except (ValueError, TypeError):
            page = 1
        try:
            page_size = min(200, max(1, int(request.GET.get('page_size', 50))))
        except (ValueError, TypeError):
            page_size = 50

        total = qs.count()
        start = (page - 1) * page_size
        hymns = qs[start:start + page_size]

        serializer = HymnListSerializer(hymns, many=True, context={'request': request})
        return Response({
            'results': serializer.data,
            'total': total,
            'page': page,
            'page_size': page_size,
            'total_pages': (total + page_size - 1) // page_size if page_size else 1,
        })

    elif request.method == 'POST':
        data = request.data
        title = data.get('hymntitle', '').strip()
        if not title:
            return Response({'error': '曲名必填'}, status=400)

        # 自動計算 stroke_id
        stroke_prefix = calc_stroke_id(title)
        existing = (Hymn.objects
                    .filter(stroke_id__startswith=stroke_prefix)
                    .order_by('-stroke_id')
                    .values_list('stroke_id', flat=True)
                    .first())
        if existing:
            try:
                seq = int(existing[4:]) + 1
            except (ValueError, TypeError):
                seq = 1
        else:
            seq = 1
        new_stroke_id = f'{stroke_prefix}{seq:02d}'

        hymn = Hymn(
            hymntitle=title,
            stroke_id=new_stroke_id,
            ename=data.get('ename', '').strip(),
            tune_mark=data.get('tune_mark', '').strip(),
            beat_mark=data.get('beat_mark', '').strip(),
            source=data.get('source', '').strip(),
            lyric_author=data.get('lyric_author', '').strip(),
            tune_author=data.get('tune_author', '').strip(),
            lyric=data.get('lyric', '').strip(),
            notes_simple=data.get('notes_simple', '').strip(),
            simplescore=data.get('simplescore', '').strip()
        )
        hymn.save()
        serializer = HymnListSerializer(hymn, context={'request': request})
        return Response(serializer.data, status=201)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def hymn_create(request):
    """(已併入 hymn_list)"""
    pass



@api_view(['GET', 'PUT', 'DELETE'])
@permission_classes([IsAuthenticated])
def hymn_detail(request, pk):
    """
    GET /api/hymns/<id>/     — 詩歌詳情
    PUT /api/hymns/<id>/     — 編輯詩歌
    DELETE /api/hymns/<id>/  — 刪除詩歌
    """
    try:
        hymn = Hymn.objects.get(pk=pk)
    except Hymn.DoesNotExist:
        return Response({'error': '找不到此詩歌'}, status=404)

    if request.method == 'GET':
        serializer = HymnDetailSerializer(hymn, context={'request': request})
        return Response(serializer.data)

    elif request.method == 'PUT':
        data = request.data
        title = data.get('hymntitle', '').strip()
        if not title:
            return Response({'error': '曲名必填'}, status=400)

        # 若修改了曲名，重新計算筆劃代碼 stroke_id
        if title != hymn.hymntitle:
            hymn.hymntitle = title
            stroke_prefix = calc_stroke_id(title)
            existing = (Hymn.objects
                        .filter(stroke_id__startswith=stroke_prefix)
                        .exclude(pk=pk)
                        .order_by('-stroke_id')
                        .values_list('stroke_id', flat=True)
                        .first())
            if existing:
                try:
                    seq = int(existing[4:]) + 1
                except (ValueError, TypeError):
                    seq = 1
            else:
                seq = 1
            hymn.stroke_id = f'{stroke_prefix}{seq:02d}'

        hymn.ename = data.get('ename', '').strip()
        hymn.tune_mark = data.get('tune_mark', '').strip()
        hymn.beat_mark = data.get('beat_mark', '').strip()
        hymn.source = data.get('source', '').strip()
        hymn.lyric_author = data.get('lyric_author', '').strip()
        hymn.tune_author = data.get('tune_author', '').strip()
        hymn.lyric = data.get('lyric', '').strip()
        hymn.notes_simple = data.get('notes_simple', '').strip()
        hymn.simplescore = data.get('simplescore', '').strip()

        hymn.save()
        serializer = HymnDetailSerializer(hymn, context={'request': request})
        return Response(serializer.data)

    elif request.method == 'DELETE':
        hymn.delete()
        return Response({'message': '刪除成功'}, status=200)



def _extract_from_htm(filepath):
    """從 HTM 檔提取歌詞和簡譜"""
    with open(filepath, 'rb') as f:
        raw = f.read()

    for enc in ['big5', 'cp950', 'utf-8']:
        try:
            text = raw.decode(enc, errors='replace')
            break
        except Exception:
            text = raw.decode('utf-8', errors='replace')

    span_re = re.compile(r"<span[^>]*?style='([^']*)'[^>]*?>([^<]*)", re.DOTALL)
    paragraphs = text.split('<p ')
    lyrics, scores = [], []

    for p in paragraphs:
        p_lyrics, p_scores = [], []
        for m in span_re.finditer(p):
            style, content = m.group(1), m.group(2)
            clean = content.replace('&nbsp;', ' ').replace('&amp;', '&').strip()
            if not clean:
                continue
            if 'SimpMusic Base' in style:
                p_scores.append(clean)
            elif '標楷體' in style:
                fs = re.search(r'font-size:\s*([\d.]+)', style)
                if fs and float(fs.group(1)) >= 40:
                    p_lyrics.append(clean)
        if p_lyrics:
            lyrics.append(''.join(p_lyrics))
        if p_scores:
            scores.append(' '.join(p_scores))

    return '\n'.join(lyrics), '\n'.join(scores)


# SimpMusic Base 字元對照
SIMPMUSIC_BASE_MAP = {
    '1': '1', '2': '2', '3': '3', '4': '4', '5': '5', '6': '6', '7': '7',
    '9': '.', '0': '0', '-': '-',
    '!': '1+', '@': '2+', '#': '3+', '$': '4+', '%': '5+', '^': '6+', '&': '7+',
    'q': '1_', 'w': '2_', 'e': '3_', 'r': '4_', 't': '5_', 'y': '6_', 'u': '7_',
    'i': '_', 'p': '0_',
    'a': '1__', 's': '2__', 'd': '3__', 'f': '4__', 'g': '5__', 'h': '6__', 'j': '7__',
    'A': '1-__', 'S': '2-__', 'D': '3-__', 'F': '4-__', 'G': '5-__', 'H': '6-__', 'J': '7-__',
    '|': '|', ' ': ' ',
}

NOTE_MAP = {
    '1': 'C', '2': 'D', '3': 'E', '4': 'F',
    '5': 'G', '6': 'A', '7': 'B', '0': 'R',
}


def _score_to_midi_str(score_text):
    """簡譜 → MIDI 音符序列"""
    if not score_text:
        return ''
    midi_notes = []
    for line in score_text.split('\n'):
        for char in line:
            mapped = SIMPMUSIC_BASE_MAP.get(char, '')
            if not mapped or mapped in ('_', ' ', '.'):
                continue
            if mapped == '|':
                midi_notes.append('|')
                continue
            if mapped == '-':
                midi_notes.append('-')
                continue
            note_num, octave = '', 4
            for c in mapped:
                if c.isdigit():
                    note_num = c
                elif c == '+':
                    octave = 5
                elif c == '-':
                    octave = 3
            if note_num in NOTE_MAP:
                n = NOTE_MAP[note_num]
                midi_notes.append('R' if n == 'R' else f'{n}{octave}')
    return ' '.join(midi_notes)


import html as html_mod
from .stroke_utils import calc_stroke_id


def _clean_lyric(text):
    """清除歌詞中的非中文字元，並依語意重組斷行"""
    if not text:
        return ''
    text = html_mod.unescape(text)
    
    # 1. 清除非中文字元（保留中文字 + 中文標點）
    lines = text.split('\n')
    clean_lines = []
    for line in lines:
        line = line.strip()
        if not line:
            continue
        # 只保留含有中文的行
        if not re.search(r'[\u4e00-\u9fff]', line):
            continue
        clean = re.sub(
            r'[^\u4e00-\u9fff\u3400-\u4dbf\uff00-\uffef\u3000-\u303f'
            r'\uff0c\u3001\u3002，。、！？：；「」『』（）【】\n ]',
            '', line
        )
        if clean.strip():
            clean_lines.append(clean.strip())
            
    raw_clean_text = '\n'.join(clean_lines)
    
    # 2. 語意斷行重組
    START_WORDS = {
        '祂', '我', '你', '祢', '您', '主', '神', '耶穌', '我們', '你們', '他們', '大家',
        '在', '當', '因', '但', '若', '而', '凡', '誰', '每', '如', '每當', '因為', '如果',
        '雖然', '但是', '然而', '所以', '因此', '耶和華', '基督'
    }
    
    MERGE_ENDINGS = {
        '為', '在', '對', '與', '同', '向', '給', '到', '把', '被', '將', '使', '令', '讓', '是',
        '領', '引', '靠', '愛', '看', '聽', '叫', '幫', '助', '救', '求', '隨', '要', '有', '無', '作', '開'
    }
    
    END_WORDS = {'我', '你', '祂', '祢', '您', '們', '了', '吧', '嗎', '阿們', '哈利路亞'}
    
    paragraphs = raw_clean_text.split('\n\n')
    cleaned_paragraphs = []
    
    for para in paragraphs:
        para_lines = [line.strip() for line in para.split('\n') if line.strip()]
        if not para_lines:
            continue
            
        cleaned_lines = []
        current_line = ""
        
        for line in para_lines:
            if not current_line:
                current_line = line
                continue
                
            should_merge = False
            
            if len(current_line) < 5:
                should_merge = True
            elif len(line) <= 2 and len(current_line) < 10:
                should_merge = True
                
            if line[0] in START_WORDS:
                should_merge = False
                
            if current_line[-1] in MERGE_ENDINGS:
                should_merge = True
                
            if current_line[-1] in END_WORDS:
                should_merge = False
                
            if should_merge:
                current_line += line
            else:
                cleaned_lines.append(current_line)
                current_line = line
                
        if current_line:
            cleaned_lines.append(current_line)
            
        cleaned_paragraphs.append('\n'.join(cleaned_lines))
        
    return '\n\n'.join(cleaned_paragraphs)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
@parser_classes([MultiPartParser])
def hymn_upload(request, pk):
    """
    POST /api/hymns/<id>/upload/
    上傳檔案（mp3, htm, pdf）至對應目錄
    接受參數：
      file  — 上傳的檔案
      title — 曲名（用於命名檔案和計算 stroke_id）
    """
    try:
        hymn = Hymn.objects.get(pk=pk)
    except Hymn.DoesNotExist:
        return Response({'error': '找不到此詩歌'}, status=404)

    uploaded_file = request.FILES.get('file')
    if not uploaded_file:
        return Response({'error': '未提供檔案'}, status=400)

    # 取得曲名
    title = request.POST.get('title', '').strip()
    if title:
        hymn.hymntitle = title

    # 計算 stroke_id 前 4 碼
    stroke_prefix = calc_stroke_id(title or hymn.hymntitle)
    # 查詢同前綴的最大序號
    existing = (Hymn.objects
                .filter(stroke_id__startswith=stroke_prefix)
                .exclude(pk=pk)
                .order_by('-stroke_id')
                .values_list('stroke_id', flat=True)
                .first())
    if existing:
        seq = int(existing[4:]) + 1
    else:
        seq = 1
    new_stroke_id = f'{stroke_prefix}{seq:02d}'
    hymn.stroke_id = new_stroke_id

    fname = uploaded_file.name.lower()

    if fname.endswith('.mp3'):
        save_name = f'{new_stroke_id}_{uploaded_file.name}'
        os.makedirs(MP3_DIR, exist_ok=True)
        dest = os.path.join(MP3_DIR, save_name)
        with open(dest, 'wb') as f:
            for chunk in uploaded_file.chunks():
                f.write(chunk)
        hymn.mp3_file = save_name
        hymn.save(update_fields=['mp3_file', 'hymntitle', 'stroke_id'])
        return Response({
            'message': f'MP3 已上傳: {save_name}',
            'mp3_file': save_name,
            'stroke_id': new_stroke_id,
        })

    elif fname.endswith('.htm') or fname.endswith('.html'):
        # 用曲名命名，前綴 stroke_id
        ext = '.htm' if fname.endswith('.htm') else '.html'
        safe_title = re.sub(r'[^\u4e00-\u9fff\w]', '', title or hymn.hymntitle)
        save_name = f'{new_stroke_id}{safe_title}{ext}'
        os.makedirs(HTM_DIR, exist_ok=True)
        dest = os.path.join(HTM_DIR, save_name)
        with open(dest, 'wb') as f:
            for chunk in uploaded_file.chunks():
                f.write(chunk)

        # 解析 HTM 提取歌詞、簡譜
        lyric, score = _extract_from_htm(dest)
        lyric = _clean_lyric(lyric)
        midi_str = _score_to_midi_str(score)

        hymn.htm_file = save_name
        hymn.lyric = lyric[:2000] if lyric else ''
        hymn.simplescore = score[:5000] if score else ''
        hymn.midistr = midi_str[:5000] if midi_str else ''
        hymn.save(update_fields=[
            'htm_file', 'lyric', 'simplescore', 'midistr',
            'hymntitle', 'stroke_id',
        ])

        return Response({
            'message': f'HTM 已上傳並解析: {save_name}',
            'htm_file': save_name,
            'stroke_id': new_stroke_id,
            'lyric_preview': lyric[:30] if lyric else '',
        })

    elif fname.endswith('.pdf'):
        save_name = f'{new_stroke_id}_{uploaded_file.name}'
        os.makedirs(SCORE_DIR, exist_ok=True)
        dest = os.path.join(SCORE_DIR, save_name)
        with open(dest, 'wb') as f:
            for chunk in uploaded_file.chunks():
                f.write(chunk)
        hymn.score_file = save_name
        hymn.save(update_fields=['score_file', 'hymntitle', 'stroke_id'])
        return Response({
            'message': f'PDF 已上傳: {save_name}',
            'score_file': save_name,
            'stroke_id': new_stroke_id,
        })

    elif fname.endswith('.mid') or fname.endswith('.midi'):
        save_name = f'{new_stroke_id}_{uploaded_file.name}'
        os.makedirs(MIDI_DIR, exist_ok=True)
        dest = os.path.join(MIDI_DIR, save_name)
        with open(dest, 'wb') as f:
            for chunk in uploaded_file.chunks():
                f.write(chunk)
        hymn.midi = save_name
        hymn.save(update_fields=['midi', 'hymntitle', 'stroke_id'])
        return Response({
            'message': f'MIDI 已上傳: {save_name}',
            'midi': save_name,
            'stroke_id': new_stroke_id,
        })

    else:
        return Response(
            {'error': f'不支援的檔案類型: {uploaded_file.name}，僅接受 .mp3 / .htm / .pdf / .mid / .midi'},
            status=400,
        )


from django.http import FileResponse, Http404

def serve_htm_resource(request, filename):
    """相容舊前端路由：直接提供 HTM 歌詞/投影檔檔案"""
    # 預防路徑穿越漏洞
    clean_filename = os.path.basename(filename)
    filepath = os.path.join(HTM_DIR, clean_filename)
    if os.path.exists(filepath) and os.path.isfile(filepath):
        return FileResponse(open(filepath, 'rb'), content_type='text/html; charset=utf-8')
    raise Http404("HTM File not found")


from django.shortcuts import render

@login_required
def hymns_page_view(request):
    """渲染詩歌資料庫前端網頁"""
    return render(request, 'hymns/hymns_page.html')



