from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import patch

from django.test import SimpleTestCase

from . import views


class ExpenseClaimBudgetChoiceTests(SimpleTestCase):
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

