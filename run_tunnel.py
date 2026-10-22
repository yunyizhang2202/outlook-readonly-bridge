"""Quiet per-user tunnel runner; no email or token logging, no popups."""
import json
import os
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path


def main():
    if sys.platform != "win32":
        return
    import win32crypt
    import win32event
    import win32api
    mutex = win32event.CreateMutex(None, False, "Local\\SchoolOutlookReadOnlyBridgeRunner")
    if win32api.GetLastError() == 183:
        return
    directory = Path(os.environ["LOCALAPPDATA"]) / "OutlookReadOnlyBridge"
    status_path = directory / "status.json"
    try:
        settings = json.loads((directory / "settings.json").read_text(encoding="utf-8"))
        key = win32crypt.CryptUnprotectData((directory / "runtime-key.dpapi").read_bytes(), None, None, None, 0)[1]
        environment = os.environ.copy()
        environment["CONTROL_PLANE_API_KEY"] = key.decode("utf-8")
        for attempt in range(1, 6):
            child = subprocess.Popen([settings["client"], "run", "--profile", settings["profile"]],
                                     env=environment, stdin=subprocess.DEVNULL,
                                     stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                                     creationflags=subprocess.CREATE_NO_WINDOW)
            status_path.write_text(json.dumps({"state": "process_started_not_remote_verified",
                                               "runner_pid": os.getpid(), "client_pid": child.pid,
                                               "attempt": attempt,
                                               "time_utc": datetime.now(timezone.utc).isoformat()}), encoding="utf-8")
            exit_code = child.wait()
            status_path.write_text(json.dumps({"state": "client_exited", "exit_code": exit_code,
                                               "attempt": attempt}), encoding="utf-8")
            if exit_code == 0:
                return
            time.sleep(10)
        status_path.write_text(json.dumps({"state": "stopped_after_repeated_failures"}), encoding="utf-8")
    except Exception as exc:
        # Store only an error type. Exceptions may contain private paths or tokens.
        if directory.is_dir():
            status_path.write_text(json.dumps({"state": "error", "error_type": type(exc).__name__}), encoding="utf-8")
    finally:
        win32api.CloseHandle(mutex)


if __name__ == "__main__":
    main()

