from decimal import Decimal
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from django.http import QueryDict
from django.test import SimpleTestCase

from . import views


class ExpenseClaimBudgetChoiceTests(SimpleTestCase):
    def test_item_post_uses_purpose_for_legacy_item_name(self):
        post = QueryDict('', mutable=True)
        post.setlist('ministry_group', ['牧養'])
        post.setlist('budget_code', ['A001'])
        post.setlist('purpose', ['購買小組教材'])
        post.setlist('amount', ['1500'])

        items = views._expense_items_from_post(post)

        self.assertEqual(items[0]['purpose'], '購買小組教材')
        self.assertEqual(items[0]['item_name'], '購買小組教材')
        self.assertEqual(items[0]['ministry_group'], '牧養')

    def test_expense_claim_table_removes_item_name_and_widens_purpose(self):
        template = (
            Path(views.settings.BASE_DIR) / 'templates' / 'facility' / 'expense_claim.html'
        ).read_text(encoding='utf-8')

        self.assertNotIn('<th>請款項目</th>', template)
        self.assertNotIn('name="item_name"', template)
        self.assertIn('class="purpose-cell"', template)
        self.assertIn('width: 42%', template)

    def test_history_replaces_claim_number_with_purpose_and_has_scope_tabs(self):
        template = (
            Path(views.settings.BASE_DIR) / 'templates' / 'facility' / 'expense_claim.html'
        ).read_text(encoding='utf-8')

        self.assertIn('<th>用途</th>', template)
        self.assertNotIn('<th>單號</th>', template)
        self.assertIn('自己送出的申請表', template)
        self.assertIn('所有人的申請表', template)

    def test_shared_claim_form_does_not_offer_check_payment(self):
        template = (
            Path(views.settings.BASE_DIR) / 'templates' / 'facility' / 'expense_claim.html'
        ).read_text(encoding='utf-8')

        self.assertNotIn('value="支票"', template)
        self.assertIn('value="匯款"', template)
        self.assertIn('value="現金"', template)

    def test_claim_form_uses_four_column_header_and_item_ministry_groups(self):
        template = (
            Path(views.settings.BASE_DIR) / 'templates' / 'facility' / 'expense_claim.html'
        ).read_text(encoding='utf-8')

        self.assertIn('grid-template-columns: repeat(4', template)
        self.assertIn('<th class="budget-category-cell">部門/團契/小組</th>', template)
        self.assertIn('name="ministry_group"', template)
        self.assertNotIn('id="ministry_group"', template)
        self.assertIn('name="save_payee_account"', template)
        self.assertIn('list="savedPayeeAccounts"', template)
        self.assertIn('applySavedPayeeAccount', template)

    def test_bank_fields_are_optional_and_save_account_control_is_below_input(self):
        template = (
            Path(views.settings.BASE_DIR) / 'templates' / 'facility' / 'expense_claim.html'
        ).read_text(encoding='utf-8')
        source = Path(views.__file__).read_text(encoding='utf-8')

        self.assertNotIn('function updateBankRequired()', template)
        self.assertNotIn("const bankInputs = ['bank_name'", template)
        account_input = '<input id="bank_account" name="bank_account" value="{{ claim.bank_account }}">'
        save_control = '<label class="save-account-control"'
        self.assertLess(template.index(account_input), template.index(save_control))
        self.assertNotIn("if claim['payment_method'] == '\\u532f\\u6b3e'", source)
        self.assertIn("or not claim['bank_account']", source)

    def test_pdf_layout_groups_items_by_ministry(self):
        source = Path(views.__file__).read_text(encoding='utf-8')

        self.assertIn("grouped_items.setdefault(group_name, []).append(item)", source)
        self.assertIn("f'部門/團契/小組：{group_name}'", source)
        self.assertIn("f'部門/團契/小組：{group_name}（續）'", source)
        self.assertIn("('請款人', claim['applicant'])", source)
        self.assertIn('憑證請黏貼在虛線以下，或用另一張A4紙靠右貼，放在第二頁', source)

    def test_expense_modal_does_not_close_from_backdrop_click(self):
        template = (
            Path(views.settings.BASE_DIR) / 'templates' / 'facility' / 'expense_claim.html'
        ).read_text(encoding='utf-8')

        self.assertNotIn("backdrop.addEventListener('click'", template)

    def test_superuser_can_view_all_staff_claims(self):
        user = SimpleNamespace(is_authenticated=True, is_superuser=True)
        request = SimpleNamespace(user=user)

        self.assertTrue(views._expense_can_view_all_staff_claims(request))

    @patch('modules.eureka.models.StaffInfo.objects.filter')
    def test_huang_meimei_can_view_all_staff_claims(self, filter_mock):
        filter_mock.return_value.exists.return_value = True
        user = SimpleNamespace(is_authenticated=True, is_superuser=False)
        request = SimpleNamespace(user=user)

        self.assertTrue(views._expense_can_view_all_staff_claims(request))
        filter_mock.assert_called_once_with(user=user, name='黃美美')

    @patch('modules.eureka.models.StaffInfo.objects.filter')
    def test_regular_user_cannot_view_all_staff_claims(self, filter_mock):
        filter_mock.return_value.exists.return_value = False
        user = SimpleNamespace(is_authenticated=True, is_superuser=False)
        request = SimpleNamespace(user=user)

        self.assertFalse(views._expense_can_view_all_staff_claims(request))

    def test_expense_claim_template_wraps_activity_budget_details(self):
        template = (
            Path(views.settings.BASE_DIR) / 'templates' / 'facility' / 'expense_claim.html'
        ).read_text(encoding='utf-8')

        self.assertIn('width: min(720px', template)
        self.assertIn('font: inherit', template)
        self.assertIn('white-space: normal', template)
        self.assertIn(r'\u6d3b\u52d5\u8207\u9810\u7b97\uff1a${choice.activityBudget', template)
        self.assertIn('class="budget-code-trigger"', template)
        self.assertIn('class="budget-code-value"', template)
        self.assertIn('selected?.code ||', template)
        self.assertIn('positionBudgetDropdown(trigger)', template)

    @patch('modules.facility.views._expense_budget_queryset')
    def test_budget_choice_includes_activity_budget(self, queryset_mock):
        queryset_mock.return_value = [SimpleNamespace(
            budget_code='A001',
            category='牧養',
            ministry='成人事工',
            activity_budget='小組教材與活動費',
            usage_ratio=Decimal('25.0'),
            balance=Decimal('7500'),
        )]

        choices = views._expense_budget_choices()

        self.assertEqual(choices[0]['activityBudget'], '小組教材與活動費')
        self.assertEqual(choices[0]['balanceText'], '7,500')
