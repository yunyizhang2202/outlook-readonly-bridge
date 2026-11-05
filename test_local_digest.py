"""Synthetic pagination/time/body tests, never accesses COM or real mail."""
import unittest
from datetime import datetime, timezone

from local_digest import collect_recent
from outlook_core import BridgeError

NOW = datetime(2026, 11, 5, 12, tzinfo=timezone.utc)


def header(entry, received="2026-11-05T10:00:00+00:00"):
    return {"entry_id": entry, "subject": "Synthetic deadline", "received_at": received, "unread": True}


class DigestTests(unittest.TestCase):
    def rpc(self, pages):
        self.calls = []
        def call(operation, **args):
            self.calls.append((operation, args))
            if operation == "list_accounts":
                return {"accounts": [{"account_id": "synthetic-account"}]}
            if operation == "search_emails":
                return pages[args["offset"]]
            if operation == "read_email":
                return {"body": "Synthetic due date 2026-11-06", "body_chars": 30,
                        "body_sha256": "synthetic-checksum", "truncated": False, "unread_unchanged": True}
            self.fail("Unexpected operation")
        return call

    def test_empty_page_then_recent_message_and_dedup(self):
        pages = {0: {"messages": [], "scanned_items": 2, "next_offset": 2, "exhausted": False},
                 2: {"messages": [header("one"), header("one")], "scanned_items": 2,
                     "next_offset": None, "exhausted": True}}
        result = collect_recent(self.rpc(pages), now=NOW)
        self.assertEqual(len(result["messages"]), 1)
        self.assertEqual(result["duplicates_removed"], 1)
        self.assertTrue(result["complete"])
        self.assertFalse(any(op == "read_email" for op, _ in self.calls))

    def test_exact_rolling_window_and_offsets(self):
        messages = [header("recent", "2026-11-04T14:00:00+01:00"),
                    header("too-old", "2026-11-04T10:00:00+00:00"),
                    header("future", "2026-11-06T10:00:00+00:00")]
        pages = {0: {"messages": messages, "scanned_items": 3, "next_offset": None, "exhausted": True}}
        result = collect_recent(self.rpc(pages), now=NOW)
        self.assertEqual([m["entry_id"] for m in result["messages"]], ["recent"])

    def test_scan_budget_is_not_no_mail(self):
        pages = {0: {"messages": [], "scanned_items": 2, "next_offset": 2, "exhausted": False}}
        result = collect_recent(self.rpc(pages), now=NOW, max_scan=2)
        self.assertFalse(result["complete"])
        self.assertIn("budget_reached", result["warnings"])
        self.assertEqual(result["messages"], [])

    def test_body_is_opt_in_and_unread_checked(self):
        pages = {0: {"messages": [header("one")], "scanned_items": 1, "next_offset": None, "exhausted": True}}
        rpc = self.rpc(pages)
        result = collect_recent(rpc, now=NOW, include_body=True)
        self.assertIn("body", result["messages"][0])
        self.assertTrue(result["messages"][0]["unread_unchanged"])
        def changed(operation, **args):
            return {"unread_unchanged": False} if operation == "read_email" else rpc(operation, **args)
        with self.assertRaises(BridgeError):
            collect_recent(changed, now=NOW, include_body=True)

    def test_pagination_stall_and_message_limit_reported(self):
        pages = {0: {"messages": [header("one"), header("two")], "scanned_items": 2,
                     "next_offset": 0, "exhausted": False}}
        result = collect_recent(self.rpc(pages), now=NOW, max_messages=1)
        self.assertFalse(result["complete"])
        self.assertEqual(len(result["messages"]), 1)
        self.assertIn("message_limit_reached", result["warnings"])
        self.assertIn("pagination_not_advancing", result["warnings"])


if __name__ == "__main__":
    unittest.main()
