import calendar
from datetime import date


def _add_months(value, months):
    """Return the calendar anniversary after ``months`` months."""
    month_index = value.month - 1 + months
    year = value.year + month_index // 12
    month = month_index % 12 + 1
    day = min(value.day, calendar.monthrange(year, month)[1])
    return date(year, month, day)


def completed_service_years(onboard_date, as_of_date):
    if not onboard_date or as_of_date < onboard_date:
        return 0
    years = as_of_date.year - onboard_date.year
    anniversary = _add_months(onboard_date, years * 12)
    return years - (anniversary > as_of_date)


def annual_leave_cycle_start(onboard_date, as_of_date):
    """Return the most recent hire-date anniversary on or before the date."""
    if not onboard_date or as_of_date < onboard_date:
        return None
    years = completed_service_years(onboard_date, as_of_date)
    return _add_months(onboard_date, years * 12)


def annual_leave_entitlement(onboard_date, as_of_date):
    """Calculate statutory-style annual leave from the hire-date anniversary."""
    if not onboard_date or as_of_date < onboard_date:
        return 0.0
    if as_of_date < _add_months(onboard_date, 6):
        return 0.0

    years = completed_service_years(onboard_date, as_of_date)
    if years < 1:
        return 3.0
    if years == 1:
        return 7.0
    if years == 2:
        return 10.0
    if years < 5:
        return 14.0
    if years < 10:
        return 15.0
    return float(min(30, 16 + (years - 10)))
