import datetime
from django.core.management.base import BaseCommand
from django.utils import timezone
from modules.backup.models import BackupConfig, BackupHistory
from modules.backup.views import run_backup_generator

class Command(BaseCommand):
    help = "Runs the scheduled backup if it is enabled and the scheduled time has passed for today."

    def add_arguments(self, parser):
        parser.add_argument('--force', action='store_true', help='Force the backup to run immediately')

    def handle(self, *args, **options):
        config = BackupConfig.get_solo()
        force = options['force']

        if not force:
            if not config.schedule_enabled:
                self.stdout.write("定期備份功能未啟用。")
                return
            
            # Check time: compare local time with configured backup_time
            now = timezone.localtime(timezone.now())
            current_time = now.time()
            scheduled_time = config.backup_time

            # Check if current time is past scheduled time
            if current_time < scheduled_time:
                self.stdout.write(f"目前時間 ({current_time.strftime('%H:%M')}) 尚未到達設定的備份時間 ({scheduled_time.strftime('%H:%M')})。")
                return

            # Check if there is already a successful scheduled backup today
            today = now.date()
            already_done = BackupHistory.objects.filter(
                trigger_type='scheduled',
                status='success',
                created_at__date=today
            ).exists()

            if already_done:
                self.stdout.write("今日已成功執行過排程備份。")
                return

        self.stdout.write("符合執行備份條件，開始備份流程...")
        
        # Run the generator synchronous from command line and print progress logs
        for log_event in run_backup_generator(trigger_type='scheduled'):
            # Extract line content from event format "data: <log>\n\n"
            if log_event.startswith("data: "):
                log_line = log_event[6:].strip()
                self.stdout.write(log_line)
