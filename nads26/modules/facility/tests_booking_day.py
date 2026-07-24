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
    def test_floor_sections_follow_requested_order(self):
        rooms = [
            {
                'id': index, 'area_id': 1, 'room_name': room_name,
                'sort_key': room_name, 'description': '', 'capacity': 10,
                'photo_urls': [],
            }
            for index, room_name in enumerate(
                ['B01', '咖啡吧', '601', '501', '401', '301', '201', '101'],
                start=1,
            )
        ]

        sections = views._group_rooms_by_floor(rooms)

        self.assertEqual(
            [section['label'] for section in sections],
            ['1F', '2F', '3F', '4F', '5F', '6F', 'B1F', '其他'],
        )

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
    def test_booking_page_renders_interactive_overview_as_single_entry(self, _rooms_mock, _entries_mock):
        response = self.client.get(reverse('facility-booking'), {'date': '2026-07-21'})

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'facility/booking_daily_overview.html')
        self.assertTemplateNotUsed(response, 'facility/booking.html')
        self.assertContains(response, '<h2>場地登記</h2>', html=True)
        self.assertContains(response, '2026-07-21')
        self.assertContains(response, '測試聚會')
        self.assertContains(response, 'writing-mode: vertical-rl')
        self.assertContains(response, 'class="day-overview-booking-unit"')
        self.assertContains(response, 'class="day-overview-slot-button"')
        self.assertContains(response, 'class="day-overview-booked-button"')
        self.assertContains(response, 'class="day-overview-room-button"')
        self.assertNotContains(response, 'class="day-overview-capacity"')
        self.assertContains(response, '::-webkit-calendar-picker-indicator')
        self.assertContains(response, '場地圖')
        self.assertNotContains(response, 'class="day-overview-map-label"')
        self.assertNotContains(response, 'class="day-overview-booked" rowspan=')
        self.assertEqual(
            response.content.decode('utf-8').count('class="day-overview-booked"'),
            3,
        )
        self.assertContains(response, 'action="/facility/booking/?date=2026-07-21"')
        self.assertNotContains(response, 'name="return_view"')
        self.assertNotContains(response, '返回場地登記')
        self.assertEqual(response.context['prev_day'], date(2026, 7, 20))
        self.assertEqual(response.context['next_day'], date(2026, 7, 22))

    def test_old_daily_overview_url_redirects_to_single_entry(self):
        response = self.client.get(reverse('facility-booking-day'), {'date': '2026-07-21'})

        self.assertRedirects(
            response,
            '/facility/booking/?date=2026-07-21',
            fetch_redirect_response=False,
        )

    @patch('modules.facility.views._create_entry', return_value=(date(2026, 7, 21), 1))
    @patch('modules.facility.views._rooms', return_value=sample_rooms())
    def test_obsolete_return_view_still_returns_to_single_entry(self, _rooms_mock, _create_mock):
        response = self.client.post(reverse('facility-booking'), {
            'action': 'create',
            'return_view': 'day',
            'date': '2026-07-21',
            'room_id': '1',
        })

        self.assertRedirects(
            response,
            '/facility/booking/?date=2026-07-21',
            fetch_redirect_response=False,
        )

    @patch('modules.facility.views._create_entry', return_value=(date(2026, 7, 21), 1))
    @patch('modules.facility.views._rooms', return_value=sample_rooms())
    def test_existing_submission_still_returns_to_existing_view(self, _rooms_mock, _create_mock):
        response = self.client.post(reverse('facility-booking'), {
            'action': 'create',
            'date': '2026-07-21',
            'room_id': '1',
        })

        self.assertRedirects(
            response,
            '/facility/booking/?date=2026-07-21',
            fetch_redirect_response=False,
        )
