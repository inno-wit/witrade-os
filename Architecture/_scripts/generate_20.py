import sys, os
sys.path.insert(0, os.path.dirname(__file__))
from excalidraw_lib import Diagram, COLORS

OUT = os.path.join(os.path.dirname(__file__), "..", "20_Model_Registry.excalidraw")

MARGIN = 40
CANVAS_W = 1280
BAND_X = MARGIN
BAND_W = CANVAS_W - 2 * MARGIN
CENTER_X = BAND_X + BAND_W / 2
MAIN_W = 860
MAIN_X = BAND_X

d = Diagram("20 — Model Registry  (one SM-5 lifecycle, three artefact kinds)")

y = 90
n = 3
item_w = (MAIN_W - 60 - (n - 1) * 16) / n
d.section(MAIN_X, y, MAIN_W, 110, "ARTEFACT KINDS — one registry, one resolve(kind, slot, as_of)", color="blue")
d.row(MAIN_X + 30, y + 50, n, item_w, 45, 16,
      ["Supervised model / RL policy", "Desk prompt", "Desk / ranking weight"],
      ["Owner: BC4", "Owner: BC5", "Owner: BC5 + BC12"],
      color="blue", title_size=12, subtitle_size=10)
prev_bottom = y + 110
y = prev_bottom + 35
d.arrow(CENTER_X, prev_bottom, CENTER_X, y - 6, color=COLORS["cyan"]["stroke"])

sm_h = 230
d.section(MAIN_X, y, MAIN_W, sm_h, "SM-5 LIFECYCLE (review/R07_State_Machines.md §6, unmodified, canonical)", color="cyan")
stages = ["TRAINING", "CANDIDATE", "VALIDATING", "VALIDATED", "SHADOW", "SHADOW_PASSED", "CHAMPION"]
n2 = 4
item_w2 = (MAIN_W - 60 - (n2 - 1) * 12) / n2
d.row(MAIN_X + 30, y + 50, n2, item_w2, 50, 12, stages[0:4], [None] * 4, color="cyan", title_size=11)
d.row(MAIN_X + 30, y + 50 + 50 + 15, 3, item_w2, 50, 12, stages[4:7], [None] * 3, color="cyan", title_size=11)
d.text(MAIN_X + 30, y + 50 + 50 + 15 + 50 + 12, MAIN_W - 60,
       "CHAMPION -> CHALLENGER (superseded) -> ARCHIVED (retired)  |  CHAMPION -> ROLLED_BACK -> CHALLENGER (automatic, no approval needed)",
       font_size=11, color="#0c8599", align="left")
prev_bottom = y + sm_h
y = prev_bottom + 35
d.arrow(CENTER_X, prev_bottom, CENTER_X, y - 6, color=COLORS["purple"]["stroke"])

gov_h = 150
d.section(MAIN_X, y, MAIN_W, gov_h, "GOVERNANCE PER TRANSITION (new in this page)", color="purple")
d.row(MAIN_X + 30, y + 50, 2, (MAIN_W - 60 - 16) / 2, 80, 16,
      ["SHADOW_PASSED -> CHAMPION", "CHAMPION -> ROLLED_BACK"],
      ["Typed confirmation, audited.\nTier 0 needs a SECOND,\nseparately-timestamped\nRisk sign-off.",
       "Automatic. No human\nlatency permitted.\nCorrelated multi-slot\ndegradation = kill switch."],
      color="purple", title_size=13, subtitle_size=10)
bottom = y + gov_h

panel_x = MAIN_X + MAIN_W + 40
panel_w = BAND_W - MAIN_W - 40
panel_y = 90
panel_h = bottom - panel_y
d.rect(panel_x, panel_y, panel_w, panel_h, stroke=COLORS["gray"]["stroke"], bg=COLORS["gray"]["bg"])
d.text(panel_x + 14, panel_y + 12, panel_w - 28, "Why one registry", font_size=14, color=COLORS["gray"]["stroke"], align="left")
d.text(panel_x + 14, panel_y + 50, panel_w - 28,
       "Two registries can\ndrift: a fix to shadow-\ncomparison logic applied\nto one and forgotten\nin the other.\n\n"
       "resolve(...,as_of) is\npoint-in-time correct\nby construction — closes\nthe prompt look-ahead\nleak R19 §8 found.\n\n"
       "Backed by MLflow,\nwrapped so no vendor\ntype leaks into BC4/BC5,\nsame rule as the broker\nand LLM Gateway ACLs.\n\n"
       "SLO\nresolve() < 10ms p99",
       font_size=11, color="#495057", align="left")

d.save(OUT)
