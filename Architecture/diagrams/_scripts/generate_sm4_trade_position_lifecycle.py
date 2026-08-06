import sys, os
sys.path.insert(0, os.path.dirname(__file__))
from sm_lib import Diagram, state_box, edge, transition, legend, caption

OUT = os.path.join(os.path.dirname(__file__), "..", "SM4_Trade_Position_Lifecycle.excalidraw")

d = Diagram("SM-4 — Trade / Position Lifecycle  (review/R07_State_Machines.md §5 · Priority P0 · Owner: OMS · absent from the source ADD entirely)")

B = {}
B["PENDING_ENTRY"]      = state_box(d, 500, 100, 240, 55, "PENDING_ENTRY", "start", "authorised, order in flight")
B["ABANDONED"]          = state_box(d, 800, 100, 220, 55, "ABANDONED", "terminal", "cancelled / expired / rejected")
B["OPEN"]               = state_box(d, 500, 210, 240, 55, "OPEN", "warn", "invariant: >60s here or in UNPROTECTED alerts")
B["ADOPTED_UNMANAGED"]  = state_box(d, 60,  210, 260, 65, "ADOPTED_UNMANAGED", "halt", "found by reconciliation, not opened here")
B["UNPROTECTED"]        = state_box(d, 800, 210, 240, 65, "UNPROTECTED", "halt", "broker-side stop missing")
B["EMERGENCY_EXIT"]     = state_box(d, 800, 330, 240, 55, "EMERGENCY_EXIT", "halt", "invalidation / risk breach / override")
B["MANAGED"]            = state_box(d, 460, 330, 260, 75, "MANAGED", "normal", "the only acceptable steady state · self-loop on stop/target/partial adjustments")
B["SCALING_OUT"]        = state_box(d, 60,  340, 240, 55, "SCALING_OUT", "normal", "partial exit in flight")
B["CLOSING"]            = state_box(d, 460, 470, 260, 55, "CLOSING", "normal", "exit authorised, in flight")
B["CLOSED"]             = state_box(d, 460, 590, 260, 55, "CLOSED", "info", "exit filled")
B["SETTLED"]            = state_box(d, 460, 700, 260, 55, "SETTLED", "info", "swaps, commissions, final P&L")
B["ATTRIBUTED"]         = state_box(d, 460, 810, 260, 55, "ATTRIBUTED", "terminal", "linked to decision_id, sent to Learning")

t = lambda a, b, label, **kw: transition(d, edge(B[a], kw.pop("s1", "bottom"), kw.pop("f1", 0.5)),
                                          edge(B[b], kw.pop("s2", "top"), kw.pop("f2", 0.5)), label, **kw)

t("PENDING_ENTRY", "OPEN", "entry filled")
t("PENDING_ENTRY", "ABANDONED", "cancelled / expired / rejected", s1="right", f1=0.6, s2="left", f2=0.3)
t("OPEN", "UNPROTECTED", "broker-side stop missing (sweep)", s1="right", f1=0.6, s2="left", f2=0.4)
t("UNPROTECTED", "OPEN", "stop restored", s1="left", f1=0.7, s2="right", f2=0.7)
t("UNPROTECTED", "EMERGENCY_EXIT", "stop cannot be restored")
t("OPEN", "MANAGED", "management plan attached", s1="bottom", f1=0.4, s2="right", f2=0.15)
t("OPEN", "ADOPTED_UNMANAGED", "discovered by reconciliation, not opened here",
  s1="left", f1=0.3, s2="right", f2=0.3)
transition(d, edge(B["MANAGED"], "bottom", 0.85), (B["MANAGED"][0] + B["MANAGED"][2] - 40, B["MANAGED"][1] + B["MANAGED"][2] * 0 + 120),
           "stop moved / target adjusted / partial taken (self)",
           points=[[0, 0], [40, 0], [40, -60], [0, -60]])
t("MANAGED", "SCALING_OUT", "partial exit in flight", s1="left", f1=0.3, s2="right", f2=0.4)
t("SCALING_OUT", "MANAGED", "partial filled, position remains", s1="right", f1=0.7, s2="left", f2=0.7)
t("SCALING_OUT", "CLOSING", "partial completed the position", s1="bottom", f1=0.5, s2="left", f2=0.2)
t("MANAGED", "CLOSING", "exit authorised and in flight")
t("MANAGED", "EMERGENCY_EXIT", "invalidation / risk breach / operator override",
  s1="right", f1=0.6, s2="left", f2=0.5)
t("EMERGENCY_EXIT", "CLOSING", "bypasses entry-blocking rules, market order",
  s1="bottom", f1=0.3, s2="right", f2=0.7)
t("ADOPTED_UNMANAGED", "MANAGED", "operator attaches a plan", s1="right", f1=0.5, s2="left", f2=0.15)
t("ADOPTED_UNMANAGED", "CLOSING", "operator closes it directly",
  s1="bottom", f1=0.6, s2="left", f2=0.15, points=[[0, 0], [0, 120], [400, 120]])
t("CLOSING", "CLOSED", "exit filled")
t("CLOSING", "MANAGED", "exit failed, position still open (alert, retry)",
  s1="left", f1=0.3, s2="bottom", f2=0.6, points=[[0, 0], [-60, 0], [-60, -140], [40, -140]])
t("CLOSED", "SETTLED", None)
t("SETTLED", "ATTRIBUTED", None)

legend(d, 40, 900, [
    ("start", "Authorisation issued, order in flight"),
    ("warn", "Open but not yet under active management"),
    ("normal", "The steady state — MANAGED is the only acceptable one"),
    ("halt", "Something is wrong: unprotected, adopted from outside, or an emergency exit"),
    ("info", "Post-exit checkpoint"),
    ("terminal", "Machine exits here"),
])

caption(d, 430, 900, 760,
        "Three states exist only because reality is messy: UNPROTECTED (an unbounded loss becomes possible — must be short-lived by "
        "construction), ADOPTED_UNMANAGED (a manual terminal trade or a post-restart survivor — never silently managed with default rules), "
        "EMERGENCY_EXIT (bypasses entry-blocking rules and uses market orders, distinct from a planned exit so TCA stays honest). Invariant: "
        "no position spends more than 60s in OPEN or UNPROTECTED without an alert. Full trigger table: review/R07_State_Machines.md §5.")

d.save(OUT)
