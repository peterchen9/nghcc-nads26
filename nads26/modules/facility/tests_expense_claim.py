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
        post.setlist('budget_code', ['A001'])
        post.setlist('purpose', ['購買小組教材'])
        post.setlist('amount', ['1500'])

        items = views._expense_items_from_post(post)

        self.assertEqual(items[0]['purpose'], '購買小組教材')
        self.assertEqual(items[0]['item_name'], '購買小組教材')

    def test_expense_claim_table_removes_item_name_and_widens_purpose(self):
        template = (
            Path(views.settings.BASE_DIR) / 'templates' / 'facility' / 'expense_claim.html'
        ).read_text(encoding='utf-8')

        self.assertNotIn('<th>請款項目</th>', template)
        self.assertNotIn('name="item_name"', template)
        self.assertIn('class="purpose-cell"', template)
        self.assertIn('width: 42%', template)

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
