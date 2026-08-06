import sys, os
sys.path.insert(0, os.path.dirname(__file__))
from excalidraw_lib import Diagram, COLORS

OUT = os.path.join(os.path.dirname(__file__), "..", "17_Evidence_Graph.excalidraw")

MARGIN = 40
CANVAS_W = 1280
BAND_X = MARGIN
BAND_W = CANVAS_W - 2 * MARGIN
CENTER_X = BAND_X + BAND_W / 2
MAIN_W = 860
MAIN_X = BAND_X

d = Diagram("17 — Evidence Graph  (C15, sits between Market Intelligence and Deliberation)")

y = 90
d.section(MAIN_X, y, MAIN_W, 130, "UPSTREAM: RESEARCH PLATFORM ENGINES (pages 03-07)", color="blue")
n = 5
item_w = (MAIN_W - 60 - (n - 1) * 14) / n
d.row(MAIN_X + 30, y + 50, n, item_w, 60, 14,
      ["Feature Store", "Regime", "Volatility", "Structure", "ML/RL"],
      ["FeatureVector", "State nodes", "Forecast nodes", "Level nodes", "Forecast nodes"],
      color="blue", title_size=13, subtitle_size=10)
prev_bottom = y + 130
y = prev_bottom + 40
d.arrow(CENTER_X, prev_bottom, CENTER_X, y - 6, color=COLORS["cyan"]["stroke"])

eg_h = 260
d.section(MAIN_X, y, MAIN_W, eg_h, "EVIDENCE GRAPH (C15) — deterministic, LLM never writes here", color="cyan")
node_y = y + 50
n = 4
item_w = (MAIN_W - 60 - (n - 1) * 14) / n
d.row(MAIN_X + 30, node_y, n, item_w, 55, 14,
      ["Node model", "Edge model\n(9 types)", "Weighting\n(5 factors)", "Log-odds\npropagation"],
      ["Observation, Level, State,\nForecast, Event, Constraint,\nPortfolioFact, Precedent",
       "SUPPORTS, CONTRADICTS,\nCONFLUENT_WITH, SHARES_MODEL_WITH...",
       "reliability x freshness x\nquality x regime_applicability\nx independence",
       "graph_baseline_posterior,\ncomputed before any desk runs"],
      color="cyan", title_size=12, subtitle_size=9)
contra_y = node_y + 55 + 20
d.labeled_box(MAIN_X + 30, contra_y, MAIN_W - 60, 55, "Contradiction classification",
              "timeframe (hierarchy) / direct / model (most informative) / stale / data — surfaced to desks, never pre-netted",
              color="orange", title_size=13, subtitle_size=10)
seal_y = contra_y + 55 + 15
d.labeled_box(MAIN_X + 30, seal_y, MAIN_W - 60, 45, "Sealed, content-addressed, immutable",
              "sha256 hash every desk citation and every AuthorisedOrder must reference (ADR-0013)",
              color="cyan", title_size=13, subtitle_size=10)
prev_bottom = y + eg_h
y = prev_bottom + 40
d.arrow(CENTER_X, prev_bottom, CENTER_X, y - 6, color=COLORS["purple"]["stroke"])

d.section(MAIN_X, y, MAIN_W, 110, "DOWNSTREAM: SIX DESKS (page 08) — read a graph SLICE, never the raw engine dump", color="purple")
n = 3
item_w = (MAIN_W - 60 - (n - 1) * 18) / n
d.row(MAIN_X + 30, y + 50, n, item_w, 45, 18,
      ["Desk's own engine nodes", "+ connected nodes\n(edges visible)", "Citations only\n(never a bare number)"],
      [None, None, None],
      color="purple", title_size=12, subtitle_size=10)
bottom = y + 110

panel_x = MAIN_X + MAIN_W + 40
panel_w = BAND_W - MAIN_W - 40
panel_y = 90
panel_h = bottom - panel_y
d.rect(panel_x, panel_y, panel_w, panel_h, stroke=COLORS["gray"]["stroke"], bg=COLORS["gray"]["bg"])
d.text(panel_x + 14, panel_y + 12, panel_w - 28, "Falsifiability test", font_size=15, color=COLORS["gray"]["stroke"], align="left")
d.text(panel_x + 14, panel_y + 45, panel_w - 28,
       "graph_committee_\ndivergence\n\n"
       "Compares the graph's\nown baseline posterior\nto the Committee's\npooled conclusion.\n\n"
       "If the Committee never\ndisagrees with the\ngraph, the LLM layer\nadds nothing and\nshould be removed.\n\n"
       "This is the one metric\nthat makes the whole\nCommittee's existence\ntestable rather than\nassumed.\n\n"
       "SLO\nassembly < 500ms p99\nslice serve < 50ms p99",
       font_size=11, color="#495057", align="left")

d.save(OUT)
