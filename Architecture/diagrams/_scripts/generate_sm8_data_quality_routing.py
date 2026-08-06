import sys, os
sys.path.insert(0, os.path.dirname(__file__))
from sm_lib import Diagram, state_box, edge, transition, legend, caption

OUT = os.path.join(os.path.dirname(__file__), "..", "SM8_Data_Quality_Routing.excalidraw")

d = Diagram("SM-8 — Data Quality Routing  (review/R07_State_Machines.md §9 · Priority P1 · Owner: Quality Engine)")

B = {}
B["SCORING"]            = state_box(d, 460, 100, 240, 55, "SCORING", "start")
B["PASS"]               = state_box(d, 160, 210, 200, 55, "PASS", "terminal", "score >= 0.8")
B["FLAGGED"]            = state_box(d, 460, 210, 240, 60, "FLAGGED", "terminal", "0.5-0.8 — forwarded with a discount tag")
B["QUARANTINED"]        = state_box(d, 800, 210, 220, 55, "QUARANTINED", "warn", "score < 0.5")
B["UNDER_REVIEW"]       = state_box(d, 800, 320, 220, 55, "UNDER_REVIEW", "gate", "operator or weekly audit")
B["RELEASED"]           = state_box(d, 620, 430, 220, 60, "RELEASED", "info", "false positive, operator force-release, audited")
B["CONFIRMED_BAD"]      = state_box(d, 980, 430, 220, 55, "CONFIRMED_BAD", "halt", "genuinely bad")
B["BACKFILL_TRIGGERED"] = state_box(d, 620, 540, 220, 55, "BACKFILL_TRIGGERED", "terminal", "downstream feature recompute")
B["GAP_RECORDED"]       = state_box(d, 980, 540, 220, 55, "GAP_RECORDED", "terminal", "permanent gap, visible to every backtest")

t = lambda a, b, label, **kw: transition(d, edge(B[a], kw.pop("s1", "bottom"), kw.pop("f1", 0.5)),
                                          edge(B[b], kw.pop("s2", "top"), kw.pop("f2", 0.5)), label, **kw)

t("SCORING", "PASS", "score >= 0.8", s1="left", f1=0.3, s2="top", f2=0.7)
t("SCORING", "FLAGGED", "0.5 <= score < 0.8")
t("SCORING", "QUARANTINED", "score < 0.5", s1="right", f1=0.6, s2="top", f2=0.3)
t("QUARANTINED", "UNDER_REVIEW", "operator or weekly audit")
t("UNDER_REVIEW", "RELEASED", "false positive confirmed, force-release (audited)",
  s1="left", f1=0.3, s2="right", f2=0.3)
t("UNDER_REVIEW", "CONFIRMED_BAD", "genuinely bad", s1="bottom", f1=0.5, s2="top", f2=0.7)
transition(d, edge(B["UNDER_REVIEW"], "right", 0.15), (B["UNDER_REVIEW"][0] + B["UNDER_REVIEW"][2] + 40, B["UNDER_REVIEW"][1] - 10),
           "deferred (self)", points=[[0, 0], [40, 0], [40, -30], [0, -30]])
t("RELEASED", "BACKFILL_TRIGGERED", "released data requires downstream recompute")
t("CONFIRMED_BAD", "GAP_RECORDED", None)

legend(d, 40, 620, [
    ("start", "Dataset arrives to be scored"),
    ("terminal", "Machine exits here"),
    ("warn", "Quarantined, not yet reviewed"),
    ("gate", "Requires an operator or the scheduled audit"),
    ("info", "Release approved, recompute pending"),
    ("halt", "Confirmed bad, permanent record"),
])

caption(d, 430, 620, 760,
        "Two additions to page 02: RELEASED must trigger a downstream backfill — force-releasing quarantined data without recomputing "
        "the features derived from the gap leaves the Feature Store permanently inconsistent, and page 02 does not mention it. "
        "GAP_RECORDED makes gaps first-class — a backtest spanning a confirmed gap must know, because the alternative is silently "
        "interpolating over a real market event. Full detail: review/R07_State_Machines.md §9.")

d.save(OUT)
