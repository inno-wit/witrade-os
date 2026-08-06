import sys, os
sys.path.insert(0, os.path.dirname(__file__))
from excalidraw_lib import Diagram, COLORS

OUT = os.path.join(os.path.dirname(__file__), "..", "16_C4_Container_Diagram.excalidraw")

MARGIN = 40
CANVAS_W = 1320
BUS_W = 90
BAND_X = MARGIN + BUS_W + 30
BAND_W = CANVAS_W - BAND_X - MARGIN

d = Diagram("16 — C4 Container Diagram (Whole Platform, Level 2)")

row_centers = []  # (y_center, color) for bus connector lines

y = 90

# Actor + external systems row
d.labeled_box(BAND_X, y, 200, 55, "Operator", "[Person]", color="blue", title_size=15)
ext_x = BAND_X + 220
ext_w = (BAND_W - 220 - 5 * 14) / 6
externals = ["MT5", "Databento", "Polygon.io", "News API", "Econ Calendar", "Broker"]
for i, name in enumerate(externals):
    d.labeled_box(ext_x + i * (ext_w + 14), y, ext_w, 55, name, "[External System]", color="gray", title_size=11, subtitle_size=9)
row_bottom = y + 55
y = row_bottom + 40


def row(title, items, color, y):
    d.text(BAND_X, y, BAND_W, title, font_size=14, color=COLORS[color]["stroke"], align="left")
    y += 26
    n = len(items)
    gap = 16
    w = (BAND_W - (n - 1) * gap) / n
    for i, (name, tech) in enumerate(items):
        d.labeled_box(BAND_X + i * (w + gap), y, w, 70, name, f"[Container: {tech}]", color=color, title_size=12, subtitle_size=9)
    row_centers.append((y + 35, color))
    return y + 70


y = row("PRESENTATION", [("Dashboard / CLI", "Next.js + Python CLI")], "blue", y)
y += 35

y = row("DATA PLATFORM  (pages 01-03)", [
    ("Data Ingestion", "Python asyncio"),
    ("Data Quality Engine", "Python"),
    ("Feature Store", "DuckDB + Parquet"),
], "blue", y)
y += 35

y = row("QUANT RESEARCH  (pages 04-07)", [
    ("Regime Engine", "arch + hmmlearn"),
    ("Volatility Engine", "arch + scipy"),
    ("Structure Engine", "smartmoneyconcepts"),
    ("ML/RL Service", "sklearn + SB3 + MLflow"),
], "yellow", y)
y += 35

y = row("DECISION INTELLIGENCE  (pages 08-09)", [
    ("AI Investment Committee", "Claude API"),
    ("Decision Intelligence Svc", "Python"),
], "cyan", y)
y += 35

y = row("RISK & EXECUTION  (pages 10-11)", [
    ("Risk Engine", "Python + Redis + Postgres"),
    ("Execution Service", "Python + MT5 bridge"),
], "red", y)
y += 35

y = row("META  (pages 12-13)", [
    ("Continuous Learning Svc", "Python + pandas + MLflow"),
    ("Monitoring", "Prometheus + Grafana"),
], "purple", y)

bottom = y + 40

# Event Bus spine (vertical, left side)
bus_x = MARGIN
bus_y = 90
bus_h = bottom - bus_y
d.rect(bus_x, bus_y, BUS_W, bus_h, stroke=COLORS["purple"]["stroke"], bg=COLORS["purple"]["bg2"])
d.text(bus_x + 6, bus_y + bus_h / 2 - 60, BUS_W - 12, "EVENT\nBUS\n\nNATS\nJetStream",
       font_size=12, color="#1e1e1e", align="center")

# Dashed connectors from bus to each row group's vertical center
for (row_y, color) in row_centers:
    d.arrow(bus_x + BUS_W, row_y, BAND_X - 4, row_y, color=COLORS[color]["stroke"],
            dashed=True, stroke_width=1)

# Primary synchronous data-flow arrows down the main pipeline (thin, black, on top of bands)
flow_x = BAND_X + 30
prev_y = row_bottom + 55
# We didn't retain exact top y of each band's box row; approximate using row_centers minus half box height (35)
box_tops = [c - 35 for c, _ in row_centers]
for i in range(len(box_tops) - 1):
    d.arrow(flow_x, box_tops[i] + 70, flow_x, box_tops[i + 1] - 26, color="#1e1e1e", stroke_width=1)

d.text(MARGIN, bottom + 15, CANVAS_W - 2 * MARGIN,
       "Dashed lines = pub/sub via Event Bus (all containers). Solid vertical arrows = primary synchronous request path down the main pipeline. Full event detail: page 15.",
       font_size=12, color="#868e96", align="left")

d.save(OUT)
