import sys, os
sys.path.insert(0, os.path.dirname(__file__))
from excalidraw_lib import Diagram, COLORS

OUT = os.path.join(os.path.dirname(__file__), "..", "09_Decision_Intelligence_Layer.excalidraw")

MARGIN = 40
CANVAS_W = 1200
BAND_X = MARGIN
BAND_W = CANVAS_W - 2 * MARGIN
CENTER_X = BAND_X + BAND_W / 2
pipe_w = 520
pipe_x = CENTER_X - pipe_w / 2

d = Diagram("09 — Decision Intelligence Layer  (Decision Intelligence Layer, sub-page 2 of 2)")

# Rule callout, top
rule_w = 700
rule_x = CENTER_X - rule_w / 2
d.rect(rule_x, 80, rule_w, 50, stroke=COLORS["red"]["stroke"], bg=COLORS["red"]["bg"])
d.text(rule_x + 10, 92, rule_w - 20, "RULE: The AI reasons. It does NOT calculate. Python calculates.",
       font_size=15, color=COLORS["red"]["stroke"], align="center")

y = 165
stages = [
    ("Quant Models", "Aggregated output of pages 04-07\n(Regime, Vol, SMC, ML/RL)", "yellow"),
    ("Evidence Graph", "Structures raw model outputs into\nlinked evidence nodes per symbol", "blue"),
    ("Committee Debate", "The 6-desk AI Investment Committee\n-- see page 08 for internals", "cyan"),
    ("Portfolio Impact", "How would this trade change current\nexposure, correlation, concentration?", "purple"),
    ("Risk Constraints", "Hard deterministic checks --\nsee page 10, cannot be reasoned around", "red"),
    ("Decision", "Approve / reject / defer,\nwith full evidence lineage", "orange"),
    ("Explanation", "Human-readable rationale for\ndashboard + permanent Journal", "green"),
]
bottom = d.pipeline(pipe_x, pipe_w, y, stages, item_h=62, gap=38, title_size=15, subtitle_size=10)

# Side panel: evidence lineage note
note_x = pipe_x + pipe_w + 40
note_w = BAND_X + BAND_W - note_x
note_y = 165
note_h = bottom - note_y
if note_w > 150:
    d.rect(note_x, note_y, note_w, note_h, stroke=COLORS["gray"]["stroke"], bg=COLORS["gray"]["bg"])
    d.text(note_x + 12, note_y + 10, note_w - 24, "Evidence Lineage",
           font_size=15, color=COLORS["gray"]["stroke"], align="left")
    d.text(note_x + 12, note_y + 40, note_w - 24,
           "Every Decision carries an\nunbroken chain back to the\nraw Feature Store inputs\nthat produced it:\n\n"
           "Decision\n  <- Committee reasoning\n  <- Desk citations\n  <- Quant Model outputs\n  <- Feature Store values\n  <- Validated bars\n\n"
           "This chain is what the\nExplanation stage renders,\nand what an operator or\nauditor can walk backward\nthrough after the fact.",
           font_size=11, color="#495057", align="left")

d.save(OUT)
