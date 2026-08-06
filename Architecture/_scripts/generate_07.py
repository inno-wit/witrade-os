import sys, os
sys.path.insert(0, os.path.dirname(__file__))
from excalidraw_lib import Diagram, COLORS

OUT = os.path.join(os.path.dirname(__file__), "..", "07_ML_RL_Model_Layer.excalidraw")

MARGIN = 40
CANVAS_W = 1160
BAND_X = MARGIN
BAND_W = CANVAS_W - 2 * MARGIN
CENTER_X = BAND_X + BAND_W / 2

d = Diagram("07 — ML / RL Model Layer  (Quant Research Platform, sub-page 4 of 4)")

y = 90
col_gap = 60
col_w = (BAND_W - col_gap) / 2
ml_x = BAND_X
rl_x = BAND_X + col_w + col_gap

d.text(ml_x, y, col_w, "ML MODELS  (supervised)", font_size=17, color=COLORS["yellow"]["stroke"], align="left")
d.text(rl_x, y, col_w, "RL MODELS  (policy / sizing agents)", font_size=17, color=COLORS["cyan"]["stroke"], align="left")
y += 35

ml_stages = [
    ("Feature Store + Labels", "Technical, Regime, SMC, Vol\n+ triple-barrier labels"),
    ("Training Pipeline", "Offline batch train\n(gradient boosting / NN)"),
    ("Validation", "Walk-forward, PBO / Deflated\nSharpe check before promotion"),
    ("Inference Service", "Low-latency scoring endpoint"),
]
ml_bottom = d.pipeline(ml_x, col_w, y, ml_stages, color="yellow", item_h=60, gap=30,
                        title_size=13, subtitle_size=10)

rl_stages = [
    ("Market Simulator", "Historical replay env,\ntransaction-cost aware"),
    ("Policy Training", "Reward = risk-adjusted PnL\n(Stable-Baselines3 / custom)"),
    ("Validation", "Out-of-sample rollout,\nsame PBO/DSR gate as ML"),
    ("Inference Service", "Policy inference endpoint\n(sizing / timing hints only)"),
]
rl_bottom = d.pipeline(rl_x, col_w, y, rl_stages, color="cyan", item_h=60, gap=30,
                        title_size=13, subtitle_size=10)

merge_y = max(ml_bottom, rl_bottom) + 55
d.arrow(ml_x + col_w / 2, ml_bottom + 6, CENTER_X, merge_y - 6, color=COLORS["yellow"]["stroke"], stroke_width=1)
d.arrow(rl_x + col_w / 2, rl_bottom + 6, CENTER_X, merge_y - 6, color=COLORS["cyan"]["stroke"], stroke_width=1)

registry_w = 480
d.labeled_box(CENTER_X - registry_w / 2, merge_y, registry_w, 60, "MLflow Model Registry",
              "Versioned models, experiment tracking, promotion gate", color="purple", title_size=15)

api_y = merge_y + 60 + 45
d.arrow(CENTER_X, merge_y + 60, CENTER_X, api_y - 6, color=COLORS["purple"]["stroke"])
api_w = 480
d.labeled_box(CENTER_X - api_w / 2, api_y, api_w, 55, "Model Prediction API",
              "predict(model_id, features) -> {prediction, confidence}",
              color="orange", title_size=14, subtitle_size=10)

d.save(OUT)
