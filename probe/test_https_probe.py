"""In-process HTTP/OAuth checks; synthetic credentials, no Windows/mail/network."""
import base64
import hashlib
import re
import unittest
import logging
from urllib.parse import parse_qs, urlsplit

from starlette.testclient import TestClient
from probe.https_probe import create_app, validate_origin, allowed_callback

ORIGIN = "https://probe.example.test"
CALLBACK = "https://chatgpt.com/connector/oauth/synthetic-probe-callback"
PASSWORD = "synthetic-probe-only-passphrase-123456"
VERIFIER = "synthetic-pkce-verifier-" + "a" * 43
logging.disable(logging.CRITICAL)


class ProbeTests(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(create_app(ORIGIN, PASSWORD), base_url=ORIGIN, follow_redirects=False)
        self.client.__enter__()
        self.addCleanup(self.client.__exit__, None, None, None)

    def register(self, callback=CALLBACK):
        return self.client.post("/register", json={"redirect_uris": [callback],
            "client_name": "Synthetic test", "grant_types": ["authorization_code", "refresh_token"],
            "response_types": ["code"], "scope": "probe:read", "token_endpoint_auth_method": "none"})

    def begin(self, resource=ORIGIN + "/mcp"):
        registration = self.register()
        self.assertEqual(registration.status_code, 201)
        client_id = registration.json()["client_id"]
        challenge = base64.urlsafe_b64encode(hashlib.sha256(VERIFIER.encode()).digest()).decode().rstrip("=")
        response = self.client.get("/authorize", params={"client_id": client_id,
            "response_type": "code", "redirect_uri": CALLBACK, "scope": "probe:read",
            "state": "synthetic-state", "code_challenge": challenge,
            "code_challenge_method": "S256", "resource": resource})
        return client_id, response

    def get_code(self):
        client_id, response = self.begin()
        self.assertEqual(response.status_code, 302)
        login_url = response.headers["location"]
        page = self.client.get(login_url)
        csrf = re.search(r"name='csrf' value='([^']+)'", page.text).group(1)
        response = self.client.post(login_url, data={"csrf": csrf, "passphrase": PASSWORD},
                                    headers={"Origin": ORIGIN})
        self.assertEqual(response.status_code, 303)
        query = parse_qs(urlsplit(response.headers["location"]).query)
        self.assertEqual(query["state"], ["synthetic-state"])
        return client_id, query["code"][0]

    def exchange(self, client_id, code, verifier=VERIFIER):
        return self.client.post("/token", data={"grant_type": "authorization_code",
            "client_id": client_id, "code": code, "code_verifier": verifier,
            "redirect_uri": CALLBACK, "resource": ORIGIN + "/mcp"})

    def test_metadata_and_unauthenticated_mcp_rejection(self):
        resource = self.client.get("/.well-known/oauth-protected-resource/mcp")
        self.assertEqual(resource.status_code, 200)
        self.assertEqual(resource.json()["resource"], ORIGIN + "/mcp")
        metadata = self.client.get("/.well-known/oauth-authorization-server").json()
        self.assertIn("S256", metadata["code_challenge_methods_supported"])
        response = self.client.post("/mcp", json={"jsonrpc": "2.0", "method": "tools/list", "id": 1})
        self.assertEqual(response.status_code, 401)
        self.assertIn("resource_metadata=", response.headers["www-authenticate"])

    def test_login_requires_secret_csrf_and_origin(self):
        _, response = self.begin()
        url = response.headers["location"]
        page = self.client.get(url)
        csrf = re.search(r"name='csrf' value='([^']+)'", page.text).group(1)
        self.assertIn("HttpOnly", page.headers["set-cookie"])
        self.assertIn("Secure", page.headers["set-cookie"])
        self.assertEqual(self.client.post(url, data={"passphrase": PASSWORD}).status_code, 403)
        self.assertEqual(self.client.post(url, data={"passphrase": PASSWORD, "csrf": "无效"}).status_code, 403)
        self.assertEqual(self.client.post(url, content=b"a" * 9000).status_code, 413)
        self.assertEqual(self.client.post(url, data={"passphrase": PASSWORD, "csrf": csrf},
                                         headers={"Origin": "https://evil.example.test"}).status_code, 403)
        self.assertEqual(self.client.post(url, data={"passphrase": "wrong", "csrf": csrf}).status_code, 401)

    def test_pkce_and_one_use_code(self):
        client_id, code = self.get_code()
        self.assertEqual(self.exchange(client_id, code, "wrong").status_code, 400)
        self.assertEqual(self.exchange(client_id, code).status_code, 200)
        self.assertEqual(self.exchange(client_id, code).status_code, 400)

    def test_wrong_resource_and_redirect_rejected(self):
        self.assertEqual(self.register("https://evil.example.test/callback").status_code, 400)
        _, response = self.begin("https://other.example.test/mcp")
        self.assertNotEqual(response.status_code, 200)
        self.assertNotIn("/probe-login", response.headers.get("location", ""))

    def test_authenticated_http_has_only_fixed_probe(self):
        client_id, code = self.get_code()
        token_response = self.exchange(client_id, code)
        self.assertEqual(token_response.status_code, 200)
        token = token_response.json()["access_token"]
        headers = {"Authorization": "Bearer " + token, "Accept": "application/json, text/event-stream",
                   "MCP-Protocol-Version": "2025-06-18"}
        listing = self.client.post("/mcp", headers=headers,
                                  json={"jsonrpc": "2.0", "id": 1, "method": "tools/list"})
        self.assertEqual(listing.status_code, 200)
        self.assertEqual([t["name"] for t in listing.json()["result"]["tools"]], ["bridge_ping"])
        called = self.client.post("/mcp", headers=headers, json={"jsonrpc": "2.0", "id": 2,
            "method": "tools/call", "params": {"name": "bridge_ping", "arguments": {}}})
        self.assertEqual(called.status_code, 200)
        self.assertIn("AUTHENTICATED_MCP_PROBE_OK", called.text)
        unknown = self.client.post("/mcp", headers=headers, json={"jsonrpc": "2.0", "id": 3,
            "method": "tools/call", "params": {"name": "outlook_read_email", "arguments": {}}})
        self.assertTrue(unknown.json()["result"]["isError"])
        headers["Authorization"] = "Bearer invalid"
        self.assertEqual(self.client.post("/mcp", headers=headers,
            json={"jsonrpc": "2.0", "id": 4, "method": "tools/list"}).status_code, 401)

    def test_origin_and_callback_validation(self):
        for value in ("http://example.test", "https://user:password@example.test", "https://example.test/mcp",
                      "https://example.test?key=secret", "https://example.test:8787"):
            with self.subTest(value=value), self.assertRaises(ValueError):
                validate_origin(value)
        self.assertFalse(allowed_callback("https://chatgpt.com.evil.test/connector_platform_oauth_redirect"))
        self.assertFalse(allowed_callback("https://chatgpt.com/connector/oauth/../evil"))
        self.assertFalse(allowed_callback(CALLBACK + "?next=evil"))


if __name__ == "__main__":
    unittest.main()
