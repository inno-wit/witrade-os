import sys, os
sys.path.insert(0, os.path.dirname(__file__))
from excalidraw_lib import Diagram, COLORS

OUT = os.path.join(os.path.dirname(__file__), "..", "13_Infrastructure_Platform.excalidraw")

MARGIN = 40
CANVAS_W = 1240
BAND_X = MARGIN
BAND_W = CANVAS_W - 2 * MARGIN

d = Diagram("13 — Infrastructure Platform")

y = 100
n_cols = 6
gap = 20
col_w = (BAND_W - (n_cols - 1) * gap) / n_cols

columns = [
    ("Compute / API", "blue", [
        ("FastAPI", "Every Python service's\nHTTP/API surface"),
        ("Docker", "Container runtime for\nall services"),
    ]),
    ("Messaging", "purple", [
        ("NATS (JetStream)", "Event Bus -- page 00\nOrchestration Layer"),
    ]),
    ("Data Storage", "yellow", [
        ("DuckDB", "Query layer -- pages\n01, 03"),
        ("Postgres", "Durable ledgers -- Risk\n(10), Journal (11)"),
        ("MinIO", "S3-compatible object\nstorage -- Parquet, model\nartifacts"),
    ]),
    ("ML Ops", "cyan", [
        ("MLflow", "Model registry --\npage 07, tracks 04-08\nfitted params"),
    ]),
    ("Observability", "gray", [
        ("Prometheus", "Metrics scrape --\npage 00 Monitoring"),
        ("Grafana", "Dashboards over\nPrometheus"),
    ]),
    ("CI/CD", "green", [
        ("GitHub Actions", "Build, test, deploy --\npage 14"),
    ]),
]

for i, (title, color, items) in enumerate(columns):
    cx = BAND_X + i * (col_w + gap)
    d.text(cx, y, col_w, title, font_size=15, color=COLORS[color]["stroke"], align="left")
    iy = y + 35
    for item_title, item_sub in items:
        ih = 85
        d.labeled_box(cx, iy, col_w, ih, item_title, item_sub, color=color, title_size=13, subtitle_size=10)
        iy += ih + 15

d.save(OUT)
