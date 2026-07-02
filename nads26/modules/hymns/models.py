"""
詩歌資料庫 — 資料模型
對應 hymns_bank.hymns 表

hymns_bank 欄位名與 Django 欄位名的對應：
  DB column       → Django field
  hymnid          → id (PK)
  cname1          → hymntitle
  ch_namestroke   → stroke_id
  ename           → ename
  tune_mark       → tune_mark  (原 tone，已改名)
  beat_mark       → beat_mark  (原 beat，已改名)
  source          → source
  lyric_author    → lyric_author
  tune_author     → tune_author
  lyric           → lyric
  midi_str        → midistr
  rsv1            → resv1
  rsv2            → resv2
  score_file      → score_file  (新增)
  mp3_file        → mp3_file   (新增)
  midi            → midi       (新增)
  simplescore     → simplescore (新增)
  htm_file        → htm_file   (新增)
"""
from django.db import models


class Hymn(models.Model):
    """詩歌主檔 — 對應 hymns_bank.hymns 表"""

    # ─── 主鍵 ───
    id = models.AutoField(primary_key=True, db_column='hymnid')

    # ─── 原 hymns_bank 既有欄位 ───
    hymntitle = models.CharField('曲名', max_length=255, default='',
                                 db_column='cname1')
    stroke_id = models.CharField('筆劃排序碼', max_length=255, default='',
                                 db_column='ch_namestroke')
    ename = models.CharField('英文名', max_length=255, blank=True, default='')
    tune_mark = models.CharField('調性', max_length=10, blank=True, default='')
    beat_mark = models.CharField('拍號', max_length=10, blank=True, default='')
    source = models.CharField('來源', max_length=500, blank=True, default='')
    lyric_author = models.CharField('作詞者', max_length=100, blank=True, default='')
    tune_author = models.CharField('作曲者', max_length=100, blank=True, default='')
    lyric = models.TextField('歌詞', blank=True, default='')
    midistr = models.TextField('MIDI 字串', blank=True, default='',
                               db_column='midistr')

    # hymns_bank 既有但前端暫不使用的欄位
    cname2 = models.CharField('曲名2', max_length=255, blank=True, default='')
    nghc_native = models.BooleanField('NGHC 原創', default=False)
    bible_verse = models.CharField('經文出處', max_length=50, blank=True, default='')
    classify = models.CharField('分類', max_length=30, blank=True, default='')
    tags = models.CharField('標籤', max_length=100, blank=True, default='')
    language = models.CharField('語言', max_length=10, blank=True, default='')
    note = models.CharField('備註', max_length=200, blank=True, default='')
    year = models.CharField('年份', max_length=50, blank=True, default='')

    # 保留欄位
    resv1 = models.CharField('保留欄位1', max_length=255, blank=True, default='',
                              db_column='rsv1')
    resv2 = models.CharField('保留欄位2', max_length=255, blank=True, default='',
                              db_column='rsv2')

    cname_nghc_old = models.CharField('舊版中文名', max_length=255, blank=True, default='', null=True)
    notes_simple = models.TextField('簡譜', blank=True, default='', null=True)

    # ─── 新增欄位（需 ALTER TABLE 加入 hymns_bank.hymns）───
    score_file = models.CharField('樂譜檔案', max_length=200, blank=True, default='')
    mp3_file = models.CharField('MP3 檔案', max_length=200, blank=True, default='')
    midi = models.CharField('MIDI 檔案', max_length=200, blank=True, default='')
    update_date = models.CharField('更新', max_length=200, blank=True, default='')
    simplescore = models.TextField('簡譜', blank=True, default='')
    htm_file = models.CharField('HTM 檔案', max_length=500, blank=True, default='')

    class Meta:
        db_table = 'hymns'
        managed = False  # 不由 Django 管理 schema
        verbose_name = '詩歌'
        verbose_name_plural = '詩歌'
        ordering = ['id']

    def __str__(self):
        return f'[{self.stroke_id}] {self.hymntitle}'

    @property
    def has_score(self):
        return bool(self.score_file)

    @property
    def has_mp3(self):
        return bool(self.mp3_file)

    @property
    def has_midi(self):
        return bool(self.midi) or bool(self.midistr)
