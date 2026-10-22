import json
import tempfile
import unittest
from pathlib import Path
from config import load_allowlist
from outlook_core import OutlookReader, BridgeError
from test_core import fixture


class AllowlistTests(unittest.TestCase):
    def load(self, value):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "config.local.json"
            path.write_text(json.dumps(value), encoding="utf-8")
            return load_allowlist(path)

    def test_empty_and_wildcard_configs_fail_closed(self):
        for value in ({}, {"allowed_domains": []}, {"allowed_domains": ["*.example.edu"]},
                      {"allowed_domains": "example.edu"}, {"allowed_addresses": ["invalid"]},
                      {"unknown": True}, []):
            with self.subTest(value=value), self.assertRaises(BridgeError):
                self.load(value)

    def test_missing_config_fails_closed(self):
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaises(BridgeError):
                load_allowlist(Path(directory) / "missing.json")

    def test_address_is_exact_and_default_grants_nothing(self):
        domains, addresses = self.load({"allowed_addresses": [" U@ED.AC.UK "]})
        original, _, _ = fixture()
        self.assertEqual(OutlookReader(original.ns).list_accounts()["accounts"], [])
        reader = OutlookReader(original.ns, domains, addresses)
        self.assertEqual(len(reader.list_accounts()["accounts"]), 1)
        original.ns.Accounts.rows[0].SmtpAddress = "other@ed.ac.uk"
        self.assertEqual(reader.list_accounts()["accounts"], [])


if __name__ == "__main__":
    unittest.main()
