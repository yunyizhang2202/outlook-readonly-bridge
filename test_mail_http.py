"""Synthetic signed-token and ASGI tests; no external IdP, Outlook or mailbox access."""
import contextlib
import io
import time
import unittest
from dataclasses import replace
from unittest.mock import patch

import jwt
from cryptography.hazmat.primitives.asymmetric import rsa
from starlette.testclient import TestClient

from mail_http import Settings, OwnerTokenVerifier, create_app, exact_mailbox_config

ORIGIN = "https://mail.example.test"
ISSUER = "https://auth.example.test/"
CONFIG = Settings(ORIGIN, ISSUER, ISSUER + ".well-known/jwks.json", ("synthetic-owner",), ("synthetic-client",))


class HTTPMailTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.key = rsa.generate_private_key(public_exponent=65537, key_size=2048)

    def token(self, **changes):
        now = int(time.time())
        claims = {"iss": ISSUER, "aud": ORIGIN + "/mcp", "sub": "synthetic-owner",
                  "azp": "synthetic-client", "scope": "mail:read", "iat": now, "exp": now + 600}
        claims.update(changes)
        return jwt.encode(claims, self.key, algorithm="RS256", headers={"kid": "synthetic-key"})

    def setUp(self):
        self.operations = []

        def rpc(operation, **arguments):
            self.operations.append((operation, arguments))
            if operation == "read_email":
                return {"body": "Synthetic assignment due tomorrow", "truncated": False,
                        "unread_unchanged": True, "attachments": [{"name": "private-name.txt"}]}
            return {"accounts": []} if operation == "list_accounts" else {"messages": [], "exhausted": True}

        self.client = TestClient(create_app(CONFIG, rpc=rpc, mailbox_check=lambda: None,
                                           key_resolver=lambda token: self.key.public_key()),
                                 base_url=ORIGIN, follow_redirects=False)
        self.client.__enter__()
        self.addCleanup(self.client.__exit__, None, None, None)

    def request(self, method, params=None, token=None):
        headers = {"Accept": "application/json, text/event-stream", "MCP-Protocol-Version": "2025-06-18"}
        if token:
            headers["Authorization"] = "Bearer " + token
        return self.client.post("/mcp", headers=headers,
                                json={"jsonrpc": "2.0", "id": 1, "method": method, "params": params or {}})

    def test_metadata_and_no_unauthenticated_mail(self):
        response = self.client.get("/.well-known/oauth-protected-resource/mcp")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["resource"], ORIGIN + "/mcp")
        self.assertEqual(response.json()["authorization_servers"], [ISSUER])
        self.assertEqual(response.json()["scopes_supported"], ["mail:read"])
        response = self.request("tools/list")
        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.headers["cache-control"], "no-store")
        self.assertIn("resource_metadata=", response.headers["www-authenticate"])
        self.assertEqual(self.operations, [])

    def test_invalid_owner_audience_scope_client_and_expiry_rejected(self):
        for change in ({"sub": "other-owner"}, {"aud": "https://other.example.test/mcp"},
                       {"iss": "https://other-issuer.example.test/"}, {"scope": "openid"},
                       {"azp": "other-client"}, {"exp": int(time.time()) - 1},
                       {"exp": int(time.time()) + 3600}, {"iat": int(time.time()) + 60},
                       {"nbf": int(time.time()) + 60}):
            with self.subTest(fields=list(change)):
                self.assertEqual(self.request("tools/list", token=self.token(**change)).status_code, 401)
        self.assertEqual(self.operations, [])

    def test_signature_and_algorithm_rejected_without_claim_logging(self):
        verifier = OwnerTokenVerifier(CONFIG, lambda token: self.key.public_key())
        fake = jwt.encode({"sub": "synthetic-owner"}, "synthetic-wrong-key-" * 3, algorithm="HS256")
        with contextlib.redirect_stdout(io.StringIO()) as output:
            for token in (fake, "not-a-jwt", "x" * 20000):
                self.assertIsNone(verifier.verify(token))
        self.assertEqual(output.getvalue(), "")
        other_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        other = jwt.encode(jwt.decode(self.token(), options={"verify_signature": False}), other_key, algorithm="RS256")
        self.assertIsNone(verifier.verify(other))

    def test_only_three_read_only_tools_and_body_read(self):
        token = self.token()
        response = self.request("tools/list", token=token)
        self.assertEqual(response.status_code, 200)
        tools = response.json()["result"]["tools"]
        self.assertEqual({x["name"] for x in tools},
                         {"outlook_list_accounts", "outlook_search_emails", "outlook_read_email"})
        self.assertTrue(all(x["annotations"]["readOnlyHint"] for x in tools))
        response = self.request("tools/call", {"name": "outlook_read_email",
                                "arguments": {"account_id": "synthetic-account", "entry_id": "synthetic-message"}}, token)
        self.assertEqual(response.status_code, 200)
        self.assertNotIn("private-name.txt", response.text)
        self.assertNotIn('"attachments"', response.text)
        self.assertIn("Synthetic assignment", response.text)
        self.assertEqual(self.operations[0][0], "read_email")
        denied = self.request("tools/call", {"name": "outlook_read_attachment", "arguments": {}}, token)
        self.assertTrue(denied.json()["result"]["isError"])

    def test_mailbox_allowlist_failure_denies_before_rpc(self):
        def denied():
            raise RuntimeError("synthetic-private-address@example.invalid")
        with TestClient(create_app(CONFIG, rpc=lambda *a, **k: self.fail("RPC must not run"),
                                  mailbox_check=denied, key_resolver=lambda token: self.key.public_key()),
                        base_url=ORIGIN) as client:
            response = client.post("/mcp", headers={"Authorization": "Bearer " + self.token(),
                "Accept": "application/json, text/event-stream", "MCP-Protocol-Version": "2025-06-18"},
                json={"jsonrpc": "2.0", "id": 1, "method": "tools/call",
                      "params": {"name": "outlook_list_accounts", "arguments": {}}})
            self.assertTrue(response.json()["result"]["isError"])
            self.assertNotIn("synthetic-private-address", response.text)

    def test_invalid_config_fails_closed(self):
        for change in ({"public_origin": "http://example.test"}, {"public_origin": ORIGIN + "/mcp"},
                       {"allowed_subjects": ()}, {"allowed_clients": ("*",)},
                       {"issuer": "https://auth.example.test"},
                       {"jwks_url": "https://name:secret@example.test/jwks"}):
            with self.subTest(fields=list(change)), self.assertRaises(ValueError):
                replace(CONFIG, **change)

    def test_auth_checked_again_after_success(self):
        self.assertEqual(self.request("tools/list", token=self.token()).status_code, 200)
        response = self.request("tools/call", {"name": "outlook_list_accounts", "arguments": {}})
        self.assertEqual(response.status_code, 401)
        self.assertEqual(self.operations, [])

    def test_exact_mailbox_config_not_domain_wide(self):
        for value in ((("example.invalid",), ()), ((), ())):
            with patch("mail_http.load_allowlist", return_value=value), self.assertRaises(ValueError):
                exact_mailbox_config()
        with patch("mail_http.load_allowlist", return_value=((), ("synthetic@example.invalid",))):
            exact_mailbox_config()


if __name__ == "__main__":
    unittest.main()
