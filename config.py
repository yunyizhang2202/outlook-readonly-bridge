"""Explicit local allowlist; an absent or empty configuration grants no access."""
import json
from pathlib import Path
from outlook_core import BridgeError


def load_allowlist(path=None):
    path = Path(path) if path is not None else Path(__file__).with_name("config.local.json")
    try:
        value = json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, ValueError):
        raise BridgeError("Create a valid config.local.json from config.example.json first") from None
    if not isinstance(value, dict) or set(value) - {"allowed_domains", "allowed_addresses"}:
        raise BridgeError("Configuration supports only allowed_domains and allowed_addresses")
    domains, addresses = value.get("allowed_domains", []), value.get("allowed_addresses", [])
    for values in (domains, addresses):
        if not isinstance(values, list) or any(not isinstance(x, str) or not x.strip() for x in values):
            raise BridgeError("Allowlist fields must be lists of nonempty strings")
    domains = tuple(x.strip().casefold() for x in domains)
    addresses = tuple(x.strip().casefold() for x in addresses)
    if any("@" in x or "." not in x or any(c.isspace() for c in x) for x in domains):
        raise BridgeError("Use exact email domains without @ or wildcards")
    if any(x.count("@") != 1 or not all(x.split("@")) or any(c.isspace() for c in x) for x in addresses):
        raise BridgeError("Use complete email addresses in allowed_addresses")
    if any("*" in x for x in domains + addresses):
        raise BridgeError("Wildcard allowlists are not supported")
    if not domains and not addresses:
        raise BridgeError("Allowlist is empty; authorize at least one exact address or domain locally")
    return domains, addresses
