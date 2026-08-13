import tempfile
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from django.http import Http404
from django.test import RequestFactory, SimpleTestCase

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
