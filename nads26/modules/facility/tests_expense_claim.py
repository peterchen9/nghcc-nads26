from decimal import Decimal
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from django.test import SimpleTestCase

from . import views


class ExpenseClaimBudgetChoiceTests(SimpleTestCase):
    def test_expense_claim_template_wraps_activity_budget_details(self):
        template = (
            Path(views.settings.BASE_DIR) / 'templates' / 'facility' / 'expense_claim.html'
        ).read_text(encoding='utf-8')

        self.assertIn('width: 380px', template)
        self.assertIn('font-size: 0.72rem', template)
        self.assertIn('white-space: nowrap', template)
        self.assertIn(r'\u6d3b\u52d5\u8207\u9810\u7b97\uff1a${choice.activityBudget', template)
        self.assertIn('class="budget-code-select"', template)
        self.assertNotIn('class="budget-picker-options"', template)

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
