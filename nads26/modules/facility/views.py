import csv
import hashlib
import json
import re
from decimal import Decimal, InvalidOperation
from io import BytesIO, StringIO
from datetime import datetime, date, time, timedelta
from pathlib import Path
from urllib.parse import quote
from urllib.request import urlopen
from zoneinfo import ZoneInfo

from django.contrib import messages
from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.core.mail import EmailMessage
from django.db import connection
from django.http import HttpResponse, HttpResponseBadRequest, HttpResponseForbidden
from django.shortcuts import redirect, render
from django.utils.html import format_html
from modules.network.views import lan_hosts_note as network_lan_hosts_note
from modules.network.views import lan_hosts_page as network_lan_hosts_page
from modules.network.views import lan_hosts_ping as network_lan_hosts_ping
from modules.network.views import lan_hosts_scan as network_lan_hosts_scan
from modules.network.views import wlan_aps_page as network_wlan_aps_page
from modules.network.views import wlan_aps_scan as network_wlan_aps_scan

TZ = ZoneInfo('Asia/Taipei')
MRBS_DB = 'mrbsdb'
BOOKING_TYPE = 'I'

FLOOR_ORDER = ['1F', '2F', '3F', '4F', '5F', '6F', 'B1F', '其他']
FLOOR_RANK = {name: index for index, name in enumerate(FLOOR_ORDER)}
SLOT_START_HOUR = 6
SLOT_END_HOUR = 22
SLOT_MINUTES = 30
ROOM_PHOTO_DIR = Path(settings.BASE_DIR) / 'static' / 'facility' / 'rooms'
ROOM_PHOTO_URL = '/static/facility/rooms/'
ROOM_PHOTO_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.webp'}
ROOM_PHOTO_FILES = None
WEEKDAY_NAMES = ['星期一', '星期二', '星期三', '星期四', '星期五', '星期六', '星期日']
EXPENSE_CLAIM_TABLE = 'facility_expense_claim'
EXPENSE_CLAIM_ITEM_TABLE = 'facility_expense_claim_item'
PASTORAL_REPORT_TABLE = 'care_pastoral_report'
PASTORAL_REPORT_PHOTO_TABLE = 'care_pastoral_report_photo'
PASTORAL_REPORT_PHOTO_DIR = Path(settings.MEDIA_ROOT if hasattr(settings, 'MEDIA_ROOT') and settings.MEDIA_ROOT else Path(settings.BASE_DIR) / 'media') / 'pastoral_reports'
PASTORAL_REPORT_PHOTO_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.webp', '.gif'}
PASTORAL_REPORT_EMAIL = 'care@nghcc.org.tw'
MAINTENANCE_ITEM_TABLE = 'facility_maintenance_item'
MAINTENANCE_RECORD_TABLE = 'facility_maintenance_record'
MAINTENANCE_SHEET_ID = '1KRbFON9anBJL6Ovh-ApEkqZabgO_gFLbv31JNfqEJJc'
MAINTENANCE_SHEET_NAME = '2025'
MAINTENANCE_SHEET_YEAR = 2025
MAINTENANCE_SHEET_CSV_URL = (
    f'https://docs.google.com/spreadsheets/d/{MAINTENANCE_SHEET_ID}/gviz/tq'
    f'?tqx=out:csv&sheet={quote(MAINTENANCE_SHEET_NAME)}'
)


def planned_page(request, unused_path=None):
    return render(request, 'planned.html')


def _room_floor(room):
    key = f"{room.get('sort_key') or ''} {room.get('room_name') or ''}".upper().strip()
    if key.startswith('B'):
        return 'B1F'
    if '6F' in key or key.startswith('6'):
        return '6F'
    if '5F' in key or key.startswith('5'):
        return '5F'
    if '4F' in key or key.startswith('4'):
        return '4F'
    if '3F' in key or key.startswith('3'):
        return '3F'
    if '2F' in key or key.startswith('2'):
        return '2F'
    if '1F' in key or key.startswith('1') or key.startswith('T1'):
        return '1F'
    return '其他'


def _room_sort_key(room):
    floor = _room_floor(room)
    key = str(room.get('sort_key') or room.get('room_name') or '')
    digits = ''.join(ch for ch in key if ch.isdigit())
    numeric = int(digits) if digits else 9999
    return (FLOOR_RANK.get(floor, 99), numeric, key)


def _normalize_room_text(value):
    return re.sub(r'\s+', '', str(value or '').strip()).upper()


def _room_digits(room):
    source = f"{room.get('sort_key') or ''} {room.get('room_name') or ''}"
    match = re.search(r'\d+', source)
    if not match:
        return ''
    digits = match.group(0)
    return digits if len(digits) >= 2 else ''


def _photo_files():
    global ROOM_PHOTO_FILES
    if ROOM_PHOTO_FILES is None:
        if ROOM_PHOTO_DIR.exists():
            ROOM_PHOTO_FILES = sorted(
                path.name for path in ROOM_PHOTO_DIR.iterdir()
                if path.is_file() and path.suffix.lower() in ROOM_PHOTO_EXTENSIONS
            )
        else:
            ROOM_PHOTO_FILES = []
    return ROOM_PHOTO_FILES


def _room_photo_urls(room):
    room_name = _normalize_room_text(room.get('room_name'))
    sort_key = _normalize_room_text(room.get('sort_key'))
    digits = _room_digits(room)
    matches = []

    for filename in _photo_files():
        stem = _normalize_room_text(Path(filename).stem)
        if (
            (room_name and stem.startswith(room_name))
            or (sort_key and stem.startswith(sort_key))
            or (digits and stem.startswith(digits))
        ):
            matches.append(f'{ROOM_PHOTO_URL}{quote(filename)}')

    return matches


def _group_rooms_by_floor(rooms):
    grouped = {floor: [] for floor in FLOOR_ORDER}
    for room in rooms:
        room['floor'] = _room_floor(room)
        grouped.setdefault(room['floor'], []).append(room)
    sections = []
    for floor in FLOOR_ORDER:
        floor_rooms = sorted(grouped.get(floor, []), key=_room_sort_key)
        if floor_rooms:
            sections.append({
                'id': floor.lower().replace('其他', 'other'),
                'label': floor,
                'rooms': floor_rooms,
            })
    return sections


def _time_slots(day):
    slots = []
    current = datetime.combine(day, time(SLOT_START_HOUR, 0), tzinfo=TZ)
    end = datetime.combine(day, time(SLOT_END_HOUR, 0), tzinfo=TZ)
    delta = timedelta(minutes=SLOT_MINUTES)
    while current < end:
        slot_end = current + delta
        slots.append({
            'label': current.strftime('%H:%M'),
            'start_label': current.strftime('%H:%M'),
            'end_label': slot_end.strftime('%H:%M'),
            'start_ts': _to_ts(current),
            'end_ts': _to_ts(slot_end),
        })
        current = slot_end
    return slots


def _build_floor_sections(rooms, entries, day):
    entries_by_room = {}
    for entry in entries:
        entries_by_room.setdefault(entry['room_id'], []).append(entry)

    slots = _time_slots(day)
    slot_seconds = SLOT_MINUTES * 60
    sections = _group_rooms_by_floor(rooms)
    for section in sections:
        rows = []
        for slot in slots:
            cells = []
            for room in section['rooms']:
                booking = None
                for entry in entries_by_room.get(room['id'], []):
                    if entry['start_time'] < slot['end_ts'] and entry['end_time'] > slot['start_ts']:
                        booking = entry
                        break
                skip_booking = False
                rowspan = 1
                if booking:
                    previous_start = slot['start_ts'] - slot_seconds
                    previous_overlap = (
                        booking['start_time'] < slot['start_ts']
                        and booking['end_time'] > previous_start
                    )
                    skip_booking = previous_overlap
                    if not skip_booking:
                        rowspan = sum(
                            1 for future_slot in slots
                            if future_slot['start_ts'] >= slot['start_ts']
                            and booking['start_time'] < future_slot['end_ts']
                            and booking['end_time'] > future_slot['start_ts']
                        )
                cell = {
                    'room': room,
                    'slot': slot,
                    'booking': booking,
                    'skip_booking': skip_booking,
                    'rowspan': rowspan,
                }
                cells.append(cell)
            rows.append({'slot': slot, 'cells': cells})
        section['rows'] = rows
    return sections


def _build_daily_overview(rooms, entries, day):
    floor_sections = _build_floor_sections(rooms, entries, day)
    overview_rooms = []
    floor_groups = []
    for section in floor_sections:
        overview_rooms.extend(section['rooms'])
        floor_groups.append({
            'label': section['label'],
            'room_count': len(section['rooms']),
        })

    overview_rows = []
    if floor_sections:
        row_count = len(floor_sections[0]['rows'])
        for row_index in range(row_count):
            cells = []
            for section in floor_sections:
                cells.extend(section['rows'][row_index]['cells'])
            overview_rows.append({
                'slot': floor_sections[0]['rows'][row_index]['slot'],
                'cells': cells,
            })

    return overview_rooms, floor_groups, overview_rows



def _dictfetchall(cursor):
    columns = [col[0] for col in cursor.description]
    return [dict(zip(columns, row)) for row in cursor.fetchall()]


def _parse_date(value):
    if not value:
        return date.today()
    try:
        return datetime.strptime(value, '%Y-%m-%d').date()
    except ValueError:
        return date.today()


def _parse_local_datetime(day, value, fallback):
    if not value:
        value = fallback
    try:
        parsed_time = datetime.strptime(value, '%H:%M').time()
    except ValueError:
        parsed_time = datetime.strptime(fallback, '%H:%M').time()
    return datetime.combine(day, parsed_time, tzinfo=TZ)


def _to_ts(dt):
    return int(dt.timestamp())


def _from_ts(ts):
    return datetime.fromtimestamp(int(ts), TZ)


def _rooms():
    with connection.cursor() as cursor:
        cursor.execute(
            f'''
            SELECT id, area_id, room_name, sort_key, description, capacity
            FROM {MRBS_DB}.mrbs_room
            WHERE disabled = 0
            ORDER BY sort_key, room_name
            '''
        )
        rows = _dictfetchall(cursor)

    for row in rows:
        row['photo_urls'] = _room_photo_urls(row)
    return rows


def _area_id():
    with connection.cursor() as cursor:
        cursor.execute(f'SELECT id FROM {MRBS_DB}.mrbs_area WHERE disabled = 0 ORDER BY id LIMIT 1')
        row = cursor.fetchone()
    return row[0] if row else 0


def _room_by_id(room_id):
    with connection.cursor() as cursor:
        cursor.execute(
            f'''
            SELECT id, area_id, room_name, sort_key, description, capacity
            FROM {MRBS_DB}.mrbs_room
            WHERE id = %s
            ''',
            [room_id],
        )
        rows = _dictfetchall(cursor)
    if not rows:
        return None
    room = rows[0]
    room['floor'] = _room_floor(room)
    room['photo_urls'] = _room_photo_urls(room)
    return room


def _save_room_photo(room, uploaded_file):
    if not uploaded_file:
        return
    suffix = Path(uploaded_file.name).suffix.lower()
    if suffix not in ROOM_PHOTO_EXTENSIONS:
        return
    ROOM_PHOTO_DIR.mkdir(parents=True, exist_ok=True)
    safe_name = re.sub(r'[^0-9A-Za-z\u4e00-\u9fff_-]+', '-', room['room_name']).strip('-') or f"room-{room['id']}"
    existing_count = len(_room_photo_urls(room))
    filename = f'{safe_name}-{existing_count + 1}{suffix}'
    target = ROOM_PHOTO_DIR / filename
    counter = existing_count + 1
    while target.exists():
        counter += 1
        filename = f'{safe_name}-{counter}{suffix}'
        target = ROOM_PHOTO_DIR / filename
    with target.open('wb') as destination:
        for chunk in uploaded_file.chunks():
            destination.write(chunk)
    global ROOM_PHOTO_FILES
    ROOM_PHOTO_FILES = None


def _room_form_values(request):
    room_name = (request.POST.get('room_name') or '').strip()
    floor = (request.POST.get('floor') or '').strip() or '其他'
    description = (request.POST.get('description') or '').strip()
    try:
        capacity = int(request.POST.get('capacity') or 0)
    except ValueError:
        capacity = 0
    capacity = max(0, capacity)
    return room_name, floor, description, capacity


def _create_room(request):
    room_name, floor, description, capacity = _room_form_values(request)
    if not room_name:
        messages.error(request, '請輸入場地名稱。')
        return
    with connection.cursor() as cursor:
        cursor.execute(
            f'''
            INSERT INTO {MRBS_DB}.mrbs_room
              (disabled, area_id, room_name, sort_key, description, capacity,
               room_admin_email, custom_html)
            VALUES (0, %s, %s, %s, %s, %s, '', '')
            ''',
            [_area_id(), room_name, floor, description, capacity],
        )
        room_id = cursor.lastrowid
    room = _room_by_id(room_id)
    _save_room_photo(room, request.FILES.get('photo'))
    messages.success(request, '場地資料已新增。')


def _update_room(request):
    try:
        room_id = int(request.POST.get('room_id') or '')
    except ValueError:
        messages.error(request, '找不到指定場地。')
        return
    room_name, floor, description, capacity = _room_form_values(request)
    if not room_name:
        messages.error(request, '請輸入場地名稱。')
        return
    with connection.cursor() as cursor:
        cursor.execute(
            f'''
            UPDATE {MRBS_DB}.mrbs_room
            SET room_name = %s,
                sort_key = %s,
                description = %s,
                capacity = %s
            WHERE id = %s
            ''',
            [room_name, floor, description, capacity, room_id],
        )
    room = _room_by_id(room_id)
    _save_room_photo(room, request.FILES.get('photo'))
    messages.success(request, '場地資料已更新。')


def _delete_room(request):
    try:
        room_id = int(request.POST.get('room_id') or '')
    except ValueError:
        messages.error(request, '找不到指定場地。')
        return
    with connection.cursor() as cursor:
        cursor.execute(f'SELECT COUNT(*) FROM {MRBS_DB}.mrbs_entry WHERE room_id = %s', [room_id])
        has_entries = cursor.fetchone()[0] > 0
        if has_entries:
            cursor.execute(f'UPDATE {MRBS_DB}.mrbs_room SET disabled = 1 WHERE id = %s', [room_id])
        else:
            cursor.execute(f'DELETE FROM {MRBS_DB}.mrbs_room WHERE id = %s', [room_id])
    messages.success(request, '場地資料已刪除。')


def _current_username(request):
    return request.user.get_username() if request.user.is_authenticated else ''


def _current_display_name(user):
    full_name = ''
    if user and getattr(user, 'is_authenticated', False):
        full_name = user.get_full_name().strip()
    return full_name or (user.get_username() if user and getattr(user, 'is_authenticated', False) else '')


def _can_write_pastoral_report(user):
    if not user or not user.is_authenticated:
        return False
    if user.is_superuser or user.is_staff:
        return True
    if user.has_perm('facility.add_pastoral_report') or user.has_perm('care.add_pastoral_report'):
        return True
    allowed_groups = {'關懷', '牧養', '牧養報告', 'care', 'pastoral_care'}
    return user.groups.filter(name__in=allowed_groups).exists()


def _pastoral_ensure_tables():
    with connection.cursor() as cursor:
        cursor.execute(
            f'''
            CREATE TABLE IF NOT EXISTS {PASTORAL_REPORT_TABLE} (
                id INT AUTO_INCREMENT PRIMARY KEY,
                report_no VARCHAR(36) NOT NULL UNIQUE,
                report_date DATE NOT NULL,
                client_name VARCHAR(200) NOT NULL,
                location VARCHAR(200) NOT NULL DEFAULT '',
                care_report TEXT NOT NULL,
                follow_up TEXT NOT NULL,
                author_user VARCHAR(150) NOT NULL DEFAULT '',
                author_name VARCHAR(200) NOT NULL DEFAULT '',
                author_email VARCHAR(254) NOT NULL DEFAULT '',
                created_at DATETIME NOT NULL,
                INDEX idx_pastoral_report_date (report_date),
                INDEX idx_pastoral_report_author (author_user)
            )
            '''
        )
        cursor.execute(
            f'''
            CREATE TABLE IF NOT EXISTS {PASTORAL_REPORT_PHOTO_TABLE} (
                id INT AUTO_INCREMENT PRIMARY KEY,
                report_id INT NOT NULL,
                file_path VARCHAR(500) NOT NULL,
                original_name VARCHAR(255) NOT NULL DEFAULT '',
                content_type VARCHAR(120) NOT NULL DEFAULT '',
                sort_order INT NOT NULL DEFAULT 0,
                created_at DATETIME NOT NULL,
                INDEX idx_pastoral_report_photo_report_id (report_id)
            )
            '''
        )


def _pastoral_report_no(cursor, created_at):
    prefix = f'CARE{created_at.strftime("%Y%m%d-%H%M%S")}'
    cursor.execute(
        f'SELECT COUNT(*) FROM {PASTORAL_REPORT_TABLE} WHERE report_no LIKE %s',
        [f'{prefix}-%'],
    )
    sequence = int(cursor.fetchone()[0] or 0) + 1
    return f'{prefix}-{sequence:03d}'


def _pastoral_from_post(request):
    report = {
        'report_date': (request.POST.get('report_date') or '').strip(),
        'client_name': (request.POST.get('client_name') or '').strip(),
        'location': (request.POST.get('location') or '').strip(),
        'care_report': (request.POST.get('care_report') or '').strip(),
        'follow_up': (request.POST.get('follow_up') or '').strip(),
        'author_user': _current_username(request),
        'author_name': _current_display_name(request.user),
        'author_email': (getattr(request.user, 'email', '') or '').strip(),
    }
    try:
        report['report_date_obj'] = datetime.strptime(report['report_date'], '%Y-%m-%d').date()
    except ValueError:
        raise ValueError('請填寫有效日期。')
    required = [
        ('client_name', '請填寫案主。'),
        ('location', '請填寫地點。'),
        ('care_report', '請填寫牧養關懷報告。'),
        ('follow_up', '請填寫後續跟進與注意事項。'),
    ]
    for key, message in required:
        if not report[key]:
            raise ValueError(message)
    return report


def _pastoral_default_report(request):
    return {
        'report_date': date.today().isoformat(),
        'client_name': '',
        'location': '',
        'care_report': '',
        'follow_up': '',
        'author_name': _current_display_name(request.user),
        'author_email': (getattr(request.user, 'email', '') or '').strip(),
    }


def _pastoral_uploaded_files(request):
    files = []
    for uploaded in request.FILES.getlist('photos'):
        suffix = Path(uploaded.name).suffix.lower()
        if suffix in PASTORAL_REPORT_PHOTO_EXTENSIONS and str(getattr(uploaded, 'content_type', '')).startswith('image/'):
            files.append(uploaded)
    return files


def _pastoral_save_photos(report_id, report_no, uploaded_files, created_at):
    saved = []
    if not uploaded_files:
        return saved
    report_dir = PASTORAL_REPORT_PHOTO_DIR / report_no
    report_dir.mkdir(parents=True, exist_ok=True)
    with connection.cursor() as cursor:
        for index, uploaded in enumerate(uploaded_files, start=1):
            suffix = Path(uploaded.name).suffix.lower() or '.jpg'
            filename = f'photo-{index:02d}{suffix}'
            target = report_dir / filename
            counter = index
            while target.exists():
                counter += 1
                filename = f'photo-{counter:02d}{suffix}'
                target = report_dir / filename
            with target.open('wb') as destination:
                for chunk in uploaded.chunks():
                    destination.write(chunk)
            cursor.execute(
                f'''
                INSERT INTO {PASTORAL_REPORT_PHOTO_TABLE}
                    (report_id, file_path, original_name, content_type, sort_order, created_at)
                VALUES (%s, %s, %s, %s, %s, %s)
                ''',
                [
                    report_id,
                    str(target),
                    Path(uploaded.name).name[:255],
                    (getattr(uploaded, 'content_type', '') or '')[:120],
                    index,
                    created_at.replace(tzinfo=None),
                ],
            )
            saved.append({
                'file_path': str(target),
                'original_name': Path(uploaded.name).name,
                'content_type': getattr(uploaded, 'content_type', '') or '',
                'sort_order': index,
            })
    return saved


def _pastoral_create_report(report, uploaded_files):
    _pastoral_ensure_tables()
    created_at = datetime.now(TZ)
    with connection.cursor() as cursor:
        report_no = _pastoral_report_no(cursor, created_at)
        cursor.execute(
            f'''
            INSERT INTO {PASTORAL_REPORT_TABLE}
                (report_no, report_date, client_name, location, care_report,
                 follow_up, author_user, author_name, author_email, created_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ''',
            [
                report_no,
                report['report_date_obj'],
                report['client_name'],
                report['location'],
                report['care_report'],
                report['follow_up'],
                report['author_user'],
                report['author_name'],
                report['author_email'],
                created_at.replace(tzinfo=None),
            ],
        )
        report_id = getattr(cursor, 'lastrowid', None) or getattr(getattr(cursor, 'cursor', None), 'lastrowid', None)
        if not report_id:
            cursor.execute('SELECT LAST_INSERT_ID()')
            report_id = cursor.fetchone()[0]
    photos = _pastoral_save_photos(report_id, report_no, uploaded_files, created_at)
    return report_no, report_id, photos


def _pastoral_get_report(report_no):
    _pastoral_ensure_tables()
    with connection.cursor() as cursor:
        cursor.execute(
            f'''
            SELECT id, report_no, report_date, client_name, location, care_report,
                   follow_up, author_user, author_name, author_email, created_at
            FROM {PASTORAL_REPORT_TABLE}
            WHERE report_no = %s
            ''',
            [report_no],
        )
        rows = _dictfetchall(cursor)
        if not rows:
            return None
        report = rows[0]
        cursor.execute(
            f'''
            SELECT file_path, original_name, content_type, sort_order
            FROM {PASTORAL_REPORT_PHOTO_TABLE}
            WHERE report_id = %s
            ORDER BY sort_order, id
            ''',
            [report['id']],
        )
        report['photos'] = _dictfetchall(cursor)
    return report


def _pastoral_report_history(filters=None):
    _pastoral_ensure_tables()
    filters = filters or {}
    where = []
    params = []
    start_date = (filters.get('start_date') or '').strip()
    end_date = (filters.get('end_date') or '').strip()
    keyword = (filters.get('keyword') or '').strip()

    if start_date:
        where.append('r.report_date >= %s')
        params.append(start_date)
    if end_date:
        where.append('r.report_date <= %s')
        params.append(end_date)
    if keyword:
        like = f'%{keyword}%'
        where.append(
            '(r.report_no LIKE %s OR r.client_name LIKE %s OR r.location LIKE %s '
            'OR r.care_report LIKE %s OR r.follow_up LIKE %s OR r.author_name LIKE %s OR r.author_user LIKE %s)'
        )
        params.extend([like, like, like, like, like, like, like])

    where_sql = f'WHERE {" AND ".join(where)}' if where else ''
    with connection.cursor() as cursor:
        cursor.execute(
            f'''
            SELECT r.id, r.report_no, r.report_date, r.client_name, r.location,
                   r.care_report, r.follow_up, r.author_user, r.author_name,
                   r.author_email, r.created_at, COUNT(p.id) AS photo_count
            FROM {PASTORAL_REPORT_TABLE} r
            LEFT JOIN {PASTORAL_REPORT_PHOTO_TABLE} p ON p.report_id = r.id
            {where_sql}
            GROUP BY r.id, r.report_no, r.report_date, r.client_name, r.location,
                     r.care_report, r.follow_up, r.author_user, r.author_name,
                     r.author_email, r.created_at
            ORDER BY r.report_date DESC, r.created_at DESC, r.id DESC
            LIMIT 200
            ''',
            params,
        )
        return _dictfetchall(cursor)


def _pastoral_draw_wrapped(page, text, x, y, width, font_name, font_size=10, line_height=15):
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.units import mm
    from reportlab.pdfbase.pdfmetrics import stringWidth

    _, page_height = A4
    page.setFont(font_name, font_size)
    paragraphs = str(text or '').replace('\r\n', '\n').replace('\r', '\n').split('\n')
    for paragraph in paragraphs:
        current = ''
        for char in paragraph or ' ':
            candidate = current + char
            if stringWidth(candidate, font_name, font_size) <= width:
                current = candidate
            else:
                if y < 22 * mm:
                    page.showPage()
                    page.setFont(font_name, font_size)
                    y = page_height - 20 * mm
                page.drawString(x, y, current)
                y -= line_height
                current = char
        if y < 22 * mm:
            page.showPage()
            page.setFont(font_name, font_size)
            y = page_height - 20 * mm
        page.drawString(x, y, current)
        y -= line_height
    return y


def _pastoral_report_pdf_bytes(report):
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.units import mm
    from reportlab.lib.utils import ImageReader
    from reportlab.pdfgen import canvas

    buffer = BytesIO()
    page = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4
    font_name = _expense_register_pdf_font()
    margin_x = 18 * mm
    content_width = width - margin_x * 2

    def new_page(title=True):
        page.setFont(font_name, 16)
        if title:
            page.drawCentredString(width / 2, height - 18 * mm, '牧養報告')
            page.setFont(font_name, 8)
            page.drawRightString(width - margin_x, height - 14 * mm, str(report.get('report_no') or ''))
        return height - 30 * mm

    y = new_page()
    page.setFont(font_name, 10)
    meta = [
        ('日期', report.get('report_date')),
        ('案主', report.get('client_name')),
        ('地點', report.get('location')),
        ('撰寫者', report.get('author_name') or report.get('author_user')),
        ('撰寫者郵箱', report.get('author_email')),
    ]
    for label, value in meta:
        page.drawString(margin_x, y, f'{label}: {value or ""}')
        y -= 7 * mm

    y -= 4 * mm
    page.setFont(font_name, 12)
    page.drawString(margin_x, y, '牧養關懷報告')
    y -= 7 * mm
    y = _pastoral_draw_wrapped(page, report.get('care_report'), margin_x, y, content_width, font_name)

    y -= 5 * mm
    if y < 48 * mm:
        page.showPage()
        y = new_page(False)
    page.setFont(font_name, 12)
    page.drawString(margin_x, y, '後續跟進與注意事項')
    y -= 7 * mm
    y = _pastoral_draw_wrapped(page, report.get('follow_up'), margin_x, y, content_width, font_name)

    photos = report.get('photos') or []
    if photos:
        page.showPage()
        y = new_page(False)
        page.setFont(font_name, 12)
        page.drawString(margin_x, y, '照片')
        y -= 9 * mm
        image_w = (content_width - 8 * mm) / 2
        image_h = 55 * mm
        x_positions = [margin_x, margin_x + image_w + 8 * mm]
        column = 0
        for photo in photos:
            path = Path(photo.get('file_path') or '')
            if not path.exists():
                continue
            if y - image_h < 18 * mm:
                page.showPage()
                y = new_page(False)
                column = 0
            x = x_positions[column]
            try:
                image = ImageReader(str(path))
                iw, ih = image.getSize()
                scale = min(image_w / iw, image_h / ih)
                draw_w = iw * scale
                draw_h = ih * scale
                page.drawImage(image, x, y - draw_h, width=draw_w, height=draw_h, preserveAspectRatio=True, mask='auto')
                page.setStrokeColor(colors.lightgrey)
                page.rect(x, y - image_h, image_w, image_h)
            except Exception:
                page.setFont(font_name, 9)
                page.drawString(x, y - 8 * mm, f'無法載入照片: {photo.get("original_name") or path.name}')
            if column == 0:
                column = 1
            else:
                column = 0
                y -= image_h + 8 * mm

    page.showPage()
    page.save()
    return buffer.getvalue()


def _pastoral_send_email(request, report):
    pdf_bytes = _pastoral_report_pdf_bytes(report)
    recipients = []
    if report.get('author_email'):
        recipients.append(report['author_email'])
    recipients.append(PASTORAL_REPORT_EMAIL)
    recipients = list(dict.fromkeys(recipients))

    subject = f'牧養報告 {report.get("report_date")} {report.get("client_name")}'
    body = (
        f'牧養報告已送出。\n\n'
        f'日期: {report.get("report_date")}\n'
        f'案主: {report.get("client_name")}\n'
        f'地點: {report.get("location")}\n'
        f'撰寫者: {report.get("author_name") or report.get("author_user")}\n'
    )
    message = EmailMessage(
        subject=subject,
        body=body,
        from_email=getattr(settings, 'DEFAULT_FROM_EMAIL', None),
        to=recipients,
    )
    message.attach(f'{report.get("report_no")}.pdf', pdf_bytes, 'application/pdf')
    message.send(fail_silently=False)
    if not report.get('author_email'):
        messages.warning(request, '撰寫者帳號沒有電子郵件，只寄送到 care@nghcc.org.tw。')


@login_required
def pastoral_report_page(request):
    if not _can_write_pastoral_report(request.user):
        return HttpResponseForbidden('您沒有撰寫牧養報告的權限。')

    _pastoral_ensure_tables()
    report = _pastoral_default_report(request)
    submitted_report = None
    report_no = request.GET.get('report_no')
    if report_no:
        submitted_report = _pastoral_get_report(report_no)

    if request.method == 'POST':
        try:
            report = _pastoral_from_post(request)
            uploaded_files = _pastoral_uploaded_files(request)
            report_no, report_id, photos = _pastoral_create_report(report, uploaded_files)
            submitted_report = _pastoral_get_report(report_no)
        except ValueError as exc:
            messages.error(request, str(exc))
        except Exception as exc:
            messages.error(request, f'牧養報告送出失敗：{exc}')
        else:
            try:
                _pastoral_send_email(request, submitted_report)
            except Exception as exc:
                messages.error(request, f'牧養報告已儲存，但寄送 PDF 時發生錯誤：{exc}')
            else:
                messages.success(request, f'牧養報告已送出並寄送 PDF：{report_no}')
            return redirect(f'{request.path.rstrip("/")}/?report_no={quote(report_no)}')

    return render(request, 'facility/pastoral_report.html', {
        'report': report,
        'submitted_report': submitted_report,
        'pastoral_report_base_path': request.path.rstrip('/') or '/facility/pastoral-reports',
    })


@login_required
def pastoral_report_admin_page(request):
    if not _can_write_pastoral_report(request.user):
        return HttpResponseForbidden('您沒有檢視牧養報告後台的權限。')

    history_filters = {
        'start_date': request.GET.get('start_date') or '',
        'end_date': request.GET.get('end_date') or '',
        'keyword': request.GET.get('keyword') or '',
    }
    return render(request, 'facility/pastoral_report_admin.html', {
        'report_history': _pastoral_report_history(history_filters),
        'history_filters': history_filters,
        'pastoral_report_base_path': '/facility/pastoral-reports',
        'pastoral_report_admin_path': request.path.rstrip('/') or '/facility/pastoral-reports/admin',
    })


@login_required
def pastoral_report_pdf(request, report_no):
    if not _can_write_pastoral_report(request.user):
        return HttpResponseForbidden('您沒有檢視牧養報告的權限。')
    report = _pastoral_get_report(report_no)
    if not report:
        return HttpResponseBadRequest('Pastoral report not found')
    pdf_bytes = _pastoral_report_pdf_bytes(report)
    response = HttpResponse(pdf_bytes, content_type='application/pdf')
    response['Content-Disposition'] = f'inline; filename="{report_no}.pdf"'
    return response


def _entry_owner(entry_id):
    with connection.cursor() as cursor:
        cursor.execute(
            f'SELECT create_by FROM {MRBS_DB}.mrbs_entry WHERE id = %s',
            [entry_id],
        )
        row = cursor.fetchone()
    return row[0] if row else None


def _can_manage_entry(request, entry_id):
    owner = _entry_owner(entry_id)
    username = _current_username(request)
    return bool(owner and username and owner == username)


def _entries(day, room_id=None, current_username=''):
    day_start = _to_ts(datetime.combine(day, time.min, tzinfo=TZ))
    day_end = _to_ts(datetime.combine(day + timedelta(days=1), time.min, tzinfo=TZ))
    params = [day_end, day_start]
    room_filter = ''
    if room_id:
        room_filter = 'AND e.room_id = %s'
        params.append(room_id)

    with connection.cursor() as cursor:
        cursor.execute(
            f'''
            SELECT e.id, e.start_time, e.end_time, e.room_id, e.create_by,
                   e.modified_by, e.name, e.use_unit, e.type, e.description, e.status,
                   r.room_name, r.sort_key, r.capacity
            FROM {MRBS_DB}.mrbs_entry e
            JOIN {MRBS_DB}.mrbs_room r ON r.id = e.room_id
            WHERE e.start_time < %s
              AND e.end_time > %s
              {room_filter}
            ORDER BY e.start_time, r.sort_key, r.room_name
            ''',
            params,
        )
        rows = _dictfetchall(cursor)

    for row in rows:
        start = _from_ts(row['start_time'])
        end = _from_ts(row['end_time'])
        row['start_label'] = start.strftime('%H:%M')
        row['end_label'] = end.strftime('%H:%M')
        row['date_label'] = start.strftime('%Y-%m-%d')
        row['duration_minutes'] = max(0, int((row['end_time'] - row['start_time']) / 60))
        row['can_edit'] = bool(current_username and row['create_by'] == current_username)
    return rows


def _has_conflict(room_id, start_ts, end_ts, exclude_id=None):
    params = [room_id, end_ts, start_ts]
    exclude_filter = ''
    if exclude_id:
        exclude_filter = 'AND id <> %s'
        params.append(exclude_id)
    with connection.cursor() as cursor:
        cursor.execute(
            f'''
            SELECT COUNT(*)
            FROM {MRBS_DB}.mrbs_entry
            WHERE room_id = %s
              AND start_time < %s
              AND end_time > %s
              {exclude_filter}
            ''',
            params,
        )
        return cursor.fetchone()[0] > 0


def _insert_entry(room_id, start_ts, end_ts, creator, name, use_unit, description):
    with connection.cursor() as cursor:
        cursor.execute(
            f'''
            INSERT INTO {MRBS_DB}.mrbs_entry
              (start_time, end_time, entry_type, repeat_id, room_id,
               create_by, modified_by, name, use_unit, type, description, status,
               reminded, info_time, info_user, info_text, ical_uid,
               ical_sequence, ical_recur_id)
            VALUES
              (%s, %s, 0, 0, %s, %s, %s, %s, %s, %s, %s, 0,
               NULL, NULL, NULL, NULL, '', 0, '')
            ''',
            [start_ts, end_ts, room_id, creator, creator, name, use_unit, BOOKING_TYPE, description],
        )


def _month_week_date(year, month, weekday, week_number):
    first = date(year, month, 1)
    offset = (weekday - first.weekday()) % 7
    candidate = first + timedelta(days=offset + (week_number - 1) * 7)
    return candidate if candidate.month == month else None


def _repeat_days(start_day, request):
    repeat_type = request.POST.get('repeat_type') or 'none'
    until = _parse_date(request.POST.get('repeat_until')) if request.POST.get('repeat_until') else start_day
    if until < start_day or repeat_type == 'none':
        return [start_day]

    days = []
    if repeat_type == 'weekly':
        current = start_day
        while current <= until:
            days.append(current)
            current += timedelta(days=7)
        return days

    if repeat_type == 'monthly_nth':
        try:
            week_number = int(request.POST.get('repeat_week') or ((start_day.day - 1) // 7 + 1))
        except ValueError:
            week_number = (start_day.day - 1) // 7 + 1
        week_number = max(1, min(5, week_number))
        current = date(start_day.year, start_day.month, 1)
        while current <= until:
            candidate = _month_week_date(current.year, current.month, start_day.weekday(), week_number)
            if candidate and start_day <= candidate <= until:
                days.append(candidate)
            if current.month == 12:
                current = date(current.year + 1, 1, 1)
            else:
                current = date(current.year, current.month + 1, 1)
        return days or [start_day]

    return [start_day]


def _create_entry(request, rooms_by_id):
    day = _parse_date(request.POST.get('date'))
    try:
        room_id = int(request.POST.get('room_id', ''))
    except ValueError:
        messages.error(request, '請選擇場地。')
        return day, None

    if room_id not in rooms_by_id:
        messages.error(request, '找不到指定場地。')
        return day, None

    start_dt = _parse_local_datetime(day, request.POST.get('start_time'), '09:00')
    end_dt = _parse_local_datetime(day, request.POST.get('end_time'), '10:00')
    if end_dt <= start_dt:
        messages.error(request, '結束時間必須晚於開始時間。')
        return day, room_id

    name = (request.POST.get('name') or '').strip()
    use_unit = (request.POST.get('use_unit') or '').strip()
    description = (request.POST.get('description') or '').strip()
    creator = (request.POST.get('create_by') or '').strip()
    if request.user.is_authenticated:
        creator = creator or request.user.get_username()
    if not name:
        messages.error(request, '請輸入活動名稱。')
        return day, room_id
    if not creator:
        messages.error(request, '請輸入登記人。')
        return day, room_id

    duration = end_dt - start_dt
    created = 0
    skipped = 0
    for repeat_day in _repeat_days(day, request):
        repeat_start = datetime.combine(repeat_day, start_dt.time(), tzinfo=TZ)
        repeat_end = repeat_start + duration
        start_ts = _to_ts(repeat_start)
        end_ts = _to_ts(repeat_end)
        if _has_conflict(room_id, start_ts, end_ts):
            skipped += 1
            continue
        _insert_entry(room_id, start_ts, end_ts, creator, name, use_unit, description)
        created += 1

    if created:
        message = f'場地登記已新增 {created} 筆。'
        if skipped:
            message += f'另有 {skipped} 筆因時段衝突未新增。'
        messages.success(request, message)
    else:
        messages.error(request, '所有週期登記時段皆已有預約，未新增資料。')
    return day, room_id


def _recurring_admin_days(request):
    start_day = _parse_date(request.POST.get('range_start'))
    end_day = _parse_date(request.POST.get('range_end'))
    if end_day < start_day:
        return []
    try:
        weekday = int(request.POST.get('weekday') or start_day.weekday())
    except ValueError:
        weekday = start_day.weekday()
    weekday = max(0, min(6, weekday))

    repeat_type = request.POST.get('recurrence_type') or 'weekly'
    days = []
    if repeat_type == 'monthly_nth':
        try:
            week_number = int(request.POST.get('repeat_week') or 1)
        except ValueError:
            week_number = 1
        week_number = max(1, min(5, week_number))
        current = date(start_day.year, start_day.month, 1)
        while current <= end_day:
            candidate = _month_week_date(current.year, current.month, weekday, week_number)
            if candidate and start_day <= candidate <= end_day:
                days.append(candidate)
            if current.month == 12:
                current = date(current.year + 1, 1, 1)
            else:
                current = date(current.year, current.month + 1, 1)
        return days

    offset = (weekday - start_day.weekday()) % 7
    current = start_day + timedelta(days=offset)
    while current <= end_day:
        days.append(current)
        current += timedelta(days=7)
    return days


def _create_recurring_admin_booking(request, rooms_by_id):
    try:
        room_id = int(request.POST.get('room_id', ''))
    except ValueError:
        messages.error(request, '請選擇場地。')
        return
    if room_id not in rooms_by_id:
        messages.error(request, '找不到指定場地。')
        return

    range_start = _parse_date(request.POST.get('range_start'))
    start_dt = _parse_local_datetime(range_start, request.POST.get('start_time'), '09:00')
    end_dt = _parse_local_datetime(range_start, request.POST.get('end_time'), '10:00')
    if end_dt <= start_dt:
        messages.error(request, '結束時間必須晚於開始時間。')
        return

    name = (request.POST.get('name') or '').strip()
    use_unit = (request.POST.get('use_unit') or '').strip()
    description = (request.POST.get('description') or '').strip()
    creator = _current_username(request) or (request.POST.get('create_by') or '').strip()
    if not name:
        messages.error(request, '請輸入活動名稱。')
        return
    if not creator:
        messages.error(request, '請輸入登記人。')
        return

    days = _recurring_admin_days(request)
    if not days:
        messages.error(request, '起訖日期內沒有符合條件的日期。')
        return

    duration = end_dt - start_dt
    created = 0
    skipped = 0
    for booking_day in days:
        booking_start = datetime.combine(booking_day, start_dt.time(), tzinfo=TZ)
        booking_end = booking_start + duration
        start_ts = _to_ts(booking_start)
        end_ts = _to_ts(booking_end)
        if _has_conflict(room_id, start_ts, end_ts):
            skipped += 1
            continue
        _insert_entry(room_id, start_ts, end_ts, creator, name, use_unit, description)
        created += 1

    if created:
        message = f'週期性登記已新增 {created} 筆。'
        if skipped:
            message += f'另有 {skipped} 筆因時段衝突未新增。'
        messages.success(request, message)
    else:
        messages.error(request, '所有週期性登記時段皆已有預約，未新增資料。')


def _update_entry(request, rooms_by_id):
    day = _parse_date(request.POST.get('date'))
    try:
        entry_id = int(request.POST.get('entry_id', ''))
        room_id = int(request.POST.get('room_id', ''))
    except ValueError:
        return HttpResponseBadRequest('Invalid entry')

    if room_id not in rooms_by_id:
        messages.error(request, '找不到指定場地。')
        return day, None
    if not _can_manage_entry(request, entry_id):
        messages.error(request, '只能修改自己登記的資料。')
        return day, room_id

    start_dt = _parse_local_datetime(day, request.POST.get('start_time'), '09:00')
    end_dt = _parse_local_datetime(day, request.POST.get('end_time'), '10:00')
    if end_dt <= start_dt:
        messages.error(request, '結束時間必須晚於開始時間。')
        return day, room_id

    name = (request.POST.get('name') or '').strip()
    use_unit = (request.POST.get('use_unit') or '').strip()
    description = (request.POST.get('description') or '').strip()
    modifier = _current_username(request)
    if not name:
        messages.error(request, '請輸入活動名稱。')
        return day, room_id

    start_ts = _to_ts(start_dt)
    end_ts = _to_ts(end_dt)
    if _has_conflict(room_id, start_ts, end_ts, exclude_id=entry_id):
        messages.error(request, '此時段已有預約，請改選其他時間。')
        return day, room_id

    with connection.cursor() as cursor:
        cursor.execute(
            f'''
            UPDATE {MRBS_DB}.mrbs_entry
            SET start_time = %s,
                end_time = %s,
                room_id = %s,
                modified_by = %s,
                name = %s,
                use_unit = %s,
                description = %s
            WHERE id = %s
            ''',
            [start_ts, end_ts, room_id, modifier, name, use_unit, description, entry_id],
        )
    messages.success(request, '場地登記已更新。')
    return day, room_id


def _delete_entry(request):
    try:
        entry_id = int(request.POST.get('entry_id', ''))
    except ValueError:
        return HttpResponseBadRequest('Invalid entry id')

    if not _can_manage_entry(request, entry_id):
        messages.error(request, '只能刪除自己登記的資料。')
        return None

    with connection.cursor() as cursor:
        cursor.execute(f'DELETE FROM {MRBS_DB}.mrbs_entry WHERE id = %s', [entry_id])
    messages.success(request, '場地登記已刪除。')
    return None


def export_bookings(request):
    selected_date = _parse_date(request.GET.get('date'))
    entries = _entries(selected_date, None, _current_username(request))
    response = HttpResponse(content_type='text/csv; charset=utf-8-sig')
    response['Content-Disposition'] = f'attachment; filename="facility-bookings-{selected_date.isoformat()}.csv"'
    response.write('\ufeff')
    writer = csv.writer(response)
    writer.writerow(['日期', '星期', '開始', '結束', '樓層', '場地', '容量', '活動名稱', '使用單位', '登記人', '備註'])
    for entry in entries:
        room = {
            'room_name': entry.get('room_name'),
            'sort_key': entry.get('sort_key'),
        }
        writer.writerow([
            selected_date.isoformat(),
            WEEKDAY_NAMES[selected_date.weekday()],
            entry.get('start_label', ''),
            entry.get('end_label', ''),
            _room_floor(room),
            entry.get('room_name', ''),
            entry.get('capacity', ''),
            entry.get('name', ''),
            entry.get('use_unit', ''),
            entry.get('create_by', ''),
            entry.get('description', ''),
        ])
    return response


def _maintenance_ensure_tables():
    with connection.cursor() as cursor:
        cursor.execute(
            f'''
            CREATE TABLE IF NOT EXISTS {MAINTENANCE_ITEM_TABLE} (
                id INT AUTO_INCREMENT PRIMARY KEY,
                source_key CHAR(40) NOT NULL UNIQUE,
                category VARCHAR(120) NOT NULL,
                facility_name VARCHAR(200) NOT NULL,
                description TEXT NOT NULL,
                owner VARCHAR(120) NOT NULL DEFAULT '',
                vendor VARCHAR(255) NOT NULL DEFAULT '',
                maintenance_cycle VARCHAR(120) NOT NULL DEFAULT '',
                created_at DATETIME NOT NULL,
                updated_at DATETIME NOT NULL,
                INDEX idx_maintenance_item_category (category),
                INDEX idx_maintenance_item_name (facility_name)
            )
            '''
        )
        cursor.execute(
            f'''
            CREATE TABLE IF NOT EXISTS {MAINTENANCE_RECORD_TABLE} (
                id INT AUTO_INCREMENT PRIMARY KEY,
                item_id INT NOT NULL,
                record_at DATETIME NOT NULL,
                note TEXT NOT NULL,
                created_at DATETIME NOT NULL,
                INDEX idx_maintenance_record_item_at (item_id, record_at),
                CONSTRAINT fk_maintenance_record_item
                    FOREIGN KEY (item_id) REFERENCES {MAINTENANCE_ITEM_TABLE}(id)
                    ON DELETE CASCADE
            )
            '''
        )


def _maintenance_source_key(category, facility_name):
    raw = f'{category.strip()}::{facility_name.strip()}'
    return hashlib.sha1(raw.encode('utf-8')).hexdigest()


def _maintenance_sheet_rows():
    with urlopen(MAINTENANCE_SHEET_CSV_URL, timeout=15) as response:
        csv_text = response.read().decode('utf-8-sig')

    reader = csv.reader(StringIO(csv_text))
    rows = list(reader)
    if not rows:
        return []

    headers = rows[0]
    date_columns = []
    for index, header in enumerate(headers[6:], start=6):
        header = (header or '').strip()
        if re.match(r'^\d{1,2}/\d{1,2}$', header):
            date_columns.append((index, header))

    parsed_rows = []
    for row in rows[1:]:
        padded = row + [''] * max(0, len(headers) - len(row))
        category = (padded[0] or '').strip()
        facility_name = (padded[1] or '').strip()
        if not category or not facility_name:
            continue
        records = []
        for index, label in date_columns:
            note = (padded[index] if index < len(padded) else '').strip()
            if not note:
                continue
            month, day = [int(part) for part in label.split('/', 1)]
            records.append({
                'record_at': datetime(MAINTENANCE_SHEET_YEAR, month, day, 9, 0),
                'note': note,
            })
        parsed_rows.append({
            'source_key': _maintenance_source_key(category, facility_name),
            'category': category,
            'facility_name': facility_name,
            'description': (padded[2] or '').strip(),
            'owner': (padded[3] or '').strip(),
            'vendor': (padded[4] or '').strip(),
            'maintenance_cycle': (padded[5] or '').strip(),
            'records': records,
        })
    return parsed_rows


def _maintenance_import_sheet(overwrite_existing=False):
    _maintenance_ensure_tables()
    imported = 0
    now = datetime.now(TZ).replace(tzinfo=None)
    rows = _maintenance_sheet_rows()
    with connection.cursor() as cursor:
        for row in rows:
            cursor.execute(
                f'SELECT id FROM {MAINTENANCE_ITEM_TABLE} WHERE source_key = %s',
                [row['source_key']],
            )
            existing = cursor.fetchone()
            if existing:
                item_id = existing[0]
                if overwrite_existing:
                    cursor.execute(
                        f'''
                        UPDATE {MAINTENANCE_ITEM_TABLE}
                        SET category = %s,
                            facility_name = %s,
                            description = %s,
                            owner = %s,
                            vendor = %s,
                            maintenance_cycle = %s,
                            updated_at = %s
                        WHERE id = %s
                        ''',
                        [
                            row['category'], row['facility_name'], row['description'],
                            row['owner'], row['vendor'], row['maintenance_cycle'],
                            now, item_id,
                        ],
                    )
            else:
                cursor.execute(
                    f'''
                    INSERT INTO {MAINTENANCE_ITEM_TABLE}
                      (source_key, category, facility_name, description, owner,
                       vendor, maintenance_cycle, created_at, updated_at)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                    ''',
                    [
                        row['source_key'], row['category'], row['facility_name'],
                        row['description'], row['owner'], row['vendor'],
                        row['maintenance_cycle'], now, now,
                    ],
                )
                item_id = cursor.lastrowid
                imported += 1

            for record in row['records']:
                cursor.execute(
                    f'''
                    SELECT id FROM {MAINTENANCE_RECORD_TABLE}
                    WHERE item_id = %s AND record_at = %s AND note = %s
                    ''',
                    [item_id, record['record_at'], record['note']],
                )
                if cursor.fetchone():
                    continue
                cursor.execute(
                    f'''
                    INSERT INTO {MAINTENANCE_RECORD_TABLE}
                      (item_id, record_at, note, created_at)
                    VALUES (%s, %s, %s, %s)
                    ''',
                    [item_id, record['record_at'], record['note'], now],
                )
    return imported


def _maintenance_item_count():
    _maintenance_ensure_tables()
    with connection.cursor() as cursor:
        cursor.execute(f'SELECT COUNT(*) FROM {MAINTENANCE_ITEM_TABLE}')
        return cursor.fetchone()[0]


def _maintenance_items():
    _maintenance_ensure_tables()
    with connection.cursor() as cursor:
        cursor.execute(
            f'''
            SELECT id, category, facility_name, description, owner, vendor, maintenance_cycle
            FROM {MAINTENANCE_ITEM_TABLE}
            ORDER BY category, facility_name, id
            '''
        )
        return _dictfetchall(cursor)


def _maintenance_records(item_id):
    with connection.cursor() as cursor:
        cursor.execute(
            f'''
            SELECT id, item_id, record_at, note
            FROM {MAINTENANCE_RECORD_TABLE}
            WHERE item_id = %s
            ORDER BY record_at DESC, id DESC
            ''',
            [item_id],
        )
        records = _dictfetchall(cursor)
    for record in records:
        if record.get('record_at'):
            record['record_at_input'] = record['record_at'].strftime('%Y-%m-%dT%H:%M')
            record['record_at_label'] = record['record_at'].strftime('%Y-%m-%d %H:%M')
    return records


def _maintenance_tree(items):
    tree = []
    by_category = {}
    for item in items:
        category = item['category'] or '未分類'
        group = by_category.get(category)
        if group is None:
            group = {'category': category, 'items': []}
            by_category[category] = group
            tree.append(group)
        group['items'].append(item)
    return tree


def _maintenance_selected_item(items, selected_id):
    if selected_id:
        for item in items:
            if item['id'] == selected_id:
                return item
    return items[0] if items else None


def _maintenance_update_item(request):
    try:
        item_id = int(request.POST.get('item_id') or '')
    except ValueError:
        messages.error(request, '找不到指定的維護項目。')
        return None

    facility_name = (request.POST.get('facility_name') or '').strip()
    if not facility_name:
        messages.error(request, '請輸入設施名稱。')
        return item_id

    with connection.cursor() as cursor:
        cursor.execute(
            f'''
            UPDATE {MAINTENANCE_ITEM_TABLE}
            SET facility_name = %s,
                owner = %s,
                vendor = %s,
                maintenance_cycle = %s,
                updated_at = %s
            WHERE id = %s
            ''',
            [
                facility_name,
                (request.POST.get('owner') or '').strip(),
                (request.POST.get('vendor') or '').strip(),
                (request.POST.get('maintenance_cycle') or '').strip(),
                datetime.now(TZ).replace(tzinfo=None),
                item_id,
            ],
        )
    messages.success(request, '日常維護項目已更新。')
    return item_id


def _maintenance_add_record(request):
    try:
        item_id = int(request.POST.get('item_id') or '')
    except ValueError:
        messages.error(request, '找不到指定的維護項目。')
        return None

    record_at_raw = (request.POST.get('record_at') or '').strip()
    try:
        record_at = datetime.strptime(record_at_raw, '%Y-%m-%dT%H:%M')
    except ValueError:
        messages.error(request, '請輸入正確的維護日期時間。')
        return item_id

    note = (request.POST.get('record_note') or '').strip()
    with connection.cursor() as cursor:
        cursor.execute(
            f'''
            INSERT INTO {MAINTENANCE_RECORD_TABLE}
              (item_id, record_at, note, created_at)
            VALUES (%s, %s, %s, %s)
            ''',
            [item_id, record_at, note, datetime.now(TZ).replace(tzinfo=None)],
        )
    messages.success(request, '維護紀錄已新增。')
    return item_id


def _maintenance_delete_record(request):
    try:
        item_id = int(request.POST.get('item_id') or '')
        record_id = int(request.POST.get('record_id') or '')
    except ValueError:
        messages.error(request, '找不到指定的維護紀錄。')
        return None

    with connection.cursor() as cursor:
        cursor.execute(
            f'DELETE FROM {MAINTENANCE_RECORD_TABLE} WHERE id = %s AND item_id = %s',
            [record_id, item_id],
        )
    messages.success(request, '維護紀錄已刪除。')
    return item_id


def maintenance_page(request):
    if _maintenance_item_count() == 0:
        try:
            imported = _maintenance_import_sheet()
            if imported:
                messages.success(request, f'已從 2025 試算表匯入 {imported} 個維護項目。')
        except Exception as exc:
            messages.error(request, f'無法從試算表匯入資料：{exc}')

    selected_id = None
    if request.method == 'POST':
        action = request.POST.get('action')
        if action == 'update_item':
            selected_id = _maintenance_update_item(request)
        elif action == 'add_record':
            selected_id = _maintenance_add_record(request)
        elif action == 'delete_record':
            selected_id = _maintenance_delete_record(request)
        elif action == 'import_sheet':
            try:
                imported = _maintenance_import_sheet(overwrite_existing=True)
                messages.success(request, f'已重新匯入試算表資料，新增 {imported} 個項目。')
            except Exception as exc:
                messages.error(request, f'無法從試算表匯入資料：{exc}')
            selected_id = int(request.POST.get('item_id') or 0) or None
        else:
            return HttpResponseBadRequest('Unknown action')
        query = f'?item={selected_id}' if selected_id else ''
        return redirect('/facility/maintenance/' + query)

    try:
        selected_id = int(request.GET.get('item') or 0) or None
    except ValueError:
        selected_id = None

    items = _maintenance_items()
    selected_item = _maintenance_selected_item(items, selected_id)
    records = _maintenance_records(selected_item['id']) if selected_item else []
    return render(request, 'facility/maintenance.html', {
        'tree': _maintenance_tree(items),
        'items': items,
        'selected_item': selected_item,
        'records': records,
        'now_input': datetime.now(TZ).strftime('%Y-%m-%dT%H:%M'),
        'sheet_url': f'https://docs.google.com/spreadsheets/d/{MAINTENANCE_SHEET_ID}/edit?usp=sharing',
    })


def room_admin_page(request):
    rooms = _rooms()
    rooms_by_id = {room['id']: room for room in rooms}
    if request.method == 'POST':
        action = request.POST.get('action')
        if action == 'create_room':
            _create_room(request)
        elif action == 'update_room':
            _update_room(request)
        elif action == 'delete_room':
            _delete_room(request)
        elif action == 'create_recurring_booking':
            _create_recurring_admin_booking(request, rooms_by_id)
        else:
            return HttpResponseBadRequest('Unknown action')
        return redirect('/facility/rooms/')

    for room in rooms:
        room['floor'] = _room_floor(room)
    return render(request, 'facility/rooms.html', {
        'rooms': sorted(rooms, key=_room_sort_key),
        'floor_order': FLOOR_ORDER,
        'default_creator': _current_username(request),
    })


def booking_page(request):
    rooms = _rooms()
    rooms_by_id = {room['id']: room for room in rooms}
    selected_date = _parse_date(request.GET.get('date'))
    selected_room = request.GET.get('room')
    try:
        selected_room_id = int(selected_room) if selected_room else None
    except ValueError:
        selected_room_id = None

    if request.method == 'POST':
        action = request.POST.get('action')
        if action == 'create':
            selected_date, selected_room_id = _create_entry(request, rooms_by_id)
        elif action == 'update':
            selected_date, selected_room_id = _update_entry(request, rooms_by_id)
        elif action == 'delete':
            result = _delete_entry(request)
            if result is not None:
                return result
        else:
            return HttpResponseBadRequest('Unknown action')
        query = f'?date={selected_date.isoformat()}'
        return redirect('/facility/booking/' + query)

    selected_room_id = None
    current_username = _current_username(request)
    entries = _entries(selected_date, None, current_username)
    prev_day = selected_date - timedelta(days=1)
    next_day = selected_date + timedelta(days=1)
    selected_room_obj = rooms_by_id.get(selected_room_id)
    floor_sections = _build_floor_sections(rooms, entries, selected_date)

    return render(request, 'facility/booking.html', {
        'rooms': rooms,
        'entries': entries,
        'floor_sections': floor_sections,
        'selected_date': selected_date,
        'selected_weekday': WEEKDAY_NAMES[selected_date.weekday()],
        'selected_room_id': selected_room_id,
        'selected_room': selected_room_obj,
        'prev_day': prev_day,
        'next_day': next_day,
        'default_creator': current_username,
    })


def booking_daily_overview(request):
    selected_date = _parse_date(request.GET.get('date'))
    current_username = _current_username(request)
    rooms = _rooms()
    entries = _entries(selected_date, None, current_username)
    overview_rooms, floor_groups, overview_rows = _build_daily_overview(
        rooms,
        entries,
        selected_date,
    )

    return render(request, 'facility/booking_daily_overview.html', {
        'rooms': overview_rooms,
        'floor_groups': floor_groups,
        'rows': overview_rows,
        'entries': entries,
        'selected_date': selected_date,
        'selected_weekday': WEEKDAY_NAMES[selected_date.weekday()],
        'prev_day': selected_date - timedelta(days=1),
        'next_day': selected_date + timedelta(days=1),
    })



def _expense_ensure_tables():
    with connection.cursor() as cursor:
        cursor.execute(
            f'''
            CREATE TABLE IF NOT EXISTS {EXPENSE_CLAIM_TABLE} (
                id INT AUTO_INCREMENT PRIMARY KEY,
                claim_no VARCHAR(32) NOT NULL UNIQUE,
                applicant VARCHAR(120) NOT NULL,
                request_date DATE NOT NULL,
                payee VARCHAR(200) NOT NULL,
                payment_method VARCHAR(40) NOT NULL,
                bank_name VARCHAR(120) NOT NULL DEFAULT '',
                bank_branch VARCHAR(120) NOT NULL DEFAULT '',
                bank_account VARCHAR(120) NOT NULL DEFAULT '',
                ministry_group VARCHAR(160) NOT NULL DEFAULT '',
                receipt_count INT NOT NULL DEFAULT 0,
                total_amount DECIMAL(12, 2) NOT NULL DEFAULT 0,
                accepted_at DATETIME NULL,
                created_by VARCHAR(120) NOT NULL DEFAULT '',
                created_at DATETIME NOT NULL
            )
            '''
        )
        cursor.execute(f"SHOW COLUMNS FROM {EXPENSE_CLAIM_TABLE} LIKE 'accepted_at'")
        if not cursor.fetchone():
            cursor.execute(f"ALTER TABLE {EXPENSE_CLAIM_TABLE} ADD COLUMN accepted_at DATETIME NULL AFTER total_amount")
        cursor.execute(
            f'''
            CREATE TABLE IF NOT EXISTS {EXPENSE_CLAIM_ITEM_TABLE} (
                id INT AUTO_INCREMENT PRIMARY KEY,
                claim_id INT NOT NULL,
                item_name VARCHAR(200) NOT NULL DEFAULT '',
                budget_code VARCHAR(80) NOT NULL DEFAULT '',
                purpose VARCHAR(500) NOT NULL DEFAULT '',
                amount DECIMAL(12, 2) NOT NULL DEFAULT 0,
                sort_order INT NOT NULL DEFAULT 0,
                INDEX idx_expense_claim_item_claim_id (claim_id)
            )
            '''
        )


def _expense_decimal(value):
    try:
        amount = Decimal(str(value or '0').replace(',', '').strip())
    except (InvalidOperation, ValueError):
        return None
    if amount < 0:
        return None
    return amount.quantize(Decimal('0.01'))


def _expense_claim_no(cursor, created_at):
    prefix = f'EXP{created_at.strftime("%Y%m%d-%H%M%S")}'
    cursor.execute(f'SELECT COUNT(*) FROM {EXPENSE_CLAIM_TABLE} WHERE claim_no LIKE %s', [f'{prefix}-%'])
    sequence = int(cursor.fetchone()[0] or 0) + 1
    return f'{prefix}-{sequence:03d}'


def _expense_budget_queryset():
    from modules.budget.models import BudgetItem
    return BudgetItem.objects.exclude(budget_code='').order_by('category', 'budget_code', 'id')


def _expense_budget_choices():
    choices = []
    for item in _expense_budget_queryset():
        ratio = item.usage_ratio
        ratio_text = '-' if ratio is None else f'{ratio.quantize(Decimal("0.1"))}%'
        balance = item.balance or Decimal('0')
        choices.append({
            'code': item.budget_code,
            'category': item.category or '\u672a\u5206\u985e',
            'ministry': item.ministry or '',
            'ratio': ratio_text,
            'balance': str(balance),
            'balanceText': f'{balance:,.0f}',
        })
    return choices


def _expense_budget_choices_json():
    return json.dumps(_expense_budget_choices(), ensure_ascii=False)


def _expense_validate_budget_balances(items):
    totals = {}
    for item in items:
        if not item.get('item_name') or not item.get('budget_code') or not item.get('purpose'):
            raise ValueError('\u8acb\u78ba\u8a8d\u6bcf\u7b46\u8acb\u6b3e\u9805\u76ee\u7684\u8acb\u6b3e\u9805\u76ee\u3001\u9810\u7b97\u4ee3\u865f\u8207\u7528\u9014\u7686\u5df2\u586b\u5beb\u3002')
        if item['amount'] <= Decimal('0.00'):
            raise ValueError('\u8acb\u78ba\u8a8d\u6bcf\u7b46\u9805\u76ee\u7684\u91d1\u984d\u5fc5\u9808\u5927\u65bc 0\u3002')
        totals[item['budget_code']] = totals.get(item['budget_code'], Decimal('0.00')) + item['amount']
    budget_map = {}
    for budget in _expense_budget_queryset().filter(budget_code__in=totals.keys()):
        budget_map.setdefault(budget.budget_code, budget)
    for code, amount in totals.items():
        budget = budget_map.get(code)
        if not budget:
            raise ValueError(f'\u8acb\u9078\u64c7\u6709\u6548\u7684\u9810\u7b97\u4ee3\u865f\uff1a{code}')
        balance = budget.balance or Decimal('0.00')
        if amount > balance:
            raise ValueError(f'\u9810\u7b97\u4ee3\u865f {code} \u7684\u7533\u8acb\u91d1\u984d {amount:,.0f} \u9ad8\u65bc\u9918\u984d {balance:,.0f}\uff0c\u4e0d\u5141\u8a31\u9001\u51fa\u3002')


def _expense_items_from_post(post):
    names = post.getlist('item_name')
    budget_codes = post.getlist('budget_code')
    purposes = post.getlist('purpose')
    amounts = post.getlist('amount')
    items = []
    max_len = max(len(names), len(budget_codes), len(purposes), len(amounts), 0)
    for index in range(max_len):
        item = {
            'item_name': (names[index] if index < len(names) else '').strip(),
            'budget_code': (budget_codes[index] if index < len(budget_codes) else '').strip(),
            'purpose': (purposes[index] if index < len(purposes) else '').strip(),
            'amount': _expense_decimal(amounts[index] if index < len(amounts) else ''),
        }
        if not item['item_name'] and not item['budget_code'] and not item['purpose'] and item['amount'] in (None, Decimal('0.00')):
            continue
        if item['amount'] is None:
            raise ValueError('\u8acb\u78ba\u8a8d\u6bcf\u7b46\u9805\u76ee\u7684\u91d1\u984d\uff0c\u91d1\u984d\u4e0d\u53ef\u70ba\u8ca0\u6578\u3002')
        items.append(item)
    if not items:
        raise ValueError('\u8acb\u81f3\u5c11\u586b\u5beb\u4e00\u7b46\u8acb\u6b3e\u9805\u76ee\u3002')
    return items


def _expense_claim_from_post(request):
    post = request.POST
    items = _expense_items_from_post(post)
    receipt_count = len(items)
    claim = {
        'applicant': (post.get('applicant') or '').strip(),
        'request_date': (post.get('request_date') or '').strip(),
        'payee': (post.get('payee') or '').strip(),
        'payment_method': (post.get('payment_method') or '').strip(),
        'bank_name': (post.get('bank_name') or '').strip(),
        'bank_branch': (post.get('bank_branch') or '').strip(),
        'bank_account': (post.get('bank_account') or '').strip(),
        'ministry_group': (post.get('ministry_group') or '').strip(),
        'receipt_count': receipt_count,
        'created_by': _current_username(request) or (post.get('applicant') or '').strip(),
        'items': items,
        'total_amount': sum((item['amount'] for item in items), Decimal('0.00')),
    }
    try:
        claim['request_date_obj'] = datetime.strptime(claim['request_date'], '%Y-%m-%d').date()
    except ValueError:
        raise ValueError('\u8acb\u9078\u64c7\u6b63\u78ba\u7684\u7533\u8acb\u65e5\u671f\u3002')
    for key, message in [('applicant', '\u8acb\u586b\u5beb\u8acb\u6b3e\u4eba\u3002'), ('payee', '\u8acb\u586b\u5beb\u4ed8\u6b3e\u7d66\u3002'), ('payment_method', '\u8acb\u9078\u64c7\u4ed8\u6b3e\u65b9\u5f0f\u3002')]:
        if not claim[key]:
            raise ValueError(message)
    if claim['payment_method'] == '\u532f\u6b3e' and (not claim['bank_name'] or not claim['bank_branch'] or not claim['bank_account']):
        raise ValueError('\u4ed8\u6b3e\u65b9\u5f0f\u70ba\u532f\u6b3e\u6642\uff0c\u8acb\u586b\u5beb\u884c\u5eab\u540d\u3001\u5206\u884c\u8207\u8f49\u5165\u5e33\u865f\u3002')
    _expense_validate_budget_balances(items)
    return claim


def _expense_create_claim(claim):
    _expense_ensure_tables()
    created_at = datetime.now(TZ)
    with connection.cursor() as cursor:
        claim_no = _expense_claim_no(cursor, created_at)
        cursor.execute(f'''INSERT INTO {EXPENSE_CLAIM_TABLE} (claim_no, applicant, request_date, payee, payment_method, bank_name, bank_branch, bank_account, ministry_group, receipt_count, total_amount, created_by, created_at) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)''', [claim_no, claim['applicant'], claim['request_date_obj'], claim['payee'], claim['payment_method'], claim['bank_name'], claim['bank_branch'], claim['bank_account'], claim['ministry_group'], claim['receipt_count'], claim['total_amount'], claim['created_by'], created_at.replace(tzinfo=None)])
        cursor.execute('SELECT LAST_INSERT_ID()')
        claim_id = cursor.fetchone()[0]
        for index, item in enumerate(claim['items'], start=1):
            cursor.execute(f'''INSERT INTO {EXPENSE_CLAIM_ITEM_TABLE} (claim_id, item_name, budget_code, purpose, amount, sort_order) VALUES (%s, %s, %s, %s, %s, %s)''', [claim_id, item['item_name'], item['budget_code'], item['purpose'], item['amount'], index])
    return claim_no


def _expense_get_claim(claim_no):
    _expense_ensure_tables()
    with connection.cursor() as cursor:
        cursor.execute(f'''SELECT id, claim_no, applicant, request_date, payee, payment_method, bank_name, bank_branch, bank_account, ministry_group, receipt_count, total_amount, accepted_at, created_by, created_at FROM {EXPENSE_CLAIM_TABLE} WHERE claim_no = %s''', [claim_no])
        rows = _dictfetchall(cursor)
        if not rows:
            return None
        claim = rows[0]
        cursor.execute(f'''SELECT item_name, budget_code, purpose, amount, sort_order FROM {EXPENSE_CLAIM_ITEM_TABLE} WHERE claim_id = %s ORDER BY sort_order, id''', [claim['id']])
        claim['items'] = _dictfetchall(cursor)
    return claim


def _expense_claim_for_form(claim):
    if not claim:
        return None
    form_claim = dict(claim)
    request_date = form_claim.get('request_date')
    if hasattr(request_date, 'isoformat'):
        form_claim['request_date'] = request_date.isoformat()
    form_claim['receipt_count'] = form_claim.get('receipt_count') or 0
    items = []
    for item in form_claim.get('items') or []:
        form_item = dict(item)
        amount = form_item.get('amount')
        form_item['amount'] = '' if amount in (None, '') else str(amount).rstrip('0').rstrip('.')
        items.append(form_item)
    form_claim['items'] = items or [{'item_name': '', 'budget_code': '', 'purpose': '', 'amount': ''}]
    return form_claim


def _expense_recent_claims():
    _expense_ensure_tables()
    with connection.cursor() as cursor:
        cursor.execute(f'''SELECT claim_no, applicant, request_date, total_amount, accepted_at, created_at FROM {EXPENSE_CLAIM_TABLE} ORDER BY created_at DESC, id DESC''')
        return _dictfetchall(cursor)


def _expense_update_claim(claim_no, claim):
    _expense_ensure_tables()
    existing = _expense_get_claim(claim_no)
    if not existing:
        raise ValueError('\u627e\u4e0d\u5230\u8acb\u6b3e\u55ae')
    if existing.get('accepted_at'):
        raise ValueError('\u6b64\u8acb\u6b3e\u55ae\u5df2\u88ab\u5f8c\u7e8c\u6d41\u7a0b\u63a5\u53d7\uff0c\u4e0d\u80fd\u4fee\u6539\u3002')
    with connection.cursor() as cursor:
        cursor.execute(f'''UPDATE {EXPENSE_CLAIM_TABLE} SET applicant=%s, request_date=%s, payee=%s, payment_method=%s, bank_name=%s, bank_branch=%s, bank_account=%s, ministry_group=%s, receipt_count=%s, total_amount=%s, created_by=%s WHERE claim_no=%s''', [claim['applicant'], claim['request_date_obj'], claim['payee'], claim['payment_method'], claim['bank_name'], claim['bank_branch'], claim['bank_account'], claim['ministry_group'], claim['receipt_count'], claim['total_amount'], claim['created_by'], claim_no])
        cursor.execute(f'DELETE FROM {EXPENSE_CLAIM_ITEM_TABLE} WHERE claim_id = %s', [existing['id']])
        for index, item in enumerate(claim['items'], start=1):
            cursor.execute(f'''INSERT INTO {EXPENSE_CLAIM_ITEM_TABLE} (claim_id, item_name, budget_code, purpose, amount, sort_order) VALUES (%s, %s, %s, %s, %s, %s)''', [existing['id'], item['item_name'], item['budget_code'], item['purpose'], item['amount'], index])


def _expense_delete_claim(claim_no):
    _expense_ensure_tables()
    existing = _expense_get_claim(claim_no)
    if not existing:
        raise ValueError('\u627e\u4e0d\u5230\u8acb\u6b3e\u55ae')
    if existing.get('accepted_at'):
        raise ValueError('\u6b64\u8acb\u6b3e\u55ae\u5df2\u88ab\u5f8c\u7e8c\u6d41\u7a0b\u63a5\u53d7\uff0c\u4e0d\u80fd\u522a\u9664\u3002')
    with connection.cursor() as cursor:
        cursor.execute(f'DELETE FROM {EXPENSE_CLAIM_ITEM_TABLE} WHERE claim_id = %s', [existing['id']])
        cursor.execute(f'DELETE FROM {EXPENSE_CLAIM_TABLE} WHERE id = %s', [existing['id']])


def _expense_default_claim(request):
    applicant_name = _current_username(request) or ''
    bank_name = ''
    bank_account = ''
    if getattr(request, 'user', None) and request.user.is_authenticated:
        user = request.user
        profile = getattr(user, 'profile', None)
        applicant_name = getattr(profile, 'display_name', '') or user.get_full_name() or user.username or applicant_name
        try:
            from modules.eureka.models import StaffInfo
            staff_info = StaffInfo.objects.filter(user=user).first()
            if staff_info:
                applicant_name = staff_info.name or applicant_name
                bank_name = staff_info.bank_branch or ''
                bank_account = staff_info.bank_account or ''
        except Exception:
            pass
    return {'applicant': applicant_name, 'request_date': date.today().isoformat(), 'payee': applicant_name, 'payment_method': '\u532f\u6b3e', 'bank_name': bank_name, 'bank_branch': '', 'bank_account': bank_account, 'ministry_group': '', 'receipt_count': 0, 'items': [{'item_name': '', 'budget_code': '', 'purpose': '', 'amount': ''}]}


def expense_claim_page(request):
    _expense_ensure_tables()
    base_path = request.path.rstrip('/') or '/facility/expense-claims'
    edit_claim_no = request.GET.get('edit') or ''
    copy_claim_no = request.GET.get('copy') or ''
    new_claim = request.GET.get('new') == '1'
    editing_claim = _expense_get_claim(edit_claim_no) if edit_claim_no else None
    source_claim = _expense_get_claim(copy_claim_no) if copy_claim_no else None
    form_modal_open = bool(new_claim or editing_claim or source_claim)
    if editing_claim:
        claim = _expense_claim_for_form(editing_claim)
    elif source_claim:
        claim = _expense_claim_for_form(source_claim)
        defaults = _expense_default_claim(request)
        for key in ['applicant', 'request_date', 'payee', 'bank_name', 'bank_branch', 'bank_account']:
            claim[key] = defaults.get(key, '')
    else:
        claim = _expense_default_claim(request)
    if request.method == 'POST':
        form_modal_open = True
        action = request.POST.get('action') or 'save'
        form_claim_no = (request.POST.get('claim_no') or '').strip()
        try:
            if action == 'delete':
                if not form_claim_no:
                    raise ValueError('\u8acb\u5148\u9078\u64c7\u8acb\u6b3e\u55ae')
                _expense_delete_claim(form_claim_no)
                messages.success(request, f'\u5df2\u522a\u9664\u8acb\u6b3e\u55ae\uff1a{form_claim_no}')
                return redirect(f'{base_path}/')
            claim = _expense_claim_from_post(request)
            if form_claim_no:
                _expense_update_claim(form_claim_no, claim)
                messages.success(request, f'\u5df2\u66f4\u65b0\u8acb\u6b3e\u55ae\uff1a{form_claim_no}')
                return redirect(f'{base_path}/')
            claim_no = _expense_create_claim(claim)
            messages.success(request, f'\u5df2\u6210\u7acb\u55ae\u865f\uff1a{claim_no}')
            return redirect(f'{base_path}/')
        except ValueError as exc:
            messages.error(request, str(exc))
    claim_history = _expense_recent_claims()
    return render(request, 'facility/expense_claim.html', {'claim': claim, 'editing_claim': editing_claim, 'source_claim': source_claim, 'form_modal_open': form_modal_open, 'claim_history': claim_history, 'expense_claim_base_path': base_path, 'budget_choices_json': _expense_budget_choices_json()})


def _expense_register_pdf_font():
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.cidfonts import UnicodeCIDFont
    from reportlab.pdfbase.ttfonts import TTFont

    candidates = [
        'C:/Windows/Fonts/msjh.ttc',
        'C:/Windows/Fonts/msjh.ttf',
        'C:/Windows/Fonts/mingliu.ttc',
        '/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc',
        '/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc',
    ]
    for font_path in candidates:
        if Path(font_path).exists():
            try:
                pdfmetrics.registerFont(TTFont('ExpenseCJK', font_path))
                return 'ExpenseCJK'
            except Exception:
                continue
    for cid_font in ['MSung-Light', 'STSong-Light']:
        try:
            pdfmetrics.registerFont(UnicodeCIDFont(cid_font))
            return cid_font
        except Exception:
            continue
    return 'Helvetica'


def _expense_pdf_text(canvas, text, x, y, max_chars=36, line_height=13):
    value = str(text or '')
    lines = [value[index:index + max_chars] for index in range(0, len(value), max_chars)] or ['']
    for offset, line in enumerate(lines[:3]):
        canvas.drawString(x, y - offset * line_height, line)
    return y - max(len(lines[:3]), 1) * line_height


def expense_claim_voucher_pdf(request, claim_no):
    claim = _expense_get_claim(claim_no)
    if not claim:
        return HttpResponseBadRequest('Expense claim not found')

    from reportlab.graphics.barcode.qr import QrCodeWidget
    from reportlab.graphics import renderPDF
    from reportlab.graphics.shapes import Drawing
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.units import mm
    from reportlab.pdfgen import canvas

    buffer = BytesIO()
    page = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4
    font_name = _expense_register_pdf_font()
    barcode_value = claim_no

    margin_x = 18 * mm
    y = height - 18 * mm
    title = '\u5317\u9580\u8acb\u6b3e\u55ae'
    page.setFont(font_name, 18)
    title_x = margin_x
    page.drawString(title_x, y, title)
    page.drawString(title_x + 0.35, y, title)

    qr_size = 18 * mm
    qr_widget = QrCodeWidget(barcode_value)
    qr_bounds = qr_widget.getBounds()
    qr_width = qr_bounds[2] - qr_bounds[0]
    qr_height = qr_bounds[3] - qr_bounds[1]
    qr_drawing = Drawing(qr_size, qr_size, transform=[qr_size / qr_width, 0, 0, qr_size / qr_height, 0, 0])
    qr_drawing.add(qr_widget)
    qr_x = width - margin_x - qr_size
    qr_y = y - 6 * mm
    renderPDF.draw(qr_drawing, page, qr_x, qr_y)
    page.setFont(font_name, 6)
    page.drawCentredString(qr_x + qr_size / 2, qr_y - 1 * mm, claim_no)
    y -= 24 * mm

    page.setFont(font_name, 10)
    page.drawString(margin_x, y, f'請款人：{claim["applicant"] or ""}')
    page.drawString(margin_x + 78 * mm, y, f'日期：{claim["request_date"]}')
    y -= 9 * mm

    page.drawString(margin_x, y, f'付款給：{claim["payee"] or ""}')
    page.drawString(margin_x + 90 * mm, y, f'付款方式：{claim["payment_method"] or ""}')
    y -= 8 * mm
    page.drawString(margin_x, y, f'行庫名：{claim["bank_name"] or ""}')
    page.drawString(margin_x + 90 * mm, y, f'分行：{claim["bank_branch"] or ""}')
    y -= 8 * mm
    page.drawString(margin_x, y, f'轉入帳號：{claim["bank_account"] or ""}')
    y -= 8 * mm
    page.drawString(margin_x, y, f'部門/團契/小組：{claim["ministry_group"] or ""}')
    page.drawString(margin_x + 88 * mm, y, f'憑證張數：{claim["receipt_count"] or 0}')
    page.drawString(margin_x + 128 * mm, y, f'總計金額：{claim["total_amount"]}')
    y -= 12 * mm

    table_x = margin_x
    table_w = width - margin_x * 2
    col_widths = [38 * mm, 88 * mm, table_w - 126 * mm]
    row_h = 10 * mm
    page.setStrokeColor(colors.black)
    page.setLineWidth(0.7)
    page.rect(table_x, y - row_h, table_w, row_h)
    x = table_x
    headers = ['預算代號', '用途', '金額']
    for index, header in enumerate(headers):
        page.drawString(x + 2 * mm, y - 6.5 * mm, header)
        if index < len(col_widths) - 1:
            x += col_widths[index]
            page.line(x, y, x, y - row_h)
    y -= row_h

    item_rows = max(len(claim['items']), 4)
    for index in range(item_rows):
        item = claim['items'][index] if index < len(claim['items']) else {}
        page.rect(table_x, y - row_h, table_w, row_h)
        x = table_x
        page.drawString(x + 2 * mm, y - 6.5 * mm, str(item.get('budget_code') or ''))
        x += col_widths[0]
        page.line(x, y, x, y - row_h)
        item_text = str(item.get('purpose') or '')
        if item.get('item_name') and item.get('item_name') not in item_text:
            item_text = f'{item.get("item_name")} {item_text}'.strip()
        page.drawString(x + 2 * mm, y - 6.5 * mm, item_text[:34])
        x += col_widths[1]
        page.line(x, y, x, y - row_h)
        amount = item.get('amount')
        page.drawRightString(table_x + table_w - 2 * mm, y - 6.5 * mm, '' if amount in (None, '') else str(amount))
        y -= row_h

    y -= 10 * mm
    sign_w = table_w / 4
    page.rect(table_x, y - 20 * mm, table_w, 20 * mm)
    for index, label in enumerate(['主任牧師', '部門區牧', '會計', '出納']):
        x = table_x + sign_w * index
        if index:
            page.line(x, y, x, y - 20 * mm)
        page.drawCentredString(x + sign_w / 2, y - 6 * mm, label)
    y -= 30 * mm

    page.setDash(3, 3)
    page.line(margin_x, y, width - margin_x, y)
    page.setDash()
    y -= 8 * mm
    page.setFont(font_name, 12)
    page.drawCentredString(width / 2, y, '憑證請黏貼在虛線以下以及背面')
    y -= 8 * mm
    page.setDash(3, 3)
    page.line(margin_x, y, width - margin_x, y)
    page.setDash()

    page.showPage()
    page.save()
    response = HttpResponse(buffer.getvalue(), content_type='application/pdf')
    response['Content-Disposition'] = f'inline; filename="{claim_no}.pdf"'
    return response
