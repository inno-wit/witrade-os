import sys, os
sys.path.insert(0, os.path.dirname(__file__))
from excalidraw_lib import Diagram, COLORS

OUT = os.path.join(os.path.dirname(__file__), "..", "18_Portfolio_Construction.excalidraw")

MARGIN = 40
CANVAS_W = 1280
BAND_X = MARGIN
BAND_W = CANVAS_W - 2 * MARGIN
CENTER_X = BAND_X + BAND_W / 2
MAIN_W = 860
MAIN_X = BAND_X

d = Diagram("18 — Portfolio Construction Engine  (BC12, between Deliberation and Risk Authorisation)")

y = 90
d.labeled_box(MAIN_X, y, MAIN_W, 55, "Signals — TradeProposal stream (BC5 Deliberation)",
              "One or more unexpired, unauthorised candidates, across symbols", color="purple", title_size=15, subtitle_size=11)
prev_bottom = y + 55
y = prev_bottom + 35
d.arrow(CENTER_X, prev_bottom, CENTER_X, y - 6, color=COLORS["purple"]["stroke"])

pce_h = 300
d.section(MAIN_X, y, MAIN_W, pce_h, "PORTFOLIO CONSTRUCTION ENGINE (BC12) — ranks and allocates, never authorises", color="orange")
row_y = y + 50
n = 3
item_w = (MAIN_W - 60 - (n - 1) * 16) / n
d.row(MAIN_X + 30, row_y, n, item_w, 70, 16,
      ["CandidatePool", "Scoring", "Ranking + allocation"],
      ["Every unexpired,\nunauthorised proposal",
       "opportunity_score =\nexpected_return / expected_risk\n+ diversification(c)",
       "Top-down budget fill,\ndisplacement if gap > 25%"],
      color="orange", title_size=12, subtitle_size=9)
row2_y = row_y + 70 + 20
d.row(MAIN_X + 30, row2_y, n, item_w, 70, 16,
      ["ADMITTED", "DEFERRED", "REJECTED"],
      ["-> Risk Authorisation,\nwith allocated_risk_budget\n(cap only, never a raise)",
       "Outranked, re-enters\npool next tick or expires",
       "Fails a portfolio-level\nconstraint outright"],
      color="orange", title_size=12, subtitle_size=9)
plan_y = row2_y + 70 + 15
d.labeled_box(MAIN_X + 30, plan_y, MAIN_W - 60, 40, "PortfolioAllocationPlan",
              "logged in full, every non-admitted candidate carries an opportunity_cost_note",
              color="orange", title_size=12, subtitle_size=9)
prev_bottom = y + pce_h
y = prev_bottom + 35
d.arrow(CENTER_X, prev_bottom, CENTER_X, y - 6, color=COLORS["red"]["stroke"], stroke_width=3)
d.text(CENTER_X + 10, prev_bottom + 5, 260, "ADMITTED only — unchanged\nsizing/gate chain, R11 §3", font_size=11, color="#c92a2a", align="left")

d.labeled_box(MAIN_X, y, MAIN_W, 55, "Risk Authorisation (BC6) — sole authority, ADR-0011 unweakened",
              "Full independent re-evaluation of every admitted candidate", color="red", title_size=15, subtitle_size=11)
prev_bottom = y + 55
y = prev_bottom + 35
d.arrow(CENTER_X, prev_bottom, CENTER_X, y - 6, color=COLORS["green"]["stroke"])

d.labeled_box(MAIN_X, y, MAIN_W, 45, "Execution Platform (BC8)", "AuthorisedOrder consumed", color="green", title_size=15, subtitle_size=11)
bottom = y + 45

panel_x = MAIN_X + MAIN_W + 40
panel_w = BAND_W - MAIN_W - 40
panel_y = 90
panel_h = bottom - panel_y
d.rect(panel_x, panel_y, panel_w, panel_h, stroke=COLORS["gray"]["stroke"], bg=COLORS["gray"]["bg"])
d.text(panel_x + 14, panel_y + 12, panel_w - 28, "Read models (sync,\nfail-closed)", font_size=14, color=COLORS["gray"]["stroke"], align="left")
d.text(panel_x + 14, panel_y + 55, panel_w - 28,
       "PortfolioSnapshot\n(BC7)\n\n"
       "RiskBudgetSnapshot\n(BC6, 30ms fail-closed)\n\n"
       "Precedent nodes\n(EvidenceGraph, pg 17)\n\n"
       "Shared correlation /\ncluster model\n(co-owned with BC6,\nnever forked)\n\n"
       "FORBIDDEN\nCannot call BC6's\nauthorisation internals.\nCannot reach BC8.\nCannot touch a filled\nposition. No signing key.\n\n"
       "SLO\nrebalance() < 300ms p99",
       font_size=11, color="#495057", align="left")

d.save(OUT)
