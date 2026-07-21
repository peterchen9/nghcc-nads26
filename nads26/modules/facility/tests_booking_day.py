from datetime import date, datetime
from unittest.mock import patch

from django.test import SimpleTestCase, TestCase
from django.urls import reverse

from . import views


def sample_rooms():
    return [
        {
            'id': 2, 'area_id': 1, 'room_name': 'B01', 'sort_key': 'B01',
            'description': '', 'capacity': 20, 'photo_urls': [],
        },
        {
            'id': 1, 'area_id': 1, 'room_name': '201', 'sort_key': '201',
            'description': '', 'capacity': 30, 'photo_urls': [],
        },
    ]


def sample_entries():
    start = datetime(2026, 7, 21, 9, 0, tzinfo=views.TZ)
    end = datetime(2026, 7, 21, 10, 30, tzinfo=views.TZ)
    return [{
        'id': 1,
        'room_id': 1,
        'room_name': '201',
        'start_time': views._to_ts(start),
        'end_time': views._to_ts(end),
        'start_label': '09:00',
        'end_label': '10:30',
        'name': '測試聚會',
        'use_unit': '測試單位',
        'create_by': 'tester',
        'description': '',
        'can_edit': False,
    }]


class DailyOverviewHelperTests(SimpleTestCase):
    def test_combines_floor_sections_and_preserves_rowspan(self):
        rooms, floor_groups, rows = views._build_daily_overview(
            sample_rooms(),
            sample_entries(),
            date(2026, 7, 21),
        )

        self.assertEqual([room['room_name'] for room in rooms], ['201', 'B01'])
        self.assertEqual(floor_groups, [
            {'label': '2F', 'room_count': 1},
            {'label': 'B1F', 'room_count': 1},
        ])
        nine_row = next(row for row in rows if row['slot']['label'] == '09:00')
        self.assertEqual(nine_row['cells'][0]['rowspan'], 3)
        self.assertEqual(nine_row['cells'][0]['booking']['name'], '測試聚會')


class DailyOverviewPageTests(TestCase):
    @patch('modules.facility.views._entries', return_value=sample_entries())
    @patch('modules.facility.views._rooms', return_value=sample_rooms())
    def test_daily_overview_renders_selected_date(self, _rooms_mock, _entries_mock):
        response = self.client.get(reverse('facility-booking-day'), {'date': '2026-07-21'})

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'facility/booking_daily_overview.html')
        self.assertContains(response, '場地登記－當天總表')
        self.assertContains(response, '2026-07-21')
        self.assertContains(response, '測試聚會')
        self.assertEqual(response.context['prev_day'], date(2026, 7, 20))
        self.assertEqual(response.context['next_day'], date(2026, 7, 22))

    @patch('modules.facility.views._entries', return_value=sample_entries())
    @patch('modules.facility.views._rooms', return_value=sample_rooms())
    def test_booking_page_keeps_existing_page_and_adds_overview_link(self, _rooms_mock, _entries_mock):
        response = self.client.get(reverse('facility-booking'), {'date': '2026-07-21'})

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'facility/booking.html')
        self.assertContains(response, '/facility/booking/day/?date=2026-07-21')
        self.assertContains(response, '當天總表')
