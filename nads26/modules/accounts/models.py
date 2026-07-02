from django.db import models
from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver

class UserProfile(models.Model):
    user = models.OneToOneField(
        User, on_delete=models.CASCADE,
        related_name='profile', verbose_name='使用者',
    )
    worker_ename = models.CharField(
        '同工英文名', max_length=50, blank=True, default='',
    )
    display_name = models.CharField(
        '顯示名稱（中文姓名）', max_length=100, blank=True, default='',
    )
    department = models.CharField('部門', max_length=50, blank=True, default='')
    worker_id = models.CharField('同工編號', max_length=20, blank=True, default='')
    role = models.CharField('角色', max_length=50, blank=True, default='')
    allowed_menu_items = models.ManyToManyField(
        'menu.MenuItem', blank=True, verbose_name='可存取的選單項目'
    )

    class Meta:
        verbose_name = '使用者擴充資料'
        verbose_name_plural = '使用者擴充資料'

    def __str__(self):
        return f'{self.user.username} — {self.display_name or self.worker_ename}'

class SystemSetting(models.Model):
    key = models.CharField("設定鍵", max_length=50, unique=True, help_text="系統內部識別碼，請勿修改。")
    value = models.TextField("設定值", blank=True)
    description = models.CharField("描述", max_length=200, blank=True)

    class Meta:
        verbose_name = "系統設定"
        verbose_name_plural = "系統設定"

    def __str__(self):
        return f"{self.description} ({self.key})"

@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        UserProfile.objects.create(
            user=instance,
            worker_ename=instance.username,
        )
