"""Dump the WeChat UIA tree (after the accessibility gate is on)."""
import sys
import uiautomation as auto

auto.SetGlobalSearchTimeout(0.5)
win = auto.WindowControl(searchDepth=1, Name="微信")
if not win.Exists(0, 0):
    # fall back to class name
    win = auto.WindowControl(searchDepth=1, ClassName="mmui::MainWindow")
print("window:", win.Name, "| class:", win.ClassName, "| rect:", win.BoundingRectangle)


def walk(ctrl, depth=0, limit=6):
    if depth > limit:
        return
    try:
        children = ctrl.GetChildren()
    except Exception:
        return
    for c in children:
        try:
            name = c.Name or ""
            cls = c.ClassName or ""
            aid = c.AutomationId or ""
            r = c.BoundingRectangle
            if name or aid:
                print("  " * depth + f"[{cls}] name={name!r} aid={aid!r} "
                      f"rect=({r.left},{r.top},{r.right - r.left}x{r.bottom - r.top})")
            walk(c, depth + 1, limit)
        except Exception:
            continue


walk(win, 0, 5)
