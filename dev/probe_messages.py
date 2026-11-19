"""Select a chat via UIA and dump the conversation pane, looking for the message list."""
import time
import uiautomation as auto

auto.SetGlobalSearchTimeout(0.5)
win = auto.WindowControl(searchDepth=1, ClassName="mmui::MainWindow")


def walk_find(ctrl, pred, depth=0, limit=14):
    if depth > limit:
        return None
    try:
        children = ctrl.GetChildren()
    except Exception:
        return None
    for c in children:
        try:
            if pred(c):
                return c
            hit = walk_find(c, pred, depth + 1, limit)
            if hit is not None:
                return hit
        except Exception:
            continue
    return None


lst = walk_find(win, lambda c: (c.ClassName or "") == "mmui::ChatSessionList")
table = lst.GetChildren()[0]
cells = table.GetChildren()
target = next(c for c in cells if (c.Name or "").startswith("文件传输助手"))
print("selecting:", target.Name.split("\n")[0])
target.Click()
time.sleep(1.0)

print("--- classes in the right pane ---")
seen = {}


def walk(ctrl, depth=0, limit=10):
    if depth > limit:
        return
    try:
        children = ctrl.GetChildren()
    except Exception:
        return
    for c in children:
        try:
            cls = c.ClassName or ""
            if "Chat" in cls or "Message" in cls or "Bubble" in cls:
                seen.setdefault(cls, 0)
                seen[cls] += 1
                if seen[cls] <= 2:
                    print(f"[{cls}] name={c.Name[:50]!r} rect={c.BoundingRectangle}")
            walk(c, depth + 1, limit)
        except Exception:
            continue


walk(win)
print("--- class counts ---")
for k, v in sorted(seen.items()):
    print(f"  {k}: {v}")
