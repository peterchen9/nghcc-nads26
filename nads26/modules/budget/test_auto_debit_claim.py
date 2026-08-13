import importlib
from datetime import datetime
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from django.contrib.auth import get_user_model
from django.test import RequestFactory, TestCase
from django.urls import resolve

from modules.facility import views as facility_views
from modules.menu.models import MenuItem


class AutoDebitClaimViewTests(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.user = get_user_model().objects.create_user(
            username='finance-user',
            password='test-only-password',
        )

    def test_finance_urls_resolve_to_auto_debit_views(self):
        page_match = resolve('/finance/auto-debit-claims/')
        pdf_match = resolve('/finance/auto-debit-claims/AUT20260811-000001-001/voucher.pdf')

        self.assertEqual(page_match.func, facility_views.auto_debit_claim_page)
        self.assertEqual(pdf_match.func, facility_views.auto_debit_claim_voucher_pdf)

    @patch('modules.facility.views._expense_claim_page')
    def test_page_uses_auto_debit_type_and_title(self, common_page):
        common_page.return_value = MagicMock(status_code=200)
        request = self.factory.get('/finance/auto-debit-claims/')
        request.user = self.user

        facility_views.auto_debit_claim_page(request)

        common_page.assert_called_once_with(
            request,
            claim_type=facility_views.EXPENSE_CLAIM_TYPE_AUTO_DEBIT,
            claim_title='請款/自動扣繳單',
            base_path_fallback='/finance/auto-debit-claims',
        )

    def test_auto_debit_claim_number_uses_distinct_prefix(self):
        cursor = MagicMock()
        cursor.fetchone.return_value = (0,)

        claim_no = facility_views._expense_claim_no(
            cursor,
            datetime(2026, 8, 11, 9, 30, 15),
            facility_views.EXPENSE_CLAIM_TYPE_AUTO_DEBIT,
        )

        self.assertEqual(claim_no, 'AUT20260811-093015-001')

    def test_auto_debit_uses_activity_budget_dropdown_design(self):
        self.assertTrue(
            facility_views._expense_uses_activity_budget(
                facility_views.EXPENSE_CLAIM_TYPE_AUTO_DEBIT
            )
        )

    @patch('modules.facility.views._expense_claim_voucher_pdf')
    def test_pdf_uses_request_and_auto_debit_title(self, common_pdf):
        common_pdf.return_value = MagicMock(status_code=200)
        request = self.factory.get(
            '/finance/auto-debit-claims/AUT20260811-000001-001/voucher.pdf'
        )
        request.user = self.user

        facility_views.auto_debit_claim_voucher_pdf(
            request, 'AUT20260811-000001-001'
        )

        common_pdf.assert_called_once_with(
            request,
            'AUT20260811-000001-001',
            claim_type=facility_views.EXPENSE_CLAIM_TYPE_AUTO_DEBIT,
            document_title='北門請款/自動扣繳單',
        )

    @patch('modules.facility.views._expense_ensure_tables')
    @patch('modules.facility.views.connection.cursor')
    def test_recent_claims_are_filtered_by_claim_type(self, cursor_factory, ensure_tables):
        cursor = MagicMock()
        cursor.fetchall.return_value = []
        cursor_factory.return_value.__enter__.return_value = cursor

        facility_views._expense_recent_claims(
            facility_views.EXPENSE_CLAIM_TYPE_AUTO_DEBIT
        )

        sql, params = cursor.execute.call_args.args
        self.assertIn('WHERE claim_type = %s', sql)
        self.assertEqual(
            params,
            [facility_views.EXPENSE_CLAIM_TYPE_AUTO_DEBIT],
        )


class AutoDebitMenuMigrationTests(TestCase):
    def test_menu_sync_preserves_existing_primary_key_and_permission(self):
        parent = MenuItem.objects.filter(title='財會', parent=None).first()
        menu_item = MenuItem.objects.get(route='/finance/auto-debit-claims/')
        menu_item.title = '舊名稱'
        menu_item.order = 99
        menu_item.save(update_fields=['title', 'order'])
        user = get_user_model().objects.create_user(
            username='menu-finance-user',
            password='test-only-password',
        )
        user.profile.allowed_menu_items.add(menu_item)
        original_id = menu_item.id
        migration = importlib.import_module(
            'modules.menu.migrations.0006_add_auto_debit_claim_menu'
        )
        apps = SimpleNamespace(get_model=lambda app, model: MenuItem)

        migration.add_auto_debit_claim_menu(apps, None)

        updated = MenuItem.objects.get(route='/finance/auto-debit-claims/')
        self.assertEqual(updated.id, original_id)
        self.assertEqual(updated.title, '自動扣繳單')
        self.assertEqual(updated.parent_id, parent.id)
        self.assertTrue(user.profile.allowed_menu_items.filter(id=original_id).exists())

    def test_reorganization_preserves_ids_and_permissions(self):
        attendance = MenuItem.objects.get(route='/eureka/attendance/')
        booking = MenuItem.objects.get(route='/facility/booking/')
        auto_debit = MenuItem.objects.get(route='/finance/auto-debit-claims/')
        admin = MenuItem.objects.get(title='管理員', parent=None)
        user = get_user_model().objects.create_user(
            username='menu-reorganization-user', password='test-only-password'
        )
        user.profile.allowed_menu_items.set([attendance, booking, auto_debit])
        original_ids = {attendance.route: attendance.id, booking.route: booking.id,
                        auto_debit.route: auto_debit.id}
        migration = importlib.import_module(
            'modules.menu.migrations.0007_reorganize_attendance_booking_auto_debit'
        )
        apps = SimpleNamespace(get_model=lambda app, model: MenuItem)

        migration.reorganize_menu_items(apps, None)

        attendance.refresh_from_db()
        booking.refresh_from_db()
        auto_debit.refresh_from_db()
        self.assertEqual(attendance.id, original_ids[attendance.route])
        self.assertEqual(attendance.parent_id, admin.id)
        self.assertEqual(booking.id, original_ids[booking.route])
        self.assertEqual(booking.parent.title, '同工')
        self.assertEqual(auto_debit.id, original_ids[auto_debit.route])
        self.assertEqual(auto_debit.title, '請款/自動扣繳單')
        self.assertEqual(
            set(user.profile.allowed_menu_items.values_list('id', flat=True)),
            set(original_ids.values()),
        )
