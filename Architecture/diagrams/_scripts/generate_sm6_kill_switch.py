import sys, os
sys.path.insert(0, os.path.dirname(__file__))
from sm_lib import Diagram, state_box, edge, transition, legend, caption

OUT = os.path.join(os.path.dirname(__file__), "..", "SM6_Kill_Switch.excalidraw")

d = Diagram("SM-6 — Kill Switch  (review/R07_State_Machines.md §7 · Priority P0 · Owner: Risk Engine · scopes: platform / account / symbol / strategy — most restrictive wins)")

B = {}
B["ACTIVE"]         = state_box(d, 460, 100, 240, 55, "ACTIVE", "start", "trading permitted")
B["UNREADABLE"]     = state_box(d, 60,  100, 260, 80, "UNREADABLE", "halt", "any tier unreachable — fails CLOSED, behaves exactly as TRIPPED — this is what B2 is missing")
B["TRIPPED_AUTO"]   = state_box(d, 800, 90,  260, 65, "TRIPPED_AUTO", "halt", "loss / drawdown / slippage / recon break / news blackout / dep loss")
B["TRIPPED_MANUAL"] = state_box(d, 800, 210, 260, 55, "TRIPPED_MANUAL", "halt", "operator or ANY component, no confirmation needed")
B["INVESTIGATING"]  = state_box(d, 800, 330, 260, 55, "INVESTIGATING", "warn", "operator acknowledges")
B["PENDING_CLEAR"]  = state_box(d, 800, 440, 260, 60, "PENDING_CLEAR", "gate", "cause identified, reconciliation clean")

t = lambda a, b, label, **kw: transition(d, edge(B[a], kw.pop("s1", "bottom"), kw.pop("f1", 0.5)),
                                          edge(B[b], kw.pop("s2", "top"), kw.pop("f2", 0.5)), label, **kw)

t("ACTIVE", "TRIPPED_AUTO", "daily loss / drawdown / slippage pattern / recon break / news blackout / dep loss",
  s1="right", f1=0.6, s2="left", f2=0.3)
t("ACTIVE", "TRIPPED_MANUAL", "operator or any component (deliberately unrestricted)",
  s1="right", f1=0.8, s2="left", f2=0.15,
  points=[[0, 0], [40, 0], [40, 130], [-40, 130]])
t("ACTIVE", "UNREADABLE", "any tier unreachable", s1="left", f1=0.3, s2="right", f2=0.3)
transition(d, edge(B["UNREADABLE"], "left", 0.7), (B["UNREADABLE"][0] - 40, B["UNREADABLE"][1] + 60),
           "still unreachable (self)", points=[[0, 0], [-40, 0], [-40, 30], [0, 30]])
t("UNREADABLE", "ACTIVE", "all tiers readable AND report active",
  s1="top", f1=0.7, s2="left", f2=0.7, points=[[0, 0], [0, -60], [400, -60], [400, 0]])
t("TRIPPED_AUTO", "INVESTIGATING", "operator acknowledges")
t("TRIPPED_MANUAL", "INVESTIGATING", None)
t("INVESTIGATING", "PENDING_CLEAR", "cause identified, reconciliation clean")
t("INVESTIGATING", "TRIPPED_AUTO", "cause not resolved",
  s1="right", f1=0.7, s2="bottom", f2=0.7, points=[[0, 0], [80, 0], [80, -270], [0, -270]])
t("PENDING_CLEAR", "ACTIVE", "dual control if auto-tripped, single operator if manual",
  s1="left", f1=0.3, s2="right", f2=0.7, points=[[0, 0], [-700, 0], [-700, -340], [-40, -340]])
t("PENDING_CLEAR", "TRIPPED_AUTO", "reconciliation not clean / second approver declines",
  s1="right", f1=0.6, s2="bottom", f2=0.85, points=[[0, 0], [80, 0], [80, -380], [0, -380]])

legend(d, 40, 560, [
    ("start", "Trading permitted"),
    ("halt", "Halted — new entries blocked, exits still permitted"),
    ("warn", "Being investigated"),
    ("gate", "Requires human authority to clear"),
])

caption(d, 40, 660, 1160,
        "Asymmetric authority, restated because it is the point: transition TO tripped is available to every component and every human, "
        "with no confirmation. Transition back to ACTIVE after an automatic trip requires two humans and a clean reconciliation. UNREADABLE "
        "is the state the source ADD is missing entirely — the switch lives only in Redis with no stated behaviour on Redis being unreachable, "
        "which means it fails open (B2). Here, unreadable behaves exactly as tripped: fail closed. Scopes (platform / account / symbol / "
        "strategy) are independent copies of this same machine; the effective state for any order is the most restrictive across all "
        "applicable scopes. Full detail: review/R07_State_Machines.md §7, and review/R11_Risk_Architecture.md.")

d.save(OUT)
