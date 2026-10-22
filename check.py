"""Local proof report; never prints mail bodies, subjects or credentials."""
import json
from bridge_rpc import call

if __name__ == "__main__":
    try:
        accounts = call("list_accounts")["accounts"]
        report = {"allowed_account_count": len(accounts), "read_test": []}
        for account in accounts:
            account_id = account["account_id"]
            listing = call("search_emails", account_id=account_id, limit=1)
            row = {"domain": account["email"].rpartition("@")[2],
                   "inbox_items": listing["total_folder_items"]}
            if listing["messages"]:
                mail = call("read_email", account_id=account_id,
                            entry_id=listing["messages"][0]["entry_id"], max_chars=1)
                row.update(body_chars=mail["body_chars"], body_sha256=mail["body_sha256"],
                           unread_unchanged=mail["unread_unchanged"])
            report["read_test"].append(row)
        print(json.dumps(report, ensure_ascii=False, indent=2))
        if not accounts:
            raise SystemExit(2)
    except Exception as exc:
        print(f"CHECK_FAILED: {type(exc).__name__}: {exc}")
        raise SystemExit(1)

