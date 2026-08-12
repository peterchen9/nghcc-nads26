import calendar
import csv
import json
from datetime import date, datetime, timedelta
from io import StringIO
from urllib.parse import urlencode
from urllib.request import urlopen

from django.contrib import messages
from django.contrib.auth import get_user_model, update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django import forms
from django.db import connection, transaction
from django.db.utils import OperationalError, ProgrammingError
from django.http import HttpResponse, HttpResponseBadRequest
from django.shortcuts import redirect, render

from modules.facility.views import expense_claim_page, expense_claim_voucher_pdf


STAFF_LEAVE_TABLE = 'staff_leave_entry'
STAFF_LEAVE_IMPORT_SOURCE = 'google-sheet-2026'
STAFF_LEAVE_YEAR = 2026
STAFF_LEAVE_SHEET_BASE_URL = 'https://docs.google.com/spreadsheets/d/e/2PACX-1vS5G7sL_shPun-R-HQ3Yn4NjnGEapP9RkvS7fTBhgGBrakjutdjqdPRPPpyAqetXA/pub'
CHURCH_CALENDAR_TABLE = 'staff_church_calendar_entry'
CHURCH_CALENDAR_IMPORT_SOURCE = 'google-sheet-2026-calendar'
CHURCH_CALENDAR_SHEET_BASE_URL = 'https://docs.google.com/spreadsheets/d/15bjkHQDuD1P2oDS8amjzAQ1SedoGB3qr55EtHjmdCqk/gviz/tq'
CHURCH_CALENDAR_SHEET_NAME = '2026行事曆'
STAFF_LEAVE_SHEET_GIDS = {
    '2026-01': '1490228276',
    '2026-02': '716472344',
    '2026-03': '212478393',
    '2026-04': '323657287',
    '2026-05': '25515846',
    '2026-06': '643088677',
    '2026-07': '1519918352',
    '2026-08': '2071719571',
    '2026-09': '973562380',
    '2026-10': '826126609',
    '2026-11': '117424320',
    '2026-12': '1003563016',
}
LEAVE_CODES = {'補', '休', '特', '公', '其他', '病假', '事假', '婚假', '陪/產假', '喪', '育嬰'}
LEAVE_PARTS = {'am': '上午', 'pm': '下午'}
LEAVE_EDITOR_CODE_OPTIONS = [
    ('休', '例休'),
    ('特', '特休'),
    ('補', '補休'),
    ('公', '公假'),
    ('其他', '其他'),
    ('病假', '病假'),
    ('事假', '事假'),
    ('婚假', '婚假'),
    ('陪/產假', '陪產'),
    ('育嬰', '育嬰'),
    ('喪', '喪假'),
]
HR_LEAVE_SUMMARY_METRICS = [
    ('當月總計', None),
    ('例休', '休'),
    ('特休', '特'),
    ('補休', '補'),
    ('公假', '公'),
    ('其他', '其他'),
    ('病假', '病假'),
    ('事假', '事假'),
    ('婚假', '婚假'),
    ('陪產', '陪/產假'),
    ('育嬰', '育嬰'),
    ('喪假', '喪'),
]
STAFF_LEAVE_DISPLAY_ORDER = [
    '明月',
    '德官',
    '明珠',
    '玉筍',
    '宜庭',
    '仲甫',
    '慕聖',
    '沐恩',
    '囿余',
    '小慧',
    '文正',
    '美美',
    '惠萍',
    '依蓮',
    '宗英',
    '方正',
    '慧芝',
    '文秀',
    '彼得陳',
]
STAFF_LEAVE_FULL_NAMES = {
    '明月': '林明月',
    '德官': '董德官',
    '明珠': '羅明珠',
    '玉筍': '周玉筍',
    '宜庭': '何宜庭',
    '仲甫': '鄭仲甫',
    '慕聖': '張慕聖',
    '沐恩': '趙沐恩',
    '囿余': '陳囿余',
    '小慧': '謝淑慧',
    '文正': '林文正',
    '美美': '黃美美',
    '惠萍': '張惠萍',
    '依蓮': '陳依蓮',
    '宗英': '楊宗英',
    '方正': '施方正',
    '慧芝': '郭慧芝',
    '文秀': '蔡文秀',
    '彼得陳': '陳潘傳',
}
STAFF_LEAVE_CANONICAL_NAMES = {
    '林明月': '明月',
    '董德官': '德官',
    '德官 董': '德官',
    '德官董': '德官',
    '羅明珠': '明珠',
    '周玉筍': '玉筍',
    '何宜庭': '宜庭',
    '鄭仲甫': '仲甫',
    '張慕聖': '慕聖',
    '趙沐恩': '沐恩',
    '陳囿余': '囿余',
    '謝淑慧': '小慧',
    '林文正': '文正',
    '黃美美': '美美',
    '張惠萍': '惠萍',
    '陳依蓮': '依蓮',
    '楊宗英': '宗英',
    '施方正': '方正',
    '方正 施': '方正',
    '方正施': '方正',
    '郭慧芝': '慧芝',
    '蔡文秀': '文秀',
    'peterchen': '彼得陳',
    '潘傳': '彼得陳',
    '陳潘傳': '彼得陳',
    '彼得 陳': '彼得陳',
}
LEGACY_HEADER_SKIP_NAMES = {'\u661f\u671f', '\u6559\u6703\u884c\u653f'}
LEGACY_OTHER_CODE = '\u5176\u4ed6'
LEGACY_CODE_PREFIXES = {'\u88dc', '\u4f11', '\u7279', '\u516c'}
LEGACY_AM_PREFIX = '\u4e0a'
LEGACY_PM_PREFIX = '\u4e0b'
CHURCH_CALENDAR_FIELD_NAMES = [
    'church_activity',
    'work_plan',
    'staff_leave_note',
    'holiday_social',
    'note',
]


class ProfileForm(forms.Form):
    username = forms.CharField(label='帳號', required=False, disabled=True)
    first_name = forms.CharField(label='名字', required=False, max_length=150)
    last_name = forms.CharField(label='姓氏', required=False, max_length=150)
    email = forms.EmailField(label='電子郵件', required=False, max_length=254)

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.user = user
        if user and not self.is_bound:
            self.fields['username'].initial = user.get_username()
            self.fields['first_name'].initial = user.first_name
            self.fields['last_name'].initial = user.last_name
            self.fields['email'].initial = user.email

    def clean_email(self):
        email = (self.cleaned_data.get('email') or '').strip()
        if not email:
            return ''

        User = get_user_model()
        duplicate = User.objects.filter(email__iexact=email).exclude(pk=self.user.pk).exists()
        if duplicate:
            raise forms.ValidationError('這個電子郵件已被其他帳號使用。')
        return email

    def save(self):
        self.user.first_name = self.cleaned_data['first_name'].strip()
        self.user.last_name = self.cleaned_data['last_name'].strip()
        self.user.email = self.cleaned_data['email']
        self.user.save(update_fields=['first_name', 'last_name', 'email'])
        return self.user


class CustomPasswordChangeForm(forms.Form):
    old_password = forms.CharField(label='目前密碼', widget=forms.PasswordInput)
    new_password1 = forms.CharField(label='新密碼', widget=forms.PasswordInput)
    new_password2 = forms.CharField(label='確認新密碼', widget=forms.PasswordInput)

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.user = user

    def clean_old_password(self):
        old_password = self.cleaned_data.get('old_password') or ''
        if not self.user.check_password(old_password):
            raise forms.ValidationError('目前密碼不正確。')
        return old_password

    def clean(self):
        cleaned_data = super().clean()
        new_password1 = cleaned_data.get('new_password1') or ''
        new_password2 = cleaned_data.get('new_password2') or ''

        if new_password1 and new_password2 and new_password1 != new_password2:
            self.add_error('new_password2', '兩次輸入的新密碼不一致。')

        if new_password1:
            try:
                validate_password(new_password1, self.user)
            except ValidationError as exc:
                self.add_error('new_password1', exc)

        return cleaned_data

    def save(self):
        self.user.set_password(self.cleaned_data['new_password1'])
        self.user.save(update_fields=['password'])
        return self.user


@login_required
def profile_page(request):
    if request.method == 'POST':
        form = ProfileForm(request.POST, user=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, '個人資料已更新。')
            return redirect('staff-profile')
    else:
        form = ProfileForm(user=request.user)

    return render(request, 'staff/profile.html', {'form': form})


@login_required
def password_change_page(request):
    if request.method == 'POST':
        form = CustomPasswordChangeForm(request.POST, user=request.user)
        if form.is_valid():
            user = form.save()
            update_session_auth_hash(request, user)
            messages.success(request, '密碼已更新。')
            return redirect('staff-password-change')
    else:
        form = CustomPasswordChangeForm(user=request.user)

    return render(request, 'staff/password_change.html', {'form': form})


@login_required
def planned_page(request, unused_path=None):
    return HttpResponse('此功能尚未開放。')


def _leave_ensure_table():
    with connection.cursor() as cursor:
        if connection.vendor == 'sqlite':
            cursor.execute(
                f'''
                CREATE TABLE IF NOT EXISTS {STAFF_LEAVE_TABLE} (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    staff_user VARCHAR(150) NOT NULL,
                    staff_name VARCHAR(200) NOT NULL DEFAULT '',
                    leave_date DATE NOT NULL,
                    day_part VARCHAR(8) NOT NULL,
                    code VARCHAR(16) NOT NULL,
                    description VARCHAR(500) NOT NULL DEFAULT '',
                    source VARCHAR(80) NOT NULL DEFAULT '',
                    created_at DATETIME NOT NULL,
                    updated_at DATETIME NOT NULL,
                    UNIQUE (staff_user, leave_date, day_part)
                )
                '''
            )
            cursor.execute(f'CREATE INDEX IF NOT EXISTS idx_staff_leave_month ON {STAFF_LEAVE_TABLE} (leave_date)')
            cursor.execute(f'CREATE INDEX IF NOT EXISTS idx_staff_leave_user_month ON {STAFF_LEAVE_TABLE} (staff_user, leave_date)')
        else:
            cursor.execute(
                f'''
                CREATE TABLE IF NOT EXISTS {STAFF_LEAVE_TABLE} (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    staff_user VARCHAR(150) NOT NULL,
                    staff_name VARCHAR(200) NOT NULL DEFAULT '',
                    leave_date DATE NOT NULL,
                    day_part VARCHAR(8) NOT NULL,
                    code VARCHAR(16) NOT NULL,
                    description VARCHAR(500) NOT NULL DEFAULT '',
                    source VARCHAR(80) NOT NULL DEFAULT '',
                    created_at DATETIME NOT NULL,
                    updated_at DATETIME NOT NULL,
                    UNIQUE KEY uniq_staff_leave_slot (staff_user, leave_date, day_part),
                    INDEX idx_staff_leave_month (leave_date),
                    INDEX idx_staff_leave_user_month (staff_user, leave_date)
                )
                '''
            )
            cursor.execute(f'SHOW COLUMNS FROM {STAFF_LEAVE_TABLE} LIKE %s', ['source'])
            if not cursor.fetchone():
                cursor.execute(
                    f'''
                    ALTER TABLE {STAFF_LEAVE_TABLE}
                    ADD COLUMN source VARCHAR(80) NOT NULL DEFAULT ''
                    AFTER description
                    '''
                )


def _church_calendar_ensure_table():
    with connection.cursor() as cursor:
        if connection.vendor == 'sqlite':
            cursor.execute(
                f'''
                CREATE TABLE IF NOT EXISTS {CHURCH_CALENDAR_TABLE} (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    event_date DATE NOT NULL,
                    weekday VARCHAR(8) NOT NULL DEFAULT '',
                    church_activity TEXT NOT NULL,
                    work_plan TEXT NOT NULL,
                    staff_leave_note TEXT NOT NULL,
                    holiday_social TEXT NOT NULL,
                    note TEXT NOT NULL,
                    source VARCHAR(80) NOT NULL DEFAULT '',
                    created_at DATETIME NOT NULL,
                    updated_at DATETIME NOT NULL,
                    UNIQUE (event_date)
                )
                '''
            )
            cursor.execute(f'CREATE INDEX IF NOT EXISTS idx_staff_church_calendar_month ON {CHURCH_CALENDAR_TABLE} (event_date)')
        else:
            cursor.execute(
                f'''
                CREATE TABLE IF NOT EXISTS {CHURCH_CALENDAR_TABLE} (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    event_date DATE NOT NULL,
                    weekday VARCHAR(8) NOT NULL DEFAULT '',
                    church_activity TEXT NOT NULL,
                    work_plan TEXT NOT NULL,
                    staff_leave_note TEXT NOT NULL,
                    holiday_social TEXT NOT NULL,
                    note TEXT NOT NULL,
                    source VARCHAR(80) NOT NULL DEFAULT '',
                    created_at DATETIME NOT NULL,
                    updated_at DATETIME NOT NULL,
                    UNIQUE KEY uniq_staff_church_calendar_date (event_date),
                    INDEX idx_staff_church_calendar_month (event_date)
                )
                '''
            )


def _month_start(day):
    return date(day.year, day.month, 1)


def _add_months(day, offset):
    month_index = day.year * 12 + day.month - 1 + offset
    return date(month_index // 12, month_index % 12 + 1, 1)


def _parse_month(value):
    if not value:
        return _month_start(date.today())
    try:
        parsed = datetime.strptime(value, '%Y-%m').date()
    except ValueError:
        return _month_start(date.today())
    return _month_start(parsed)


def _parse_leave_date(value, fallback_month):
    if not value:
        return fallback_month
    try:
        return datetime.strptime(value, '%Y-%m-%d').date()
    except ValueError:
        return fallback_month


def _month_end(month_start):
    return _add_months(month_start, 1) - timedelta(days=1)


def _is_leave_month_locked(month_start, today=None):
    today = today or date.today()
    current_month = _month_start(today)
    previous_month = _add_months(current_month, -1)
    if month_start < previous_month:
        return True
    return month_start == previous_month and today.day >= 5


def _staff_display_name(user):
    full_name = user.get_full_name().strip()
    return full_name or user.get_username()


def _staff_user_aliases(user):
    alias_map = _staff_name_aliases()
    username = user.get_username()
    display_name = _staff_display_name(user)
    canonical_name = _canonical_staff_name(username, alias_map)
    if canonical_name == username:
        canonical_name = _canonical_staff_name(display_name, alias_map)
    aliases = [username, display_name, canonical_name]
    aliases.extend(
        alias
        for alias, canonical in alias_map.items()
        if canonical == canonical_name
    )
    return [alias for index, alias in enumerate(aliases) if alias and alias not in aliases[:index]]


def _compact_staff_name(name):
    return ''.join(str(name or '').split())


def _canonical_staff_name(name, alias_map=None):
    alias_map = alias_map or STAFF_LEAVE_CANONICAL_NAMES
    text = str(name or '').strip()
    compact = _compact_staff_name(text)
    return alias_map.get(text, alias_map.get(compact, text))


def _staff_name_aliases():
    aliases = dict(STAFF_LEAVE_CANONICAL_NAMES)
    for alias, canonical in list(aliases.items()):
        aliases.setdefault(_compact_staff_name(alias), canonical)
    try:
        from modules.eureka.models import StaffInfo

        staff_records = StaffInfo.objects.select_related('user').all()
        for staff in staff_records:
            canonical_name = _canonical_staff_name(staff.name, aliases)
            aliases[staff.name] = canonical_name
            aliases[_compact_staff_name(staff.name)] = canonical_name
            if staff.user_id:
                username = staff.user.get_username()
                full_name = staff.user.get_full_name().strip()
                aliases[username] = canonical_name
                if full_name:
                    aliases[full_name] = canonical_name
                    aliases[_compact_staff_name(full_name)] = canonical_name

        for user in get_user_model().objects.filter(is_active=True):
            full_name = user.get_full_name().strip()
            canonical_name = _canonical_staff_name(full_name, aliases)
            if canonical_name not in STAFF_LEAVE_DISPLAY_ORDER:
                continue
            aliases.setdefault(user.get_username(), canonical_name)
            aliases.setdefault(full_name, canonical_name)
            aliases.setdefault(_compact_staff_name(full_name), canonical_name)
    except (OperationalError, ProgrammingError):
        pass
    return aliases


def _staff_full_name_map(alias_map=None):
    alias_map = alias_map or _staff_name_aliases()
    full_names = dict(STAFF_LEAVE_FULL_NAMES)
    try:
        from modules.eureka.models import StaffInfo

        for staff in StaffInfo.objects.exclude(name=''):
            staff_name = staff.name.strip()
            canonical_name = _canonical_staff_name(staff_name, alias_map)
            if (
                canonical_name in STAFF_LEAVE_DISPLAY_ORDER
                and staff_name != canonical_name
                and len(staff_name) >= len(full_names.get(canonical_name, canonical_name))
            ):
                full_names[canonical_name] = staff_name
    except (OperationalError, ProgrammingError):
        pass
    return full_names


def _month_options(today):
    selected_range = []
    for month_number in range(1, 13):
        month = date(STAFF_LEAVE_YEAR, month_number, 1)
        is_locked = _is_leave_month_locked(month, today)
        selected_range.append({
            'value': month.strftime('%Y-%m'),
            'label': f'{month.month}月已鎖定' if is_locked else f'{month.month}月',
            'is_locked': is_locked,
        })
    return selected_range


def _calendar_weeks(month_start):
    weeks = []
    for week in calendar.Calendar(firstweekday=6).monthdatescalendar(month_start.year, month_start.month):
        weeks.append([
            {
                'iso': day.isoformat(),
                'day': day.day,
                'in_month': day.month == month_start.month,
            }
            for day in week
        ])
    return weeks


def _normalize_leave_text(value):
    return str(value or '').replace('\u3000', ' ').strip()


def _legacy_leave_code_and_description(value):
    text = _normalize_leave_text(value)
    if not text:
        return None, ''
    if text.startswith(LEGACY_OTHER_CODE):
        return LEGACY_OTHER_CODE, text[2:].strip()
    first = text[0]
    if first in LEGACY_CODE_PREFIXES:
        return first, text[1:].strip()
    return LEGACY_OTHER_CODE, text


def _legacy_staff_columns(rows):
    if len(rows) < 3:
        return []
    name_row = rows[1]
    part_row = rows[2]
    columns = []
    current_name = ''
    max_len = max(len(name_row), len(part_row))
    for index in range(max_len):
        raw_name = _normalize_leave_text(name_row[index] if index < len(name_row) else '')
        if raw_name and raw_name not in LEGACY_HEADER_SKIP_NAMES and not raw_name.isdigit():
            current_name = raw_name

        part_text = _normalize_leave_text(part_row[index] if index < len(part_row) else '')
        if part_text.startswith(LEGACY_AM_PREFIX) and current_name:
            columns.append((index, current_name, 'am'))
        elif part_text.startswith(LEGACY_PM_PREFIX) and current_name:
            columns.append((index, current_name, 'pm'))
    return columns


def _fetch_legacy_leave_sheet(sheet_name, gid):
    params = urlencode({'gid': gid, 'single': 'true', 'output': 'csv'})
    url = f'{STAFF_LEAVE_SHEET_BASE_URL}?{params}'
    with urlopen(url, timeout=20) as response:
        content = response.read().decode('utf-8-sig')
    rows = list(csv.reader(StringIO(content)))
    year, month = [int(part) for part in sheet_name.split('-')]
    staff_columns = _legacy_staff_columns(rows)
    entries = []

    for row in rows[3:]:
        if not row:
            continue
        try:
            day = int(_normalize_leave_text(row[0]))
            leave_day = date(year, month, day)
        except (ValueError, IndexError):
            continue

        for column, staff_name, day_part in staff_columns:
            value = row[column] if column < len(row) else ''
            code, description = _legacy_leave_code_and_description(value)
            if not code:
                continue
            entries.append({
                'staff_user': staff_name,
                'staff_name': staff_name,
                'leave_date': leave_day,
                'day_part': day_part,
                'code': code,
                'description': description,
            })
    return entries


def _legacy_staff_names_for_month(month_start):
    sheet_name = month_start.strftime('%Y-%m')
    gid = STAFF_LEAVE_SHEET_GIDS.get(sheet_name)
    if not gid:
        return []
    try:
        params = urlencode({'gid': gid, 'single': 'true', 'output': 'csv'})
        url = f'{STAFF_LEAVE_SHEET_BASE_URL}?{params}'
        with urlopen(url, timeout=20) as response:
            content = response.read().decode('utf-8-sig')
        rows = list(csv.reader(StringIO(content)))
        names = []
        for _column, staff_name, _day_part in _legacy_staff_columns(rows):
            if staff_name not in names:
                names.append(staff_name)
        return names
    except Exception:
        return []


def _parse_church_calendar_date(value):
    text = _normalize_leave_text(value)
    if not text:
        return None
    for separator in ('-', '/', '.'):
        if separator in text:
            parts = text.split(separator)
            break
    else:
        return None
    if len(parts) < 2:
        return None
    try:
        month = int(parts[0])
        day = int(parts[1])
        return date(2026, month, day)
    except ValueError:
        return None


def _fetch_church_calendar_sheet():
    params = urlencode({'tqx': 'out:csv', 'sheet': CHURCH_CALENDAR_SHEET_NAME})
    url = f'{CHURCH_CALENDAR_SHEET_BASE_URL}?{params}'
    with urlopen(url, timeout=20) as response:
        content = response.read().decode('utf-8-sig')
    rows = list(csv.reader(StringIO(content)))
    entries = []

    for row in rows[1:]:
        if not row:
            continue
        event_date = _parse_church_calendar_date(row[0] if len(row) > 0 else '')
        if not event_date:
            continue

        entry = {
            'event_date': event_date,
            'weekday': _normalize_leave_text(row[1] if len(row) > 1 else ''),
        }
        has_content = False
        for index, field_name in enumerate(CHURCH_CALENDAR_FIELD_NAMES, start=2):
            value = _normalize_leave_text(row[index] if len(row) > index else '')
            entry[field_name] = value
            has_content = has_content or bool(value)
        if has_content:
            entries.append(entry)
    return entries


def _import_legacy_leave_entries_if_needed():
    imported_entries = []
    for sheet_name, gid in STAFF_LEAVE_SHEET_GIDS.items():
        month_start = _parse_month(sheet_name)
        with connection.cursor() as cursor:
            cursor.execute(
                f'''
                SELECT COUNT(*)
                FROM {STAFF_LEAVE_TABLE}
                WHERE source = %s
                  AND leave_date BETWEEN %s AND %s
                ''',
                [STAFF_LEAVE_IMPORT_SOURCE, month_start, _month_end(month_start)],
            )
            has_imported_month = int(cursor.fetchone()[0] or 0) > 0
        if not has_imported_month:
            imported_entries.extend(_fetch_legacy_leave_sheet(sheet_name, gid))

    if not imported_entries:
        return 0

    now = datetime.now()
    with transaction.atomic():
        with connection.cursor() as cursor:
            for entry in imported_entries:
                cursor.execute(
                    f'''
                    DELETE FROM {STAFF_LEAVE_TABLE}
                    WHERE staff_user = %s AND leave_date = %s AND day_part = %s
                    ''',
                    [entry['staff_user'], entry['leave_date'], entry['day_part']],
                )
                cursor.execute(
                    f'''
                    INSERT INTO {STAFF_LEAVE_TABLE}
                        (staff_user, staff_name, leave_date, day_part, code, description, source, created_at, updated_at)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                    ''',
                    [
                        entry['staff_user'],
                        entry['staff_name'],
                        entry['leave_date'],
                        entry['day_part'],
                        entry['code'],
                        entry['description'],
                        STAFF_LEAVE_IMPORT_SOURCE,
                        now,
                        now,
                    ],
                )
    return len(imported_entries)


def _import_church_calendar_entries_if_needed(force=False):
    start = date(2026, 1, 1)
    end = date(2026, 12, 31)
    if not force:
        with connection.cursor() as cursor:
            cursor.execute(
                f'''
                SELECT COUNT(*)
                FROM {CHURCH_CALENDAR_TABLE}
                WHERE source = %s AND event_date BETWEEN %s AND %s
                ''',
                [CHURCH_CALENDAR_IMPORT_SOURCE, start, end],
            )
            if int(cursor.fetchone()[0] or 0) > 0:
                return 0

    imported_entries = _fetch_church_calendar_sheet()
    if not imported_entries:
        return 0

    now = datetime.now()
    with transaction.atomic():
        with connection.cursor() as cursor:
            if force:
                cursor.execute(
                    f'''
                    DELETE FROM {CHURCH_CALENDAR_TABLE}
                    WHERE source = %s AND event_date BETWEEN %s AND %s
                    ''',
                    [CHURCH_CALENDAR_IMPORT_SOURCE, start, end],
                )
            for entry in imported_entries:
                cursor.execute(
                    f'''
                    DELETE FROM {CHURCH_CALENDAR_TABLE}
                    WHERE event_date = %s
                    ''',
                    [entry['event_date']],
                )
                cursor.execute(
                    f'''
                    INSERT INTO {CHURCH_CALENDAR_TABLE}
                        (event_date, weekday, church_activity, work_plan, staff_leave_note, holiday_social, note, source, created_at, updated_at)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    ''',
                    [
                        entry['event_date'],
                        entry['weekday'],
                        entry['church_activity'],
                        entry['work_plan'],
                        entry['staff_leave_note'],
                        entry['holiday_social'],
                        entry['note'],
                        CHURCH_CALENDAR_IMPORT_SOURCE,
                        now,
                        now,
                    ],
                )
    return len(imported_entries)


def _leave_entries(month_start):
    start = month_start
    end = _month_end(month_start)
    with connection.cursor() as cursor:
        cursor.execute(
            f'''
            SELECT id, staff_user, staff_name, leave_date, day_part, code, description
            FROM {STAFF_LEAVE_TABLE}
            WHERE leave_date BETWEEN %s AND %s
            ORDER BY leave_date, day_part, staff_name, staff_user
            ''',
            [start, end],
        )
        columns = [col[0] for col in cursor.description]
        rows = [dict(zip(columns, row)) for row in cursor.fetchall()]
    for row in rows:
        if hasattr(row['leave_date'], 'isoformat'):
            row['leave_date'] = row['leave_date'].isoformat()
    return rows


def _church_calendar_entries(month_start):
    start = month_start
    end = _month_end(month_start)
    with connection.cursor() as cursor:
        cursor.execute(
            f'''
            SELECT id, event_date, weekday, church_activity, work_plan, staff_leave_note, holiday_social, note
            FROM {CHURCH_CALENDAR_TABLE}
            WHERE event_date BETWEEN %s AND %s
            ORDER BY event_date
            ''',
            [start, end],
        )
        columns = [col[0] for col in cursor.description]
        rows = [dict(zip(columns, row)) for row in cursor.fetchall()]
    for row in rows:
        if hasattr(row['event_date'], 'isoformat'):
            row['event_date'] = row['event_date'].isoformat()
    return rows


@login_required
def church_calendar_page(request):
    _church_calendar_ensure_table()

    if request.method == 'GET':
        try:
            imported_calendar_count = _import_church_calendar_entries_if_needed(
                force=request.GET.get('refresh') == '1',
            )
        except Exception as exc:
            messages.warning(request, f'Google Sheet 教會行事曆暫時無法匯入：{exc}')
        else:
            if imported_calendar_count:
                messages.success(request, f'已匯入「2026行事曆」{imported_calendar_count} 筆。')

    selected_month = _parse_month(request.GET.get('month'))
    entries = _church_calendar_entries(selected_month)
    context = {
        'month_options': _month_options(date.today()),
        'selected_month': selected_month,
        'calendar_weeks': _calendar_weeks(selected_month),
        'church_calendar_entries': entries,
        'church_calendar_entries_json': json.dumps(entries, ensure_ascii=False),
    }
    return render(request, 'staff/calendar.html', context)


def _staff_names_for_month(month_start, entries, alias_map=None):
    alias_map = alias_map or _staff_name_aliases()
    names = []
    candidates = [
        *STAFF_LEAVE_DISPLAY_ORDER,
        *_legacy_staff_names_for_month(month_start),
    ]
    for entry in entries:
        candidates.append(entry.get('staff_name') or entry.get('staff_user') or '')
    for candidate in candidates:
        name = _canonical_staff_name(candidate, alias_map)
        if name and name not in names:
            names.append(name)
    return names


def _get_used_annual_leave_days(user):
    aliases = _staff_user_aliases(user)
    with connection.cursor() as cursor:
        placeholders = ', '.join(['%s'] * len(aliases))
        query = f"""
            SELECT leave_date, day_part
            FROM {STAFF_LEAVE_TABLE} 
            WHERE (staff_user IN ({placeholders}) OR staff_name IN ({placeholders}))
              AND STRFTIME('%%Y', leave_date) = %s
              AND code = '特'
        """ if connection.vendor == 'sqlite' else f"""
            SELECT leave_date, day_part
            FROM {STAFF_LEAVE_TABLE} 
            WHERE (staff_user IN ({placeholders}) OR staff_name IN ({placeholders}))
              AND YEAR(leave_date) = %s
              AND code = '特'
        """
        params = list(aliases) + list(aliases) + [str(STAFF_LEAVE_YEAR)]
        cursor.execute(query, params)
        unique_slots = {
            (str(leave_date), day_part)
            for leave_date, day_part in cursor.fetchall()
        }
    return float(len(unique_slots)) * 0.5


def _monthly_leave_summary(user, entries):
    aliases = set(_staff_user_aliases(user))
    alias_map = _staff_name_aliases()
    canonical_aliases = {
        _canonical_staff_name(alias, alias_map)
        for alias in aliases
    }
    code_days = {code: 0.0 for code in LEAVE_CODES}
    total_days = 0.0
    seen_slots = set()

    for entry in entries:
        entry_names = {
            entry.get('staff_user') or '',
            entry.get('staff_name') or '',
        }
        canonical_entry_names = {
            _canonical_staff_name(name, alias_map)
            for name in entry_names
            if name
        }
        if not (entry_names & aliases or canonical_entry_names & canonical_aliases):
            continue
        slot = (str(entry.get('leave_date') or ''), entry.get('day_part') or '')
        if slot in seen_slots:
            continue
        seen_slots.add(slot)
        code = entry.get('code') or ''
        total_days += 0.5
        if code in code_days:
            code_days[code] += 0.5

    return {
        'total': total_days,
        '休': code_days['休'],
        '特': code_days['特'],
        '補': code_days['補'],
        '公': code_days['公'],
        '其他': code_days['其他'],
        '病': code_days['病假'],
        '事': code_days['事假'],
        '婚': code_days['婚假'],
        '陪產': code_days['陪/產假'],
        '喪': code_days['喪'],
        '育嬰': code_days['育嬰'],
    }


def _hr_monthly_leave_overview(staff_names, entries, alias_map, full_names):
    canonical_names = [
        _canonical_staff_name(name, alias_map)
        for name in staff_names
    ]
    summaries = {
        name: {'total': 0.0, **{code: 0.0 for code in LEAVE_CODES}}
        for name in canonical_names
    }
    seen_slots = set()

    for entry in entries:
        entry_name = entry.get('staff_name') or entry.get('staff_user') or ''
        canonical_name = _canonical_staff_name(entry_name, alias_map)
        if canonical_name not in summaries:
            continue
        slot = (
            canonical_name,
            str(entry.get('leave_date') or ''),
            entry.get('day_part') or '',
        )
        if slot in seen_slots:
            continue
        seen_slots.add(slot)
        code = entry.get('code') or ''
        summaries[canonical_name]['total'] += 0.5
        if code in LEAVE_CODES:
            summaries[canonical_name][code] += 0.5

    columns = [
        {'name': full_names.get(name, name)}
        for name in canonical_names
    ]
    rows = []
    for label, code in HR_LEAVE_SUMMARY_METRICS:
        key = code or 'total'
        rows.append({
            'label': label,
            'values': [summaries[name][key] for name in canonical_names],
        })
    return {'columns': columns, 'rows': rows}


def _save_leave_entry(request, selected_month):
    raw_slots = request.POST.get('leave_slots') or ''
    try:
        submitted_slots = json.loads(raw_slots) if raw_slots else []
    except (TypeError, ValueError):
        submitted_slots = []
    if not submitted_slots:
        submitted_slots = [{
            'date': request.POST.get('leave_date'),
            'part': request.POST.get('day_part'),
        }]
    slots = []
    for submitted in submitted_slots:
        if not isinstance(submitted, dict):
            continue
        try:
            leave_day = date.fromisoformat(str(submitted.get('date') or ''))
        except ValueError:
            continue
        day_part = submitted.get('part') or ''
        slot = (leave_day, day_part)
        if (
            leave_day.year != selected_month.year
            or leave_day.month != selected_month.month
            or day_part not in LEAVE_PARTS
            or slot in slots
        ):
            continue
        slots.append(slot)
    if not slots:
        messages.error(request, '請至少選擇一個正確的日期與時段。')
        return selected_month
    if _is_leave_month_locked(selected_month):
        messages.error(request, '此月份已鎖定，只能閱讀。')
        return slots[0][0]

    code = request.POST.get('code') or ''
    description = (request.POST.get('description') or '').strip()
    if code not in LEAVE_CODES:
        messages.error(request, '請選擇正確的日期、上午/下午與假別。')
        return slots[0][0]
    if code in {'公', '事假', '其他'} and not description:
        messages.error(request, '選擇「公假」、「事假」或「其他」時，請填寫文字說明。')
        return slots[0][0]

    username = request.user.get_username()
    staff_name = _staff_display_name(request.user)
    aliases = _staff_user_aliases(request.user)

    if code == '特':
        additional_special_slots = 0
        with connection.cursor() as cursor:
            placeholders = ', '.join(['%s'] * len(aliases))
            for leave_day, day_part in slots:
                cursor.execute(
                    f'''SELECT code FROM {STAFF_LEAVE_TABLE}
                        WHERE (staff_user IN ({placeholders}) OR staff_name IN ({placeholders}))
                          AND leave_date = %s AND day_part = %s''',
                    list(aliases) + list(aliases) + [leave_day, day_part],
                )
                if not any(row[0] == '特' for row in cursor.fetchall()):
                    additional_special_slots += 1
        if additional_special_slots:
            annual_leave_quota = 0.0
            try:
                from modules.eureka.models import StaffInfo
                staff_info = StaffInfo.objects.filter(user=request.user).first()
                if not staff_info:
                    staff_info = StaffInfo.objects.filter(name=staff_name).first()
                if staff_info:
                    annual_leave_quota = staff_info.annual_leave_quota
            except Exception:
                pass
                
            used_days = _get_used_annual_leave_days(request.user)
            requested_days = additional_special_slots * 0.5
            if used_days + requested_days > annual_leave_quota:
                messages.error(request, f"本次需要 {requested_days:g} 天特休，將超過年度上限 {annual_leave_quota:g} 天。")
                return slots[0][0]

    now = datetime.now()
    placeholders = ', '.join(['%s'] * len(aliases))
    with transaction.atomic(), connection.cursor() as cursor:
        for leave_day, day_part in slots:
            cursor.execute(
                f'''DELETE FROM {STAFF_LEAVE_TABLE}
                    WHERE (staff_user IN ({placeholders}) OR staff_name IN ({placeholders}))
                      AND leave_date = %s AND day_part = %s''',
                aliases + aliases + [leave_day, day_part],
            )
            cursor.execute(
                f'''INSERT INTO {STAFF_LEAVE_TABLE}
                    (staff_user, staff_name, leave_date, day_part, code, description, source, created_at, updated_at)
                    VALUES (%s, %s, %s, %s, %s, %s, '', %s, %s)''',
                [username, staff_name, leave_day, day_part, code, description, now, now],
            )
    messages.success(request, f'已完成 {len(slots)} 個時段的休假登記。')
    return slots[0][0]


def _delete_leave_entry(request, selected_month):
    raw_slots = request.POST.get('leave_slots') or ''
    try:
        submitted_slots = json.loads(raw_slots) if raw_slots else []
    except (TypeError, ValueError):
        submitted_slots = []
    if not submitted_slots:
        submitted_slots = [{
            'date': request.POST.get('leave_date'),
            'part': request.POST.get('day_part'),
        }]
    slots = []
    for submitted in submitted_slots:
        if not isinstance(submitted, dict):
            continue
        try:
            leave_day = date.fromisoformat(str(submitted.get('date') or ''))
        except ValueError:
            continue
        day_part = submitted.get('part') or ''
        slot = (leave_day, day_part)
        if (
            leave_day.year == selected_month.year
            and leave_day.month == selected_month.month
            and day_part in LEAVE_PARTS
            and slot not in slots
        ):
            slots.append(slot)
    if not slots:
        messages.error(request, '請至少選擇一個正確的日期與時段。')
        return selected_month
    if _is_leave_month_locked(selected_month):
        messages.error(request, '此月份已鎖定，只能閱讀。')
        return slots[0][0]

    aliases = _staff_user_aliases(request.user)
    placeholders = ', '.join(['%s'] * len(aliases))
    deleted_count = 0
    with transaction.atomic(), connection.cursor() as cursor:
        for leave_day, day_part in slots:
            cursor.execute(
                f'''DELETE FROM {STAFF_LEAVE_TABLE}
                    WHERE (staff_user IN ({placeholders}) OR staff_name IN ({placeholders}))
                      AND leave_date = %s AND day_part = %s''',
                aliases + aliases + [leave_day, day_part],
            )
            deleted_count += cursor.rowcount
    messages.success(request, f'已刪除 {deleted_count} 筆休假資料。')
    return slots[0][0]


@login_required
def leave_calendar_page(request):
    _leave_ensure_table()
    _church_calendar_ensure_table()
    if request.method == 'GET':
        try:
            imported_count = _import_legacy_leave_entries_if_needed()
        except Exception as exc:
            messages.warning(request, f'Google Sheet 休假資料暫時無法匯入：{exc}')
        else:
            if imported_count:
                messages.success(request, f'已匯入 2026 年 Google Sheet 休假資料 {imported_count} 筆。')
        try:
            imported_calendar_count = _import_church_calendar_entries_if_needed()
        except Exception as exc:
            messages.warning(request, f'Google Sheet 教會行事曆暫時無法匯入：{exc}')
        else:
            if imported_calendar_count:
                messages.success(request, f'已匯入「2026行事曆」{imported_calendar_count} 筆。')

    selected_month = _parse_month(request.GET.get('month') or request.POST.get('month'))
    if selected_month.year != STAFF_LEAVE_YEAR:
        selected_month = date(STAFF_LEAVE_YEAR, selected_month.month, 1)
    selected_day = _parse_leave_date(request.GET.get('day') or request.POST.get('leave_date'), selected_month)
    if selected_day.year != STAFF_LEAVE_YEAR:
        selected_day = selected_month

    if request.method == 'POST':
        action = request.POST.get('action')
        if action == 'save':
            selected_day = _save_leave_entry(request, selected_month)
        elif action == 'delete':
            selected_day = _delete_leave_entry(request, selected_month)
        else:
            return HttpResponseBadRequest('Unknown action')
        return redirect(f'/staff/leaves/?month={_month_start(selected_day).strftime("%Y-%m")}&day={selected_day.isoformat()}')

    today = date.today()
    entries = _leave_entries(selected_month)
    church_calendar_entries = _church_calendar_entries(selected_month)
    staff_name_aliases = _staff_name_aliases()
    staff_names = _staff_names_for_month(selected_month, entries, staff_name_aliases)
    staff_full_names = _staff_full_name_map(staff_name_aliases)
    current_user = request.user.get_username()

    annual_leave_quota = 0.0
    try:
        from modules.eureka.models import StaffInfo
        staff_info = StaffInfo.objects.filter(user=request.user).first()
        if not staff_info:
            staff_info = StaffInfo.objects.filter(name=_staff_display_name(request.user)).first()
        if staff_info:
            annual_leave_quota = staff_info.annual_leave_quota
    except Exception:
        pass
    used_leave_days = _get_used_annual_leave_days(request.user)
    monthly_leave_summary = _monthly_leave_summary(request.user, entries)
    can_view_hr_leave_summary = request.user.has_perm(
        'eureka.view_staff_leave_summary'
    )
    hr_leave_overview = None
    if can_view_hr_leave_summary:
        hr_leave_overview = _hr_monthly_leave_overview(
            staff_names,
            entries,
            staff_name_aliases,
            staff_full_names,
        )

    context = {
        'month_options': _month_options(today),
        'selected_month': selected_month,
        'selected_day': selected_day,
        'calendar_weeks': _calendar_weeks(selected_month),
        'entries_json': json.dumps(entries, ensure_ascii=False),
        'staff_names_json': json.dumps(staff_names, ensure_ascii=False),
        'staff_name_aliases_json': json.dumps(staff_name_aliases, ensure_ascii=False),
        'staff_full_names_json': json.dumps(staff_full_names, ensure_ascii=False),
        'church_calendar_entries': church_calendar_entries,
        'church_calendar_entries_json': json.dumps(church_calendar_entries, ensure_ascii=False),
        'current_user': current_user,
        'current_staff_name': _staff_display_name(request.user),
        'current_user_aliases_json': json.dumps(_staff_user_aliases(request.user), ensure_ascii=False),
        'leave_code_options': [
            {'code': code, 'label': label}
            for code, label in LEAVE_EDITOR_CODE_OPTIONS
        ],
        'leave_parts': LEAVE_PARTS,
        'is_locked': _is_leave_month_locked(selected_month, today),
        'lock_note': '每月5日鎖住前一個月；已鎖定月份只能閱讀。',
        'annual_leave_quota': annual_leave_quota,
        'used_leave_days': used_leave_days,
        'monthly_leave_summary': monthly_leave_summary,
        'can_view_hr_leave_summary': can_view_hr_leave_summary,
        'hr_leave_overview': hr_leave_overview,
    }
    return render(request, 'staff/leaves.html', context)
