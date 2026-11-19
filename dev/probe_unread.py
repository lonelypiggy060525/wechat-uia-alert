"""Create one unread (右键→标为未读) to learn what the unread state looks like in the UIA cell."""
import ctypes
import time
import uiautomation as auto

auto.SetGlobalSearchTimeout(0.5)
user32 = ctypes.windll.user32

win = auto.WindowControl(searchDepth=1, ClassName="mmui::MainWindow")
hwnd = win.NativeWindowHandle
user32.SetWindowPos(hwnd, 0, 473, 146, 0, 0, 0x0001 | 0x0004 | 0x0010)
time.sleep(0.5)


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


lst = find(win, "mmui::ChatSessionList")
table = lst.GetChildren()[0]
cell = table.GetChildren()[0]
print("before:", repr(cell.Name))
cell.RightClick()
time.sleep(1.0)

# the menu may be a popup window or a child of the main window
target = None
for root in (auto.GetRootControl(), win):
    try:
        for c in root.GetChildren():
            text = (c.Name or "")
            print("top:", c.ClassName, repr(text[:30]))
            if "标为未读" in text or "未读" in text:
                target = c
    except Exception:
        pass


def find_text(ctrl, needle, depth=0, limit=6):
    if depth > limit:
        return None
    try:
        children = ctrl.GetChildren()
    except Exception:
        return None
    for c in children:
        try:
            if needle in (c.Name or ""):
                return c
            hit = find_text(c, needle, depth + 1, limit)
            if hit is not None:
                return hit
        except Exception:
            continue
    return None


item = find_text(win, "标为未读") or find_text(auto.GetRootControl(), "标为未读")
print("menu item:", item)
if item is not None:
    item.Click()
    time.sleep(0.8)

lst = find(win, "mmui::ChatSessionList")
table = lst.GetChildren()[0]
for c in table.GetChildren()[:3]:
    print("after:", repr(c.Name))
