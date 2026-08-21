import datetime
import json
from unittest.mock import patch
from django.test import TestCase, Client
from django.contrib.auth.models import User
from django.contrib.auth.models import Permission
from django.urls import reverse
from django.db import connection
from modules.eureka.models import StaffInfo
from modules.staff.views import (
    STAFF_LEAVE_TABLE,
    STAFF_LEAVE_YEAR,
    _annual_leave_balances,
    _get_used_annual_leave_days,
    _hr_monthly_leave_overview,
    _monthly_leave_summary,
    _staff_name_aliases,
    _staff_full_name_map,
)

class StaffLeaveTests(TestCase):
    def setUp(self):
        self.client = Client()
        # Create a user with a display name that matches a staff name display logic
        self.user = User.objects.create_user(username="teststaff", password="password123")
        self.user.first_name = "測試同工"
        self.user.save()
        
        # Create corresponding StaffInfo
        self.staff_info = StaffInfo.objects.create(
            staff_id=999,
            user=self.user,
            name="測試同工",
            onboard_date=datetime.date(STAFF_LEAVE_YEAR, 2, 1),
            annual_leave_quota=3.0,
        )
        
        # Ensure the raw SQL tables are created
        self.client.login(username="teststaff", password="password123")
        self.client.get(reverse('staff-leaves'))

    def test_save_new_leave_categories(self):
        """Verify that the new leave types can be saved successfully"""
        new_types = ['病假', '事假', '婚假', '陪/產假', '喪', '育嬰']
        today = datetime.date.today()
        month_str = today.strftime('%Y-%m')
        for idx, ltype in enumerate(new_types):
            leave_date = datetime.date(STAFF_LEAVE_YEAR, today.month, 10 + idx)
            post_data = {
                'action': 'save',
                'month': month_str,
                'leave_date': leave_date.isoformat(),
                'day_part': 'am',
                'code': ltype,
                'description': f'Testing {ltype}'
            }
            response = self.client.post(reverse('staff-leaves'), post_data)
            self.assertEqual(response.status_code, 302) # Redirects on success

            # Query database to confirm
            with connection.cursor() as cursor:
                cursor.execute(
                    f"SELECT code, description FROM {STAFF_LEAVE_TABLE} WHERE staff_user = %s AND leave_date = %s",
                    [self.user.username, leave_date]
                )
                row = cursor.fetchone()
                self.assertIsNotNone(row)
                self.assertEqual(row[0], ltype)
                self.assertEqual(row[1], f'Testing {ltype}')

    def test_team_month_uses_full_staff_names(self):
        full_names = _staff_full_name_map()

        self.assertEqual(full_names['明月'], '林明月')
        self.assertEqual(full_names['小慧'], '謝淑慧')
        self.assertEqual(full_names['彼得陳'], '陳潘傳')

        response = self.client.get(reverse('staff-leaves'))
        self.assertContains(response, 'staffFullNames')
        self.assertContains(response, 'national-holiday')
        self.assertContains(response, 'sunday')
        self.assertContains(response, '--team-date-column-width: 80px')
        self.assertContains(response, 'width: 60px')
        self.assertContains(response, 'team-slots')
        self.assertContains(response, "code === '陪/產假' ? '陪產' : code")
        self.assertContains(response, '個人休假瀏覽表')
        self.assertContains(response, '總特休數')
        self.assertContains(response, '已休特休')
        self.assertContains(response, '剩餘特休')
        self.assertContains(response, '.hr-summary-table tbody tr:nth-child(4) td')
        self.assertContains(response, 'personal-leave-stat featured total-quota')
        self.assertContains(response, 'personal-leave-stat featured used-quota')
        self.assertContains(response, 'personal-leave-stat featured remaining-quota')
        self.assertContains(response, '當月總計')
        self.assertContains(response, '日期與時段（可複選）')
        self.assertContains(response, 'name="leave_slots"')
        self.assertContains(response, 'width: min(500px, 100%)')
        self.assertContains(response, 'min-height: 20px')
        self.assertContains(response, 'protectedModalBackdropSelector')
        self.assertContains(response, "event.target.matches(protectedModalBackdropSelector)")
        self.assertContains(response, 'event.stopImmediatePropagation()')
        self.assertContains(response, '.content-area .leave-modal .batch-slot-button')
        self.assertContains(response, 'height: 20px')
        self.assertContains(response, 'applyNationalHolidayBackgrounds')
        self.assertContains(response, 'function nationalHolidayName(date)')
        self.assertContains(response, 'function leaveDateNotices(date)')
        self.assertContains(response, 'function appendNoticeLines(container, notice)')
        self.assertContains(response, "`${holidayName}(請擇休)`")
        self.assertContains(response, "lines: isSunday ? [holidayName, '(請擇休)']")
        self.assertContains(response, "date === '2026-10-03'")
        self.assertContains(response, '秋令會(同工禁休)')
        self.assertContains(response, "lines: ['秋令會', '(同工禁休)']")
        self.assertContains(response, 'label.replaceChildren()')
        self.assertContains(response, 'date-notice-line')
        self.assertContains(response, 'activity-notice')
        self.assertContains(response, 'data-holiday-name-for=')
        self.assertContains(response, 'team-date-holiday')
        self.assertContains(response, 'const extendedHolidayPattern = /連假|補假|調整放假|彈性放假/;')
        self.assertContains(response, '!extendedHolidayPattern.test(holidayText)')
        self.assertContains(response, 'data-batch-day=')
        self.assertNotContains(response, 'data-batch-part="am">上</button>')
        self.assertNotContains(response, 'data-batch-part="pm">下</button>')
        for label in ['例休', '特休', '補休', '公假', '病假', '事假', '婚假', '陪產', '育嬰', '喪假']:
            self.assertContains(response, f'>{label}</button>')
        self.assertContains(response, '左格：上午／右格：下午')
        self.assertContains(response, '每年最多14天')
        self.assertContains(response, "['公', '事假', '其他'].includes(codeInput.value)")
        self.assertContains(response, 'leave-toolbar-actions')
        self.assertContains(response, '.content-area:has(> .leave-page)')
        self.assertContains(response, 'top: 0')
        self.assertNotContains(response, "slot.classList.add('present-dot')")
        html = response.content.decode()
        labels = [
            '總特休數', '已休特休', '剩餘特休', '例休', '特休', '補休',
            '公假', '其他', '病假', '事假', '婚假', '陪產', '育嬰', '喪假', '當月總計',
        ]
        positions = [html.index(f'<span>{label}</span>') for label in labels]
        self.assertEqual(positions, sorted(positions))

    def test_remaining_annual_leave_warns_in_month_before_onboard_month(self):
        warning_month = self.client.get(
            reverse('staff-leaves'), {'month': '2026-01'}
        )
        self.assertContains(
            warning_month,
            'remaining-quota renewal-warning',
        )
        self.assertContains(
            warning_month,
            '到職週年前一個月提醒：特休即將歸零，請儘速安排休假',
        )

        other_month = self.client.get(
            reverse('staff-leaves'), {'month': '2026-02'}
        )
        self.assertNotContains(other_month, 'remaining-quota renewal-warning')

    def test_january_onboard_date_warns_in_december(self):
        StaffInfo.objects.filter(user=self.user).update(
            onboard_date=datetime.date(2025, 1, 15)
        )

        december = self.client.get(reverse('staff-leaves'), {'month': '2026-12'})
        self.assertContains(december, 'remaining-quota renewal-warning')

    def test_monthly_leave_summary_counts_half_days(self):
        entries = [
            {
                'staff_user': self.user.username,
                'staff_name': self.user.get_full_name(),
                'leave_date': '2026-08-03',
                'day_part': 'am',
                'code': '休',
            },
            {
                'staff_user': self.user.username,
                'staff_name': self.user.get_full_name(),
                'leave_date': '2026-08-03',
                'day_part': 'pm',
                'code': '陪/產假',
            },
            {
                'staff_user': self.user.get_full_name(),
                'staff_name': self.user.get_full_name(),
                'leave_date': '2026-08-03',
                'day_part': 'am',
                'code': '休',
            },
            {
                'staff_user': 'someone-else',
                'staff_name': '其他同工',
                'leave_date': '2026-08-04',
                'day_part': 'am',
                'code': '病假',
            },
        ]

        summary = _monthly_leave_summary(self.user, entries)

        self.assertEqual(summary['total'], 1.0)
        self.assertEqual(summary['休'], 0.5)
        self.assertEqual(summary['特'], 0.0)
        self.assertEqual(summary['陪產'], 0.5)
        self.assertEqual(summary['病'], 0.0)

    def test_batch_save_multiple_leave_slots_in_one_request(self):
        slots = [
            {'date': f'{STAFF_LEAVE_YEAR}-08-03', 'part': 'am'},
            {'date': f'{STAFF_LEAVE_YEAR}-08-03', 'part': 'pm'},
            {'date': f'{STAFF_LEAVE_YEAR}-08-03', 'part': 'am'},
        ]
        response = self.client.post(reverse('staff-leaves'), {
            'action': 'save',
            'month': f'{STAFF_LEAVE_YEAR}-08',
            'leave_date': f'{STAFF_LEAVE_YEAR}-08-03',
            'day_part': 'am',
            'leave_slots': json.dumps(slots),
            'code': '休',
            'description': '',
        })
        self.assertEqual(response.status_code, 302)
        with connection.cursor() as cursor:
            cursor.execute(
                f'''SELECT leave_date, day_part, code FROM {STAFF_LEAVE_TABLE}
                    WHERE staff_user = %s AND leave_date = %s
                    ORDER BY day_part''',
                [self.user.username, f'{STAFF_LEAVE_YEAR}-08-03'],
            )
            rows = cursor.fetchall()
        self.assertEqual(len(rows), 2)
        self.assertEqual([row[1] for row in rows], ['am', 'pm'])
        self.assertTrue(all(row[2] == '休' for row in rows))

    def test_hr_leave_overview_requires_permission_and_expands_categories(self):
        response = self.client.get(reverse('staff-leaves'))
        self.assertNotContains(response, '人事休假總覽（每格以天數計）')

        permission = Permission.objects.get(
            content_type__app_label='eureka',
            codename='view_staff_leave_summary',
        )
        self.user.user_permissions.add(permission)
        response = self.client.get(reverse('staff-leaves'))
        self.assertContains(response, '人事休假總覽（每格以天數計）')
        self.assertContains(response, '<th class="hr-summary-label" scope="row">陪產</th>', html=True)
        self.assertContains(response, '<th class="hr-summary-label" scope="row">事假</th>', html=True)
        self.assertContains(response, '<th class="hr-summary-label" scope="row">婚假</th>', html=True)

        overview = _hr_monthly_leave_overview(
            ['美美'],
            [
                {
                    'staff_user': '美美',
                    'staff_name': '美美',
                    'leave_date': '2026-08-03',
                    'day_part': 'am',
                    'code': '休',
                },
                {
                    'staff_user': 'huangmeimei',
                    'staff_name': '黃美美',
                    'leave_date': '2026-08-03',
                    'day_part': 'am',
                    'code': '休',
                },
            ],
            _staff_name_aliases(),
            {'美美': '黃美美'},
            {'美美': {'total': 15, 'used': 5.5, 'remaining': 9.5}},
        )
        row_values = {row['label']: row['values'][0] for row in overview['rows']}
        self.assertEqual(overview['columns'][0]['name'], '黃美美')
        self.assertEqual(len(overview['rows']), 15)
        self.assertEqual(row_values['總特休數'], 15)
        self.assertEqual(row_values['已休特休'], 5.5)
        self.assertEqual(row_values['剩餘特休'], 9.5)
        self.assertEqual(row_values['當月總計'], 0.5)
        self.assertEqual(row_values['例休'], 0.5)

    def test_used_annual_leave_days_deduplicates_alias_slots(self):
        now = datetime.datetime.now()
        rows = [
            (self.user.username, self.user.get_full_name(), '2026-08-03', 'am'),
            (self.user.get_full_name(), self.user.get_full_name(), '2026-08-03', 'am'),
            (self.user.username, self.user.get_full_name(), '2026-08-03', 'pm'),
        ]
        with connection.cursor() as cursor:
            for staff_user, staff_name, leave_date, day_part in rows:
                cursor.execute(
                    f'''INSERT INTO {STAFF_LEAVE_TABLE}
                        (staff_user, staff_name, leave_date, day_part, code,
                         description, source, created_at, updated_at)
                        VALUES (%s, %s, %s, %s, '特', '', '', %s, %s)''',
                    [staff_user, staff_name, leave_date, day_part, now, now],
                )

        self.assertEqual(_get_used_annual_leave_days(self.user), 1.0)

    def test_used_leave_starts_with_imported_balance_then_counts_future_slots(self):
        self.staff_info.annual_leave_used_base = 1.5
        self.staff_info.annual_leave_used_base_year = STAFF_LEAVE_YEAR
        self.staff_info.annual_leave_tracking_start = datetime.date(2026, 8, 31)
        self.staff_info.save()
        now = datetime.datetime.now()
        with connection.cursor() as cursor:
            for leave_date in ['2026-08-10', '2026-08-31', '2026-09-01']:
                cursor.execute(
                    f'''INSERT INTO {STAFF_LEAVE_TABLE}
                        (staff_user, staff_name, leave_date, day_part, code,
                         description, source, created_at, updated_at)
                        VALUES (%s, %s, %s, 'am', '特', '', '', %s, %s)''',
                    [self.user.username, self.staff_info.name, leave_date, now, now],
                )

        self.assertEqual(
            _get_used_annual_leave_days(self.user, self.staff_info), 2.0
        )

    def test_used_leave_only_accumulates_through_viewed_month(self):
        self.staff_info.annual_leave_used_base = 1.5
        self.staff_info.annual_leave_used_base_year = STAFF_LEAVE_YEAR
        self.staff_info.annual_leave_tracking_start = datetime.date(2026, 8, 31)
        self.staff_info.save()
        now = datetime.datetime.now()
        with connection.cursor() as cursor:
            for leave_date in ['2026-09-01', '2026-10-01']:
                cursor.execute(
                    f'''INSERT INTO {STAFF_LEAVE_TABLE}
                        (staff_user, staff_name, leave_date, day_part, code,
                         description, source, created_at, updated_at)
                        VALUES (%s, %s, %s, 'am', '特', '', '', %s, %s)''',
                    [self.user.username, self.staff_info.name, leave_date, now, now],
                )

        self.assertEqual(
            _get_used_annual_leave_days(
                self.user,
                self.staff_info,
                STAFF_LEAVE_YEAR,
                datetime.date(2026, 8, 31),
            ),
            1.5,
        )
        self.assertEqual(
            _annual_leave_balances(
                [self.staff_info.name],
                {self.staff_info.name: self.staff_info.name},
                datetime.date(2026, 9, 30),
            )[self.staff_info.name]['used'],
            2.0,
        )

        with patch(
            'modules.staff.views._import_legacy_leave_entries_if_needed',
            return_value=0,
        ), patch(
            'modules.staff.views._import_church_calendar_entries_if_needed',
            return_value=0,
        ), patch(
            'modules.staff.views._get_used_annual_leave_days',
            side_effect=lambda user, staff_info, year, through_date: {
                8: 1.5,
                9: 2.0,
                10: 2.5,
            }[through_date.month],
        ):
            august = self.client.get(reverse('staff-leaves'), {'month': '2026-08'})
            september = self.client.get(reverse('staff-leaves'), {'month': '2026-09'})
            october = self.client.get(reverse('staff-leaves'), {'month': '2026-10'})

        self.assertEqual(august.context['used_leave_days'], 1.5)
        self.assertEqual(september.context['used_leave_days'], 2.0)
        self.assertEqual(october.context['used_leave_days'], 2.5)

    def test_special_leave_quota_limit(self):
        """Verify that creating '特' leave entries is restricted by quota"""
        today = datetime.date.today()
        month_str = today.strftime('%Y-%m')
        # Save 6 special leave entries (0.5 day * 6 = 3.0 days, exactly the half-year quota)
        for idx in range(6):
            leave_date = datetime.date(STAFF_LEAVE_YEAR, today.month, 1 + idx)
            post_data = {
                'action': 'save',
                'month': month_str,
                'leave_date': leave_date.isoformat(),
                'day_part': 'am',
                'code': '特',
                'description': f'Special leave {idx}'
            }
            response = self.client.post(reverse('staff-leaves'), post_data)
            self.assertEqual(response.status_code, 302)

        # Confirm 6 entries exist
        with connection.cursor() as cursor:
            cursor.execute(
                f"SELECT COUNT(*) FROM {STAFF_LEAVE_TABLE} WHERE staff_user = %s AND code = '特'",
                [self.user.username]
            )
            count = cursor.fetchone()[0]
            self.assertEqual(count, 6)

        # Attempt to save a 7th special leave entry (which exceeds the quota of 3.0 days)
        exceeding_date = datetime.date(STAFF_LEAVE_YEAR, today.month, 20)
        post_data = {
            'action': 'save',
            'month': month_str,
            'leave_date': exceeding_date.isoformat(),
            'day_part': 'am',
            'code': '特',
            'description': 'Exceeding quota'
        }
        # Views handles form submit error by redirecting back with messages, or rendering page
        response = self.client.post(reverse('staff-leaves'), post_data)
        # Check that the 5th entry was NOT inserted
        with connection.cursor() as cursor:
            cursor.execute(
                f"SELECT COUNT(*) FROM {STAFF_LEAVE_TABLE} WHERE staff_user = %s AND leave_date = %s",
                [self.user.username, exceeding_date]
            )
            count = cursor.fetchone()[0]
            self.assertEqual(count, 0)
