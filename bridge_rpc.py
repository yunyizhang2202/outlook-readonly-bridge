import json
import subprocess
import sys
from pathlib import Path
from outlook_core import BridgeError


def call(operation, **arguments):
    payload = json.dumps({"operation": operation, "arguments": arguments}, ensure_ascii=False)
    try:
        completed = subprocess.run(
            [sys.executable, str(Path(__file__).with_name("backend_worker.py"))],
            input=payload, capture_output=True, encoding="utf-8", timeout=60,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
            env=None,
        )
    except subprocess.TimeoutExpired:
        raise BridgeError("Outlook timed out; check its local security/sign-in prompts") from None
    try:
        output = json.loads(completed.stdout)
    except (ValueError, TypeError):
        raise BridgeError("Local Outlook worker did not return valid JSON") from None
    if completed.returncode or not output.get("ok"):
        raise BridgeError(output.get("error", "Local worker failed"))
    return output["result"]

