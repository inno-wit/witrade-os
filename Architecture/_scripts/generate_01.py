import sys, os
sys.path.insert(0, os.path.dirname(__file__))
from excalidraw_lib import Diagram, COLORS

OUT = os.path.join(os.path.dirname(__file__), "..", "01_Data_Ingestion.excalidraw")

MARGIN = 40
CANVAS_W = 1160
BAND_X = MARGIN
BAND_W = CANVAS_W - 2 * MARGIN
CENTER_X = BAND_X + BAND_W / 2

d = Diagram("01 — Data Ingestion  (Data Platform, sub-page 1 of 3)")

y = 90

# ── External sources row ────────────────────────────────────────────────
d.text(BAND_X, y, BAND_W, "EXTERNAL SOURCES", font_size=18, color=COLORS["blue"]["stroke"], align="left")
y += 35
n = 5
gap = 16
item_w = (BAND_W - (n - 1) * gap) / n
src_y = y
sources = d.row(BAND_X, src_y, n, item_w, 65, gap,
      ["MT5", "Databento", "Polygon", "News", "Econ Calendar"],
      ["Broker feed\n(push, tick-level)", "Institutional tick/\nbar data (pull)",
       "OHLCV + fundamentals\n(pull, REST)", "Headlines + sentiment\n(pull, poll 5min)",
       "Scheduled macro events\n(pull, daily sync)"],
      color="blue", title_size=14, subtitle_size=10)

pipeline_top = src_y + 65 + 50
pipe_w = 460
pipe_x = CENTER_X - pipe_w / 2

# converging arrows from each source into the pipeline entry point
for (sx, sy, sw, sh) in sources:
    d.arrow(sx + sw / 2, sy + sh, pipe_x + pipe_w / 2, pipeline_top - 4,
            color=COLORS["blue"]["stroke"], stroke_width=1)

d.text(pipe_x - 40, pipeline_top - 45, pipe_w + 80, "INGESTION PIPELINE (per symbol, per source)",
       font_size=18, color=COLORS["yellow"]["stroke"], align="left")

stages = [
    ("Raw Tick / Bar Storage", "Append-only, source-tagged, never mutated"),
    ("Cleaning", "Dedup, timestamp normalize, unit conversion"),
    ("Validation", "Quality Engine hook — see page 02"),
    ("Resampling", "Tick → 1m/5m/15m/1H/4H/1D bars"),
    ("Parquet", "Columnar cold storage, partitioned by symbol/date"),
    ("DuckDB", "Queryable warehouse layer over Parquet"),
]
bottom = d.pipeline(pipe_x, pipe_w, pipeline_top, stages, color="yellow",
                     item_h=55, gap=40, title_size=15, subtitle_size=11)

# Arrow out to Feature Store (external reference, page 03)
fs_y = bottom + 45
d.arrow(pipe_x + pipe_w / 2, bottom + 6, pipe_x + pipe_w / 2, fs_y - 6, color=COLORS["green"]["stroke"])
d.labeled_box(pipe_x, fs_y, pipe_w, 55, "Feature Store", "See page 03 — Feature Store",
              color="green", title_size=15, subtitle_size=11)

# Side note: failure handling
note_x = pipe_x + pipe_w + 40
note_w = BAND_X + BAND_W - note_x
d.rect(note_x, pipeline_top - 45, note_w, 350, stroke=COLORS["red"]["stroke"], bg=COLORS["red"]["bg"])
d.text(note_x + 12, pipeline_top - 35, note_w - 24, "Per-Source Circuit Breaker",
       font_size=15, color=COLORS["red"]["stroke"], align="left")
d.text(note_x + 12, pipeline_top - 5, note_w - 24,
       "Each source has an independent\ncircuit breaker:\n\n"
       "- 3 consecutive failures -> OPEN\n"
       "- OPEN = skip source, flag gap,\n  continue pipeline with remaining\n  sources\n"
       "- Half-open retry every 60s\n"
       "- Databento can fall back for\n  Polygon gaps (both provide OHLCV)\n\n"
       "MT5 has no fallback -- broker\nfeed loss halts live execution\ninputs for that account only.",
       font_size=12, color="#495057", align="left")

d.save(OUT)
