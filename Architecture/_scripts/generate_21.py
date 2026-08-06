import sys, os
sys.path.insert(0, os.path.dirname(__file__))
from excalidraw_lib import Diagram, COLORS

OUT = os.path.join(os.path.dirname(__file__), "..", "21_Security_Architecture.excalidraw")

MARGIN = 40
CANVAS_W = 1320
BAND_X = MARGIN
BAND_W = CANVAS_W - 2 * MARGIN
MAIN_W = 760
MAIN_X = BAND_X

d = Diagram("21 — Security Architecture  (trust zones extended with T7-T11, pages 17-20)")

y = 90
zone_h = 90
zones = [
    ("DMZ", "Ingestion adapters, Text ACL, LLM Gateway", "blue"),
    ("CORE", "Quant, Feature, Committee, Decision, PCE, Model Registry, Learning", "cyan"),
    ("VAULT", "Risk Engine, Position Ledger, OMS, Reconciliation, Execution, MT5", "red"),
    ("OPS", "Dashboard, CLI, operator workstation", "gray"),
]
zone_boxes = {}
for name, desc, color in zones:
    d.labeled_box(MAIN_X, y, MAIN_W, zone_h, name, desc, color=color, title_size=16, subtitle_size=11)
    zone_boxes[name] = (MAIN_X, y, MAIN_W, zone_h)
    y += zone_h + 20

d.text(MAIN_X, y, MAIN_W,
       "Rule that carries the weight: only the Risk Engine may open a connection to the Execution\n"
       "Service (VAULT). BC12 Portfolio Construction and the Model Registry sit in CORE and are\n"
       "subject to the identical rule — neither can reach VAULT under any configuration.",
       font_size=12, color="#c92a2a", align="left")
y += 60

d.arrow(MAIN_X + 30, zone_boxes["CORE"][1] + zone_boxes["CORE"][3], MAIN_X + 30, zone_boxes["VAULT"][1], color="#495057", dashed=True)

# Threat panel
panel_x = MAIN_X + MAIN_W + 40
panel_w = BAND_W - MAIN_W - 40
panel_y = 90
panel_h = y - panel_y
d.rect(panel_x, panel_y, panel_w, panel_h, stroke=COLORS["orange"]["stroke"], bg=COLORS["orange"]["bg"])
d.text(panel_x + 14, panel_y + 12, panel_w - 28, "Threat model, T1-T11", font_size=15, color=COLORS["orange"]["stroke"], align="left")
d.text(panel_x + 14, panel_y + 48, panel_w - 28,
       "T1-T6  review/R15 §1\n(credential compromise,\nprompt injection, supply\nchain, insider error, data\npoisoning, DoS)\n\n"
       "T7  Evidence graph\npoisoning (page 17)\n\n"
       "T8  Unauthorised model /\nprompt promotion (page 20)\n\n"
       "T9  Event spoofing /\nreplay confusion\n\n"
       "T10  Schema / wire-\ncontract manipulation\n\n"
       "T11  Correlated model\ndrift exploited — the\nlargest single-incident\nloss category, mitigated\nby the platform-scope\nkill switch, no operator\nlatency permitted.",
       font_size=11, color="#495057", align="left")

d.save(OUT)
