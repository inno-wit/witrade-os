import sys, os
sys.path.insert(0, os.path.dirname(__file__))
from excalidraw_lib import Diagram, COLORS

OUT = os.path.join(os.path.dirname(__file__), "..", "05_Volatility_Engine.excalidraw")

MARGIN = 40
CANVAS_W = 1160
BAND_X = MARGIN
BAND_W = CANVAS_W - 2 * MARGIN
CENTER_X = BAND_X + BAND_W / 2

d = Diagram("05 — Volatility Engine  (Quant Research Platform, sub-page 2 of 4)")

y = 90
n_in = 2
gap_in = 20
in_w = (600 - gap_in) / n_in
in_x_start = CENTER_X - 600 / 2
d.text(BAND_X, y, BAND_W, "INPUTS", font_size=16, color=COLORS["blue"]["stroke"], align="left")
y += 30
d.labeled_box(in_x_start, y, in_w, 50, "Price / Returns", "from Feature Store", color="blue", title_size=13)
d.labeled_box(in_x_start + in_w + gap_in, y, in_w, 50, "Regime State", "from page 04", color="blue", title_size=13)
in_bottom = y + 50
y = in_bottom + 45
d.arrow(in_x_start + in_w / 2, in_bottom, CENTER_X, y - 6, color=COLORS["blue"]["stroke"], stroke_width=1)
d.arrow(in_x_start + in_w + gap_in + in_w / 2, in_bottom, CENTER_X, y - 6, color=COLORS["blue"]["stroke"], stroke_width=1)

outer_h = 300
d.section(BAND_X, y, BAND_W, outer_h, "VOLATILITY ENGINE", color="yellow")
grid_y = y + 55
metrics = [
    ("ATR", "Average True Range,\nclassic bar-range vol"),
    ("Forecast Vol", "Forward-looking estimate\n(GARCH-derived, shared w/ page 04)"),
    ("Realized Vol", "Backward-looking,\nrolling-window realized"),
    ("Expected Move", "Options-style expected range\nfor N-bar horizon"),
    ("Vol Percentile", "Current vol vs. trailing\n1yr distribution"),
    ("Tail Risk", "Fat-tail / extreme-move\nprobability (EVT-based)"),
]
n_cols = 3
gap = 20
cell_w = (BAND_W - 60 - (n_cols - 1) * gap) / n_cols
cell_h = 95
for i, (title, sub) in enumerate(metrics):
    col = i % n_cols
    row = i // n_cols
    cx = BAND_X + 30 + col * (cell_w + gap)
    cy = grid_y + row * (cell_h + 15)
    d.labeled_box(cx, cy, cell_w, cell_h, title, sub, color="yellow", title_size=14, subtitle_size=10)

api_y = y + outer_h + 45
d.arrow(CENTER_X, y + outer_h, CENTER_X, api_y - 6, color=COLORS["yellow"]["stroke"])
api_w = 480
d.labeled_box(CENTER_X - api_w / 2, api_y, api_w, 55, "Volatility API",
              "get_volatility(symbol, as_of) -> {atr, forecast, realized, expected_move, percentile, tail_risk}",
              color="orange", title_size=14, subtitle_size=10)

d.save(OUT)
