import sys, os
sys.path.insert(0, os.path.dirname(__file__))
from excalidraw_lib import Diagram, COLORS

OUT = os.path.join(os.path.dirname(__file__), "..", "14_Deployment_Pipeline.excalidraw")

MARGIN = 40
CANVAS_W = 1160
BAND_X = MARGIN
BAND_W = CANVAS_W - 2 * MARGIN
CENTER_X = BAND_X + BAND_W / 2
pipe_w = 500
pipe_x = CENTER_X - pipe_w / 2

d = Diagram("14 — Deployment Pipeline")

y = 100
stages = [
    ("Research Workstation", "Local dev, model research,\nbacktesting -- pages 04-07", "blue"),
    ("CI/CD (GitHub Actions)", "Lint, test, PBO/DSR validation\ngate on any model change", "green"),
    ("Cloud", "Container registry, staged\ndeploy, shadow-mode run\n(page 08 practice)", "purple"),
    ("VPS", "Windows VPS -- MT5 terminal +\nbridge process, page 11", "orange"),
    ("MT5", "Live broker connection", "red"),
    ("Dashboard", "Operator-facing, page 00\nUsers layer", "cyan"),
]
bottom = d.pipeline(pipe_x, pipe_w, y, stages, item_h=62, gap=36, title_size=14, subtitle_size=10)

# Side panel
note_x = pipe_x + pipe_w + 40
note_w = BAND_X + BAND_W - note_x
note_y = 100
note_h = bottom - note_y
if note_w > 150:
    d.rect(note_x, note_y, note_w, note_h, stroke=COLORS["gray"]["stroke"], bg=COLORS["gray"]["bg"])
    d.text(note_x + 12, note_y + 10, note_w - 24, "Promotion Gates", font_size=15, color=COLORS["gray"]["stroke"], align="left")
    d.text(note_x + 12, note_y + 40, note_w - 24,
           "Research -> CI/CD:\n  PBO / Deflated Sharpe gate\n  (page 07) -- no model or\n  Committee-weight change\n  skips this.\n\n"
           "CI/CD -> Cloud:\n  Automated tests pass +\n  shadow-mode run for any\n  Committee/LLM change\n  (page 08).\n\n"
           "Cloud -> VPS:\n  Manual operator approval\n  for anything touching live\n  order paths (execution-\n  safety skill pattern).\n\n"
           "VPS -> MT5:\n  ALLOW_TRADING gate,\n  paper by default.",
           font_size=11, color="#495057", align="left")

d.save(OUT)
