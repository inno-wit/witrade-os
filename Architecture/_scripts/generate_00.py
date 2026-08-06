import sys, os
sys.path.insert(0, os.path.dirname(__file__))
from excalidraw_lib import Diagram

OUT = os.path.join(os.path.dirname(__file__), "..", "00_Master_Architecture.excalidraw")

MARGIN = 40
CANVAS_W = 1160
BAND_X = MARGIN
BAND_W = CANVAS_W - 2 * MARGIN
CENTER_X = BAND_X + BAND_W / 2
GAP = 40

d = Diagram("WITrade Quant Platform — Master System Architecture (C4 Level 1: System Context)")

y = 90

# Legend (top-right, small, doesn't interfere with flow)
d.rect(BAND_X + BAND_W - 260, 15, 260, 60, stroke="#495057", bg="#f8f9fa")
d.text(BAND_X + BAND_W - 252, 20, 244, "Legend", font_size=13, color="#495057", align="left")
legend_items = [("blue", "External / Input"), ("yellow", "Deterministic (Python)"),
                ("cyan", "AI-driven (LLM reasoning)"), ("red", "Risk / Safety")]
lx = BAND_X + BAND_W - 252
ly = 40
from excalidraw_lib import COLORS
for i, (color, label) in enumerate(legend_items):
    cx = lx + (i % 2) * 125
    cy = ly + (i // 2) * 18
    d.rect(cx, cy, 12, 12, stroke=COLORS[color]["stroke"], bg=COLORS[color]["bg"])
    d.text(cx + 16, cy - 2, 110, label, font_size=10, color="#495057", align="left")

def connector(y_top, y_bottom, label=None):
    mid_y = (y_top + y_bottom) / 2
    d.arrow(CENTER_X, y_top, CENTER_X, y_bottom, color="#1e1e1e", stroke_width=2)
    if label:
        d.text(CENTER_X - 150, mid_y - 22, 300, label, font_size=13, color="#868e96", align="center")

# ── 1. USERS ─────────────────────────────────────────────────────────────
h = 100
d.section(BAND_X, y, BAND_W, h, "USERS", color="blue")
box_w, box_h = 400, 45
d.labeled_box(CENTER_X - box_w / 2, y + 45, box_w, box_h, "Web Dashboard / CLI",
              "Human operator interface", color="blue", title_size=16)
prev_bottom = y + h
y = prev_bottom + GAP

# ── 2. ORCHESTRATION LAYER ──────────────────────────────────────────────
h = 150
connector(prev_bottom, y, "requests")
d.section(BAND_X, y, BAND_W, h, "ORCHESTRATION LAYER", color="purple")
n = 3
item_w = (BAND_W - 60 - (n - 1) * 20) / n
d.row(BAND_X + 30, y + 55, n, item_w, 70, 20,
      ["Event Bus", "Scheduler", "Workflow Engine"],
      ["NATS — pub/sub between all subsystems", "Cron / interval triggers for jobs",
       "DAG execution, retries, backoff"],
      color="purple", title_size=16, subtitle_size=11)
prev_bottom = y + h
y = prev_bottom + GAP

# ── 3. DATA PLATFORM ────────────────────────────────────────────────────
h = 300
connector(prev_bottom, y, "orchestrates")
d.section(BAND_X, y, BAND_W, h, "DATA PLATFORM  (see page 01-03)", color="blue")
n = 5
item_w = (BAND_W - 60 - (n - 1) * 16) / n
sources_y = y + 55
d.row(BAND_X + 30, sources_y, n, item_w, 55, 16,
      ["MT5", "Databento", "Polygon", "News", "Econ Calendar"],
      ["Broker feed", "Tick / bar data", "OHLCV + fundamentals",
       "Headlines + sentiment", "Scheduled macro events"],
      color="blue", title_size=14, subtitle_size=10)
val_y = sources_y + 55 + 30
d.arrow(CENTER_X, sources_y + 55, CENTER_X, val_y, color="#1971c2")
val_w = 420
d.labeled_box(CENTER_X - val_w / 2, val_y, val_w, 45, "Data Validation",
              "Quality Engine — see page 02", color="yellow", title_size=15)
fs_y = val_y + 45 + 30
d.arrow(CENTER_X, val_y + 45, CENTER_X, fs_y, color="#f59f00")
fs_w = 420
d.labeled_box(CENTER_X - fs_w / 2, fs_y, fs_w, 45, "Feature Store",
              "Technical, Regime, SMC, Vol, Macro, Labels — see page 03",
              color="yellow", title_size=15)
prev_bottom = y + h
y = prev_bottom + GAP

# ── 4. QUANT RESEARCH PLATFORM ──────────────────────────────────────────
h = 155
connector(prev_bottom, y, "features")
d.section(BAND_X, y, BAND_W, h, "QUANT RESEARCH PLATFORM  (see page 04-07)", color="yellow")
n = 5
item_w = (BAND_W - 60 - (n - 1) * 16) / n
d.row(BAND_X + 30, y + 55, n, item_w, 85, 16,
      ["Regime Engine", "Volatility Engine", "SMC Engine", "ML Models", "RL Models"],
      ["GARCH/HMM\nregime probability", "ATR/forecast/\nrealized vol",
       "BOS/CHoCH/OB/\nFVG structure", "Supervised\npredictors", "Policy /\nsizing agents"],
      color="yellow", title_size=14, subtitle_size=10)
prev_bottom = y + h
y = prev_bottom + GAP

# ── 5. DECISION INTELLIGENCE LAYER ──────────────────────────────────────
h = 150
connector(prev_bottom, y, "signals + confidence")
d.section(BAND_X, y, BAND_W, h, "DECISION INTELLIGENCE LAYER — AI Investment Committee  (see page 08-09)", color="cyan")
n = 3
item_w = (BAND_W - 60 - (n - 1) * 20) / n
d.row(BAND_X + 30, y + 55, n, item_w, 75, 20,
      ["AI Investment Committee", "Consensus Engine", "Explainability"],
      ["6 desks debate: Regime, SMC,\nVol, Macro, Risk, Execution",
       "Weighted vote + conflict\nresolution → recommendation",
       "Human-readable reasoning\ntrace per decision"],
      color="cyan", title_size=15, subtitle_size=11)
prev_bottom = y + h
y = prev_bottom + GAP

# ── 6. RISK MANAGEMENT ──────────────────────────────────────────────────
h = 130
connector(prev_bottom, y, "trade recommendation")
d.section(BAND_X, y, BAND_W, h, "RISK MANAGEMENT  (see page 10)", color="red")
n = 4
item_w = (BAND_W - 60 - (n - 1) * 16) / n
d.row(BAND_X + 30, y + 55, n, item_w, 55, 16,
      ["Position Sizing", "Portfolio", "Exposure", "Kill Switch"],
      ["Kelly / vol-adjusted", "Correlation & concentration",
       "Per-symbol & aggregate caps", "Hard stop on breach"],
      color="red", title_size=14, subtitle_size=10)
prev_bottom = y + h
y = prev_bottom + GAP

# ── 7. EXECUTION ENGINE ─────────────────────────────────────────────────
h = 130
connector(prev_bottom, y, "approved trade")
d.section(BAND_X, y, BAND_W, h, "EXECUTION ENGINE  (see page 11)", color="green")
n = 3
item_w = (BAND_W - 60 - (n - 1) * 20) / n
d.row(BAND_X + 30, y + 55, n, item_w, 55, 20,
      ["MT5 / Broker Adapter", "Order Verification", "Fill Verification"],
      ["Broker-agnostic order routing", "Pre-send checks",
       "Slippage analysis + confirmation"],
      color="green", title_size=14, subtitle_size=10)
prev_bottom = y + h
y = prev_bottom + GAP

# ── 8. MONITORING & OBSERVABILITY (cross-cutting) ──────────────────────
h = 130
connector(prev_bottom, y, "fills + telemetry")
d.section(BAND_X, y, BAND_W, h, "MONITORING & OBSERVABILITY  (cross-cutting — see page 13)", color="gray")
n = 4
item_w = (BAND_W - 60 - (n - 1) * 16) / n
d.row(BAND_X + 30, y + 55, n, item_w, 55, 16,
      ["Logs", "Metrics", "Alerts", "Journal"],
      ["Structured, per-service", "Prometheus / Grafana",
       "PagerDuty / Slack on breach", "Every decision + fill, permanent"],
      color="gray", title_size=14, subtitle_size=10)
prev_bottom = y + h
y = prev_bottom + GAP

# ── 9. CONTINUOUS LEARNING ──────────────────────────────────────────────
h = 130
connector(prev_bottom, y, "observes everything above")
d.section(BAND_X, y, BAND_W, h, "CONTINUOUS LEARNING  (see page 12)", color="purple")
n = 4
item_w = (BAND_W - 60 - (n - 1) * 16) / n
d.row(BAND_X + 30, y + 55, n, item_w, 55, 16,
      ["Weekly Review", "Trade Analytics", "Model Evaluation", "Strategy Evolution"],
      ["Scheduled retro", "Win rate, R, drawdown",
       "Drift & decay checks", "Hypothesis → experiment queue"],
      color="purple", title_size=14, subtitle_size=10)
prev_bottom = y + h

# Feedback loop: Continuous Learning back to Quant Research + AI Committee.
# Drawn as a simple vertical dashed arrow in the left margin, bottom-to-top.
quant_research_mid_y = 90 + 100 + GAP + 150 + GAP + 300 + GAP + 155 / 2
learning_mid_y = prev_bottom + 130 / 2
loop_x = BAND_X - 30
d.arrow(loop_x, learning_mid_y, loop_x, quant_research_mid_y, color="#862e9c", dashed=True)
d.text(loop_x - 150, (learning_mid_y + quant_research_mid_y) / 2 - 10, 140,
       "weekly retrain /\nfeedback loop", font_size=12, color="#862e9c", align="center")

d.save(OUT)
