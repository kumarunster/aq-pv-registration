import json
import tempfile
import threading
import unittest
from concurrent.futures import ThreadPoolExecutor
from http.client import HTTPConnection
from pathlib import Path
from unittest.mock import patch

from kataster.core import ServiceError
from kataster.server import create_server


class RestServiceTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.output = Path(self.temp.name)
        self.server = create_server('127.0.0.1', 0, self.output)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=3)
        self.temp.cleanup()

    def request(self, method, path, body=None, content_type='application/json'):
        conn = HTTPConnection('127.0.0.1', self.server.server_port, timeout=5)
        try:
            conn.request(method, path, body=body, headers={'Content-Type': content_type})
            response = conn.getresponse()
            return response.status, response.getheader('Content-Type'), response.read()
        finally:
            conn.close()

    def test_health_and_providers(self):
        status, _, raw = self.request('GET', '/health')
        self.assertEqual(status, 200)
        self.assertEqual(json.loads(raw), {'status': 'ok'})
        status, _, raw = self.request('GET', '/laender')
        self.assertEqual(status, 200)
        self.assertEqual(len(json.loads(raw)), 16)

    def test_extract_and_download_links(self):
        def fake_extract(address, dest, width, **kwargs):
            self.assertEqual(address, 'Im Schönenfelde 14, 21109 Hamburg')
            self.assertEqual(width, 60)
            self.assertFalse(kwargs['allow_fallback'])
            dest.mkdir()
            (dest / 'karte.png').write_bytes(b'example-png')
            (dest / 'grundstueck.json').write_text('{"gemarkung":"Wilhelmsburg"}')
            return {'status': 'ok', 'bild': {'datei': 'karte.png'}}

        payload = json.dumps({'adresse': 'Im Schönenfelde 14, 21109 Hamburg', 'nur_amtlich': True})
        with patch('kataster.server.extract', side_effect=fake_extract):
            status, _, raw = self.request('POST', '/auszug', payload)
        self.assertEqual(status, 200)
        urls = json.loads(raw)['dateien']
        status, content_type, raw = self.request('GET', urls['bild'])
        self.assertEqual((status, content_type, raw), (200, 'image/png', b'example-png'))
        status, _, raw = self.request('GET', urls['json'])
        self.assertEqual(status, 200)
        self.assertEqual(json.loads(raw)['gemarkung'], 'Wilhelmsburg')

    def test_invalid_requests_do_not_trigger_extraction(self):
        bodies = ['[]', '{', '{}', '{"adresse":"abcde","nur_amtlich":1}',
                  '{"adresse":"abcde","breite_meter":true}',
                  '{"adresse":"abcde","breite_meter":"60"}']
        with patch('kataster.server.extract') as extract:
            for body in bodies:
                with self.subTest(body=body):
                    status, _, _ = self.request('POST', '/auszug', body)
                    self.assertEqual(status, 400)
            status, _, _ = self.request('POST', '/auszug', '{}', 'text/plain')
            self.assertEqual(status, 415)
            extract.assert_not_called()

    def test_unknown_download_and_traversal_rejected(self):
        for path in ['/ergebnisse/../../kataster/core.py', '/ergebnisse/' + 'a'*32 + '/unknown', '/missing']:
            self.assertEqual(self.request('GET', path)[0], 404)

    def test_upstream_and_address_errors_are_json(self):
        for code, expected in [('ADDRESS_AMBIGUOUS', 422), ('UPSTREAM_ERROR', 502)]:
            with patch('kataster.server.extract', side_effect=ServiceError(code, 'Testfehler')):
                status, _, raw = self.request('POST', '/auszug', '{"adresse":"Testadresse 1"}')
                self.assertEqual(status, expected)
                self.assertEqual(json.loads(raw)['code'], code)

    def test_concurrent_job_gets_busy_response(self):
        entered = threading.Event()
        release = threading.Event()

        def fake_extract(*args, **kwargs):
            entered.set()
            release.wait(timeout=4)
            return {'status': 'teilweise', 'bild': {'datei': None}}

        with patch('kataster.server.extract', side_effect=fake_extract), ThreadPoolExecutor(max_workers=1) as pool:
            first = pool.submit(self.request, 'POST', '/auszug', '{"adresse":"Testadresse 1"}')
            try:
                self.assertTrue(entered.wait(timeout=2))
                status, _, raw = self.request('POST', '/auszug', '{"adresse":"Testadresse 2"}')
                self.assertEqual(status, 429)
                self.assertEqual(json.loads(raw)['code'], 'BUSY')
            finally:
                release.set()
            self.assertEqual(first.result(timeout=3)[0], 200)


if __name__ == '__main__':
    unittest.main()
