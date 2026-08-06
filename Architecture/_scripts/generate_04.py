import sys, os
sys.path.insert(0, os.path.dirname(__file__))
from excalidraw_lib import Diagram, COLORS

OUT = os.path.join(os.path.dirname(__file__), "..", "04_Regime_Engine.excalidraw")

MARGIN = 40
CANVAS_W = 1160
BAND_X = MARGIN
BAND_W = CANVAS_W - 2 * MARGIN
CENTER_X = BAND_X + BAND_W / 2

d = Diagram("04 — Regime Engine  (Quant Research Platform, sub-page 1 of 4)")

y = 90
pipe_w = 480
pipe_x = CENTER_X - pipe_w / 2

d.text(BAND_X, y, BAND_W, "INPUT", font_size=16, color=COLORS["blue"]["stroke"], align="left")
y += 30
d.labeled_box(pipe_x, y, pipe_w, 50, "Price Returns", "from Feature Store (page 03), per symbol",
              color="blue", title_size=14)
y += 50 + 35
d.arrow(CENTER_X, y - 29, CENTER_X, y - 6, color=COLORS["blue"]["stroke"])

stages = [
    ("GARCH", "Conditional volatility estimate\n(feeds regime + page 05 Vol Engine)"),
    ("Markov Switching Model", "Discrete regime states from\nreturn/vol dynamics"),
    ("Hidden Markov Model", "Latent state inference,\nsmoothed regime path"),
    ("Transition Matrix", "P(regime[t+1] | regime[t])\nupdated on rolling window"),
    ("Regime Probability", "Current-state probability vector\n(e.g. bull 0.62 / bear 0.11 / sideways 0.27)"),
]
bottom = d.pipeline(pipe_x, pipe_w, y, stages, color="yellow", item_h=60, gap=40,
                     title_size=15, subtitle_size=10)

api_y = bottom + 45
d.arrow(CENTER_X, bottom + 6, CENTER_X, api_y - 6, color=COLORS["yellow"]["stroke"])
d.labeled_box(pipe_x, api_y, pipe_w, 55, "Regime API", "get_regime(symbol, as_of) -> {state, probs, confidence}",
              color="orange", title_size=15, subtitle_size=11)

# Consumers panel
note_x = pipe_x + pipe_w + 40
note_w = BAND_X + BAND_W - note_x
note_y = 90
d.rect(note_x, note_y, note_w, api_y + 55 - note_y, stroke=COLORS["cyan"]["stroke"], bg=COLORS["cyan"]["bg"])
d.text(note_x + 12, note_y + 10, note_w - 24, "Consumers", font_size=15, color=COLORS["cyan"]["stroke"], align="left")
d.text(note_x + 12, note_y + 40, note_w - 24,
       "- Regime Desk (page 08)\n  primary consumer\n\n"
       "- Volatility Engine (page 05)\n  regime-conditional vol\n\n"
       "- Data Quality Engine (page 02)\n  regime-aware spread/\n  flash-crash thresholds\n\n"
       "- Risk Management (page 10)\n  regime-based exposure caps\n\n"
       "Every consumer reads\nconfidence, not just state --\nlow-confidence regime calls\nmust be discounted downstream.",
       font_size=11, color="#495057", align="left")

d.arrow(CENTER_X + pipe_w / 2 + 5, api_y + 27, note_x - 5, note_y + 150,
        color=COLORS["cyan"]["stroke"], stroke_width=1, dashed=True)

d.save(OUT)
