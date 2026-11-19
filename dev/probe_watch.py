"""Watch the UIA session list and print the exact cell text when something changes."""
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


def snapshot():
    lst = find(win, "mmui::ChatSessionList")
    if lst is None:
        return {}
    table = lst.GetChildren()[0]
    out = {}
    for cell in table.GetChildren():
        aid = cell.AutomationId or cell.Name.split("\n")[0]
        out[aid] = cell.Name
    return out


base = snapshot()
print(f"baseline: {len(base)} sessions", flush=True)
deadline = time.time() + 60
seen = dict(base)
while time.time() < deadline:
    time.sleep(1.5)
    cur = snapshot()
    for key, text in cur.items():
        if seen.get(key) != text:
            print("CHANGED", repr(text), flush=True)
    seen = cur
print("done", flush=True)
