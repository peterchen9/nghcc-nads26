from datetime import date, datetime
from types import SimpleNamespace
from unittest.mock import patch

from django.http import QueryDict
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
        'ical_uid': 'nads26-series-test',
        'can_edit': False,
    }]


class DailyOverviewHelperTests(SimpleTestCase):
    def test_conflict_detail_identifies_requested_slot_and_existing_owner(self):
        requested_start = datetime(2026, 8, 12, 9, 0, tzinfo=views.TZ)
        requested_end = datetime(2026, 8, 12, 10, 0, tzinfo=views.TZ)
        existing_start = datetime(2026, 8, 12, 9, 30, tzinfo=views.TZ)
        existing_end = datetime(2026, 8, 12, 11, 0, tzinfo=views.TZ)

        detail = views._conflict_detail(requested_start, requested_end, {
            'start_time': views._to_ts(existing_start),
            'end_time': views._to_ts(existing_end),
            'room_name': '201',
            'name': '同工會議',
            'create_by': '王小明',
        })

        self.assertIn('欲登記 2026-08-12 09:00–10:00／201', detail)
        self.assertIn('既有登記「同工會議」2026-08-12 09:30–11:00', detail)
        self.assertIn('登記人：王小明', detail)

    @patch('modules.facility.views.messages.error')
    def test_show_conflicts_displays_every_conflicting_booking(self, error_mock):
        requested_start = datetime(2026, 8, 12, 9, 0, tzinfo=views.TZ)
        requested_end = datetime(2026, 8, 12, 12, 0, tzinfo=views.TZ)
        conflicts = []
        for name, owner, hour in [('會議一', '甲', 9), ('會議二', '乙', 10)]:
            conflicts.append((requested_start, requested_end, {
                'start_time': views._to_ts(datetime(2026, 8, 12, hour, 0, tzinfo=views.TZ)),
                'end_time': views._to_ts(datetime(2026, 8, 12, hour + 1, 0, tzinfo=views.TZ)),
                'room_name': '201',
                'name': name,
                'create_by': owner,
            }))

        views._show_conflicts(SimpleNamespace(), conflicts)

        self.assertEqual(error_mock.call_count, 2)
        self.assertIn('登記人：甲', error_mock.call_args_list[0].args[1])
        self.assertIn('登記人：乙', error_mock.call_args_list[1].args[1])

    def test_weekly_recurring_days_accept_multiple_weekdays(self):
        data = QueryDict('', mutable=True)
        data.update({'range_start': '2026-07-20', 'range_end': '2026-07-26', 'recurrence_type': 'weekly'})
        data.setlist('weekdays', ['0', '2', '6'])
        request = SimpleNamespace(POST=data)

        self.assertEqual(
            views._recurring_admin_days(request),
            [date(2026, 7, 20), date(2026, 7, 22), date(2026, 7, 26)],
        )

    def test_monthly_recurring_days_accept_multiple_weeks_and_weekdays(self):
        data = QueryDict('', mutable=True)
        data.update({'range_start': '2026-08-01', 'range_end': '2026-08-31', 'recurrence_type': 'monthly_nth'})
        data.setlist('repeat_weeks', ['1', '3'])
        data.setlist('weekdays', ['0', '4'])
        request = SimpleNamespace(POST=data)

        self.assertEqual(
            views._recurring_admin_days(request),
            [date(2026, 8, 3), date(2026, 8, 7), date(2026, 8, 17), date(2026, 8, 21)],
        )

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
    @patch('modules.facility.views._rooms', return_value=sample_rooms())
    def test_room_admin_hides_legacy_recurring_booking_entry(self, _rooms_mock):
        response = self.client.get(reverse('facility-rooms'))

        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, 'id="openRecurringModal"')
        self.assertNotContains(response, 'id="recurringModal"')

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
        self.assertNotContains(response, 'id="dayOpenNewBooking"')
        self.assertNotContains(response, '>查詢</button>')
        self.assertContains(response, 'onchange="this.form.submit()"')
        self.assertContains(response, 'id="dayModalRoomSelect"')
        self.assertContains(response, '>週期性登記</option>')
        self.assertContains(response, 'name="range_start"')
        self.assertContains(response, 'name="range_end"')
        self.assertContains(response, 'name="weekdays"')
        self.assertContains(response, 'name="repeat_weeks"')
        self.assertContains(response, 'id="dayDeleteScopeModal"')
        self.assertContains(response, '取消當天及之後')
        self.assertContains(response, 'data-series-id="nads26-series-test"')
        self.assertContains(response, 'style="--booking-row-count: 3; z-index: 5;"')
        self.assertContains(response, 'height: calc(var(--booking-row-count, 1) * 27px)')
        self.assertContains(response, 'text-align: start')
        self.assertNotContains(response, 'class="day-overview-capacity"')
        self.assertContains(response, '::-webkit-calendar-picker-indicator')
        self.assertContains(response, 'class="day-overview-date-input"')
        self.assertContains(response, "stroke='%23facc15'")
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

    @patch('modules.facility.views._create_recurring_admin_booking')
    @patch('modules.facility.views._rooms', return_value=sample_rooms())
    def test_integrated_recurring_submission_uses_existing_admin_logic(self, _rooms_mock, recurring_mock):
        response = self.client.post(reverse('facility-booking'), {
            'action': 'create_recurring_booking',
            'range_start': '2026-07-21',
            'range_end': '2026-08-31',
            'room_id': '1',
            'recurrence_type': 'weekly',
            'weekday': '1',
        })

        recurring_mock.assert_called_once()
        self.assertRedirects(
            response,
            '/facility/booking/?date=2026-07-21',
            fetch_redirect_response=False,
        )
