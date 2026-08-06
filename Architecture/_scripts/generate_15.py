import sys, os, math
sys.path.insert(0, os.path.dirname(__file__))
from excalidraw_lib import Diagram, COLORS

OUT = os.path.join(os.path.dirname(__file__), "..", "15_Event_Catalog.excalidraw")

CANVAS_W = 1240
CANVAS_H = 1050

d = Diagram("15 — Event Catalog  (cross-cutting reference)")

cx, cy = CANVAS_W / 2, 560
hub_w, hub_h = 260, 80
d.labeled_box(cx - hub_w / 2, cy - hub_h / 2, hub_w, hub_h, "EVENT BUS", "NATS JetStream -- page 00",
              color="purple", title_size=17, subtitle_size=11)

nodes = [
    ("Data Platform", "blue", "data.*, feature.*\n(pages 01-03)"),
    ("Regime Engine", "yellow", "regime.*\n(page 04)"),
    ("Volatility Engine", "yellow", "volatility.*\n(page 05)"),
    ("Structure Engine", "yellow", "structure.*\n(page 06)"),
    ("ML/RL Models", "yellow", "model.*\n(page 07)"),
    ("AI Committee", "cyan", "committee.*\n(page 08)"),
    ("Decision Intel.", "cyan", "evidence.*, decision.*\n(page 09)"),
    ("Risk Management", "red", "risk.*\n(page 10)"),
    ("Execution", "green", "order.*, execution.*\n(page 11)"),
    ("Monitoring", "gray", "alert.*\n(cross-cutting)"),
    ("Continuous Learning", "purple", "learning.*\n(page 12)"),
    ("Deployment", "gray", "deploy.*, shadow.*\n(page 14)"),
]

n = len(nodes)
rx, ry = 480, 420
box_w, box_h = 190, 65
for i, (title, color, sub) in enumerate(nodes):
    angle = 2 * math.pi * i / n - math.pi / 2
    nx = cx + rx * math.cos(angle) - box_w / 2
    ny = cy + ry * math.sin(angle) - box_h / 2
    d.labeled_box(nx, ny, box_w, box_h, title, sub, color=color, title_size=12, subtitle_size=9)
    # arrow from node edge to hub edge (approx, straight line between centers looks fine at this scale)
    node_cx, node_cy = nx + box_w / 2, ny + box_h / 2
    dx, dy = cx - node_cx, cy - node_cy
    dist = math.hypot(dx, dy)
    ux, uy = dx / dist, dy / dist
    start_x = node_cx + ux * (box_w / 2 * 0.9)
    start_y = node_cy + uy * (box_h / 2 * 0.9)
    end_x = cx - ux * (hub_w / 2 * 0.9)
    end_y = cy - uy * (hub_h / 2 * 0.9)
    d.arrow(start_x, start_y, end_x, end_y, color=COLORS[color]["stroke"], stroke_width=1)

d.text(30, CANVAS_H - 40, CANVAS_W - 60,
       "Full event schema (publisher, consumer, payload) is documented in 15_Event_Catalog.md -- this diagram shows topology only.",
       font_size=13, color="#868e96", align="center")

d.save(OUT)
