"""Attach to an existing classic Outlook COM instance (never starts a new one).

Only MK_E_UNAVAILABLE is retried. Status codes deliberately omit mailbox names,
local paths, Windows account names, and messages returned by COM exceptions.
"""
import time
from outlook_core import BridgeError

MK_E_UNAVAILABLE = 0x800401E3


def _hresult(exc):
    value = getattr(exc, "hresult", None)
    if not isinstance(value, int) and getattr(exc, "args", ()):
        value = exc.args[0]
    return value & 0xFFFFFFFF if isinstance(value, int) else None


def attach_active_outlook(get_active, attempts=4, delay=0.5, sleep=time.sleep):
    """Resolve Outlook from ROT; never Dispatch/create Outlook on failure."""
    if not isinstance(attempts, int) or not 1 <= attempts <= 10:
        raise ValueError("attempts out of range")
    for attempt in range(1, attempts + 1):
        try:
            return get_active("Outlook.Application")
        except Exception as exc:
            code = _hresult(exc)
            if code != MK_E_UNAVAILABLE:
                label = "unknown" if code is None else f"0x{code:08X}"
                raise BridgeError("COM_ATTACH_FAILED: HRESULT=" + label +
                                  "; run local Outlook diagnostics") from None
            if attempt < attempts:
                sleep(delay)
    raise BridgeError(
        "COM_ATTACH_FAILED: HRESULT=0x800401E3 (MK_E_UNAVAILABLE); "
        "Outlook may be running but not visible in this worker ROT. "
        "Compare user/session/elevation, activate Outlook then switch focus "
        "to another app and retry. Run Run-Outlook-Diagnostics.cmd locally."
    )
