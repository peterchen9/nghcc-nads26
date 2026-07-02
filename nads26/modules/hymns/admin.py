"""詩歌資料庫 — Django Admin 設定"""
from django.contrib import admin
from .models import Hymn


@admin.register(Hymn)
class HymnAdmin(admin.ModelAdmin):
    list_display = ['stroke_id', 'hymntitle', 'ename', 'tune_mark', 'beat_mark',
                    'source', 'lyric_author', 'tune_author',
                    'has_score', 'has_mp3', 'has_midi']
    list_filter = ['tune_mark']
    search_fields = ['stroke_id', 'hymntitle', 'ename', 'source']
    list_per_page = 50

    # 使用 hymns_bank
    using = 'hymns_bank'

    def get_queryset(self, request):
        return super().get_queryset(request).using('hymns_bank')

    def save_model(self, request, obj, form, change):
        obj.save(using='hymns_bank')

    def delete_model(self, request, obj):
        obj.delete(using='hymns_bank')
