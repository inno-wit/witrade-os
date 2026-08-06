import sys, os
sys.path.insert(0, os.path.dirname(__file__))
from excalidraw_lib import Diagram, COLORS

OUT = os.path.join(os.path.dirname(__file__), "..", "02_Data_Quality_Engine.excalidraw")

MARGIN = 40
CANVAS_W = 1160
BAND_X = MARGIN
BAND_W = CANVAS_W - 2 * MARGIN
CENTER_X = BAND_X + BAND_W / 2

d = Diagram("02 — Data Quality Engine  (Data Platform, sub-page 2 of 3)")

y = 90
in_w = 400
d.labeled_box(CENTER_X - in_w / 2, y, in_w, 50, "Raw / Cleaned Bars", "from page 01 — Data Ingestion",
              color="blue", title_size=15)
y += 50 + 40
d.arrow(CENTER_X, y - 34, CENTER_X, y - 6, color=COLORS["blue"]["stroke"])

d.text(BAND_X, y, BAND_W, "DETECTORS  (run in parallel, per dataset)", font_size=18,
       color=COLORS["yellow"]["stroke"], align="left")
y += 35

detectors = [
    ("Missing Candles", "Gap in expected bar sequence"),
    ("Duplicates", "Same (symbol,timestamp) twice"),
    ("DST Issues", "Off-by-1hr alignment at transitions"),
    ("Broker Outages", "Feed silence beyond expected heartbeat"),
    ("Spread Spikes", "Bid/ask spread > N std dev"),
    ("Flash Crashes", "Single-bar move > threshold, reverts fast"),
    ("Bad Ticks", "Zero/negative price, impossible OHLC"),
]
n = 4
gap = 16
item_w = (BAND_W - (n - 1) * gap) / n
row1 = detectors[:4]
row2 = detectors[4:]
det_y1 = y
d.row(BAND_X, det_y1, len(row1), item_w, 65, gap,
      [t for t, s in row1], [s for t, s in row1], color="yellow", title_size=13, subtitle_size=10)
det_y2 = det_y1 + 65 + 20
n2 = len(row2)
item_w2 = (BAND_W - (n2 - 1) * gap) / n2 if n2 > 1 else BAND_W
d.row(BAND_X, det_y2, n2, item_w2, 65, gap,
      [t for t, s in row2], [s for t, s in row2], color="yellow", title_size=13, subtitle_size=10)

scorer_y = det_y2 + 65 + 55
# converging arrows from all 7 detectors to the scorer
all_boxes_row1 = [(BAND_X + i * (item_w + gap), det_y1, item_w, 65) for i in range(len(row1))]
all_boxes_row2 = [(BAND_X + i * (item_w2 + gap), det_y2, item_w2, 65) for i in range(len(row2))]
for (bx, by, bw, bh) in all_boxes_row1 + all_boxes_row2:
    d.arrow(bx + bw / 2, by + bh, CENTER_X, scorer_y - 6, color=COLORS["yellow"]["stroke"], stroke_width=1)

scorer_w = 460
d.labeled_box(CENTER_X - scorer_w / 2, scorer_y, scorer_w, 60, "Quality Scorer",
              "Weighted composite -> 0.0-1.0 score per dataset", color="orange", title_size=16)

branch_y = scorer_y + 60 + 55

n3 = 3
gap3 = 30
item_w3 = (BAND_W - (n3 - 1) * gap3) / n3
outcomes = [
    ("PASS  (score >= 0.8)", "Feature Store, no annotation", "green"),
    ("FLAG  (0.5 <= score < 0.8)", "Feature Store, tagged for\ndownstream discount", "orange"),
    ("REJECT  (score < 0.5)", "Quarantine table + alert,\nnever reaches Feature Store", "red"),
]
xs = [BAND_X + i * (item_w3 + gap3) for i in range(n3)]
for x, (t, s, c) in zip(xs, outcomes):
    d.arrow(CENTER_X, scorer_y + 60, x + item_w3 / 2, branch_y - 6,
            color=COLORS["orange"]["stroke"], stroke_width=1)
    d.labeled_box(x, branch_y, item_w3, 75, t, s, color=c, title_size=13, subtitle_size=11)

d.save(OUT)
