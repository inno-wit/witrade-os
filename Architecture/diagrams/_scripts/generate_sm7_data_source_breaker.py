import sys, os
sys.path.insert(0, os.path.dirname(__file__))
from sm_lib import Diagram, state_box, edge, transition, legend, caption

OUT = os.path.join(os.path.dirname(__file__), "..", "SM7_Data_Source_Breaker.excalidraw")

d = Diagram("SM-7 — Data Source / Circuit Breaker  (review/R07_State_Machines.md §8 · Priority P1 · Owner: Ingestion, per source)")

B = {}
B["CLOSED"]           = state_box(d, 460, 100, 240, 55, "CLOSED", "start", "healthy")
B["DEGRADED_QUALITY"] = state_box(d, 460, 210, 260, 75, "DEGRADED_QUALITY", "warn",
                                   "responding, but data fails quality checks — the addition; the ADD's breaker models availability only")
B["OPEN"]             = state_box(d, 780, 210, 220, 55, "OPEN", "halt", "3 consecutive failures")
B["HALF_OPEN"]        = state_box(d, 780, 320, 220, 55, "HALF_OPEN", "warn", "60s elapsed, probing")
B["BACKFILLING"]      = state_box(d, 780, 430, 220, 60, "BACKFILLING", "info", "fallback engaged / source recovered")

t = lambda a, b, label, **kw: transition(d, edge(B[a], kw.pop("s1", "bottom"), kw.pop("f1", 0.5)),
                                          edge(B[b], kw.pop("s2", "top"), kw.pop("f2", 0.5)), label, **kw)

transition(d, edge(B["CLOSED"], "left", 0.2), (B["CLOSED"][0] - 40, B["CLOSED"][1] - 10),
           "success, reset failure count (self)", points=[[0, 0], [-40, 0], [-40, -30], [0, -30]])
t("CLOSED", "OPEN", "3 consecutive failures", s1="right", f1=0.6, s2="left", f2=0.15)
t("CLOSED", "DEGRADED_QUALITY", "responding, but data fails quality checks")
t("DEGRADED_QUALITY", "CLOSED", "quality recovers", s1="left", f1=0.3, s2="left", f2=0.7)
t("DEGRADED_QUALITY", "OPEN", "quality collapses", s1="right", f1=0.6, s2="left", f2=0.7)
t("OPEN", "HALF_OPEN", "60s elapsed")
t("HALF_OPEN", "CLOSED", "3 consecutive probe successes",
  s1="left", f1=0.3, s2="right", f2=0.85, points=[[0, 0], [-620, 0], [-620, -180], [-40, -180]])
t("HALF_OPEN", "OPEN", "any probe fails (reset the 60s timer)", s1="top", f1=0.7, s2="bottom", f2=0.7)
t("OPEN", "BACKFILLING", "fallback engaged / source recovered", s1="bottom", f1=0.7, s2="top", f2=0.7)
t("BACKFILLING", "CLOSED", "gap filled, cross-source check passed",
  s1="left", f1=0.3, s2="bottom", f2=0.85, points=[[0, 0], [-700, 0], [-700, -300], [-40, -300]])
t("BACKFILLING", "OPEN", "backfill failed",
  s1="right", f1=0.6, s2="bottom", f2=0.85, points=[[0, 0], [60, 0], [60, -220], [0, -220]])

legend(d, 40, 540, [
    ("start", "Healthy"),
    ("warn", "Degraded — quality failing or probing after an open"),
    ("halt", "Open — source not in use"),
    ("info", "Filling the gap left by the outage"),
])

caption(d, 40, 630, 1140,
        "DEGRADED_QUALITY is the addition to page 01's breaker: a source returning bad data is more dangerous than one returning nothing, "
        "because a source that is up and subtly wrong will never trip an availability-only breaker. This connects page 01's circuit breaker "
        "to page 02's quality score, which the source ADD describes separately with nothing joining them. Full detail: "
        "review/R07_State_Machines.md §8.")

d.save(OUT)
