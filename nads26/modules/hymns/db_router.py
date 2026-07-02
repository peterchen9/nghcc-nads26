"""
資料庫路由器：將 hymns app 的查詢導向 hymns_bank
"""


class HymnsRouter:
    """將 modules.hymns 的所有資料庫操作導向 hymns_bank"""

    app_label = 'hymns'

    def db_for_read(self, model, **hints):
        if model._meta.app_label == self.app_label:
            return 'hymns_bank'
        return None

    def db_for_write(self, model, **hints):
        if model._meta.app_label == self.app_label:
            return 'hymns_bank'
        return None

    def allow_relation(self, obj1, obj2, **hints):
        return None

    def allow_migrate(self, db, app_label, model_name=None, **hints):
        if app_label == self.app_label:
            return False  # managed = False，不需要 migrate
        return None
