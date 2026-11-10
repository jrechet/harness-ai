import json
import threading
import unittest
import urllib.error
import urllib.request

from shared.http import make_server


class Echo:
    def handle(self, method, path, body=None):
        if path == "/missing":
            return 404, {"error": "not_found"}
        return 200, {"method": method, "path": path, "body": body}


class HttpAdapterTest(unittest.TestCase):
    def setUp(self):
        self.server = make_server(Echo(), 0)
        self.base = f"http://127.0.0.1:{self.server.server_address[1]}"
        threading.Thread(target=self.server.serve_forever, daemon=True).start()

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()

    def call(self, method, path, data=None):
        request = urllib.request.Request(self.base + path, data=data, method=method)
        try:
            with urllib.request.urlopen(request, timeout=5) as response:
                return response.status, json.loads(response.read())
        except urllib.error.HTTPError as error:
            return error.code, json.loads(error.read())

    def test_a_get_reaches_the_service(self):
        self.assertEqual(self.call("GET", "/orders/o-1?x=1"), (200, {"method": "GET", "path": "/orders/o-1?x=1", "body": None}))

    def test_a_json_body_is_decoded(self):
        status, payload = self.call("POST", "/orders", json.dumps({"quantity": 2}).encode())
        self.assertEqual((status, payload["body"]), (200, {"quantity": 2}))

    def test_the_status_of_the_service_is_the_status_of_the_response(self):
        self.assertEqual(self.call("GET", "/missing"), (404, {"error": "not_found"}))

    def test_a_body_that_is_not_json_never_reaches_the_service(self):
        self.assertEqual(self.call("POST", "/orders", b"{not json"), (400, {"error": "invalid_json"}))


if __name__ == "__main__":
    unittest.main()
