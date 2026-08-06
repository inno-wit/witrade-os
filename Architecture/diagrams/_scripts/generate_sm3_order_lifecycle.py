import sys, os
sys.path.insert(0, os.path.dirname(__file__))
from sm_lib import Diagram, state_box, edge, transition, legend, caption

OUT = os.path.join(os.path.dirname(__file__), "..", "SM3_Order_Lifecycle.excalidraw")

d = Diagram("SM-3 — Order Lifecycle  (review/R07_State_Machines.md §4 · Priority P0 · Owner: Execution · one row per client_order_id)")

B = {}
B["CREATED"]          = state_box(d, 500, 100, 220, 55, "CREATED", "start")
B["REJECTED_LOCAL"]   = state_box(d, 800, 100, 220, 55, "REJECTED_LOCAL", "terminal", "token invalid / expired / no lease")
B["VALIDATED"]        = state_box(d, 500, 210, 220, 50, "VALIDATED", "info")
B["SUBMITTING"]       = state_box(d, 500, 310, 220, 55, "SUBMITTING", "normal")
B["REJECTED_BROKER"]  = state_box(d, 800, 310, 220, 55, "REJECTED_BROKER", "terminal", "broker rejects synchronously")
B["UNKNOWN"]          = state_box(d, 60,  400, 240, 90, "UNKNOWN", "halt", "no timeout to a safe assumption — resolves only by querying the broker")
B["SUBMITTED"]        = state_box(d, 500, 420, 220, 55, "SUBMITTED", "normal")
B["NOT_SENT"]         = state_box(d, 60,  560, 240, 55, "NOT_SENT", "terminal", "broker confirms it never existed")
B["WORKING"]          = state_box(d, 500, 530, 220, 55, "WORKING", "normal")
B["PARTIALLY_FILLED"] = state_box(d, 500, 640, 240, 65, "PARTIALLY_FILLED", "warn", "self-loop on each further partial")
B["CANCELLING"]       = state_box(d, 800, 640, 220, 55, "CANCELLING", "normal")
B["EXPIRED_TIF"]      = state_box(d, 1060, 530, 200, 55, "EXPIRED_TIF", "terminal", "time in force elapsed")
B["CLOSED_PARTIAL"]   = state_box(d, 500, 760, 240, 60, "CLOSED_PARTIAL", "terminal", "TIF elapsed, remainder unfilled")
B["CANCELLED"]        = state_box(d, 800, 760, 220, 55, "CANCELLED", "terminal")
B["FILLED"]           = state_box(d, 220, 760, 220, 55, "FILLED", "normal")
B["ANALYSED"]         = state_box(d, 500, 880, 240, 55, "ANALYSED", "terminal", "slippage decomposed")

t = lambda a, b, label, **kw: transition(d, edge(B[a], kw.pop("s1", "bottom"), kw.pop("f1", 0.5)),
                                          edge(B[b], kw.pop("s2", "top"), kw.pop("f2", 0.5)), label, **kw)

t("CREATED", "VALIDATED", "token valid, not expired, not consumed")
t("CREATED", "REJECTED_LOCAL", "invalid token / staleness gate / no lease", s1="right", f1=0.6, s2="left", f2=0.3)
t("VALIDATED", "SUBMITTING", None)
t("SUBMITTING", "SUBMITTED", "broker ack with broker_order_id")
t("SUBMITTING", "REJECTED_BROKER", "broker rejects synchronously", s1="right", f1=0.7, s2="left", f2=0.4)
t("SUBMITTING", "UNKNOWN", "timeout / connection lost", s1="left", f1=0.3, s2="right", f2=0.3)
transition(d, edge(B["UNKNOWN"], "right", 0.15), (B["UNKNOWN"][0] + B["UNKNOWN"][2] + 40, B["UNKNOWN"][1] - 10),
           "query fails, retry w/ backoff (self)", points=[[0, 0], [40, 0], [40, -30], [0, -30]])
t("UNKNOWN", "SUBMITTED", "query finds it working", s1="right", f1=0.5, s2="left", f2=0.5)
t("UNKNOWN", "PARTIALLY_FILLED", "query finds partial", s1="right", f1=0.8, s2="left", f2=0.3)
t("UNKNOWN", "NOT_SENT", "query confirms it does not exist", s1="bottom", f1=0.4, s2="top", f2=0.5)
t("SUBMITTED", "WORKING", "broker confirms resting")
t("SUBMITTED", "PARTIALLY_FILLED", None, s1="left", f1=0.4, s2="right", f2=0.4)
t("SUBMITTED", "EXPIRED_TIF", "TIF elapsed", s1="right", f1=0.7, s2="left", f2=0.3)
t("WORKING", "PARTIALLY_FILLED", None)
t("WORKING", "FILLED", "remainder unnecessary — fills in full",
  s1="left", f1=0.3, s2="top", f2=0.6, points=[[0, 0], [-260, 0], [-260, 200], [-30, 200]])
t("WORKING", "CANCELLING", "cancel requested", s1="right", f1=0.6, s2="left", f2=0.3)
t("WORKING", "EXPIRED_TIF", None, s1="right", f1=0.9, s2="left", f2=0.7)
transition(d, edge(B["PARTIALLY_FILLED"], "right", 0.15), (B["PARTIALLY_FILLED"][0] + B["PARTIALLY_FILLED"][2] + 40, B["PARTIALLY_FILLED"][1] - 10),
           "another partial (self)", points=[[0, 0], [40, 0], [40, -30], [0, -30]])
t("PARTIALLY_FILLED", "FILLED", "remainder fills", s1="left", f1=0.4, s2="right", f2=0.4)
t("PARTIALLY_FILLED", "CANCELLING", "cancel remainder", s1="right", f1=0.6, s2="left", f2=0.3)
t("PARTIALLY_FILLED", "CLOSED_PARTIAL", "TIF elapsed, remainder unfilled")
t("CANCELLING", "CANCELLED", None)
t("CANCELLING", "FILLED", "race: it filled before the cancel landed",
  s1="left", f1=0.3, s2="right", f2=0.9, points=[[0, 0], [-500, 0], [-500, 90], [-30, 90]])
t("CANCELLING", "UNKNOWN", "cancel timed out",
  s1="left", f1=0.7, s2="right", f2=0.9, points=[[0, 0], [-700, 0], [-700, -170], [190, -170]])
t("FILLED", "ANALYSED", None)
t("CANCELLED", "ANALYSED", None, s1="left", f1=0.4, s2="right", f2=0.7)
t("CLOSED_PARTIAL", "ANALYSED", None)
t("EXPIRED_TIF", "ANALYSED", None, s1="bottom", f1=0.3, s2="right", f2=0.8)
t("REJECTED_BROKER", "ANALYSED", None, s1="bottom", f1=0.3, s2="right", f2=0.9)

legend(d, 40, 970, [
    ("start", "Order created"),
    ("info", "Structural checkpoint"),
    ("normal", "Ordinary working state"),
    ("warn", "Partially filled — remainder still live"),
    ("halt", "Unknown outcome — never guessed, never blind-retried"),
    ("terminal", "Terminal, every one routes to ANALYSED except the four early rejects"),
])

caption(d, 430, 970, 760,
        "Four states the source ADD is missing: UNKNOWN (no timeout to a safe assumption — resolves only by broker query), "
        "NOT_SENT (the safe-retry resolution of UNKNOWN, distinct from REJECTED_BROKER), CLOSED_PARTIAL (the remainder's own terminal "
        "outcome, distinct from CANCELLED), and CANCELLING→FILLED (the cancel/fill race). Guessing at UNKNOWN is how duplicate positions "
        "get created. Full guard table: review/R07_State_Machines.md §4.")

d.save(OUT)
