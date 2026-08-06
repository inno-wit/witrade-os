import sys, os
sys.path.insert(0, os.path.dirname(__file__))
from sm_lib import Diagram, COLORS, legend, caption

OUT = os.path.join(os.path.dirname(__file__), "..", "16_Container_Model_v2.excalidraw")

MARGIN = 40
CANVAS_W = 1500
BAND_X = MARGIN
BAND_W = CANVAS_W - 2 * MARGIN

d = Diagram("16v2 — Container Model, Deployment Groups  (generated/16_Container_Model_v2.md §3, §5 · 39 containers, page 16 lists 15)")

STATUS_COLOR = {
    "EXISTS":  "blue",
    "NEW":     "orange",
    "SPLIT":   "cyan",
    "CHANGED": "purple",
}


def band(y, title, group_note, items, tier0=()):
    """items: list of (id, name, status). Draws a titled band of equal-width boxes."""
    d.text(BAND_X, y, BAND_W, f"{title}   —   {group_note}", font_size=15,
           color="#1e1e1e", align="left")
    y += 26
    n = len(items)
    gap = 12
    w = (BAND_W - (n - 1) * gap) / n
    h = 68
    for i, (cid, name, status) in enumerate(items):
        x = BAND_X + i * (w + gap)
        color = COLORS[STATUS_COLOR[status]]
        stroke_w = 3 if cid in tier0 else 2
        d.rect(x, y, w, h, stroke=color["stroke"], bg=color["bg"], stroke_width=stroke_w)
        tier_mark = "▲ " if cid in tier0 else ""
        d.text(x + 5, y + 6, w - 10, f"{tier_mark}{cid}", font_size=11, color="#1e1e1e", align="left")
        d.text(x + 5, y + 20, w - 10, name, font_size=10.5, color="#1e1e1e", align="left")
        d.text(x + 5, y + h - 15, w - 10, status, font_size=8.5, color=color["stroke"], align="left")
    return y + h + 34


y = 90

y = band(y, "EDGE", "no inbound internet except here", [
    ("C01", "Market Data Ingestion", "EXISTS"),
    ("C02", "Untrusted Text ACL", "NEW"),
    ("C03", "Data Quality Engine", "EXISTS"),
])

y = band(y, "DATA", "storage locality", [
    ("C04", "Instrument & Reference Data Master", "NEW"),
    ("C06", "Feature Materialiser (offline)", "SPLIT"),
    ("C07", "Feature Serving (online)", "SPLIT"),
    ("C08", "Lakehouse (Iceberg + MinIO)", "CHANGED"),
], tier0=("C04",))

y = band(y, "QUANT", "scales horizontally by symbol", [
    ("C09", "Regime Engine", "EXISTS"),
    ("C10", "Volatility Engine", "EXISTS"),
    ("C11", "Market Structure Engine", "EXISTS"),
    ("C12", "Model Training Service", "SPLIT"),
    ("C13", "Model Inference Service", "SPLIT"),
    ("C14", "Model Monitor", "NEW"),
    ("C28", "Simulation & Replay Harness", "NEW"),
])

y = band(y, "DECISION", "bursty, cheap to scale", [
    ("C15", "Evidence Graph Service", "SPLIT"),
    ("C16", "Committee Service", "EXISTS"),
    ("C17", "LLM Gateway", "NEW"),
    ("C18", "Prompt & Policy Registry", "NEW"),
    ("C19", "Decision Saga Service", "CHANGED"),
    ("C20", "Decision Record Store", "NEW"),
    ("C27", "Continuous Learning Service", "EXISTS"),
    ("C30", "Cost Governor", "NEW"),
], tier0=("C20",))

y = band(y, "CAPITAL", "isolated network segment, one failure domain, Risk-Ledger latency on the hot path", [
    ("C21", "Risk Engine", "CHANGED"),
    ("C22", "Account & Position Ledger", "NEW"),
    ("C23", "Order & Position Lifecycle Manager (OMS)", "NEW"),
    ("C25", "Reconciliation Service", "NEW"),
    ("C26", "Platform Supervisor", "NEW"),
    ("C29", "TCA Service", "NEW"),
], tier0=("C21", "C22", "C23", "C25", "C26"))

y = band(y, "BRIDGE", "Windows VPS, active/standby with leader lease — the ONLY Windows-bound group", [
    ("C24", "Execution Service (+ MT5 terminal)", "CHANGED"),
], tier0=("C24",))

y = band(y, "PLATFORM", "shared services", [
    ("C31", "Observability Stack", "EXISTS"),
    ("C32", "API Gateway / BFF", "NEW"),
    ("C33", "Dashboard", "EXISTS"),
    ("C34", "Ops CLI", "EXISTS"),
    ("C35", "Scheduler", "SPLIT"),
    ("C36", "Event Bus (NATS)", "EXISTS"),
    ("C37", "Schema Registry", "NEW"),
    ("C38", "Secrets Manager", "NEW"),
    ("C39", "Identity Provider", "NEW"),
], tier0=("C36", "C38"))

# C05 Clock — library, not a deployable container, linked into everything above
d.rect(BAND_X, y, 260, 55, stroke=COLORS["gray"]["stroke"], bg=COLORS["gray"]["bg"], dashed=True)
d.text(BAND_X + 8, y + 8, 244, "C05  Clock", font_size=12, color="#1e1e1e", align="left")
d.text(BAND_X + 8, y + 26, 244, "library, not a deployable — injected everywhere, banned direct wall-clock calls", font_size=9, color="#868e96", align="left")
y += 55 + 30

legend(d, BAND_X, y, [
    ("normal", "EXISTS — carried from page 16 unchanged"),
    ("warn", "NEW — has no counterpart in the source ADD"),
    ("info", "SPLIT — carved out of one page-16 container"),
    ("gate", "CHANGED — materially rescoped from page 16"),
])
d.text(BAND_X + 420, y, 700, "▲  Tier 0 — failure threatens capital directly", font_size=12, color="#c92a2a", align="left")

y += 150
caption(d, BAND_X, y, BAND_W,
        "Page 16 lists 15 containers; 39 are required (21 new or split). Every container in CAPITAL is Tier 0 and four of six are new — "
        "that concentration is the finding: the source capital plane is two containers (Risk, Execution) doing the work of six. "
        "Only C24 and the MT5 terminal are Windows-bound; everything else the source design implicitly ties to that one VPS can and should "
        "move off it. Full contract per container: generated/16_Container_Model_v2.md.")

d.save(OUT)
