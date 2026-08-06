import sys, os
sys.path.insert(0, os.path.dirname(__file__))
from excalidraw_lib import Diagram, COLORS

OUT = os.path.join(os.path.dirname(__file__), "..", "08_AI_Investment_Committee.excalidraw")

MARGIN = 40
CANVAS_W = 1280
BAND_X = MARGIN
BAND_W = CANVAS_W - 2 * MARGIN
CENTER_X = BAND_X + BAND_W / 2
MAIN_W = 880
MAIN_X = BAND_X

d = Diagram("08 — AI Investment Committee  (Decision Intelligence Layer, sub-page 1 of 2)")

y = 90
pm_w = 500
d.labeled_box(MAIN_X + MAIN_W / 2 - pm_w / 2, y, pm_w, 55, "Portfolio Manager",
              "Convenes the committee, sets agenda, receives final recommendation",
              color="cyan", title_size=16, subtitle_size=11)
pm_bottom = y + 55
y = pm_bottom + 45
d.arrow(MAIN_X + MAIN_W / 2, pm_bottom, MAIN_X + MAIN_W / 2, y - 6, color=COLORS["cyan"]["stroke"])

d.text(MAIN_X, y, MAIN_W, "SIX DESKS  (parallel, independent reasoning — each implements the shared Desk Contract)",
       font_size=15, color=COLORS["cyan"]["stroke"], align="left")
y += 30

desks = [
    ("Regime Desk", "Reads: Regime API (pg 04)"),
    ("SMC Desk", "Reads: Structure API (pg 06)"),
    ("Volatility Desk", "Reads: Volatility API (pg 05)"),
    ("Macro Desk", "Reads: Macro features (pg 03)"),
    ("Risk Desk", "Reads: Portfolio state (pg 10)"),
    ("Execution Desk", "Reads: Liquidity/spread (pg 11)"),
]
n_cols = 3
gap = 18
cell_w = (MAIN_W - (n_cols - 1) * gap) / n_cols
cell_h = 90
desk_boxes = []
for i, (title, sub) in enumerate(desks):
    col = i % n_cols
    row = i // n_cols
    cx = MAIN_X + col * (cell_w + gap)
    cy = y + row * (cell_h + 15)
    d.labeled_box(cx, cy, cell_w, cell_h, title, sub, color="cyan", title_size=14, subtitle_size=10)
    desk_boxes.append((cx, cy, cell_w, cell_h))

desks_bottom = y + 2 * (cell_h + 15) - 15
y2 = desks_bottom + 50
for (bx, by, bw, bh) in desk_boxes:
    d.arrow(bx + bw / 2, by + bh, MAIN_X + MAIN_W / 2, y2 - 6, color=COLORS["cyan"]["stroke"], stroke_width=1)

ce_w = 500
d.labeled_box(MAIN_X + MAIN_W / 2 - ce_w / 2, y2, ce_w, 55, "Consensus Engine",
              "Weighted vote across 6 desk outputs, by confidence",
              color="purple", title_size=15, subtitle_size=10)
ce_bottom = y2 + 55
y3 = ce_bottom + 40
d.arrow(MAIN_X + MAIN_W / 2, ce_bottom, MAIN_X + MAIN_W / 2, y3 - 6, color=COLORS["purple"]["stroke"])

cr_w = 500
d.labeled_box(MAIN_X + MAIN_W / 2 - cr_w / 2, y3, cr_w, 55, "Conflict Resolver",
              "Deadlock -> default 'no trade'. Never forces a tiebreak toward action.",
              color="purple", title_size=15, subtitle_size=10)
cr_bottom = y3 + 55
y4 = cr_bottom + 40
d.arrow(MAIN_X + MAIN_W / 2, cr_bottom, MAIN_X + MAIN_W / 2, y4 - 6, color=COLORS["purple"]["stroke"])

tr_w = 500
d.labeled_box(MAIN_X + MAIN_W / 2 - tr_w / 2, y4, tr_w, 60, "Trade Recommendation",
              "direction, size hint, confidence, full reasoning trace -> page 09",
              color="orange", title_size=16, subtitle_size=11)
tr_bottom = y4 + 60

# ── Side panel: Desk Contract Schema ────────────────────────────────────
panel_x = MAIN_X + MAIN_W + 40
panel_w = BAND_W - MAIN_W - 40
panel_y = 90
panel_h = tr_bottom - panel_y
d.rect(panel_x, panel_y, panel_w, panel_h, stroke=COLORS["gray"]["stroke"], bg=COLORS["gray"]["bg"])
d.text(panel_x + 14, panel_y + 12, panel_w - 28, "Shared Desk Contract",
       font_size=16, color=COLORS["gray"]["stroke"], align="left")
d.text(panel_x + 14, panel_y + 45, panel_w - 28,
       "Every desk implements the\nsame interface:\n\n"
       "INPUTS\n  Deterministic API outputs\n  from its assigned engine only\n\n"
       "MEMORY\n  Last N committee cycles for\n  this symbol (continuity)\n\n"
       "TOOLS\n  Read-only queries into its\n  engine's API -- no write access,\n  no cross-desk calls\n\n"
       "OUTPUT JSON\n  { stance, confidence,\n    key_evidence[], reasoning }\n\n"
       "CONFIDENCE\n  0-100, discounted if inputs\n  carry a staleness/flag tag\n\n"
       "REASONING\n  Human-readable, cites only\n  numbers present in its own\n  Inputs (schema-validated --\n  a desk cannot cite a figure\n  the Quant layer never\n  produced)",
       font_size=11, color="#495057", align="left")

d.save(OUT)
