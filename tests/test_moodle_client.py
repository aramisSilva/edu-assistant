import json
import unittest

import httpx

from src.services.moodle_client import MoodleClient, MoodleClientError


class MoodleClientTest(unittest.TestCase):
    def test_calls_site_info(self):
        def handler(request):
            self.assertEqual(request.url.path, "/webservice/rest/server.php")
            self.assertIn(b"wsfunction=core_webservice_get_site_info", request.content)
            return httpx.Response(200, json={"userid": 7, "username": "student"})

        client = MoodleClient("http://moodle.test", "token", transport=httpx.MockTransport(handler))
        self.addCleanup(client.close)
        self.assertEqual(client.get_site_info()["userid"], 7)

    def test_reports_moodle_error(self):
        def handler(request):
            return httpx.Response(200, json={"exception": "moodle_exception", "message": "Invalid token"})

        client = MoodleClient("http://moodle.test", "bad", transport=httpx.MockTransport(handler))
        self.addCleanup(client.close)
        with self.assertRaisesRegex(MoodleClientError, "Invalid token"):
            client.get_site_info()

    def test_reports_timeout(self):
        def handler(request):
            raise httpx.ReadTimeout("timeout", request=request)

        client = MoodleClient("http://moodle.test", "token", transport=httpx.MockTransport(handler))
        self.addCleanup(client.close)
        with self.assertRaisesRegex(MoodleClientError, "demorou demais"):
            client.get_site_info()

    def test_paginates_events(self):
        pages = [
            [{"id": index} for index in range(1, 51)],
            [{"id": 51}],
        ]

        def handler(request):
            return httpx.Response(200, json={"events": pages.pop(0)})

        client = MoodleClient("http://moodle.test", "token", transport=httpx.MockTransport(handler))
        self.addCleanup(client.close)
        self.assertEqual(len(client.get_action_events()), 51)


if __name__ == "__main__":
    unittest.main()
