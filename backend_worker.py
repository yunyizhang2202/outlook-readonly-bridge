"""Short-lived STA COM worker. Receives one JSON request on stdin."""
import json
import sys
from outlook_core import OutlookReader, BridgeError

sys.stdin.reconfigure(encoding="utf-8")
sys.stdout.reconfigure(encoding="utf-8")

OPERATIONS = {"list_accounts", "list_folders", "search_emails", "read_email", "read_attachment"}


def run():
    if sys.platform != "win32":
        raise BridgeError("Windows classic Outlook is required")
    import pythoncom
    import win32com.client
    request = json.loads(sys.stdin.read())
    if request.get("operation") not in OPERATIONS:
        raise BridgeError("Unsupported read-only operation")
    pythoncom.CoInitialize()
    app = namespace = reader = None
    try:
        try:
            app = win32com.client.GetActiveObject("Outlook.Application")
        except Exception:
            raise BridgeError("Open classic Outlook in the logged-in Windows session first") from None
        namespace = app.GetNamespace("MAPI")
        from config import load_allowlist
        domains, addresses = load_allowlist()
        reader = OutlookReader(namespace, allowed_domains=domains, allowed_addresses=addresses)
        return getattr(reader, request["operation"])(**request.get("arguments", {}))
    finally:
        reader = namespace = app = None
        pythoncom.CoUninitialize()


if __name__ == "__main__":
    try:
        result = {"ok": True, "result": run()}
    except BridgeError as exc:
        result = {"ok": False, "error": str(exc)}
    except Exception as exc:
        # COM errors can include private folder/account names: do not return their text.
        result = {"ok": False, "error": f"Local Outlook operation failed ({type(exc).__name__}); check local access and security prompts"}
    sys.stdout.write(json.dumps(result, ensure_ascii=False))

