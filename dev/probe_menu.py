"""Right-click a session cell and look for the '标为未读' menu item (to create an unread state)."""
import time
import uiautomation as auto

auto.SetGlobalSearchTimeout(0.5)
win = auto.WindowControl(searchDepth=1, ClassName="mmui::MainWindow")


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
cell = lst.GetChildren()[0].GetChildren()[0]
print("cell:", cell.Name.split("\n")[0])
cell.RightClick()
time.sleep(0.8)

print("--- top-level windows ---")
for w in auto.GetRootControl().GetChildren():
    try:
        print(f"[{w.ClassName}] {w.Name!r} type={w.ControlTypeName}")
        for c in w.GetChildren()[:12]:
            print(f"    [{c.ClassName}] {c.Name!r} {c.ControlTypeName}")
    except Exception:
        pass

auto.SendKeys("{ESC}")
