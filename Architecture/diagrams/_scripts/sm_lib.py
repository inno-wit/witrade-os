"""
Shared helpers for state-machine and container-model Excalidraw diagrams.
Imports the existing Architecture/_scripts/excalidraw_lib.py rather than
duplicating it, so the source-page generator scripts remain untouched.
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "_scripts"))
from excalidraw_lib import Diagram, COLORS  # noqa: F401

# Maps a semantic "kind" onto one of excalidraw_lib's existing named colors,
# so no new palette needs to be introduced.
KIND_COLOR = {
    "start":    "green",   # entry point into the machine
    "normal":   "blue",    # ordinary operating state
    "warn":     "orange",  # degraded / unusual but not halted
    "gate":     "purple",  # requires a human action to leave
    "halt":     "red",     # halted / failed / emergency
    "terminal": "gray",    # [*] — machine exits here
    "info":     "cyan",    # informational / observational state
}


def state_box(d, x, y, w, h, name, kind="normal", note=None,
              title_size=13, subtitle_size=9):
    """Draws one state as a labeled box. Terminal states get a dashed border."""
    color = KIND_COLOR[kind]
    c = COLORS[color]
    dashed = (kind == "terminal")
    d.rect(x, y, w, h, stroke=c["stroke"], bg=c["bg"], dashed=dashed,
           stroke_width=3 if kind == "start" else 2)
    if note:
        d.text(x + 6, y + 8, w - 12, name, font_size=title_size, align="center")
        d.text(x + 6, y + h - subtitle_size - 10, w - 12, note,
               font_size=subtitle_size, color="#868e96", align="center")
    else:
        d.text(x + 6, y + h / 2 - title_size * 0.7, w - 12, name,
               font_size=title_size, align="center")
    return (x, y, w, h)


def edge(box, side, frac=0.5):
    """Returns a point on the given side of a (x,y,w,h) box. frac slides along the side."""
    x, y, w, h = box
    if side == "top":
        return (x + w * frac, y)
    if side == "bottom":
        return (x + w * frac, y + h)
    if side == "left":
        return (x, y + h * frac)
    if side == "right":
        return (x + w, y + h * frac)
    raise ValueError(side)


def transition(d, p1, p2, label=None, color="#495057", dashed=False,
               points=None, label_dx=0, label_dy=-10, font_size=9):
    """Draws an arrow between two points (tuples), with an optional midpoint label."""
    x1, y1 = p1
    x2, y2 = p2
    d.arrow(x1, y1, x2, y2, color=color, dashed=dashed, points=points)
    if label:
        if points:
            mx = x1 + points[len(points) // 2][0]
            my = y1 + points[len(points) // 2][1]
        else:
            mx, my = (x1 + x2) / 2, (y1 + y2) / 2
        d.text(mx - 75 + label_dx, my + label_dy, 150, label,
               font_size=font_size, color=color, align="center")


def legend(d, x, y, items, title="Legend"):
    """items: list of (kind, description)."""
    d.text(x, y, 340, title, font_size=13, color="#1e1e1e", align="left")
    yy = y + 24
    for kind, desc in items:
        c = COLORS[KIND_COLOR[kind]]
        d.rect(x, yy, 20, 16, stroke=c["stroke"], bg=c["bg"], rounded=False)
        d.text(x + 28, yy - 3, 360, desc, font_size=11, color="#343a40", align="left")
        yy += 24
    return yy


def caption(d, x, y, w, text):
    d.text(x, y, w, text, font_size=12, color="#868e96", align="left")


def section_label(d, x, y, w, text, color="gray"):
    c = COLORS[color]
    d.text(x, y, w, text, font_size=14, color=c["stroke"], align="left")
