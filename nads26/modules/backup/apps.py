from django.apps import AppConfig

class BackupConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'modules.backup'
    verbose_name = '系統備份管理'
