"""Turn on WeChat 4.x's Qt accessibility gate (one byte inside Weixin.dll).

The tree is what makes everything else possible: without it UIA only sees an empty Qt shell.
Ported from wechatauto-replica's tools/wake_uia.py (Apache-2.0); the RVA scan and cache are
theirs, only the "make sure it is on" wrapper is ours.
"""
from __future__ import annotations

import ctypes

import wake_uia as wu


def gate_state() -> tuple[str | None, bool, int | None]:
    """(root class, materialised?, hwnd) for the first WeChat window."""
    wins = wu.wechat_windows()
    if not wins:
        return None, False, None
    _area, hwnd, _pid, _base, _dll, _title = wins[0]
    cls, ready = wu.tree_state(hwnd, timeout=0.3)
    return cls, ready, hwnd


def ensure_gate(verbose: bool = False) -> bool:
    """Write the gate byte if it is still 0. Cheap to call repeatedly."""
    wins = wu.wechat_windows()
    if not wins:
        return False
    _area, hwnd, pid, base, dll, _title = wins[0]
    cls, ready = wu.tree_state(hwnd, timeout=0.3)
    if ready:
        return True

    rvas = wu.candidates_for(dll, wu.GATE_CACHE_FILE)
    if not rvas:
        return False
    k32 = ctypes.windll.kernel32
    handle = k32.OpenProcess(wu.PROCESS_ACCESS, False, pid)
    if not handle:
        return False
    try:
        for rva in rvas:
            address = base + rva
            original = wu.read_byte(handle, address)
            if original is None:
                continue
            if original != 1 and not wu.write_byte(handle, address, 1):
                continue
            _cn, now = wu.tree_state(hwnd, timeout=2.0)
            if now:
                cache = wu.load_cache(wu.GATE_CACHE_FILE)
                cache.setdefault(wu.dll_identity(dll), {})["verified"] = int(rva)
                wu.save_cache(wu.GATE_CACHE_FILE, cache)
                return True
            if original != 1:
                wu.write_byte(handle, address, original)
    finally:
        k32.CloseHandle(handle)
    return False


if __name__ == "__main__":
    cls, ready, hwnd = gate_state()
    print("root:", cls, "| materialised:", ready, "| hwnd:", hwnd)
    print("ensure_gate ->", ensure_gate())
    cls, ready, _ = gate_state()
    print("after:", cls, ready)
