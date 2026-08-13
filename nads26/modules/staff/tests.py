import datetime
import json
from django.test import TestCase, Client
from django.contrib.auth.models import User
from django.contrib.auth.models import Permission
from django.urls import reverse
from django.db import connection
from modules.eureka.models import StaffInfo
from modules.staff.views import (
    STAFF_LEAVE_TABLE,
    STAFF_LEAVE_YEAR,
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
            user=self.user,
            name="測試同工",
            annual_leave_quota=2.0
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
        self.assertContains(response, '年度特休天數')
        self.assertContains(response, '已休特休天數')
        self.assertContains(response, '當月總計')
        self.assertContains(response, '日期與時段（可複選）')
        self.assertContains(response, 'name="leave_slots"')
        self.assertContains(response, 'width: min(500px, 100%)')
        self.assertContains(response, 'min-height: 20px')
        self.assertContains(response, '.content-area .leave-modal .batch-slot-button')
        self.assertContains(response, 'height: 20px')
        self.assertContains(response, 'applyNationalHolidayBackgrounds')
        self.assertContains(response, 'function nationalHolidayName(date)')
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
            '年度特休天數', '已休特休天數', '例休', '特休', '補休',
            '公假', '其他', '病假', '事假', '婚假', '陪產', '育嬰', '喪假', '當月總計',
        ]
        positions = [html.index(f'<span>{label}</span>') for label in labels]
        self.assertEqual(positions, sorted(positions))

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
        )
        row_values = {row['label']: row['values'][0] for row in overview['rows']}
        self.assertEqual(overview['columns'][0]['name'], '黃美美')
        self.assertEqual(len(overview['rows']), 12)
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

    def test_special_leave_quota_limit(self):
        """Verify that creating '特' leave entries is restricted by quota"""
        today = datetime.date.today()
        month_str = today.strftime('%Y-%m')
        # Save 4 special leave entries (0.5 day * 4 = 2.0 days, which is exactly the quota)
        for idx in range(4):
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

        # Confirm 4 entries exist
        with connection.cursor() as cursor:
            cursor.execute(
                f"SELECT COUNT(*) FROM {STAFF_LEAVE_TABLE} WHERE staff_user = %s AND code = '特'",
                [self.user.username]
            )
            count = cursor.fetchone()[0]
            self.assertEqual(count, 4)

        # Attempt to save a 5th special leave entry (which exceeds the quota of 2.0 days)
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
