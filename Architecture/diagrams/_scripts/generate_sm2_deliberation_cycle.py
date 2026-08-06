import sys, os
sys.path.insert(0, os.path.dirname(__file__))
from sm_lib import Diagram, state_box, edge, transition, legend, caption

OUT = os.path.join(os.path.dirname(__file__), "..", "SM2_Deliberation_Cycle.excalidraw")

d = Diagram("SM-2 — Deliberation Cycle  (review/R07_State_Machines.md §3 · Priority P0 · Owner: Decision Saga · max dwell 12s)")

B = {}
B["TRIGGERED"]          = state_box(d, 460, 100, 220, 55, "TRIGGERED", "start")
B["ADMITTED"]           = state_box(d, 460, 210, 220, 55, "ADMITTED", "normal")
B["SUPPRESSED"]         = state_box(d, 760, 210, 200, 55, "SUPPRESSED", "terminal", "budget / cooldown / duplicate")
B["ASSEMBLING_EVIDENCE"]= state_box(d, 460, 320, 220, 55, "ASSEMBLING_EVIDENCE", "normal", "max dwell 1s")
B["ABORTED"]            = state_box(d, 760, 320, 200, 55, "ABORTED", "terminal", "critical staleness / engine down")
B["EVIDENCE_SEALED"]    = state_box(d, 460, 430, 220, 50, "EVIDENCE_SEALED", "info", "graph built + hashed")
B["POLLING_DESKS"]      = state_box(d, 460, 530, 220, 60, "POLLING_DESKS", "normal", "max dwell 8s · self-loop on each opinion")
B["QUORUM_FAILED"]      = state_box(d, 60,  530, 220, 60, "QUORUM_FAILED", "warn", "< 4 of 6 valid opinions at deadline")
B["NO_ACTION"]          = state_box(d, 60,  650, 220, 55, "NO_ACTION", "terminal")
B["DESKS_COMPLETE"]     = state_box(d, 460, 650, 220, 50, "DESKS_COMPLETE", "info", "quorum met at deadline / all responded")
B["RED_TEAM"]           = state_box(d, 460, 750, 220, 50, "RED_TEAM", "normal")
B["CONSENSUS"]          = state_box(d, 460, 850, 220, 55, "CONSENSUS", "normal")
B["DEADLOCKED"]         = state_box(d, 60,  850, 220, 55, "DEADLOCKED", "terminal", "dispersion > threshold")
B["PROPOSAL_DRAFTED"]   = state_box(d, 760, 850, 220, 55, "PROPOSAL_DRAFTED", "normal")
B["WITHDRAWN"]          = state_box(d, 1020, 750, 200, 55, "WITHDRAWN", "terminal", "risk preview hard-fail")
B["PROPOSAL_ISSUED"]    = state_box(d, 760, 960, 220, 55, "PROPOSAL_ISSUED", "normal", "max dwell 2s")
B["REJECTED"]           = state_box(d, 1020, 1060, 200, 55, "REJECTED", "terminal")
B["EXPIRED"]            = state_box(d, 760, 1160, 220, 55, "EXPIRED", "terminal", "valid_until passed")
B["AUTHORISED"]         = state_box(d, 460, 1060, 220, 55, "AUTHORISED", "gate", "signed token from Risk Engine")
B["EXECUTED"]           = state_box(d, 460, 1160, 220, 55, "EXECUTED", "terminal")
B["EXECUTION_FAILED"]   = state_box(d, 220, 1160, 220, 55, "EXECUTION_FAILED", "terminal", "broker rejects / unknown")

t = lambda a, b, label, **kw: transition(d, edge(B[a], kw.pop("s1", "bottom"), kw.pop("f1", 0.5)),
                                          edge(B[b], kw.pop("s2", "top"), kw.pop("f2", 0.5)), label, **kw)

t("TRIGGERED", "ADMITTED", "budget, rate limit, cooldown all pass")
t("TRIGGERED", "SUPPRESSED", "budget exceeded / cooldown / duplicate", s1="right", f1=0.7, s2="left", f2=0.3)
t("ADMITTED", "ASSEMBLING_EVIDENCE", None)
t("ASSEMBLING_EVIDENCE", "ABORTED", "required evidence critically stale / engine down", s1="right", f1=0.7, s2="left", f2=0.3)
t("ASSEMBLING_EVIDENCE", "EVIDENCE_SEALED", None)
t("EVIDENCE_SEALED", "POLLING_DESKS", None)
transition(d, edge(B["POLLING_DESKS"], "right", 0.85), (B["POLLING_DESKS"][0] + B["POLLING_DESKS"][2] + 40, B["POLLING_DESKS"][1] + 10),
           "desk opinion received (self)",
           points=[[0, 0], [40, 0], [40, -30], [0, -30]])
t("POLLING_DESKS", "QUORUM_FAILED", "< 4 of 6 valid at deadline", s1="left", f1=0.3, s2="right", f2=0.5)
t("QUORUM_FAILED", "NO_ACTION", None)
t("POLLING_DESKS", "DESKS_COMPLETE", "quorum met, all responded / deadline")
t("DESKS_COMPLETE", "RED_TEAM", None)
t("RED_TEAM", "CONSENSUS", None)
t("CONSENSUS", "DEADLOCKED", "dispersion > threshold", s1="left", f1=0.3, s2="right", f2=0.5)
t("CONSENSUS", "NO_ACTION", "pooled stance flat / conviction < floor",
  s1="left", f1=0.7, s2="top", f2=0.7,
  points=[[0, 0], [-350, 0], [-350, -180], [-90, -180]])
t("CONSENSUS", "PROPOSAL_DRAFTED", "actionable stance", s1="right", f1=0.7, s2="left", f2=0.3)
t("PROPOSAL_DRAFTED", "WITHDRAWN", "risk preview hard-fail", s1="right", f1=0.5, s2="bottom", f2=0.5)
t("PROPOSAL_DRAFTED", "PROPOSAL_ISSUED", "risk preview not hard-fail", s1="bottom", f1=0.4, s2="top", f2=0.6)
t("PROPOSAL_ISSUED", "REJECTED", "Risk Engine rejects", s1="right", f1=0.6, s2="top", f2=0.5)
t("PROPOSAL_ISSUED", "EXPIRED", "valid_until passed before authorisation", s1="bottom", f1=0.6, s2="right", f2=0.6)
t("PROPOSAL_ISSUED", "AUTHORISED", "Risk Engine approves (signed token)", s1="left", f1=0.4, s2="right", f2=0.4)
t("AUTHORISED", "EXECUTED", "order acknowledged", s1="bottom", f1=0.4, s2="top", f2=0.4)
t("AUTHORISED", "EXPIRED", "staleness gate at Execution", s1="right", f1=0.7, s2="left", f2=0.4)
t("AUTHORISED", "EXECUTION_FAILED", "broker rejected / unknown", s1="left", f1=0.4, s2="top", f2=0.5)

legend(d, 40, 1250, [
    ("start", "Trigger"),
    ("normal", "Ordinary state"),
    ("info", "Structural checkpoint (sealed / quorum met)"),
    ("gate", "Signed token issued — capital can now move"),
    ("warn", "Below quorum"),
    ("terminal", "One of ten terminal outcomes — every one produces a durable record"),
])

caption(d, 400, 1250, 780,
        "No path ends silently: SUPPRESSED, ABORTED, NO_ACTION (x2), DEADLOCKED, WITHDRAWN, REJECTED, EXPIRED, EXECUTED, EXECUTION_FAILED "
        "are all durably recorded, which is what makes deadlock rate and quorum-failure rate measurable (page 08 names deadlock rate as a health "
        "metric without the state to produce it). Illegal transitions and guards in full: review/R07_State_Machines.md §3.")

d.save(OUT)
