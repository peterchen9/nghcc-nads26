import datetime
import urllib3
import requests
from requests.auth import HTTPDigestAuth

from django.core.management.base import BaseCommand, CommandError
from django.conf import settings
from django.utils import timezone
from modules.eureka.models import StaffAttendance

# Disable SSL verification warnings for local self-signed certificates
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

class Command(BaseCommand):
    help = 'Sync staff clock-in data from Hikvision Access Control device'

    def handle(self, *args, **options):
        self.stdout.write("Starting staff attendance sync...")

        host = getattr(settings, 'HIKVISION_HOST', 'https://172.20.22.123').rstrip('/')
        user = getattr(settings, 'HIKVISION_USER', 'admin')
        password = getattr(settings, 'HIKVISION_PASS', 'nghcc8765')

        # Define time range: from yesterday 00:00:00 to today 23:59:59
        tz = timezone.get_current_timezone()
        now = datetime.datetime.now(tz)
        yesterday = now - datetime.timedelta(days=1)
        
        start_time = yesterday.replace(hour=0, minute=0, second=0, microsecond=0).isoformat()
        end_time = now.replace(hour=23, minute=59, second=59, microsecond=0).isoformat()

        self.stdout.write(f"Querying events from {start_time} to {end_time}")

        url = f"{host}/ISAPI/AccessControl/AcsEvent?format=json"
        
        position = 0
        limit = 30  # Device maximum limit is 30
        new_records_count = 0
        duplicate_count = 0
        search_id = f"sync_{int(now.timestamp())}"

        while True:
            self.stdout.write(f"Fetching events starting from position {position}...")
            
            payload = {
                "AcsEventCond": {
                    "searchID": search_id,
                    "searchResultPosition": position,
                    "maxResults": limit,
                    "major": 5,
                    "minor": 0,
                    "startTime": start_time,
                    "endTime": end_time
                }
            }

            try:
                response = requests.post(
                    url,
                    json=payload,
                    auth=HTTPDigestAuth(user, password),
                    verify=False,
                    timeout=15
                )
                response.raise_for_status()
                data = response.json()
            except Exception as e:
                self.stderr.write(self.style.ERROR(f"Failed to query Hikvision device: {e}"))
                raise CommandError(f"Failed to query Hikvision device: {e}")

            acs_event = data.get('AcsEvent', {})
            info_list = acs_event.get('InfoList', [])

            if not info_list:
                self.stdout.write(f"No more events found at position {position}.")
                break

            self.stdout.write(f"Processing {len(info_list)} events...")

            for event in info_list:
                name = event.get('name', '').strip()
                employee_no = event.get('employeeNoString', '').strip()
                serial_no = event.get('serialNo')
                time_str = event.get('time')
                card_no = event.get('cardNo', '').strip()

                if not name or not employee_no or serial_no is None or not time_str:
                    continue

                # Check if this is a successful authentication event
                minor = event.get('minor')
                if minor not in [1, 2, 38, 75, 77]:
                    continue

                # Parse the timestamp (e.g. 2026-06-09T14:52:53+08:00)
                try:
                    timestamp = datetime.datetime.fromisoformat(time_str)
                except ValueError:
                    self.stderr.write(self.style.WARNING(f"Skipping event with invalid timestamp format: {time_str}"))
                    continue

                # Check if this serial_no already exists
                if StaffAttendance.objects.filter(serial_no=serial_no).exists():
                    duplicate_count += 1
                    continue

                # Create new record
                try:
                    StaffAttendance.objects.create(
                        employee_no=employee_no,
                        name=name,
                        card_no=card_no,
                        timestamp=timestamp,
                        serial_no=serial_no
                    )
                    new_records_count += 1
                except Exception as e:
                    self.stderr.write(self.style.ERROR(f"Error saving attendance record {serial_no}: {e}"))

            # If we retrieved fewer events than the page limit, we reached the end
            if len(info_list) < limit:
                break
                
            position += len(info_list)

        self.stdout.write(
            self.style.SUCCESS(
                f"Sync complete. Added {new_records_count} new records, skipped {duplicate_count} duplicates."
            )
        )

