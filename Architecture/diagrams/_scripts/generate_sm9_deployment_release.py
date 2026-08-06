import sys, os
sys.path.insert(0, os.path.dirname(__file__))
from sm_lib import Diagram, state_box, edge, transition, legend, caption

OUT = os.path.join(os.path.dirname(__file__), "..", "SM9_Deployment_Release.excalidraw")

d = Diagram("SM-9 — Deployment / Release  (review/R07_State_Machines.md §10 · Priority P2 · Owner: CI/CD)")

B = {}
B["BUILDING"]          = state_box(d, 500, 100, 220, 55, "BUILDING", "start")
B["BUILD_FAILED"]      = state_box(d, 800, 100, 220, 55, "BUILD_FAILED", "terminal")
B["GATED"]             = state_box(d, 500, 210, 220, 55, "GATED", "info", "artefact signed, SBOM produced")
B["GATE_FAILED"]       = state_box(d, 800, 210, 220, 55, "GATE_FAILED", "terminal", "tests / schema / determinism / PBO-DSR")
B["STAGED"]            = state_box(d, 500, 320, 220, 55, "STAGED", "normal")
B["STAGE_FAILED"]      = state_box(d, 800, 320, 220, 55, "STAGE_FAILED", "terminal", "integration / chaos test fail")
B["SHADOWING"]         = state_box(d, 220, 430, 220, 60, "SHADOWING", "warn", "behaviour-affecting change")
B["SHADOW_FAILED"]     = state_box(d, 60,  540, 200, 55, "SHADOW_FAILED", "terminal")
B["AWAITING_APPROVAL"] = state_box(d, 500, 540, 240, 55, "AWAITING_APPROVAL", "gate", "7-day timeout")
B["ABANDONED"]         = state_box(d, 800, 540, 220, 55, "ABANDONED", "terminal", "declined or 7-day timeout")
B["CANARY"]            = state_box(d, 500, 650, 220, 55, "CANARY", "warn")
B["ROLLING_BACK"]      = state_box(d, 800, 650, 220, 55, "ROLLING_BACK", "halt", "error rate / latency SLO / slippage breach")
B["ROLLED_BACK"]       = state_box(d, 800, 760, 220, 55, "ROLLED_BACK", "terminal")
B["ROLLED_OUT"]        = state_box(d, 500, 760, 220, 55, "ROLLED_OUT", "info", "canary window passed")
B["MONITORING"]        = state_box(d, 500, 870, 220, 55, "MONITORING", "warn", "24h heightened watch")
B["STABLE"]            = state_box(d, 220, 870, 220, 55, "STABLE", "terminal")

t = lambda a, b, label, **kw: transition(d, edge(B[a], kw.pop("s1", "bottom"), kw.pop("f1", 0.5)),
                                          edge(B[b], kw.pop("s2", "top"), kw.pop("f2", 0.5)), label, **kw)

t("BUILDING", "BUILD_FAILED", None, s1="right", f1=0.6, s2="left", f2=0.3)
t("BUILDING", "GATED", "artefact signed, SBOM produced")
t("GATED", "GATE_FAILED", "tests / schema compat / determinism / PBO-DSR", s1="right", f1=0.6, s2="left", f2=0.3)
t("GATED", "STAGED", None)
t("STAGED", "STAGE_FAILED", "integration or chaos test fail", s1="right", f1=0.6, s2="left", f2=0.3)
t("STAGED", "SHADOWING", "behaviour-affecting change", s1="left", f1=0.3, s2="right", f2=0.3)
t("STAGED", "AWAITING_APPROVAL", "infrastructure-only change")
t("SHADOWING", "SHADOW_FAILED", None, s1="left", f1=0.4, s2="right", f2=0.6)
t("SHADOWING", "AWAITING_APPROVAL", "shadow passed", s1="right", f1=0.7, s2="left", f2=0.15)
t("AWAITING_APPROVAL", "CANARY", "operator approves (typed confirmation)")
t("AWAITING_APPROVAL", "ABANDONED", "declined or 7-day timeout", s1="right", f1=0.6, s2="left", f2=0.3)
t("CANARY", "ROLLING_BACK", "auto-trigger: error rate / latency SLO / slippage breach",
  s1="right", f1=0.6, s2="left", f2=0.3)
t("CANARY", "ROLLED_OUT", "canary window passed")
t("ROLLING_BACK", "ROLLED_BACK", None)
t("ROLLED_OUT", "MONITORING", "24h heightened watch")
t("MONITORING", "ROLLING_BACK", "regression detected",
  s1="right", f1=0.7, s2="bottom", f2=0.7, points=[[0, 0], [80, 0], [80, -240], [0, -240]])
t("MONITORING", "STABLE", None, s1="left", f1=0.3, s2="right", f2=0.5)

legend(d, 40, 950, [
    ("start", "Build begins"),
    ("info", "Structural checkpoint"),
    ("normal", "Ordinary state"),
    ("warn", "Under observation — shadow, canary, or heightened watch"),
    ("gate", "Requires operator typed confirmation"),
    ("halt", "Auto-triggered rollback in progress"),
    ("terminal", "Machine exits here"),
])

caption(d, 430, 950, 760,
        "AWAITING_APPROVAL has a 7-day timeout to ABANDONED — a release sitting pending indefinitely is how a stale artefact gets promoted "
        "weeks later against a codebase that has moved on. Gates are enforced in CI/CD tooling (required status checks); a bypass requires "
        "a mechanically logged administrative override, not a fast-path button (contracts/14_Deployment_Pipeline.contract.md invariant 1). "
        "Full detail: review/R07_State_Machines.md §10.")

d.save(OUT)
