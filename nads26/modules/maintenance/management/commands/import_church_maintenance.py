import json
import mimetypes
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path
from urllib.parse import unquote, urlparse

from django.core.files import File
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone
from django.utils.dateparse import parse_datetime

from modules.maintenance.models import (
    MaintenanceAttachment,
    MaintenanceCategory,
    MaintenanceLocation,
    MaintenanceRecord,
    MaintenanceVendor,
)


class Command(BaseCommand):
    help = 'Import the exported React/Express church maintenance data into Django/MySQL.'

    def add_arguments(self, parser):
        parser.add_argument('source_dir', help='Directory containing exported JSON files and uploads/')

    def _load(self, source_dir, filename):
        path = source_dir / filename
        if not path.is_file():
            raise CommandError(f'Missing source file: {path}')
        return json.loads(path.read_text(encoding='utf-8-sig'))

    def _date(self, value):
        if not value:
            return timezone.localdate()
        parsed = parse_datetime(value)
        if parsed:
            return parsed.date()
        return date.fromisoformat(str(value)[:10])

    def _datetime(self, value):
        parsed = parse_datetime(value or '')
        if not parsed:
            return None
        if timezone.is_naive(parsed):
            parsed = timezone.make_aware(parsed, timezone.get_current_timezone())
        return parsed

    def _source_file(self, source_dir, source_path):
        filename = Path(unquote(urlparse(source_path or '').path)).name
        if not filename:
            return None
        candidate = source_dir / 'uploads' / filename
        return candidate if candidate.is_file() else None

    @transaction.atomic
    def handle(self, *args, **options):
        source_dir = Path(options['source_dir']).resolve()
        if not source_dir.is_dir():
            raise CommandError(f'Source directory does not exist: {source_dir}')

        category_rows = self._load(source_dir, 'categories.json')
        location_rows = self._load(source_dir, 'locations.json')
        vendor_rows = self._load(source_dir, 'vendors.json')
        record_rows = self._load(source_dir, 'maintenance-records.json')

        categories = {}
        for row in category_rows:
            item, _ = MaintenanceCategory.objects.update_or_create(
                source_id=row['id'],
                defaults={
                    'name': (row.get('name') or '').strip(),
                    'notes': row.get('notes') or '',
                    'is_active': bool(row.get('isActive', True)),
                },
            )
            categories[row['id']] = item

        locations = {}
        for row in location_rows:
            item, _ = MaintenanceLocation.objects.update_or_create(
                source_id=row['id'],
                defaults={
                    'name': (row.get('name') or '').strip(),
                    'area': row.get('area') or '',
                    'floor': row.get('floor') or '',
                    'notes': row.get('notes') or '',
                    'is_active': bool(row.get('isActive', True)),
                },
            )
            locations[row['id']] = item

        vendors = {}
        vendor_fields = {
            'category': 'category', 'contact': 'contact', 'mobile_phone': 'mobilePhone',
            'company_phone': 'companyPhone', 'email': 'email', 'line': 'line',
            'address': 'address', 'tax_id': 'taxId', 'bank_name': 'bankName',
            'bank_branch': 'bankBranch', 'bank_account_name': 'bankAccountName',
            'bank_account_number': 'bankAccountNumber', 'notes': 'notes',
        }
        for row in vendor_rows:
            defaults = {'name': (row.get('name') or '').strip(), 'is_active': bool(row.get('isActive', True))}
            defaults.update({target: row.get(source) or '' for target, source in vendor_fields.items()})
            item, _ = MaintenanceVendor.objects.update_or_create(source_id=row['id'], defaults=defaults)
            vendors[row['id']] = item

        attachment_total = 0
        path_types = (
            ('onsiteImagePath', MaintenanceAttachment.Type.ONSITE),
            ('quoteImagePath', MaintenanceAttachment.Type.QUOTE),
            ('receiptImagePath', MaintenanceAttachment.Type.RECEIPT),
        )
        for row in record_rows:
            defaults = {
                'maintenance_date': self._date(row.get('maintenanceDate')),
                'type': row.get('type') if row.get('type') in MaintenanceRecord.Type.values else MaintenanceRecord.Type.GENERAL,
                'category': categories.get(row.get('categoryId')),
                'location': locations.get(row.get('locationId')),
                'handler': row.get('handler') or '未指定',
                'vendor': vendors.get(row.get('vendorId')),
                'vendor_representative': row.get('vendorRepresentative') or '',
                'issue': row.get('issue') or '',
                'result': row.get('result') or '',
                'status': row.get('status') if row.get('status') in MaintenanceRecord.Status.values else MaintenanceRecord.Status.PENDING,
                'cost': Decimal(str(row.get('cost') or 0)),
                'notes': row.get('notes') or '',
            }
            record, _ = MaintenanceRecord.objects.update_or_create(source_id=row['id'], defaults=defaults)
            created_at = self._datetime(row.get('createdAt'))
            updated_at = self._datetime(row.get('updatedAt'))
            if created_at or updated_at:
                MaintenanceRecord.objects.filter(pk=record.pk).update(
                    created_at=created_at or record.created_at,
                    updated_at=updated_at or record.updated_at,
                )

            sources = [(row.get(field), attachment_type, None, None) for field, attachment_type in path_types]
            for nested in row.get('attachments') or []:
                raw_type = str(nested.get('type') or 'OTHER').upper()
                attachment_type = raw_type if raw_type in MaintenanceAttachment.Type.values else MaintenanceAttachment.Type.OTHER
                sources.append((nested.get('filePath'), attachment_type, nested.get('originalName'), nested.get('mimeType')))

            seen_paths = set()
            for source_path, attachment_type, original_name, mime_type in sources:
                source_file = self._source_file(source_dir, source_path)
                if not source_file or str(source_file) in seen_paths:
                    continue
                seen_paths.add(str(source_file))
                source_key = f'record:{row["id"]}:{attachment_type}:{source_file.name}'
                if MaintenanceAttachment.objects.filter(source_key=source_key).exists():
                    continue
                with source_file.open('rb') as handle:
                    attachment = MaintenanceAttachment(
                        source_key=source_key,
                        record=record,
                        type=attachment_type,
                        original_name=original_name or source_file.name,
                        mime_type=mime_type or mimetypes.guess_type(source_file.name)[0] or '',
                    )
                    attachment.file.save(source_file.name, File(handle), save=True)
                attachment_total += 1

        self.stdout.write(self.style.SUCCESS(
            f'Imported categories={len(category_rows)}, locations={len(location_rows)}, '
            f'vendors={len(vendor_rows)}, records={len(record_rows)}, new_attachments={attachment_total}'
        ))
