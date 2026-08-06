import sys, os
sys.path.insert(0, os.path.dirname(__file__))
from excalidraw_lib import Diagram, COLORS

OUT = os.path.join(os.path.dirname(__file__), "..", "03_Feature_Store.excalidraw")

MARGIN = 40
CANVAS_W = 1160
BAND_X = MARGIN
BAND_W = CANVAS_W - 2 * MARGIN
CENTER_X = BAND_X + BAND_W / 2

d = Diagram("03 — Feature Store  (Data Platform, sub-page 3 of 3)")

y = 90
in_w = 400
d.labeled_box(CENTER_X - in_w / 2, y, in_w, 50, "Validated Bars", "PASS / FLAG from page 02 — Quality Engine",
              color="blue", title_size=14)
y += 50 + 45
d.arrow(CENTER_X, y - 39, CENTER_X, y - 6, color=COLORS["blue"]["stroke"])

# Outer Feature Store container
outer_h = 420
d.section(BAND_X, y, BAND_W, outer_h, "FEATURE STORE", color="purple")

grid_y = y + 55
categories = [
    ("Technical", "RSI, MACD, EMA, BB,\nStochastic, ATR"),
    ("Regime", "Bull/bear/sideways prob,\nHMM state — page 04"),
    ("SMC", "BOS, CHoCH, OB, FVG,\nliquidity — page 06"),
    ("Volatility", "Realized/forecast vol,\nvol percentile — page 05"),
    ("Time", "Session, day-of-week,\ntime-to-close/event"),
    ("Macro", "Rates, DXY, yield curve,\nrisk-on/off score"),
    ("Alternative Data", "Options flow, sentiment,\non-chain (future)"),
    ("Cross Asset", "Correlated pair moves,\nintermarket signals"),
    ("Labels", "Forward returns, triple-\nbarrier outcomes (training)"),
]
n_cols = 3
gap = 20
cell_w = (BAND_W - 60 - (n_cols - 1) * gap) / n_cols
cell_h = 95
for i, (title, sub) in enumerate(categories):
    col = i % n_cols
    row = i // n_cols
    cx = BAND_X + 30 + col * (cell_w + gap)
    cy = grid_y + row * (cell_h + 15)
    d.labeled_box(cx, cy, cell_w, cell_h, title, sub, color="purple", title_size=14, subtitle_size=10)

out_y = y + outer_h + 45
d.arrow(CENTER_X, y + outer_h, CENTER_X, out_y - 6, color=COLORS["purple"]["stroke"])
out_w = 500
d.labeled_box(CENTER_X - out_w / 2, out_y, out_w, 55, "Quant Research Platform",
              "Consumes via versioned feature API — see pages 04-07",
              color="yellow", title_size=15, subtitle_size=11)

d.save(OUT)
