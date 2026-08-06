import sys, os
sys.path.insert(0, os.path.dirname(__file__))
from excalidraw_lib import Diagram, COLORS

OUT = os.path.join(os.path.dirname(__file__), "..", "19_Bounded_Context_Map.excalidraw")

MARGIN = 40
CANVAS_W = 1400
BAND_X = MARGIN
BAND_W = CANVAS_W - 2 * MARGIN
MAIN_W = 620
MAIN_X = BAND_X + 260
CENTER_X = MAIN_X + MAIN_W / 2

d = Diagram("19 — Bounded Context Map  (12 contexts, BC2/BC7 as read models, BC10/BC11 as gates)")

box_h = 58
gap = 34
y = 90

main_chain = [
    ("BC1", "Market Data", "blue"),
    ("BC3", "Feature Engineering", "blue"),
    ("BC4", "Market Intelligence", "cyan"),
    ("BC5", "Deliberation", "cyan"),
    ("BC12", "Portfolio Construction", "orange"),
    ("BC6", "Risk Authorisation", "red"),
    ("BC8", "Order Execution", "green"),
    ("BC9", "Learning", "purple"),
]

positions = {}
for i, (code, name, color) in enumerate(main_chain):
    d.labeled_box(MAIN_X, y, MAIN_W, box_h, f"{code}  {name}", None, color=color, title_size=15)
    positions[code] = (MAIN_X, y, MAIN_W, box_h)
    if i < len(main_chain) - 1:
        d.arrow(CENTER_X, y + box_h, CENTER_X, y + box_h + gap - 6, color=COLORS[color]["stroke"])
    y += box_h + gap

bottom_y = y - gap

# Side box: BC2 Reference Data, conformist upstream of everyone
bc2_x = BAND_X
bc2_y = 90
d.labeled_box(bc2_x, bc2_y, 200, 70, "BC2  Reference Data", "Conformist -> everyone", color="gray", title_size=13, subtitle_size=10)
for code in ["BC1", "BC3", "BC12", "BC6", "BC8"]:
    px, py, pw, ph = positions[code]
    d.arrow(bc2_x + 200, bc2_y + 35, px, py + ph / 2, color=COLORS["gray"]["stroke"], stroke_width=1, dashed=True)

# Side box: BC7 Portfolio, published read model into BC5, BC12, BC6
bc7_x = MAIN_X + MAIN_W + 60
bc7_y = positions["BC5"][1]
d.labeled_box(bc7_x, bc7_y, 220, 70, "BC7  Portfolio", "PortfolioSnapshot\n(published read model)", color="gray", title_size=13, subtitle_size=10)
for code in ["BC5", "BC12", "BC6"]:
    px, py, pw, ph = positions[code]
    d.arrow(bc7_x, bc7_y + 35, px + pw, py + ph / 2, color=COLORS["gray"]["stroke"], dashed=True)
d.arrow(positions["BC8"][0] + positions["BC8"][2], positions["BC8"][1] + positions["BC8"][3] / 2,
        bc7_x + 20, positions["BC9"][1] - 10, color=COLORS["green"]["stroke"], dashed=True)
d.text(bc7_x, bc7_y + 80, 220, "Fill events feed the ledger;\nthe ledger publishes back.", font_size=10, color="#868e96", align="left")

# Side box: BC6 -> BC12 RiskBudgetSnapshot (explicit callout, opposite direction of main flow)
rb_y = positions["BC12"][1] - 46
d.text(bc7_x, rb_y, 220, "BC6 -> BC12: RiskBudgetSnapshot\n(sync, 30ms fail-closed read model —\nnever the reverse)", font_size=10, color="#c92a2a", align="left")

# Bottom gates: BC10, BC11
gate_y = bottom_y + 40
d.labeled_box(MAIN_X, gate_y, MAIN_W / 2 - 10, 60, "BC10  Platform Operations", "mode gate -> every order-capable context", color="gray", title_size=12, subtitle_size=9)
d.labeled_box(MAIN_X + MAIN_W / 2 + 10, gate_y, MAIN_W / 2 - 10, 60, "BC11  Identity & Governance", "authz on every privileged action", color="gray", title_size=12, subtitle_size=9)
d.arrow(MAIN_X + MAIN_W / 4, gate_y, positions["BC6"][0] + 40, positions["BC6"][1] + positions["BC6"][3], color=COLORS["gray"]["stroke"], dashed=True)
d.arrow(MAIN_X + 3 * MAIN_W / 4, gate_y, positions["BC6"][0] + positions["BC6"][2] - 40, positions["BC6"][1] + positions["BC6"][3], color=COLORS["gray"]["stroke"], dashed=True)

# Legend
lx = BAND_X
ly = gate_y + 90
d.rect(lx, ly, 340, 130, stroke="#495057", bg="#f8f9fa")
d.text(lx + 12, ly + 10, 316, "Legend", font_size=13, color="#495057", align="left")
d.text(lx + 12, ly + 34, 316,
       "Solid arrow = main data-flow chain\n"
       "Dashed arrow = published read model\n"
       "(never a live dependency on internals)\n\n"
       "BC12 and BC5 both read; neither is\n"
       "ever read BACK by BC6 or BC8 — the\n"
       "acyclic property ADR-0012 established\n"
       "and ADR-0043 preserves.",
       font_size=11, color="#495057", align="left")

d.save(OUT)
