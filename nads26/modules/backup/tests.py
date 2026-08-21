from django.test import TestCase
from modules.backup.models import BackupConfig, BackupHistory
import datetime

class BackupModelTest(TestCase):
    def test_backup_config_singleton(self):
        # Retrieve the singleton
        config1 = BackupConfig.get_solo()
        self.assertIsNotNone(config1)
        self.assertEqual(config1.backup_path, "/app/backups")
        self.assertEqual(config1.dest_type, "local")
        self.assertFalse(config1.schedule_enabled)
        
        # Modify the singleton
        config1.backup_path = "/custom/backups"
        config1.save()
        
        # Retrieve again and check it's the same record
        config2 = BackupConfig.get_solo()
        self.assertEqual(config2.id, 1)
        self.assertEqual(config2.backup_path, "/custom/backups")
        
    def test_backup_history_creation(self):
        history = BackupHistory.objects.create(
            filename="nads26_backup_test.tar.gz",
            filepath="/app/backups/archive/nads26_backup_test.tar.gz",
            filesize=1024,
            status="success",
            trigger_type="manual",
            comment="Test comment"
        )
        self.assertEqual(history.filename, "nads26_backup_test.tar.gz")
        self.assertEqual(history.status, "success")
        self.assertEqual(history.trigger_type, "manual")
        self.assertEqual(history.comment, "Test comment")
        
        # Check ordering (latest first)
        history2 = BackupHistory.objects.create(
            filename="nads26_backup_test2.tar.gz",
            filepath="/app/backups/archive/nads26_backup_test2.tar.gz",
            filesize=2048,
            status="failed",
            trigger_type="scheduled"
        )
        
        latest = BackupHistory.objects.all().first()
        self.assertEqual(latest.filename, "nads26_backup_test2.tar.gz")
