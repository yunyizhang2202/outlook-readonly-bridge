import base64
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace as Obj
from outlook_core import BridgeError, OutlookReader


class Collection:
    def __init__(self, rows):
        self.rows = rows
    @property
    def Count(self):
        return len(self.rows)
    def Item(self, index):
        return self.rows[index-1]
    def Sort(self, field, descending):
        self.rows.sort(key=lambda m: m.ReceivedTime, reverse=descending)


class Attachment:
    def __init__(self, name, data, reported_size=None):
        self.FileName, self.data = name, data
        self.Size = len(data) if reported_size is None else reported_size
        self.last_path = None
    def SaveAsFile(self, path):
        self.last_path = Path(path)
        self.last_path.write_bytes(self.data)


def fixture():
    folder = Obj(StoreID="school", EntryID="inbox", Name="Inbox", FolderPath="School/Inbox",
                 DefaultItemType=0, Folders=Collection([]))
    rows = [Obj(Class=43, EntryID=f"m{i}", Subject=f"Class test {i}", SenderName="Tutor",
                SenderEmailAddress="tutor@ed.ac.uk", ReceivedTime=datetime(2026, 10, i+1, tzinfo=timezone.utc),
                UnRead=True, Size=128, Attachments=Collection([]), Parent=folder,
                Body="中文正文 and R code" if i == 0 else "Course notes") for i in range(3)]
    folder.Items = Collection(rows)
    store = Obj(StoreID="school", DisplayName="School", GetDefaultFolder=lambda n: folder,
                GetRootFolder=lambda: folder)
    unrelated = Obj(StoreID="personal", DisplayName="Personal")
    accounts = Collection([Obj(SmtpAddress="u@ed.ac.uk", DisplayName="School", DeliveryStore=store),
                           Obj(SmtpAddress="u@gmail.com", DisplayName="Personal", DeliveryStore=unrelated)])
    namespace = Obj(Accounts=accounts, GetFolderFromID=lambda f, s: folder,
                    GetItemFromID=lambda m, s: next(x for x in rows if x.EntryID == m))
    return OutlookReader(namespace, allowed_domains=("ed.ac.uk", "sms.ed.ac.uk")), rows, folder


class Tests(unittest.TestCase):
    def setUp(self):
        self.reader, self.rows, self.folder = fixture()

    def test_school_scope_and_cross_account_denial(self):
        self.assertEqual(len(self.reader.list_accounts()["accounts"]), 1)
        with self.assertRaises(BridgeError): self.reader.read_email("personal", "m0")
        self.folder.StoreID = "personal"
        with self.assertRaises(BridgeError): self.reader.read_email("school", "m0")

    def test_student_school_domain_and_lookalikes(self):
        school = self.reader.ns.Accounts.rows[0]
        school.SmtpAddress = "u@sms.ed.ac.uk"
        self.reader.ns.Accounts.rows.extend([
            Obj(SmtpAddress="u@fake.sms.ed.ac.uk", DisplayName="Other", DeliveryStore=school.DeliveryStore),
            Obj(SmtpAddress="u@sms.ed.ac.uk.example.com", DisplayName="Other", DeliveryStore=school.DeliveryStore),
        ])
        self.assertEqual([x["email"] for x in self.reader.list_accounts()["accounts"]],
                         ["u@sms.ed.ac.uk"])
        self.assertEqual(self.reader.read_email("school", "m0")["body"], "中文正文 and R code")
        school.SmtpAddress = "u@ed.ac.uk"
        self.assertEqual([x["email"] for x in self.reader.list_accounts()["accounts"]], ["u@ed.ac.uk"])

    def test_read_is_unmodified_and_reports_truncation(self):
        original = [x.UnRead for x in self.rows]
        result = self.reader.read_email("school", "m0", 2)
        self.assertEqual(result["body"], "中文")
        self.assertTrue(result["truncated"])
        self.assertGreater(result["body_chars"], 2)
        self.assertEqual([x.UnRead for x in self.rows], original)

    def test_search_partial_pages_are_explicit(self):
        result = self.reader.search_emails("school", query="no match", scan_limit=1)
        self.assertEqual(result["messages"], [])
        self.assertFalse(result["exhausted"])
        self.assertEqual(result["next_offset"], 1)

    def test_search_body_and_pagination(self):
        result = self.reader.search_emails("school", query="中文", search_body=True, offset=2)
        self.assertEqual([x["entry_id"] for x in result["messages"]], ["m0"])
        self.assertTrue(result["exhausted"])
        self.assertTrue(self.rows[0].UnRead)

    def test_dates_and_validation(self):
        result = self.reader.search_emails("school", since="2026-10-02", before="2026-10-03")
        self.assertEqual([x["entry_id"] for x in result["messages"]], ["m1"])
        for kwargs in ({"limit": 0}, {"offset": -1}, {"scan_limit": 100000},
                       {"since": "2026-1-1"}, {"unread_only": "true"}):
            with self.assertRaises(BridgeError): self.reader.search_emails("school", **kwargs)

    def test_attachment_never_uses_untrusted_name_as_path(self):
        attachment = Attachment("../../escape.txt", b"sample")
        self.rows[0].Attachments = Collection([attachment])
        result = self.reader.read_attachment("school", "m0", 1)
        self.assertEqual(base64.b64decode(result["content_base64"]), b"sample")
        self.assertEqual(attachment.last_path.name, "attachment.bin")
        self.assertFalse(attachment.last_path.exists())
        self.assertTrue(self.rows[0].UnRead)

    def test_attachment_size_limits(self):
        attachment = Attachment("large.txt", b"12345", reported_size=1)
        self.rows[0].Attachments = Collection([attachment])
        with self.assertRaises(BridgeError): self.reader.read_attachment("school", "m0", 1, 4)
        self.assertFalse(attachment.last_path.exists())
        with self.assertRaises(BridgeError): self.reader.read_attachment("school", "m0", 2)


if __name__ == "__main__":
    unittest.main()

