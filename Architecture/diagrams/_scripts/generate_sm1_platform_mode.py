import sys, os
sys.path.insert(0, os.path.dirname(__file__))
from sm_lib import Diagram, state_box, edge, transition, legend, caption

OUT = os.path.join(os.path.dirname(__file__), "..", "SM1_Platform_Mode.excalidraw")

d = Diagram("SM-1 — Platform Mode  (review/R07_State_Machines.md §2 · Priority P0 · Owner: Platform Supervisor)")

B = {}
B["STARTING"]         = state_box(d, 300, 100, 220, 60, "STARTING", "start")
B["STANDBY"]          = state_box(d, 40,  230, 200, 60, "STANDBY", "normal", "leader lease held elsewhere")
B["RECONCILING"]      = state_box(d, 300, 230, 220, 60, "RECONCILING", "normal", "ledger rebuild + broker diff")
B["HALTED"]           = state_box(d, 980, 210, 200, 480, "HALTED", "halt")
B["AWAITING_CONFIRM"] = state_box(d, 620, 350, 240, 70, "AWAITING_CONFIRM", "gate", "prev shutdown was a crash")
B["NORMAL"]           = state_box(d, 300, 470, 240, 90, "NORMAL", "normal", "all actions permitted")
B["DEGRADED"]         = state_box(d, 600, 470, 220, 90, "DEGRADED", "warn", "no NEW entries; exits ok")
B["MAINTENANCE"]      = state_box(d, 300, 610, 240, 60, "MAINTENANCE", "normal", "operator, market closed only")
B["DRAINING"]         = state_box(d, 620, 610, 220, 60, "DRAINING", "normal", "finish in-flight, no new work")
B["STOPPED"]          = state_box(d, 300, 730, 240, 60, "STOPPED", "terminal")

# STARTING branches
transition(d, edge(B["STARTING"], "left", 0.2), edge(B["STANDBY"], "top", 0.7),
           "lease held elsewhere")
transition(d, edge(B["STARTING"], "bottom", 0.5), edge(B["RECONCILING"], "top", 0.5),
           "infra healthy, ledger rebuilt")
transition(d, edge(B["STARTING"], "right", 0.8), edge(B["HALTED"], "top", 0.1),
           "any Tier-0 dep unhealthy")

# STANDBY
transition(d, edge(B["STANDBY"], "right", 0.3), edge(B["RECONCILING"], "left", 0.3),
           "lease acquired (failover)")
transition(d, edge(B["STANDBY"], "bottom", 0.5), edge(B["STOPPED"], "left", 0.3),
           "shutdown", dashed=True)

# RECONCILING
transition(d, edge(B["RECONCILING"], "right", 0.5), edge(B["HALTED"], "top", 0.3),
           "critical break found")
transition(d, edge(B["RECONCILING"], "bottom", 0.35), edge(B["NORMAL"], "top", 0.3),
           "clean, prev shutdown clean")
transition(d, edge(B["RECONCILING"], "bottom", 0.8), edge(B["AWAITING_CONFIRM"], "left", 0.3),
           "clean, prev shutdown crash")

# AWAITING_CONFIRM
transition(d, edge(B["AWAITING_CONFIRM"], "bottom", 0.3), edge(B["NORMAL"], "right", 0.25),
           "operator typed confirmation")
transition(d, edge(B["AWAITING_CONFIRM"], "right", 0.5), edge(B["HALTED"], "left", 0.35),
           "declines / 4h timeout")

# NORMAL <-> DEGRADED (offset the two arrows so they don't overlap)
transition(d, edge(B["NORMAL"], "right", 0.35), edge(B["DEGRADED"], "left", 0.35),
           "soft dep lost / SLO breach / cost budget")
transition(d, edge(B["DEGRADED"], "left", 0.7), edge(B["NORMAL"], "right", 0.7),
           "condition cleared (auto, if no capital event)")
transition(d, edge(B["NORMAL"], "right", 0.15), edge(B["HALTED"], "left", 0.55),
           "kill switch / critical break / Tier-0 lost / drawdown limit")
transition(d, edge(B["NORMAL"], "bottom", 0.3), edge(B["MAINTENANCE"], "top", 0.5),
           "operator, market closed")
transition(d, edge(B["NORMAL"], "bottom", 0.75), edge(B["DRAINING"], "top", 0.2),
           "shutdown requested")

# DEGRADED
transition(d, edge(B["DEGRADED"], "right", 0.5), edge(B["HALTED"], "left", 0.7),
           "escalation")
transition(d, edge(B["DEGRADED"], "bottom", 0.6), edge(B["DRAINING"], "top", 0.7),
           "shutdown requested")

# HALTED, MAINTENANCE -> back to RECONCILING
transition(d, edge(B["HALTED"], "left", 0.15), edge(B["RECONCILING"], "right", 0.75),
           "operator clears (dual control if auto-tripped)",
           points=[[0, 0], [-560, 0], [-560, 210], [-460, 210]])
transition(d, edge(B["HALTED"], "bottom", 0.4), edge(B["DRAINING"], "right", 0.3),
           "shutdown requested")
transition(d, edge(B["MAINTENANCE"], "right", 0.9), edge(B["RECONCILING"], "bottom", 0.9),
           "maintenance complete", points=[[0, 0], [40, 0], [40, -450], [-70, -450]])

# DRAINING -> STOPPED
transition(d, edge(B["DRAINING"], "bottom", 0.5), edge(B["STOPPED"], "right", 0.7),
           "drain complete or 60s timeout")

legend(d, 40, 830, [
    ("start", "Entry point"),
    ("normal", "Ordinary operating state"),
    ("warn", "Degraded but not halted"),
    ("gate", "Requires human action to leave"),
    ("halt", "Halted — no new entries; exits still permitted"),
    ("terminal", "Machine exits here"),
])

caption(d, 40, 970, 1140,
        "Fail-safe rule: any component unable to read the current mode within 10s behaves as HALTED for entries, NORMAL for exits. "
        "The load-bearing row: exits are permitted in every non-STOPPED state, including HALTED (page 10's kill switch does not trap the platform in a position). "
        "Full permitted-action table by mode and every guard: review/R07_State_Machines.md §2.")

d.save(OUT)
