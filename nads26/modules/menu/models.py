from django.db import models

class MenuItem(models.Model):
    title = models.CharField("標題", max_length=100)
    route = models.CharField(
        "路由", max_length=200, blank=True, default="",
        help_text="連結路徑，例如 /expense。父目錄留空即可。",
    )
    icon = models.CharField(
        "圖示", max_length=50, blank=True, default="",
        help_text="選填，例如 🎇 或 Material Icon 名稱",
    )
    parent = models.ForeignKey(
        "self", null=True, blank=True,
        on_delete=models.CASCADE,
        related_name="children",
        verbose_name="上層目錄",
    )
    order = models.PositiveSmallIntegerField("排序", default=0, help_text="數字越小越前面")
    roles = models.CharField(
        "可見角色", max_length=200, default="*",
        help_text="逗號分隔角色名稱，* 表示所有人可見。例如：admin,staff",
    )
    is_active = models.BooleanField("啟用", default=True)

    class Meta:
        ordering = ["order", "id"]
        verbose_name = "選單項目"
        verbose_name_plural = "選單項目"

    def __str__(self):
        if self.parent:
            return f"  └── {self.title}"
        return self.title
