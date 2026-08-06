import sys, os
sys.path.insert(0, os.path.dirname(__file__))
from excalidraw_lib import Diagram, COLORS

OUT = os.path.join(os.path.dirname(__file__), "..", "10_Risk_Portfolio_Platform.excalidraw")

MARGIN = 40
CANVAS_W = 1200
BAND_X = MARGIN
BAND_W = CANVAS_W - 2 * MARGIN
CENTER_X = BAND_X + BAND_W / 2
pipe_w = 520
pipe_x = CENTER_X - pipe_w / 2

d = Diagram("10 — Risk & Portfolio Management")

y = 90
d.labeled_box(pipe_x, y, pipe_w, 55, "Trade Recommendation", "from page 09 — Decision Intelligence",
              color="cyan", title_size=15, subtitle_size=11)
y += 55 + 35
d.arrow(CENTER_X, y - 29, CENTER_X, y - 6, color=COLORS["cyan"]["stroke"])

stages = [
    ("Portfolio Risk", "Current aggregate risk vs. limits", "red"),
    ("Exposure", "Per-symbol & aggregate exposure caps", "red"),
    ("Position Sizing", "Vol-adjusted base size", "red"),
    ("Correlation", "Cross-position correlation check", "red"),
    ("Kelly", "Fractional Kelly sizing overlay\n(half/quarter Kelly default)", "red"),
    ("Drawdown Guard", "Reduces/blocks new size as\nrealized drawdown deepens", "red"),
    ("Kill Switch", "Hard synchronous stop --\nnot an async event, see below", "red"),
]
bottom = d.pipeline(pipe_x, pipe_w, y, stages, item_h=58, gap=32, title_size=14, subtitle_size=10)

out_y = bottom + 45
d.arrow(CENTER_X, bottom + 6, CENTER_X, out_y - 6, color=COLORS["red"]["stroke"])
d.labeled_box(pipe_x, out_y, pipe_w, 55, "Approved Trade", "-> page 11, Execution Platform",
              color="green", title_size=15, subtitle_size=11)

# Rejected branch
rej_x = pipe_x - 260
d.arrow(pipe_x - 4, bottom + 20, rej_x + 220, bottom + 20, color=COLORS["red"]["stroke"], stroke_width=1)
d.labeled_box(rej_x, bottom - 10, 220, 60, "Rejected", "Logged with reason,\nno trade sent", color="gray", title_size=13, subtitle_size=10)

# Side panel: kill switch note
note_x = pipe_x + pipe_w + 40
note_w = BAND_X + BAND_W - note_x
note_y = 90
note_h = out_y + 55 - note_y
if note_w > 150:
    d.rect(note_x, note_y, note_w, note_h, stroke=COLORS["red"]["stroke"], bg=COLORS["red"]["bg"])
    d.text(note_x + 12, note_y + 10, note_w - 24, "Kill Switch", font_size=15, color=COLORS["red"]["stroke"], align="left")
    d.text(note_x + 12, note_y + 40, note_w - 24,
           "Synchronous, in-process gate\n-- not a subscriber to a\n'kill' event.\n\n"
           "Trips on:\n- Max daily loss breached\n- Max drawdown breached\n- Anomalous fill/slippage\n  pattern\n- Manual operator trigger\n- News Guard blackout\n  (see news-guard skill)\n\n"
           "When tripped: blocks ALL\nnew Approved Trades\nplatform-wide until manually\ncleared. Does not close\nexisting positions --\nthat is a separate,\nexplicit operator action.",
           font_size=11, color="#495057", align="left")

d.save(OUT)
