"""Configure official tunnel-client. The key stays DPAPI-encrypted on Windows."""
import argparse
import getpass
import json
import os
import re
import subprocess
import sys
from pathlib import Path


def main():
    if sys.platform != "win32":
        raise SystemExit("This setup requires Windows")
    import win32crypt
    import win32com.client
    parser = argparse.ArgumentParser()
    parser.add_argument("--tunnel-id")
    parser.add_argument("--client", required=True, help="Official tunnel-client.exe path")
    parser.add_argument("--startup", action="store_true")
    args = parser.parse_args()
    tunnel_id = args.tunnel_id or input("Tunnel ID: ").strip()
    if not re.fullmatch(r"tunnel_[A-Za-z0-9_-]{10,128}", tunnel_id):
        raise SystemExit("Invalid tunnel_id")
    client = Path(args.client).resolve()
    if not client.is_file() or client.name.casefold() != "tunnel-client.exe":
        raise SystemExit("Use the official Windows tunnel-client.exe")
    root = Path(__file__).resolve().parent
    python = root / ".venv" / "Scripts" / "python.exe"
    pythonw = python.with_name("pythonw.exe")
    if not python.is_file() or not pythonw.is_file():
        raise SystemExit("Run Setup.cmd first")
    result = subprocess.run([str(python), str(root / "check.py")], capture_output=True)
    if result.returncode:
        raise SystemExit("Local Outlook check failed. Resolve it before tunnel setup.")
    key = getpass.getpass("OpenAI runtime key (local entry only): ")
    if not key.strip():
        raise SystemExit("No key entered")
    directory = Path(os.environ["LOCALAPPDATA"]) / "OutlookReadOnlyBridge"
    directory.mkdir(parents=True, exist_ok=True)
    profile = "outlook-school"
    environment = os.environ.copy()
    environment["CONTROL_PLANE_API_KEY"] = key
    # Forward slashes preserve Windows paths in the client's command parser.
    # Keep Windows quoting for subprocess/shortcut argument lists elsewhere.
    command = subprocess.list2cmdline([python.as_posix(), (root / "server.py").as_posix()])
    subprocess.run([str(client), "init", "--sample", "sample_mcp_stdio_local", "--profile", profile,
                    "--tunnel-id", tunnel_id, "--mcp-command", command], env=environment, check=True)
    subprocess.run([str(client), "doctor", "--profile", profile, "--explain"], env=environment, check=True)
    encrypted = win32crypt.CryptProtectData(key.encode("utf-8"), "Outlook read-only tunnel", None, None, None, 0)
    (directory / "runtime-key.dpapi").write_bytes(encrypted)
    settings = {"client": str(client), "profile": profile, "tunnel_id": tunnel_id,
                "package_root": str(root)}
    (directory / "settings.json").write_text(json.dumps(settings, indent=2), encoding="utf-8")
    environment.pop("CONTROL_PLANE_API_KEY", None)
    key = ""
    if args.startup:
        startup = Path(os.environ["APPDATA"]) / "Microsoft/Windows/Start Menu/Programs/Startup"
        shortcut = win32com.client.Dispatch("WScript.Shell").CreateShortcut(str(startup / "School Outlook Read-only Bridge.lnk"))
        shortcut.TargetPath = str(pythonw)
        shortcut.Arguments = subprocess.list2cmdline([str(root / "run_tunnel.py")])
        shortcut.WorkingDirectory = str(root)
        shortcut.WindowStyle = 7
        shortcut.Save()
    subprocess.Popen([str(pythonw), str(root / "run_tunnel.py")], creationflags=subprocess.CREATE_NO_WINDOW)
    print("Local tunnel configured and started. Add this tunnel in ChatGPT Plugins to finish.")
    print("Remote ChatGPT reading is not yet verified.")


if __name__ == "__main__":
    main()

