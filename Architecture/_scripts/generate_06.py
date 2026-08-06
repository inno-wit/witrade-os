import sys, os
sys.path.insert(0, os.path.dirname(__file__))
from excalidraw_lib import Diagram, COLORS

OUT = os.path.join(os.path.dirname(__file__), "..", "06_Market_Structure_Engine.excalidraw")

MARGIN = 40
CANVAS_W = 1160
BAND_X = MARGIN
BAND_W = CANVAS_W - 2 * MARGIN
CENTER_X = BAND_X + BAND_W / 2

d = Diagram("06 — Market Structure Engine (SMC)  (Quant Research Platform, sub-page 3 of 4)")

y = 90
pipe_w = 480
pipe_x = CENTER_X - pipe_w / 2

d.text(BAND_X, y, BAND_W, "INPUT", font_size=16, color=COLORS["blue"]["stroke"], align="left")
y += 30
d.labeled_box(pipe_x, y, pipe_w, 50, "OHLCV Bars (multi-timeframe)", "5m / 15m / 1H / 4H / D — from Feature Store",
              color="blue", title_size=13)
y += 50 + 35
d.arrow(CENTER_X, y - 29, CENTER_X, y - 6, color=COLORS["blue"]["stroke"])

stages = [
    ("Swing Detection", "swing_highs_lows() -- local pivot points"),
    ("BOS / CHoCH", "Break of Structure / Change of Character"),
    ("Liquidity", "Unswept swing-high/low clusters"),
    ("Order Blocks (OB)", "Last opposing candle before displacement"),
    ("Fair Value Gaps (FVG)", "3-candle imbalance, join_consecutive"),
    ("Mitigation", "Has price returned to fill OB/FVG?"),
    ("Structure Confidence", "0-10 composite score from\nconfluence count (see below)"),
]
bottom = d.pipeline(pipe_x, pipe_w, y, stages, color="yellow", item_h=55, gap=35,
                     title_size=14, subtitle_size=10)

api_y = bottom + 45
d.arrow(CENTER_X, bottom + 6, CENTER_X, api_y - 6, color=COLORS["yellow"]["stroke"])
d.labeled_box(pipe_x, api_y, pipe_w, 55, "Structure API",
              "get_structure(symbol, tf) -> {bos, choch, obs, fvgs, liquidity, confidence}",
              color="orange", title_size=13, subtitle_size=10)

# Confluence rule panel
note_x = pipe_x + pipe_w + 40
note_w = BAND_X + BAND_W - note_x
note_y = 90
note_h = api_y + 55 - note_y
d.rect(note_x, note_y, note_w, note_h, stroke=COLORS["cyan"]["stroke"], bg=COLORS["cyan"]["bg"])
d.text(note_x + 12, note_y + 10, note_w - 24, "Confluence Rule", font_size=15, color=COLORS["cyan"]["stroke"], align="left")
d.text(note_x + 12, note_y + 40, note_w - 24,
       "Structure Confidence rises\nwhen >= 2 of the following\nalign within 0.5% of price:\n\n"
       "1. Unmitigated FVG\n"
       "2. BOS/CHoCH confirmation\n"
       "3. Unswept liquidity\n"
       "4. Order block\n"
       "5. Grid level ($10/$40, XAUUSD)\n\n"
       "Top-down rule: never trade\nagainst Daily+4H combined\nbias (enforced by the SMC\nDesk in the Committee, page 08,\nnot by this engine).\n\n"
       "Ported from the existing\nTradeHub smc-analyzer /\nsmartmoneyconcepts pipeline.",
       font_size=11, color="#495057", align="left")

d.save(OUT)
