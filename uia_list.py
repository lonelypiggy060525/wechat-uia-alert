"""Read WeChat's session list through UI Automation (after the accessibility gate is on).

No screen capture, no OCR, no window visibility requirement: the list stays readable while
WeChat is minimised, off-screen or behind other windows.
"""
from __future__ import annotations

import ctypes
import re
import threading
import time
from ctypes import wintypes

import uiautomation as auto

import gate

auto.SetGlobalSearchTimeout(0.4)

WECHAT_TITLE = "微信"
_GATE_RETRY = 30.0          # re-check the gate this often (WeChat restarts reset it)

_kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
_user32 = ctypes.WinDLL("user32", use_last_error=True)
PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
TH32CS_SNAPPROCESS = 0x00000002
WECHAT_EXES = ("weixin.exe", "wechat.exe")

SWP_NOSIZE = 0x0001
SWP_NOZORDER = 0x0004
SWP_NOACTIVATE = 0x0010
SWP_NOOWNERZORDER = 0x0200
SWP_SHOWWINDOW = 0x0040
HWND_BOTTOM = 1
SM_XVIRTUALSCREEN, SM_YVIRTUALSCREEN, SM_CXVIRTUALSCREEN, SM_CYVIRTUALSCREEN = 76, 77, 78, 79

_TIME_RE = re.compile(
    r"^(?:(?:昨天|今天|前天|星期[一二三四五六日天]|周[一二三四五六日天])?\s*\d{1,2}[:：]\d{2}"
    r"|昨天|今天|前天|星期[一二三四五六日天]|\d{1,2}月\d{1,2}[日号]|\d{2}/\d{1,2})$")
_UNREAD_RE = re.compile(r"\[(\d+)\+?条\]")
_FLAGS = {"已置顶", "消息免打扰"}


# ------------------------------------------------------------------ win32 helpers
class _PROCESSENTRY32W(ctypes.Structure):
    _fields_ = [
        ("dwSize", wintypes.DWORD),
        ("cntUsage", wintypes.DWORD),
        ("th32ProcessID", wintypes.DWORD),
        ("th32DefaultHeapID", ctypes.c_size_t),
        ("th32ModuleID", wintypes.DWORD),
        ("cntThreads", wintypes.DWORD),
        ("th32ParentProcessID", wintypes.DWORD),
        ("pcPriClassBase", ctypes.c_long),
        ("dwFlags", wintypes.DWORD),
        ("szExeFile", ctypes.c_wchar * 260),
    ]


def _process_names() -> list[tuple[int, str]]:
    out: list[tuple[int, str]] = []
    snap = _kernel32.CreateToolhelp32Snapshot(TH32CS_SNAPPROCESS, 0)
    if snap in (0, -1):
        return out
    try:
        entry = _PROCESSENTRY32W()
        entry.dwSize = ctypes.sizeof(_PROCESSENTRY32W)
        if not _kernel32.Process32FirstW(snap, ctypes.byref(entry)):
            return out
        while True:
            out.append((int(entry.th32ProcessID), entry.szExeFile.lower()))
            if not _kernel32.Process32NextW(snap, ctypes.byref(entry)):
                break
    finally:
        _kernel32.CloseHandle(snap)
    return out


def _pid_image(pid: int) -> str:
    handle = _kernel32.OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, False, pid)
    if not handle:
        return ""
    try:
        buf = ctypes.create_unicode_buffer(32768)
        size = wintypes.DWORD(len(buf))
        if _kernel32.QueryFullProcessImageNameW(handle, 0, buf, ctypes.byref(size)):
            return buf.value
    finally:
        _kernel32.CloseHandle(handle)
    return ""


def wechat_running() -> bool:
    try:
        return any(name in WECHAT_EXES for _pid, name in _process_names())
    except Exception:
        return False


def find_wechat_window() -> int:
    for cls in ("mmui::MainWindow", "Qt51514QWindowIcon"):
        hwnd = _user32.FindWindowW(cls, WECHAT_TITLE)
        if hwnd:
            return hwnd
    return 0


def window_rect(hwnd: int) -> tuple[int, int, int, int]:
    r = wintypes.RECT()
    _user32.GetWindowRect(hwnd, ctypes.byref(r))
    return int(r.left), int(r.top), int(r.right), int(r.bottom)


def virtual_bounds() -> tuple[int, int, int, int]:
    return (_user32.GetSystemMetrics(SM_XVIRTUALSCREEN), _user32.GetSystemMetrics(SM_YVIRTUALSCREEN),
            _user32.GetSystemMetrics(SM_CXVIRTUALSCREEN), _user32.GetSystemMetrics(SM_CYVIRTUALSCREEN))


def is_on_screen(hwnd: int) -> bool:
    l, t, r, b = window_rect(hwnd)
    vx, vy, vw, vh = virtual_bounds()
    return not (r <= vx or l >= vx + vw or b <= vy or t >= vy + vh)


def park_offscreen(hwnd: int) -> bool:
    l, t, r, b = window_rect(hwnd)
    vx, _vy, _vw, _vh = virtual_bounds()
    width = r - l
    if width <= 0:
        return False
    if r <= vx:
        return True
    return bool(_user32.SetWindowPos(hwnd, 0, vx - width - 80, t, 0, 0,
                                     SWP_NOSIZE | SWP_NOZORDER | SWP_NOACTIVATE | SWP_NOOWNERZORDER))


def bring_on_screen(hwnd: int) -> bool:
    l, t, r, b = window_rect(hwnd)
    w, h = r - l, b - t
    sw, sh = _user32.GetSystemMetrics(0), _user32.GetSystemMetrics(1)
    return bool(_user32.SetWindowPos(hwnd, 0, max(0, (sw - w) // 2), max(0, (sh - h) // 3), 0, 0,
                                     SWP_NOSIZE | SWP_NOZORDER | SWP_NOACTIVATE | SWP_NOOWNERZORDER))


def wechat_focused() -> bool:
    try:
        hwnd = _user32.GetForegroundWindow()
        if not hwnd or not is_on_screen(hwnd):
            return False
        cls = ctypes.create_unicode_buffer(128)
        _user32.GetClassNameW(hwnd, cls, 128)
        if not cls.value.startswith(("mmui::", "Qt51514QWindowIcon")):
            return False
        pid = wintypes.DWORD()
        _user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
        return _pid_image(pid.value).lower().endswith(WECHAT_EXES)
    except Exception:
        return False


# ------------------------------------------------------------------ UIA tree
def _walk(ctrl, cls: str, depth: int = 0, limit: int = 14):
    if depth > limit:
        return None
    try:
        children = ctrl.GetChildren()
    except Exception:
        return None
    for child in children:
        try:
            if (child.ClassName or "") == cls:
                return child
            hit = _walk(child, cls, depth + 1, limit)
            if hit is not None:
                return hit
        except Exception:
            continue
    return None


def _main_window():
    win = auto.WindowControl(searchDepth=1, Name=WECHAT_TITLE)
    if win.Exists(0):
        return win
    win = auto.WindowControl(searchDepth=1, ClassName="mmui::MainWindow")
    return win if win.Exists(0) else None


_table = None


def _session_table():
    """mmui::XTableView under ChatSessionList - cached, re-found when the tree is rebuilt."""
    global _table
    if _table is not None:
        try:
            _table.GetChildren()
            return _table
        except Exception:
            _table = None
    win = _main_window()
    if win is None:
        return None
    lst = _walk(win, "mmui::ChatSessionList")
    if lst is None:
        return None
    try:
        _table = lst.GetChildren()[0]
    except Exception:
        return None
    return _table


def parse_cell(text: str) -> dict:
    lines = [l.strip() for l in (text or "").split("\n") if l.strip()]
    if not lines:
        return {}
    name = lines[0]
    unread = 0
    body: list[str] = []
    for line in lines[1:]:
        m = _UNREAD_RE.search(line)
        if m:
            unread = int(m.group(1))
            rest = line[m.end():].strip(" :：")
            if rest:
                body.append(rest)          # 公众号: "[4条] 新华社: 标题" -> keep the title
            continue
        if line in _FLAGS or _TIME_RE.match(line):
            continue
        body.append(line)
    stamp = next((l for l in lines[1:] if _TIME_RE.match(l)), "")
    preview = body[-1] if body else ""
    return {"name": name, "unread": unread, "preview": preview, "time": stamp}


def read_sessions() -> list[dict]:
    table = _session_table()
    if table is None:
        return []
    out = []
    try:
        cells = table.GetChildren()
    except Exception:
        global _table
        _table = None
        return []
    for cell in cells:
        try:
            item = parse_cell(cell.Name)
            if not item:
                continue
            item["id"] = cell.AutomationId or item["name"]
            out.append(item)
        except Exception:
            continue
    return out


def _split_sender(name: str, preview: str) -> tuple[str, str]:
    m = re.match(r"^(.{1,24}?)[:：]\s*(\S.*)$", preview)
    if m and not m.group(1).isdigit():
        return m.group(1).strip(), m.group(2).strip()
    return name, preview


def _similar(full: str, preview: str) -> bool:
    """Guard against reading an older message when the newest one is an image/sticker."""
    a = (full or "").strip()
    b = (preview or "").strip().rstrip("…").strip()
    if not a or not b:
        return False
    return b in a or a in b or a.startswith(b[:12])


def read_last_text(chat_name: str, timeout: float = 2.0) -> str:
    """Open the chat through UIA and return the newest message's full text.

    Selecting a chat marks it read - same trade-off as clicking it by hand. The tree lags a
    little behind the click, so poll until a text item shows up."""
    global _table
    table = _session_table()
    if table is None:
        return ""
    cell = None
    try:
        for c in table.GetChildren():
            if (c.Name or "").split("\n")[0] == chat_name:
                cell = c
                break
    except Exception:
        _table = None
        return ""
    if cell is None:
        return ""
    try:
        cell.Click()
    except Exception:
        try:
            cell.GetSelectionItemPattern().Select()
        except Exception:
            return ""

    deadline = time.time() + timeout
    while time.time() < deadline:
        time.sleep(0.25)
        win = _main_window()
        if win is None:
            continue
        view = _walk(win, "mmui::MessageView")
        if view is None:
            continue
        rv = _walk(view, "mmui::RecyclerListView")
        if rv is None:
            continue
        try:
            items = rv.GetChildren()
        except Exception:
            continue
        for item in reversed(items):
            if not (item.ClassName or "").endswith("ChatTextItemView"):
                continue
            text = (item.Name or "").strip()
            if text:
                return text
    return ""


class ChatListWatcher(threading.Thread):
    """Same interface as the screen-reading watcher, so the UI code can be shared."""

    def __init__(self, on_message, on_status, interval: float = 0.8,
                 auto_restore=None, stealth=None, full_read=None) -> None:
        super().__init__(name="uia-watcher", daemon=True)
        self.on_message = on_message
        self.on_status = on_status
        self.interval = max(0.3, float(interval))
        self._stop = threading.Event()
        self._prev: dict[str, tuple[int, str]] = {}
        self._seeded = False
        self._status = ""
        self._last_gate = 0.0
        self.auto_restore = auto_restore or (lambda: False)
        self.stealth = stealth or (lambda: False)
        self.full_read = full_read or (lambda: False)

    def _set_status(self, text: str) -> None:
        if text != self._status:
            self._status = text
            try:
                self.on_status(text)
            except Exception:
                pass

    def stop(self) -> None:
        self._stop.set()

    def run(self) -> None:
        while not self._stop.is_set():
            if not wechat_running():
                self._set_status("等待微信登录")
                time.sleep(2)
                continue
            cls, ready, _hwnd = gate.gate_state()
            if not ready:
                if time.time() - self._last_gate > _GATE_RETRY:
                    self._last_gate = time.time()
                    self._set_status("正在打开微信控件树…")
                    gate.ensure_gate()
                    cls, ready, _hwnd = gate.gate_state()
                if not ready:
                    self._set_status("微信控件树未打开")
                    time.sleep(2)
                    continue
            sessions = read_sessions()
            if not sessions:
                self._set_status("等待会话列表")
                time.sleep(1.5)
                continue

            for s in sessions:
                key = s["id"]
                prev = self._prev.get(key)
                if prev is None:
                    self._prev[key] = (s["unread"], s["preview"])
                    continue
                old_unread, old_preview = prev
                # Only a rising unread counter proves an incoming message. WeChat keeps a chat
                # at 0 unread while you are talking in it, so "preview changed" would also fire
                # for every message you send yourself (typed here or on the phone).
                new_msg = s["unread"] > old_unread
                self._prev[key] = (s["unread"], s["preview"])
                if new_msg and self._seeded:
                    sender, content = _split_sender(s["name"], s["preview"])
                    full = False
                    if self.full_read() and (content.endswith("…") or len(content) >= 40):
                        whole = read_last_text(s["name"])
                        if whole and _similar(whole, content):
                            content, full = whole, True
                    self.on_message({"chat": s["name"], "sender": sender, "content": content,
                                     "source": "uia", "unread": s["unread"], "full": full})
            self._seeded = True
            unread_total = sum(1 for s in sessions if s["unread"] > 0)
            self._set_status(f"运行中 · {len(sessions)} 个会话" + (f" · {unread_total} 个未读" if unread_total else ""))
            time.sleep(self.interval)


if __name__ == "__main__":
    def on_msg(m):
        print("MSG", m, flush=True)

    w = ChatListWatcher(on_msg, lambda s: print("STATUS", s, flush=True), 1.0)
    w.start()
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        w.stop()
