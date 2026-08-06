import sys, os
sys.path.insert(0, os.path.dirname(__file__))
from excalidraw_lib import Diagram, COLORS

OUT = os.path.join(os.path.dirname(__file__), "..", "11_Execution_Platform.excalidraw")

MARGIN = 40
CANVAS_W = 1200
BAND_X = MARGIN
BAND_W = CANVAS_W - 2 * MARGIN
CENTER_X = BAND_X + BAND_W / 2
pipe_w = 520
pipe_x = CENTER_X - pipe_w / 2

d = Diagram("11 — Execution Platform")

y = 90
d.labeled_box(pipe_x, y, pipe_w, 55, "Approved Trade", "from page 10 — Risk & Portfolio Management",
              color="red", title_size=15, subtitle_size=11)
y += 55 + 35
d.arrow(CENTER_X, y - 29, CENTER_X, y - 6, color=COLORS["red"]["stroke"])

stages = [
    ("Broker Adapter", "Broker-agnostic interface\n(MT5 first implementation)", "green"),
    ("MT5", "Order send via Windows VPS\nbridge process", "green"),
    ("Order Verification", "Pre-send checks: price still\nvalid, size within limits", "green"),
    ("Fill / Slippage Analysis", "Actual vs. expected fill,\nfeeds Risk Kill Switch", "green"),
    ("Trade Confirmation", "Idempotent confirmation,\nreconciled against broker truth", "green"),
    ("Journal", "Permanent record --\nsee page 13 / Monitoring", "gray"),
]
bottom = d.pipeline(pipe_x, pipe_w, y, stages, item_h=58, gap=34, title_size=14, subtitle_size=10)

# Feedback arrows to Risk (slippage) and Continuous Learning (journal)
note_x = pipe_x + pipe_w + 40
note_w = BAND_X + BAND_W - note_x
note_y = 90
note_h = bottom - note_y
if note_w > 150:
    d.rect(note_x, note_y, note_w, note_h, stroke=COLORS["gray"]["stroke"], bg=COLORS["gray"]["bg"])
    d.text(note_x + 12, note_y + 10, note_w - 24, "Idempotency & Retry",
           font_size=15, color=COLORS["gray"]["stroke"], align="left")
    d.text(note_x + 12, note_y + 40, note_w - 24,
           "Every order carries a\nclient-generated idempotent\norder ID.\n\n"
           "Retry-safe: a retried send\nwith the same ID never\ndouble-submits -- the broker\nadapter checks order status\nfirst.\n\n"
           "Partial fills are an explicit\nstate, not an error:\nremaining size is either\nre-queued or cancelled per\nthe original trade's\ntime-in-force.\n\n"
           "Slippage beyond tolerance\nauto-flags for operator\nreview -- does not\nauto-cancel or auto-retry.",
           font_size=11, color="#495057", align="left")

out_y = bottom + 45
d.arrow(CENTER_X, bottom + 6, CENTER_X, out_y - 6, color=COLORS["gray"]["stroke"])
d.labeled_box(pipe_x, out_y, pipe_w, 55, "Continuous Learning", "-> page 12, weekly trade history input",
              color="purple", title_size=15, subtitle_size=11)

d.save(OUT)
