from django.core.management.base import BaseCommand

from modules.network.views import _payload, _scan


class Command(BaseCommand):
    help = 'Scan NU-840 LAN hosts and bandwidth status.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--force',
            action='store_true',
            help='Ignore cached scan data and fetch from the NU-840 immediately.',
        )

    def handle(self, *args, **options):
        snapshot, hosts = _scan(force=options['force'])
        payload = _payload(snapshot, hosts)
        self.stdout.write(
            self.style.SUCCESS(
                f"scanned_at={payload['scanned_at']} status={payload['status']} alive_hosts={payload['host_count']}"
            )
        )
        if payload.get('error_message'):
            self.stdout.write(self.style.WARNING(payload['error_message']))
