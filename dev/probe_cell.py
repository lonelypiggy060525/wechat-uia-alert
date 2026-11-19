"""Inspect every UIA property of a session cell (looking for the unread badge)."""
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
table = lst.GetChildren()[0]
cells = table.GetChildren()
print("cells:", len(cells))
for cell in cells[:4]:
    print("=" * 60)
    print("Name      :", repr(cell.Name))
    print("Class     :", cell.ClassName, "| Type:", cell.ControlTypeName)
    print("AutomationId:", repr(cell.AutomationId))
    for attr in ("ItemStatus", "HelpText", "FullDescription", "AccessKey", "AcceleratorKey",
                 "LocalizedControlType", "IsOffscreen", "IsEnabled", "IsSelected"):
        try:
            print(f"{attr:14s}:", repr(getattr(cell, attr)))
        except Exception as exc:
            print(f"{attr:14s}: <{exc}>")
    # raw view children (control view may hide the badge)
    try:
        raw = cell.GetChildren()
        print("GetChildren  :", len(raw), [c.ClassName for c in raw])
    except Exception as exc:
        print("GetChildren  : err", exc)
