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
LEAVE_CODES = {'補', '休', '特', '公', '其他'}
LEAVE_PARTS = {'am': '上午', 'pm': '下午'}
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
    aliases = [user.get_username(), _staff_display_name(user)]
    return [alias for index, alias in enumerate(aliases) if alias and alias not in aliases[:index]]


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


def _staff_names_for_month(month_start, entries):
    names = _legacy_staff_names_for_month(month_start)
    for entry in entries:
        name = entry.get('staff_name') or entry.get('staff_user') or ''
        if name and name not in names:
            names.append(name)
    return names


def _save_leave_entry(request, selected_month):
    leave_day = _parse_leave_date(request.POST.get('leave_date'), selected_month)
    month_start = _month_start(leave_day)
    if _is_leave_month_locked(month_start):
        messages.error(request, '此月份已鎖定，只能閱讀。')
        return leave_day

    day_part = request.POST.get('day_part') or ''
    code = request.POST.get('code') or ''
    description = (request.POST.get('description') or '').strip()
    if day_part not in LEAVE_PARTS or code not in LEAVE_CODES:
        messages.error(request, '請選擇正確的日期、上午/下午與假別。')
        return leave_day
    if code in {'公', '其他'} and not description:
        messages.error(request, '選擇「公」或「其他」時，請填寫文字說明。')
        return leave_day

    username = request.user.get_username()
    staff_name = _staff_display_name(request.user)
    aliases = _staff_user_aliases(request.user)
    now = datetime.now()
    with connection.cursor() as cursor:
        cursor.execute(
            f'''
            DELETE FROM {STAFF_LEAVE_TABLE}
            WHERE staff_user IN ({', '.join(['%s'] * len(aliases))})
              AND leave_date = %s
              AND day_part = %s
            ''',
            aliases + [leave_day, day_part],
        )
        cursor.execute(
            f'''
            INSERT INTO {STAFF_LEAVE_TABLE}
                (staff_user, staff_name, leave_date, day_part, code, description, source, created_at, updated_at)
            VALUES (%s, %s, %s, %s, %s, %s, '', %s, %s)
            ''',
            [username, staff_name, leave_day, day_part, code, description, now, now],
        )
    messages.success(request, '休假資料已更新。')
    return leave_day


def _delete_leave_entry(request, selected_month):
    leave_day = _parse_leave_date(request.POST.get('leave_date'), selected_month)
    month_start = _month_start(leave_day)
    if _is_leave_month_locked(month_start):
        messages.error(request, '此月份已鎖定，只能閱讀。')
        return leave_day

    day_part = request.POST.get('day_part') or ''
    if day_part not in LEAVE_PARTS:
        messages.error(request, '請選擇正確的上午/下午。')
        return leave_day

    aliases = _staff_user_aliases(request.user)
    with connection.cursor() as cursor:
        cursor.execute(
            f'''
            DELETE FROM {STAFF_LEAVE_TABLE}
            WHERE staff_user IN ({', '.join(['%s'] * len(aliases))})
              AND leave_date = %s
              AND day_part = %s
            ''',
            aliases + [leave_day, day_part],
        )
    messages.success(request, '休假資料已刪除。')
    return leave_day


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
    staff_names = _staff_names_for_month(selected_month, entries)
    current_user = request.user.get_username()
    context = {
        'month_options': _month_options(today),
        'selected_month': selected_month,
        'selected_day': selected_day,
        'calendar_weeks': _calendar_weeks(selected_month),
        'entries_json': json.dumps(entries, ensure_ascii=False),
        'staff_names_json': json.dumps(staff_names, ensure_ascii=False),
        'church_calendar_entries': church_calendar_entries,
        'church_calendar_entries_json': json.dumps(church_calendar_entries, ensure_ascii=False),
        'current_user': current_user,
        'current_staff_name': _staff_display_name(request.user),
        'current_user_aliases_json': json.dumps(_staff_user_aliases(request.user), ensure_ascii=False),
        'leave_codes': ['補', '休', '特', '公', '其他'],
        'leave_parts': LEAVE_PARTS,
        'is_locked': _is_leave_month_locked(selected_month, today),
        'lock_note': '每月5日鎖住前一個月；已鎖定月份只能閱讀。',
    }
    return render(request, 'staff/leaves.html', context)
