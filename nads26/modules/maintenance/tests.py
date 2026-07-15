import json
import tempfile
from pathlib import Path

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.test import TestCase, override_settings
from django.urls import resolve, reverse

from .models import (
    MaintenanceAttachment,
    MaintenanceCategory,
    MaintenanceLocation,
    MaintenanceRecord,
    MaintenanceVendor,
)


class MaintenanceViewTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(username='maintenance-test', password='test-pass-123')
        self.category = MaintenanceCategory.objects.create(name='電力系統')
        self.location = MaintenanceLocation.objects.create(name='機房')

    def test_existing_maintenance_route_is_preserved(self):
        match = resolve('/facility/maintenance/')
        self.assertEqual(match.url_name, 'facility-maintenance')

    def test_management_requires_login(self):
        response = self.client.get(reverse('maintenance:dashboard'))
        self.assertEqual(response.status_code, 302)
        self.assertIn('/accounts/login/', response.url)

    def test_authenticated_dashboard_and_record_create(self):
        self.client.force_login(self.user)
        response = self.client.get(reverse('maintenance:dashboard'))
        self.assertEqual(response.status_code, 200)
        response = self.client.post(reverse('maintenance:record-create'), {
            'maintenance_date': '2026-07-15', 'type': 'GENERAL',
            'category': self.category.pk, 'location': self.location.pk,
            'handler': '行政同工', 'vendor': '', 'vendor_representative': '',
            'status': 'PENDING', 'cost': '0', 'issue': '測試維護問題',
            'result': '', 'notes': '',
        })
        self.assertEqual(response.status_code, 302)
        self.assertEqual(MaintenanceRecord.objects.count(), 1)
        self.assertEqual(MaintenanceRecord.objects.get().created_by, self.user)

    def test_public_report_creates_pending_record(self):
        response = self.client.post(reverse('maintenance_public:report'), {
            'maintenance_date': '2026-07-15', 'type': 'EMERGENCY',
            'category': self.category.pk, 'location': self.location.pk,
            'handler': '測試會友', 'issue': '燈具不亮', 'website': '',
        })
        self.assertEqual(response.status_code, 302)
        record = MaintenanceRecord.objects.get()
        self.assertEqual(record.status, MaintenanceRecord.Status.PENDING)
        self.assertIn('公開維護回報', record.notes)

    def test_all_management_pages_render(self):
        self.client.force_login(self.user)
        record = MaintenanceRecord.objects.create(
            maintenance_date='2026-07-15', type='GENERAL', category=self.category,
            location=self.location, handler='行政同工', issue='頁面測試', status='PENDING',
        )
        urls = (
            reverse('maintenance:dashboard'), reverse('maintenance:record-list'),
            reverse('maintenance:record-create'), reverse('maintenance:record-detail', args=[record.pk]),
            reverse('maintenance:record-update', args=[record.pk]), reverse('maintenance:vendor-list'),
            reverse('maintenance:category-list'), reverse('maintenance:location-list'),
            reverse('maintenance:statistics'), reverse('maintenance:unfinished'),
        )
        for url in urls:
            with self.subTest(url=url):
                self.assertEqual(self.client.get(url).status_code, 200)
        self.client.logout()
        self.assertEqual(self.client.get(reverse('maintenance_public:report')).status_code, 200)


class MaintenanceImportTests(TestCase):
    @override_settings(MEDIA_ROOT=tempfile.gettempdir())
    def test_import_is_idempotent_and_keeps_attachments(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            source = Path(temp_dir)
            (source / 'uploads').mkdir()
            (source / 'uploads' / 'onsite.jpg').write_bytes(b'test-image')
            files = {
                'categories.json': [{'id': 1, 'name': '消防設備', 'notes': None, 'isActive': True}],
                'locations.json': [{'id': 1, 'name': '大堂', 'area': None, 'floor': '1F', 'notes': None, 'isActive': True}],
                'vendors.json': [{'id': 1, 'name': '測試廠商', 'isActive': True}],
                'maintenance-records.json': [{
                    'id': 7, 'maintenanceDate': '2026-06-04T00:00:00.000Z',
                    'type': 'SCHEDULED', 'categoryId': 1, 'locationId': 1,
                    'handler': '行政同工', 'vendorId': 1, 'vendorRepresentative': '',
                    'issue': '定期檢查', 'result': '完成', 'status': 'COMPLETED',
                    'cost': '500', 'notes': '', 'onsiteImagePath': '/uploads/onsite.jpg',
                    'quoteImagePath': None, 'receiptImagePath': None, 'attachments': [],
                    'createdAt': '2026-06-04T01:00:00.000Z', 'updatedAt': '2026-06-04T02:00:00.000Z',
                }],
            }
            for filename, data in files.items():
                (source / filename).write_text(json.dumps(data, ensure_ascii=False), encoding='utf-8')

            call_command('import_church_maintenance', str(source))
            call_command('import_church_maintenance', str(source))

            self.assertEqual(MaintenanceCategory.objects.count(), 1)
            self.assertEqual(MaintenanceLocation.objects.count(), 1)
            self.assertEqual(MaintenanceVendor.objects.count(), 1)
            self.assertEqual(MaintenanceRecord.objects.count(), 1)
            self.assertEqual(MaintenanceAttachment.objects.count(), 1)
            self.assertEqual(MaintenanceRecord.objects.get().cost, 500)
