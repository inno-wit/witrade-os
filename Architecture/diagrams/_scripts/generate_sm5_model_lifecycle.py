import sys, os
sys.path.insert(0, os.path.dirname(__file__))
from sm_lib import Diagram, state_box, edge, transition, legend, caption

OUT = os.path.join(os.path.dirname(__file__), "..", "SM5_Model_Lifecycle.excalidraw")

d = Diagram("SM-5 — Model Lifecycle  (review/R07_State_Machines.md §6 · Priority P1 · Owner: Model Registry · also governs prompts + desk weights)")

B = {}
B["TRAINING"]        = state_box(d, 520, 100, 220, 55, "TRAINING", "start")
B["TRAINING_FAILED"] = state_box(d, 820, 100, 220, 55, "TRAINING_FAILED", "terminal")
B["CANDIDATE"]       = state_box(d, 520, 210, 220, 50, "CANDIDATE", "info", "snapshot id + commit + seed")
B["VALIDATING"]      = state_box(d, 520, 310, 220, 55, "VALIDATING", "normal", "PBO / DSR / walk-forward / leakage")
B["REJECTED"]        = state_box(d, 820, 310, 220, 55, "REJECTED", "terminal")
B["VALIDATED"]       = state_box(d, 520, 420, 220, 50, "VALIDATED", "info")
B["SHADOW"]          = state_box(d, 520, 520, 220, 70, "SHADOW", "warn", "min 24h AND min N decisions · self-loop while accumulating")
B["SHADOW_FAILED"]   = state_box(d, 820, 520, 220, 55, "SHADOW_FAILED", "terminal", "degrades on any dimension")
B["SHADOW_PASSED"]   = state_box(d, 520, 640, 220, 50, "SHADOW_PASSED", "info")
B["CHAMPION"]        = state_box(d, 520, 740, 220, 55, "CHAMPION", "gate", "operator promotes, typed confirmation")
B["ROLLED_BACK"]     = state_box(d, 820, 740, 220, 55, "ROLLED_BACK", "warn", "post-promotion degradation, pointer flip")
B["CHALLENGER"]      = state_box(d, 520, 850, 240, 70, "CHALLENGER", "normal", "keeps running for comparison · never acted on · self-loop")
B["ARCHIVED"]        = state_box(d, 860, 850, 220, 55, "ARCHIVED", "terminal", "retired after N days")

t = lambda a, b, label, **kw: transition(d, edge(B[a], kw.pop("s1", "bottom"), kw.pop("f1", 0.5)),
                                          edge(B[b], kw.pop("s2", "top"), kw.pop("f2", 0.5)), label, **kw)

t("TRAINING", "CANDIDATE", "training completed, registered")
t("TRAINING", "TRAINING_FAILED", None, s1="right", f1=0.6, s2="left", f2=0.3)
t("CANDIDATE", "VALIDATING", None)
t("VALIDATING", "REJECTED", "PBO fail / DSR fail / walk-forward fail / leakage detected",
  s1="right", f1=0.6, s2="left", f2=0.3)
t("VALIDATING", "VALIDATED", "all gates pass")
t("VALIDATED", "SHADOW", "deployed alongside champion")
transition(d, edge(B["SHADOW"], "right", 0.15), (B["SHADOW"][0] + B["SHADOW"][2] + 40, B["SHADOW"][1] - 10),
           "accumulating comparison (self)", points=[[0, 0], [40, 0], [40, -30], [0, -30]])
t("SHADOW", "SHADOW_FAILED", "degrades on any dimension", s1="right", f1=0.6, s2="left", f2=0.3)
t("SHADOW", "SHADOW_PASSED", None)
t("SHADOW_PASSED", "CHAMPION", "operator promotes (typed confirmation, audited)")
t("CHAMPION", "CHALLENGER", "superseded by a new champion")
t("CHAMPION", "ROLLED_BACK", "post-promotion degradation detected", s1="right", f1=0.6, s2="left", f2=0.3)
t("ROLLED_BACK", "CHALLENGER", "pointer flip, not a redeploy", s1="left", f1=0.4, s2="right", f2=0.7)
transition(d, edge(B["CHALLENGER"], "right", 0.15), (B["CHALLENGER"][0] + B["CHALLENGER"][2] + 40, B["CHALLENGER"][1] - 10),
           "keeps running (self)", points=[[0, 0], [40, 0], [40, -30], [0, -30]])
t("CHALLENGER", "CHAMPION", "promoted back (rollback path)",
  s1="left", f1=0.3, s2="left", f2=0.9, points=[[0, 0], [-260, 0], [-260, -300], [0, -300]])
t("CHALLENGER", "ARCHIVED", "retired after N days", s1="right", f1=0.6, s2="left", f2=0.4)

legend(d, 40, 940, [
    ("start", "Training run begins"),
    ("info", "Structural checkpoint"),
    ("normal", "Ordinary operating state"),
    ("warn", "Under evaluation or rolled back"),
    ("gate", "Requires operator promotion, audited"),
    ("terminal", "Machine exits here"),
])

caption(d, 430, 940, 760,
        "CHALLENGER is a running state, not storage — the previous champion keeps producing recorded-but-not-acted-on predictions, "
        "which is the only way to answer whether a promotion actually helped a month later. ROLLED_BACK is a pointer flip: both versions "
        "stay loaded in the inference service. Leakage detection is mechanical (no point_in_time_safe=false feature in the training set), "
        "never a review item. This machine governs prompts and desk weights too, not only ML models — a prompt change takes the identical "
        "path, which is what page 08's shadow-mode requirement actually implies. Full detail: review/R07_State_Machines.md §6.")

d.save(OUT)
