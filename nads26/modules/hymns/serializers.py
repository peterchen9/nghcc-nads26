"""詩歌資料庫 — API 序列化器"""
from rest_framework import serializers
from .models import Hymn


class NullToEmptyMixin:
    """將所有 None 字串值轉為空字串，避免前端 null type error"""
    # 不轉換 boolean 和 integer 欄位
    _keep_null_fields = set()

    def to_representation(self, instance):
        data = super().to_representation(instance)
        for key, value in data.items():
            if value is None and key not in self._keep_null_fields:
                data[key] = ''
        return data


class HymnListSerializer(NullToEmptyMixin, serializers.ModelSerializer):
    """列表用"""
    has_score = serializers.BooleanField(read_only=True)
    has_mp3 = serializers.BooleanField(read_only=True)
    has_midi = serializers.BooleanField(read_only=True)
    lyric_preview = serializers.SerializerMethodField()

    _keep_null_fields = {'id', 'has_score', 'has_mp3', 'has_midi'}

    class Meta:
        model = Hymn
        fields = ['id', 'stroke_id', 'tune_mark', 'beat_mark', 'hymntitle',
                  'ename', 'source', 'lyric_author', 'tune_author',
                  'score_file', 'mp3_file', 'midi', 'htm_file',
                  'has_score', 'has_mp3', 'has_midi',
                  'lyric_preview', 'midistr', 'cname_nghc_old', 'notes_simple', 'lyric']

    def get_lyric_preview(self, obj):
        """歌詞前 50 字預覽"""
        if not obj.lyric:
            return ''
        text = obj.lyric.replace('\n', ' ').strip()
        return text[:50]


class HymnDetailSerializer(NullToEmptyMixin, serializers.ModelSerializer):
    """詳情用"""
    has_score = serializers.BooleanField(read_only=True)
    has_mp3 = serializers.BooleanField(read_only=True)
    has_midi = serializers.BooleanField(read_only=True)
    score_url = serializers.SerializerMethodField()
    mp3_url = serializers.SerializerMethodField()
    midi_url = serializers.SerializerMethodField()

    _keep_null_fields = {'id', 'has_score', 'has_mp3', 'has_midi'}

    class Meta:
        model = Hymn
        fields = ['id', 'stroke_id', 'tune_mark', 'beat_mark', 'hymntitle',
                  'ename', 'source', 'lyric_author', 'tune_author',
                  'score_file', 'mp3_file', 'midi', 'htm_file',
                  'has_score', 'has_mp3', 'has_midi',
                  'score_url', 'mp3_url', 'midi_url',
                  'lyric', 'simplescore', 'midistr',
                  'resv1', 'resv2']

    def _build_media_url(self, request, path):
        """將檔案路徑轉為完整 URL"""
        if not path:
            return None
        if not path.startswith('/'):
            ext = path.split('.')[-1].lower()
            if ext in ['htm', 'html']:
                path = f'/media/hymns/html/{path}'
            elif ext in ['pdf']:
                path = f'/media/hymns/pdf/{path}'
            elif ext in ['mid', 'midi']:
                path = f'/media/hymns/midi/{path}'
            elif ext in ['mp3']:
                path = f'/media/hymns/mp3/{path}'
            else:
                path = f'/media/hymns/{path}'
        if request:
            return request.build_absolute_uri(path)
        return path

    def get_score_url(self, obj):
        if not obj.score_file:
            return ''
        return self._build_media_url(
            self.context.get('request'),
            obj.score_file
        )

    def get_mp3_url(self, obj):
        if not obj.mp3_file:
            return ''
        return self._build_media_url(
            self.context.get('request'),
            obj.mp3_file
        )

    def get_midi_url(self, obj):
        if not obj.midi:
            return ''
        return self._build_media_url(
            self.context.get('request'),
            obj.midi
        )
