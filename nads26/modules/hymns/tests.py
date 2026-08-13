import tempfile
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from django.http import Http404
from django.test import RequestFactory, SimpleTestCase

from .serializers import HymnDetailSerializer
from .views import serve_midi_resource


class MidiResourceTests(SimpleTestCase):
    def setUp(self):
        self.request = RequestFactory().get('/hymn_resources/midi/test.mid')
        self.request.user = SimpleNamespace(is_authenticated=True)

    def test_serves_existing_midi_file(self):
        with tempfile.TemporaryDirectory() as midi_dir:
            midi_path = Path(midi_dir) / 'test.mid'
            midi_path.write_bytes(b'MThd-test-midi')
            with patch('modules.hymns.views.MIDI_DIR', midi_dir):
                response = serve_midi_resource(self.request, 'test.mid')

            self.assertEqual(response.status_code, 200)
            self.assertEqual(response['Content-Type'], 'audio/midi')
            self.assertEqual(b''.join(response.streaming_content), b'MThd-test-midi')
            response.close()

    def test_rejects_non_midi_extension(self):
        with self.assertRaises(Http404):
            serve_midi_resource(self.request, 'notes.txt')

    def test_requires_authentication(self):
        self.request.user = SimpleNamespace(is_authenticated=False)
        response = serve_midi_resource(self.request, 'test.mid')

        self.assertEqual(response.status_code, 302)
        self.assertIn('/accounts/login/', response.url)

    def test_detail_midi_url_remains_relative_behind_https_proxy(self):
        request = RequestFactory().get('/api/hymns/1/', HTTP_HOST='ad.nghcc.org.tw')
        serializer = HymnDetailSerializer(context={'request': request})

        midi_url = serializer.get_midi_url(SimpleNamespace(midi='100801_時刻近主.mid'))

        self.assertEqual(midi_url, '/hymn_resources/midi/100801_%E6%99%82%E5%88%BB%E8%BF%91%E4%B8%BB.mid')
        self.assertFalse(midi_url.startswith(('http://', 'https://')))
