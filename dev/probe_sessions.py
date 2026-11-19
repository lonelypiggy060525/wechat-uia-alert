"""Find the session-list subtree in WeChat's materialised UIA tree."""
import sys
import uiautomation as auto

auto.SetGlobalSearchTimeout(0.5)
win = auto.WindowControl(searchDepth=1, ClassName="mmui::MainWindow")
print("window:", win.Name, win.ClassName)

found = []


def walk(ctrl, depth=0, limit=12):
    if depth > limit:
        return
    try:
        children = ctrl.GetChildren()
    except Exception:
        return
    for c in children:
        try:
            cls = c.ClassName or ""
            name = c.Name or ""
            if "Session" in cls or "session" in cls.lower() or "会话" in name:
                r = c.BoundingRectangle
                found.append((depth, cls, name, c.AutomationId,
                              (r.left, r.top, r.right - r.left, r.bottom - r.top)))
            walk(c, depth + 1, limit)
        except Exception:
            continue


walk(win)
print(f"session-ish nodes: {len(found)}")
for depth, cls, name, aid, rect in found[:20]:
    print("  " * min(depth, 8) + f"[{cls}] name={name!r} aid={aid!r} rect={rect}")
