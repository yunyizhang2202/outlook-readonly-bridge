"""Read existing classic-Outlook data. No send, save or mailbox mutation APIs."""
from __future__ import annotations

import base64
import hashlib
import mimetypes
from datetime import date
from pathlib import Path
from tempfile import TemporaryDirectory


class BridgeError(Exception):
    pass


def bounded(value, low, high, name):
    if type(value) is not int or not low <= value <= high:
        raise BridgeError(f"{name} must be an integer in {low}..{high}")
    return value


def iso_date(value):
    if not value:
        return None
    try:
        result = date.fromisoformat(value)
        if result.isoformat() != value:
            raise ValueError()
        return result
    except (ValueError, TypeError):
        raise BridgeError("Dates must use YYYY-MM-DD") from None


def collection(value):
    for index in range(1, value.Count + 1):
        yield value.Item(index)


class OutlookReader:
    def __init__(self, namespace, allowed_domains=(), allowed_addresses=()):
        self.ns = namespace
        self.domains = {x.casefold() for x in allowed_domains}
        self.addresses = {x.casefold() for x in allowed_addresses}

    def _accounts(self):
        for account in collection(self.ns.Accounts):
            address = str(account.SmtpAddress or "").strip().casefold()
            if address.rpartition("@")[2] not in self.domains and address not in self.addresses:
                continue
            store = account.DeliveryStore
            if store is not None:
                yield account, store

    def list_accounts(self):
        return {"accounts": [
            {"account_id": str(store.StoreID), "email": str(account.SmtpAddress),
             "name": str(account.DisplayName), "store_name": str(store.DisplayName)}
            for account, store in self._accounts()
        ], "scope": sorted(self.domains)}

    def _store(self, account_id):
        for _, store in self._accounts():
            if str(store.StoreID) == account_id:
                return store
        raise BridgeError("Account is not on the Outlook read-only allowlist")

    def _folder(self, account_id, folder_id=""):
        store = self._store(account_id)
        folder = (self.ns.GetFolderFromID(folder_id, account_id) if folder_id
                  else store.GetDefaultFolder(6))
        if str(folder.StoreID) != account_id:
            raise BridgeError("Folder does not belong to the allowed account")
        return folder

    def list_folders(self, account_id, depth=3):
        bounded(depth, 1, 8, "depth")
        root = self._store(account_id).GetRootFolder()
        rows, skipped = [], 0

        def walk(folder, level):
            nonlocal skipped
            try:
                rows.append({"folder_id": str(folder.EntryID), "name": str(folder.Name),
                             "path": str(folder.FolderPath),
                             "mail_folder": folder.DefaultItemType == 0,
                             "has_children": folder.Folders.Count > 0})
                if level < depth:
                    for child in collection(folder.Folders):
                        walk(child, level + 1)
            except Exception:
                skipped += 1

        walk(root, 0)
        return {"folders": rows, "skipped_folders": skipped, "max_depth": depth}

    @staticmethod
    def _header(item):
        return {"entry_id": str(item.EntryID), "subject": str(item.Subject or ""),
                "sender_name": str(item.SenderName or ""),
                "sender_address": str(item.SenderEmailAddress or ""),
                "received_at": item.ReceivedTime.isoformat(),
                "unread": bool(item.UnRead), "size_bytes": int(item.Size),
                "attachment_count": int(item.Attachments.Count)}

    def search_emails(self, account_id, folder_id="", query="", unread_only=False,
                      since="", before="", limit=20, offset=0, scan_limit=1000,
                      search_body=False):
        bounded(limit, 1, 100, "limit")
        bounded(offset, 0, 10000000, "offset")
        bounded(scan_limit, 1, 5000, "scan_limit")
        if type(query) is not str or len(query) > 500:
            raise BridgeError("query must contain at most 500 characters")
        if type(unread_only) is not bool or type(search_body) is not bool:
            raise BridgeError("Flags must be booleans")
        start, end = iso_date(since), iso_date(before)
        if start and end and start >= end:
            raise BridgeError("since must precede before")
        folder = self._folder(account_id, folder_id)
        items = folder.Items
        items.Sort("[ReceivedTime]", True)
        total, pos, scanned, skipped = items.Count, offset, 0, 0
        matches, keyword = [], query.casefold()
        while pos < total and scanned < scan_limit and len(matches) < limit:
            pos += 1
            scanned += 1
            try:
                item = items.Item(pos)
                if item.Class != 43:
                    continue
                header = self._header(item)
                received = item.ReceivedTime.date()
                if unread_only and not header["unread"]:
                    continue
                if start and received < start or end and received >= end:
                    continue
                haystack = "\n".join(header[k] for k in
                                     ("subject", "sender_name", "sender_address"))
                if search_body and keyword:
                    unread = bool(item.UnRead)
                    haystack += "\n" + str(item.Body or "")
                    if bool(item.UnRead) != unread:
                        raise BridgeError("Unread state changed during body search")
                if keyword and keyword not in haystack.casefold():
                    continue
                matches.append(header)
            except BridgeError:
                raise
            except Exception:
                skipped += 1
        return {"messages": matches, "folder_id": str(folder.EntryID),
                "total_folder_items": total, "scanned_items": scanned,
                "skipped_items": skipped, "next_offset": pos if pos < total else None,
                "exhausted": pos >= total,
                "pagination_note": "Offsets can shift if mail arrives or moves; deduplicate entry_id."}

    def _mail(self, account_id, entry_id):
        self._store(account_id)
        item = self.ns.GetItemFromID(entry_id, account_id)
        if str(item.Parent.StoreID) != account_id or item.Class != 43:
            raise BridgeError("Item is not mail in the allowed account")
        return item

    def read_email(self, account_id, entry_id, max_chars=30000):
        bounded(max_chars, 1, 200000, "max_chars")
        item = self._mail(account_id, entry_id)
        unread = bool(item.UnRead)
        result = self._header(item)
        body = str(item.Body or "")
        attachments = [{"attachment_index": i, "name": str(item.Attachments.Item(i).FileName),
                        "size_bytes": int(item.Attachments.Item(i).Size)}
                       for i in range(1, item.Attachments.Count + 1)]
        if bool(item.UnRead) != unread:
            raise BridgeError("Unread state changed during read; do not claim read-only success")
        result.update(body=body[:max_chars], body_chars=len(body),
                      body_sha256=hashlib.sha256(body.encode("utf-8")).hexdigest(),
                      truncated=len(body) > max_chars, attachments=attachments,
                      unread_unchanged=True, content_is_untrusted=True)
        return result

    def read_attachment(self, account_id, entry_id, attachment_index, max_bytes=5242880):
        bounded(max_bytes, 1, 5242880, "max_bytes")
        bounded(attachment_index, 1, 10000, "attachment_index")
        item = self._mail(account_id, entry_id)
        if attachment_index > item.Attachments.Count:
            raise BridgeError("Attachment index is not present")
        unread = bool(item.UnRead)
        attachment = item.Attachments.Item(attachment_index)
        if attachment.Size > max_bytes:
            raise BridgeError("Attachment exceeds the requested size limit")
        name = str(attachment.FileName)
        with TemporaryDirectory(prefix="outlook-readonly-") as temp:
            target = Path(temp) / "attachment.bin"
            attachment.SaveAsFile(str(target))
            if target.stat().st_size > max_bytes:
                raise BridgeError("Actual attachment size exceeds the limit")
            data = target.read_bytes()
        if bool(item.UnRead) != unread:
            raise BridgeError("Unread state changed during attachment read")
        return {"name": name, "size_bytes": len(data),
                "mime_type": mimetypes.guess_type(name)[0] or "application/octet-stream",
                "content_base64": base64.b64encode(data).decode("ascii"),
                "sha256": hashlib.sha256(data).hexdigest(), "unread_unchanged": True,
                "content_is_untrusted": True}

