import datetime

from django.contrib.auth.models import Permission, User
from django.test import TestCase, override_settings
from django.urls import reverse

from .models import StaffInfo


@override_settings(ROOT_URLCONF='modules.eureka.test_staff_urls')
class StaffAdminCreateTests(TestCase):
    def setUp(self):
        self.superuser = User.objects.create_superuser(
            username='staff-admin',
            password='test-only-password',
            email='admin@example.test',
        )

    def test_superuser_can_create_staff(self):
        self.client.force_login(self.superuser)

        today = datetime.date.today()
        onboard_date = today.replace(year=today.year - 1)

        response = self.client.post(reverse('eureka:staff-add'), {
            'staff_id': '101',
            'name': '測試同工',
            'identity_code': 'W',
            'employee_no': 'E101',
            'onboard_date': onboard_date.isoformat(),
            'is_active': 'true',
        })

        self.assertRedirects(response, reverse('eureka:staff-list'))
        staff = StaffInfo.objects.get(pk=101)
        self.assertEqual(staff.name, '測試同工')
        self.assertEqual(staff.employee_no, 'E101')
        self.assertEqual(staff.annual_leave_quota, 7)
        self.assertTrue(staff.is_active)

    def test_duplicate_staff_id_does_not_overwrite(self):
        StaffInfo.objects.create(staff_id=101, name='原同工')
        self.client.force_login(self.superuser)

        response = self.client.post(reverse('eureka:staff-add'), {
            'staff_id': '101',
            'name': '新同工',
        })

        self.assertRedirects(response, reverse('eureka:staff-list'))
        self.assertEqual(StaffInfo.objects.get(pk=101).name, '原同工')
        self.assertEqual(StaffInfo.objects.count(), 1)

    def test_add_permission_is_required(self):
        viewer = User.objects.create_user(
            username='staff-viewer',
            password='test-only-password',
        )
        viewer.user_permissions.add(Permission.objects.get(codename='view_staffinfo'))
        self.client.force_login(viewer)

        list_response = self.client.get(reverse('eureka:staff-list'))
        self.assertEqual(list_response.status_code, 200)
        self.assertNotContains(list_response, 'id="add-staff-button"')

        response = self.client.post(reverse('eureka:staff-add'), {
            'staff_id': '102',
            'name': '不可新增',
        })
        self.assertRedirects(response, reverse('eureka:staff-list'))
        self.assertFalse(StaffInfo.objects.filter(pk=102).exists())

    def test_user_with_add_permission_sees_button_and_can_create(self):
        creator = User.objects.create_user(
            username='staff-creator',
            password='test-only-password',
        )
        creator.user_permissions.add(
            Permission.objects.get(codename='view_staffinfo'),
            Permission.objects.get(codename='add_staffinfo'),
        )
        self.client.force_login(creator)

        list_response = self.client.get(reverse('eureka:staff-list'))
        self.assertContains(list_response, 'id="add-staff-button"')
        self.assertContains(list_response, 'id="edit-annual-leave"')
        self.assertContains(list_response, 'readonly')

        response = self.client.post(reverse('eureka:staff-add'), {
            'staff_id': '103',
            'name': '可新增同工',
            'is_active': 'false',
        })
        self.assertRedirects(response, reverse('eureka:staff-list'))
        self.assertFalse(StaffInfo.objects.get(pk=103).is_active)
