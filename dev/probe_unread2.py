"""Real right-click on a session cell, find the popup menu, click 标为未读."""
import ctypes
import time
import uiautomation as auto

auto.SetGlobalSearchTimeout(0.5)
user32 = ctypes.windll.user32

win = auto.WindowControl(searchDepth=1, ClassName="mmui::MainWindow")
hwnd = win.NativeWindowHandle
user32.SetWindowPos(hwnd, 0, 473, 146, 0, 0, 0x0001 | 0x0004 | 0x0010)
time.sleep(0.6)


def find(ctrl, cls, depth=0, limit=14):
    if depth > limit:
        return None
    try:
        children = ctrl.GetChildren()
    except Exception:
        return None
    for c in children:
        try:
            if (c.ClassName or "") == cls:
                return c
            hit = find(c, cls, depth + 1, limit)
            if hit is not None:
                return hit
        except Exception:
            continue
    return None


cell = find(win, "mmui::ChatSessionList").GetChildren()[0].GetChildren()[1]
r = cell.BoundingRectangle
x, y = (r.left + 120, r.top + 30)
print("cell:", cell.Name.split("\n")[0], "click at", (x, y))
user32.SetCursorPos(x, y)
time.sleep(0.2)
user32.mouse_event(0x0008, 0, 0, 0, 0)      # RIGHTDOWN
time.sleep(0.08)
user32.mouse_event(0x0010, 0, 0, 0, 0)      # RIGHTUP
time.sleep(1.0)

print("--- windows after right-click ---")
for w in auto.GetRootControl().GetChildren():
    try:
        print(f"[{w.ClassName}] {w.Name!r} {w.ControlTypeName} {w.BoundingRectangle}")
        for c in w.GetChildren()[:10]:
            print(f"    [{c.ClassName}] {c.Name!r}")
    except Exception:
        pass
