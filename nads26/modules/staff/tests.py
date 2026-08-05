import datetime
from django.test import TestCase, Client
from django.contrib.auth.models import User
from django.urls import reverse
from django.db import connection
from modules.eureka.models import StaffInfo
from modules.staff.views import STAFF_LEAVE_TABLE, STAFF_LEAVE_YEAR

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
        new_types = ['病假', '事假', '陪/產假', '喪', '育嬰']
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
