"""Walk to mmui::ChatSessionList, then dump its rows."""
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
print("list:", lst, lst.BoundingRectangle if lst else None)


def dump(ctrl, depth=0, limit=4):
    if depth > limit:
        return
    try:
        children = ctrl.GetChildren()
    except Exception as exc:
        print("  " * depth + f"<err {exc}>")
        return
    for c in children:
        try:
            r = c.BoundingRectangle
            print("  " * depth + f"[{c.ClassName}] name={c.Name!r} "
                  f"rect=({r.left},{r.top},{r.right - r.left}x{r.bottom - r.top})")
            dump(c, depth + 1, limit)
        except Exception as exc:
            print("  " * depth + f"<err {exc}>")


if lst:
    dump(lst, 0, 4)
