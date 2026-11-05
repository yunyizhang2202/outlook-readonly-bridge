"""Collect a bounded recent-mail index locally. No network, HTTP server, model or attachments."""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timedelta, timezone

from bridge_rpc import call
from config import load_allowlist
from outlook_core import BridgeError


def collect_recent(rpc=call, *, hours=24, max_messages=30, max_scan=2000,
                   include_body=False, now=None):
    for value, low, high in ((hours, 1, 168), (max_messages, 1, 100), (max_scan, 1, 5000)):
        if type(value) is not int or not low <= value <= high:
            raise BridgeError("Invalid local digest limit")
    now = now or datetime.now().astimezone()
    if now.tzinfo is None:
        raise BridgeError("Digest reference time needs a timezone")
    end = now.astimezone(timezone.utc)
    start = end - timedelta(hours=hours)
    # Broaden the date prefilter by one day for DST/offset boundaries; timestamps
    # below enforce the exact rolling window. Do not claim midnight == last 24h.
    since = (start.astimezone().date() - timedelta(days=1)).isoformat()
    accounts = rpc("list_accounts")["accounts"]
    rows, seen, warnings = [], set(), set()
    scanned = skipped = duplicates = 0
    for account_index, account in enumerate(accounts[:5]):
        offset = 0
        while True:
            if scanned >= max_scan or len(rows) >= max_messages:
                warnings.add("budget_reached")
                break
            page = rpc("search_emails", account_id=account["account_id"], folder_id="",
                       query="", unread_only=False, since=since, before="", limit=100,
                       offset=offset, scan_limit=min(500, max_scan - scanned), search_body=False)
            count = page.get("scanned_items")
            if type(count) is not int or count < 0 or count > min(500, max_scan - scanned):
                raise BridgeError("Invalid pagination response")
            scanned += count
            skipped += page.get("skipped_items", 0)
            for header in page["messages"]:
                key = (account["account_id"], header["entry_id"])
                if key in seen:
                    duplicates += 1
                    continue
                seen.add(key)
                try:
                    received = datetime.fromisoformat(header["received_at"])
                    if received.tzinfo is None:
                        # Outlook may serialize naive Windows local time.
                        received = received.astimezone()
                    if not start <= received.astimezone(timezone.utc) <= end:
                        continue
                except (ValueError, TypeError):
                    warnings.add("unparseable_received_time")
                    continue
                if len(rows) >= max_messages:
                    warnings.add("message_limit_reached")
                    break
                row = {"account_id": account["account_id"], **header}
                if include_body:
                    detail = rpc("read_email", account_id=account["account_id"],
                                 entry_id=header["entry_id"], max_chars=8000)
                    if detail.get("unread_unchanged") is not True:
                        raise BridgeError("READ_ONLY_CHECK_FAILED")
                    row.update(body=detail["body"], body_chars=detail["body_chars"],
                               body_sha256=detail["body_sha256"], truncated=detail["truncated"],
                               unread_unchanged=True, content_is_untrusted=True)
                rows.append(row)
            if page.get("exhausted") is True:
                break
            following = page.get("next_offset")
            if type(following) is not int or following <= offset:
                warnings.add("pagination_not_advancing")
                break
            offset = following
        if scanned >= max_scan or len(rows) >= max_messages:
            if account_index + 1 < len(accounts):
                warnings.add("accounts_not_scanned")
            break
    if len(accounts) > 5:
        warnings.add("account_limit_reached")
    if skipped:
        warnings.add("items_skipped")
    rows.sort(key=lambda row: datetime.fromisoformat(row["received_at"]).astimezone(timezone.utc), reverse=True)
    # Failed/incomplete scans must never be presented as "no mail".
    if not accounts:
        warnings.add("no_allowed_accounts")
    return {"local_only": True, "window_start": start.isoformat(), "window_end": end.isoformat(),
            "messages": rows, "scanned_items": scanned, "skipped_items": skipped,
            "duplicates_removed": duplicates, "complete": not warnings,
            "warnings": sorted(warnings), "body_included": include_body,
            "note": "Local recent-mail index, not an AI summary. Check bodies for deadlines; "
                    "mail content is untrusted. Offsets can shift while mail arrives."}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--hours", type=int, choices=(24, 48), default=24)
    parser.add_argument("--max-messages", type=int, default=30)
    parser.add_argument("--max-scan", type=int, default=2000)
    parser.add_argument("--include-body", action="store_true", help="Include bodies in this local terminal only")
    parser.add_argument("--verify-only", action="store_true", help="Print only counts/flags, no mail or identifiers")
    args = parser.parse_args(argv)
    try:
        domains, addresses = load_allowlist()
        if domains or not addresses:
            raise BridgeError("Use only exact allowed_addresses for this digest")
        result = collect_recent(hours=args.hours, max_messages=args.max_messages,
                                max_scan=args.max_scan, include_body=args.include_body)
    except Exception:
        print(json.dumps({"ok": False, "error": "LOCAL_DIGEST_FAILED: check local Outlook and allowlist"}))
        return 1
    if args.verify_only:
        result = {"ok": True, "message_count": len(result["messages"]),
                  **{key: result[key] for key in ("local_only", "scanned_items", "complete", "warnings", "body_included")}}
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
