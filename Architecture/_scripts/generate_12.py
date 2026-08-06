import sys, os
sys.path.insert(0, os.path.dirname(__file__))
from excalidraw_lib import Diagram, COLORS

OUT = os.path.join(os.path.dirname(__file__), "..", "12_Continuous_Learning.excalidraw")

MARGIN = 40
CANVAS_W = 1200
BAND_X = MARGIN
BAND_W = CANVAS_W - 2 * MARGIN
CENTER_X = BAND_X + BAND_W / 2
pipe_w = 520
pipe_x = CENTER_X - pipe_w / 2

d = Diagram("12 — Continuous Learning")

y = 90
d.labeled_box(pipe_x, y, pipe_w, 55, "Trade History", "Journal, from page 11 -- weekly-triggered review",
              color="gray", title_size=15, subtitle_size=11)
y += 55 + 35
d.arrow(CENTER_X, y - 29, CENTER_X, y - 6, color=COLORS["gray"]["stroke"])

stages = [
    ("Performance Analytics", "Win rate, R-multiple, drawdown,\nper-desk accuracy", "purple"),
    ("Failure Detection", "Where did realized outcomes\ndiverge from Committee confidence?", "purple"),
    ("Hypothesis Generator", "Proposes specific, testable\nchanges (not vague 'do better')", "purple"),
    ("Experiment Queue", "Prioritized backlog of\nhypotheses awaiting validation", "purple"),
    ("Research Backlog", "Validated changes ready\nfor promotion", "purple"),
]
bottom = d.pipeline(pipe_x, pipe_w, y, stages, item_h=60, gap=34, title_size=14, subtitle_size=10)

branch_y = bottom + 55
n = 2
gap3 = 40
item_w3 = (pipe_w - gap3) / n
xs = [pipe_x, pipe_x + item_w3 + gap3]
targets = [
    ("Quant Research Platform", "Retrained models -- pages 04-07\n(gated by PBO/DSR, page 07)", "yellow"),
    ("AI Investment Committee", "Revised desk weights/prompts\n-- page 08 Consensus Engine", "cyan"),
]
for x, (t, s, c) in zip(xs, targets):
    d.arrow(CENTER_X, bottom + 6, x + item_w3 / 2, branch_y - 6, color=COLORS["purple"]["stroke"], stroke_width=1)
    d.labeled_box(x, branch_y, item_w3, 75, t, s, color=c, title_size=13, subtitle_size=10)

# Validation gate note
note_x = pipe_x + pipe_w + 40
note_w = BAND_X + BAND_W - note_x
note_y = 90
note_h = branch_y + 75 - note_y
if note_w > 150:
    d.rect(note_x, note_y, note_w, note_h, stroke=COLORS["red"]["stroke"], bg=COLORS["red"]["bg"])
    d.text(note_x + 12, note_y + 10, note_w - 24, "No Shortcut Rule",
           font_size=15, color=COLORS["red"]["stroke"], align="left")
    d.text(note_x + 12, note_y + 40, note_w - 24,
           "Every change this loop\nproposes -- a retrained\nmodel, a new desk weight --\ngoes through the SAME\nPBO / Deflated Sharpe\nvalidation gate as any\nbrand-new strategy\n(page 07).\n\n"
           "The learning loop does not\nget to bypass validation\njust because it's the\nplatform 'learning about\nitself' -- that is exactly\nthe scenario overfitting\nchecks exist for.\n\n"
           "See pbo-deflated-sharpe\nand trading-loop /\nautoresearch skills.",
           font_size=11, color="#495057", align="left")

d.save(OUT)
