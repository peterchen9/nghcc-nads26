from datetime import date

from django.test import SimpleTestCase

from .leave_rules import annual_leave_cycle_start, annual_leave_entitlement


class AnnualLeaveEntitlementTests(SimpleTestCase):
    def test_anniversary_thresholds(self):
        onboard = date(2020, 8, 14)
        cases = [
            (date(2021, 2, 13), 0),
            (date(2021, 2, 14), 3),
            (date(2021, 8, 14), 7),
            (date(2022, 8, 14), 10),
            (date(2023, 8, 14), 14),
            (date(2025, 8, 14), 15),
            (date(2030, 8, 14), 16),
            (date(2031, 8, 14), 17),
            (date(2044, 8, 14), 30),
            (date(2050, 8, 14), 30),
        ]
        for as_of_date, expected in cases:
            with self.subTest(as_of_date=as_of_date):
                self.assertEqual(
                    annual_leave_entitlement(onboard, as_of_date), expected
                )

    def test_leap_day_anniversary_uses_last_day_of_february(self):
        onboard = date(2020, 2, 29)
        self.assertEqual(annual_leave_entitlement(onboard, date(2021, 2, 27)), 3)
        self.assertEqual(annual_leave_entitlement(onboard, date(2021, 2, 28)), 7)

    def test_missing_or_future_onboard_date_has_no_entitlement(self):
        self.assertEqual(annual_leave_entitlement(None, date(2026, 8, 14)), 0)
        self.assertEqual(
            annual_leave_entitlement(date(2027, 1, 1), date(2026, 8, 14)), 0
        )

    def test_cycle_start_uses_exact_anniversary_day(self):
        onboard = date(2006, 9, 1)
        self.assertEqual(
            annual_leave_cycle_start(onboard, date(2026, 8, 31)),
            date(2025, 9, 1),
        )
        self.assertEqual(
            annual_leave_cycle_start(onboard, date(2026, 9, 1)),
            date(2026, 9, 1),
        )

    def test_cycle_start_preserves_mid_month_and_leap_day_boundaries(self):
        self.assertEqual(
            annual_leave_cycle_start(date(2020, 11, 15), date(2026, 11, 14)),
            date(2025, 11, 15),
        )
        self.assertEqual(
            annual_leave_cycle_start(date(2020, 11, 15), date(2026, 11, 15)),
            date(2026, 11, 15),
        )
        self.assertEqual(
            annual_leave_cycle_start(date(2020, 2, 29), date(2026, 2, 28)),
            date(2026, 2, 28),
        )
