# R15 — Security Architecture

**Deliverable:** 15
**Delta against:** the whole ADD. Security appears in zero of the 17 pages. This is the largest single omission and the primary reason the institutional readiness score is 3.5.
**Status:** Review v1.0

---

## 1. Threat model

Security work without a threat model produces controls that are expensive and irrelevant. Six threats, ranked by expected loss for **this** platform.

| # | Threat | Vector | Impact | Likelihood | Priority |
|---|---|---|---|---|---|
| T1 | **Broker credential compromise** | Windows VPS compromise, credential in a log, credential in a repo, phishing the operator | **Total account loss.** An attacker with MT5 credentials can liquidate or reverse the book in minutes | Medium | **P0** |
| T2 | **Prompt injection via news text** | Attacker-influencable text reaching an LLM that allocates capital (B5) | Manipulated position. Plausibly deniable, hard to detect after the fact | **Medium and rising.** Paid press-release syndication makes this cheap | **P0** |
| T3 | **Supply chain compromise** | A malicious or compromised Python dependency in a process that can send orders | Total account loss, plus persistence | Low-medium. Real precedent in the Python ecosystem | **P0** |
| T4 | **Insider / operator error under duress** | Panicked manual override, limit loosened during a drawdown, gate bypass | Large loss, procedurally invisible | **High.** The most likely of the six | **P1** |
| T5 | **Data poisoning** | A compromised or manipulated vendor feed | Systematically bad decisions, potentially over weeks | Low | P2 |
| T6 | **Denial of service** | Vendor outage, infrastructure failure, cost exhaustion | Missed opportunity, not loss, provided the platform fails closed | Medium | P2 |

**T1 and T3 share a single most-effective control: credential isolation.** If only one process can send an order, and that process runs a minimal, pinned, reviewed dependency set on an isolated network segment, both threats shrink dramatically.

**T4 deserves emphasis** because security work usually ignores it. For a single-operator quant platform, the most probable path to a large loss is not an attacker. It is the operator, under stress, disabling a control that was working. Dual control, typed confirmations, cooling periods and audited overrides are security controls, and they are the highest-value ones here.

---

## 2. Network architecture and trust zones

Four zones, per R02 §2. The rules between them are the primary control.

| Zone | Contains | Inbound | Outbound | Secrets |
|---|---|---|---|---|
| **DMZ** | Ingestion adapters, Text ACL, LLM Gateway | None from the internet. Only from CORE | Internet, allowlisted vendor endpoints only | Tier-1 vendor keys |
| **CORE** | Quant, Feature, Committee, Decision, Learning, platform services | From OPS via the gateway; from DMZ | To DMZ, to VAULT | Tier-2 internal |
| **VAULT** | Risk Engine, Position Ledger, OMS, Reconciliation, Execution, MT5 | **From CORE only, and only the Risk Engine may reach Execution** | To the broker endpoint only | **Tier-0 broker credentials, token signing key** |
| **OPS** | Dashboard, CLI, operator workstation | Operator, MFA | To CORE via the gateway; to VAULT only for privileged, audited operations | Session tokens |

### The rules that carry the weight

1. **Only the Execution Service holds broker credentials.** Enforced by secret scoping, not by convention. If any other process is compromised, it cannot trade.
2. **Only the Risk Engine may open a connection to the Execution Service.** Enforced at the network layer (firewall or mTLS peer identity), not in application code. An attacker in CORE cannot reach Execution even with valid application credentials.
3. **No inbound internet to CORE or VAULT.** All external data enters through DMZ adapters.
4. **All LLM egress via the gateway.** One allowlisted destination, one place to enforce budget and redaction.
5. **The MT5 VPS has no inbound access except a management path** restricted to the operator's IP with MFA, and preferably via a bastion rather than exposed RDP. An internet-exposed RDP port on a machine holding broker credentials is the single most likely realisation of T1.

---

## 3. Authentication and authorization

Specified in R04 §2 and §3. The security-critical elements restated:

| Control | Requirement |
|---|---|
| Human auth | OIDC with **MFA mandatory** for the `operator` role. No exceptions, no bypass for convenience |
| Service auth | mTLS, per-service certificates, 24h TTL, auto-rotated. **Not shared API keys** |
| Session lifetime | 15 minutes for privileged operations, re-auth required |
| Privileged operations | Typed confirmation, plus a second approver for: risk-limit loosening, clearing an auto-tripped kill switch, enabling live trading, gate override, quarantine force-release, ledger correction |
| Role separation | `researcher` tokens are **invalid in prod**. This is an attribute check, not a role check, and it is what prevents a research credential from becoming a trading credential |

**The asymmetry principle applied to authority:** stopping is always easier than starting. Any identity, human or service, may trip the kill switch with no confirmation. Clearing it after an automatic trip requires two humans and a clean reconciliation. Any friction added to stopping is a security defect.

---

## 4. Secrets

Specified in R04 §4. The controls that matter for T1:

1. **Tier-0 secrets exist on exactly one host and are readable by exactly one process.** Verified by an automated check, not assumed.
2. **No secret in an image, a build artefact, an environment variable visible in a process listing, a log, or a git object.** Enforced by a pre-commit secret scanner, a CI secret scanner including git history, and a log redaction filter that **fails loudly** rather than silently redacting.
3. **The approval-token signing key lives only in the Risk Engine.** If Execution could sign approvals, the entire authorisation chain is decorative. This is a design property, not a configuration.
4. **Rotation is rehearsed.** Broker credential rotation quarterly, executed as a drill, because a rotation procedure first attempted during a compromise will fail.
5. **Compromise runbook exists and is tested:** revoke at the broker first, halt the platform, rotate, reconcile, audit every action taken during the exposure window.

---

## 5. Prompt injection defence (T2)

The threat is concrete and the current architecture is fully exposed. Page 01 ingests article text, page 03 places it in the Macro category, page 08 gives the Macro Desk that category. Nothing sanitises it. A crafted press release is a path from a public, purchasable channel to a component that sizes positions.

### Defence in depth, five layers

| Layer | Control |
|---|---|
| **L1 Architectural (primary)** | **Raw text never reaches a desk.** The ACL (R03 §9) converts prose to typed, bounded features: a sentiment float, entity tags from a closed vocabulary, an event-type enum, a source tier. A desk's context contains numbers and enums. There is no code path from prose to a desk. This layer alone defeats the threat; the rest are defence in depth |
| **L2 Extraction isolation** | The extraction model call runs with no tools, no memory, no platform context, and a hard output schema. It cannot be induced to do anything because it can do nothing. Its output is schema-clamped and range-checked; a violation quarantines the article rather than passing defaults |
| **L3 Source tiering** | `source_tier` is looked up from configuration keyed by provider and publisher, never taken from the article's own claims. Low-tier sources are weighted down in the evidence graph regardless of content |
| **L4 Gateway inspection** | The LLM Gateway rejects any evidence payload containing instruction-like patterns, and raises P1. Should never fire after L1; if it does, L1 has a hole |
| **L5 Structural blast radius** | Even a fully successful injection can only move **one desk's** opinion. Quorum, pooling, the Red Team, the CRO Gate, and the deterministic Risk Engine all sit downstream. A single manipulated desk cannot produce a trade on its own. **This is a security property of the committee architecture that page 08 did not set out to provide but does** |

L5 is worth naming explicitly because it is an argument for the multi-desk design that has nothing to do with decision quality: it bounds the impact of any single compromised input channel.

---

## 6. Supply chain (T3)

The most under-defended threat in a Python trading system, because the dependency graph is large and one compromised package in the order-sending process is total loss.

| Control | Requirement |
|---|---|
| **Pinned, hashed dependencies** | Lock files with hashes. `pip install --require-hashes`. No unpinned transitive dependencies |
| **Minimal Execution dependency set** | The Execution Service and the MT5 bridge run the **smallest possible** dependency tree. Every package there is individually reviewed. This is the one place where "write it yourself" beats "add a library" |
| **SBOM per build** | Generated, stored, diffed. A new transitive dependency appearing without an explicit change is a review trigger |
| **Vulnerability scanning** | Dependencies and container images, on every build and on a nightly schedule for already-deployed artefacts |
| **No auto-update** | Dependency bumps are reviewed changes with a shadow run, not automated merges. Renovate/Dependabot open PRs; they never merge |
| **Artefact signing** | cosign on every image. Deployment verifies the signature. An unsigned image cannot be deployed |
| **Base image pinning** | By digest, not by tag |
| **Internal package index** | If any internal packages exist, an index with strict priority to prevent dependency confusion |
| **Cooling period** | A dependency version released less than 7 days ago is not deployed to prod, absent an active security fix. Most malicious package injections are discovered within days |

The cooling period is cheap and disproportionately effective against the actual pattern of Python supply-chain attacks.

---

## 7. Insider and operator controls (T4)

The highest-likelihood threat, and the one security architectures usually ignore.

| Control | Applies to |
|---|---|
| **Dual control** | Loosening a risk limit, clearing an auto-tripped kill switch, enabling live trading, overriding a CI gate, force-releasing quarantined data, correcting the ledger |
| **Cooling period** | A risk-limit loosening cannot take effect for N hours after approval. This defeats the impulsive change during a drawdown, which is the specific scenario |
| **Asymmetric friction** | Tightening a limit is immediate. Loosening requires the dry run, both approvers, and the cooling period |
| **Mandatory dry run** | Any limit change reports what would have changed over the last 30 days of proposals before it can be approved |
| **Everything audited** | Actor, timestamp, justification, before/after values, in the append-only hash-chained store |
| **No emergency bypass path** | The gate override is a deliberately slow, loud, separate workflow. Page 14's identified failure mode ("just this once during a fast market") is addressed by making "just this once" take twenty minutes and notify loudly |
| **Post-hoc review** | Every override creates a mandatory review item in the next weekly cycle |

**The design principle:** the platform should be **hardest to weaken exactly when the operator most wants to weaken it**, which is during a drawdown or a fast market. Every control above is calibrated to that.

---

## 8. Data protection

| Class | Examples | At rest | In transit | Retention |
|---|---|---|---|---|
| **Secret** | Broker credentials, API keys, signing keys | Encrypted, single-holder | mTLS | Rotated |
| **Confidential** | Positions, P&L, decision reasoning, model parameters | Encrypted volumes, encrypted MinIO buckets | mTLS | Per audit policy |
| **Internal** | Features, engine outputs, metrics | Encrypted at rest | mTLS internal | Per tier |
| **Public** | Vendor market data | Standard | TLS | Per licence |

**Note on vendor licensing:** Databento and Polygon data carry redistribution restrictions. Publishing raw vendor bars to a dashboard, an artefact, or any external surface is a licence matter as well as a security one. Worth an explicit check before the dashboard exposes raw data.

**Encryption:** disk-level encryption on every host. Postgres TDE is unnecessary at this scale; volume encryption plus access control is proportionate. MinIO server-side encryption on the `decisions` and `raw` buckets.

---

## 9. API security

| Control | Detail |
|---|---|
| Single ingress | Everything human-facing goes through the API Gateway. No service is directly reachable from OPS |
| Rate limiting | Per identity and per endpoint. A runaway dashboard poll must not degrade the platform |
| Input validation | Pydantic at every boundary. Reject, never coerce |
| Output filtering | The dashboard receives only what its role permits. An `auditor` sees decisions, not credentials or vendor keys |
| CORS | Explicit allowlist. No wildcards |
| CSRF | Required on every state-changing operation |
| Idempotency | Mutating API calls take an idempotency key, so a double-clicked "halt" is one halt |
| Audit before forward | Every mutating call is audited before it is executed, so a call that crashes mid-execution is still recorded |

---

## 10. Security testing

| Test | Frequency | Asserts |
|---|---|---|
| Secret scanning (repo + history + images) | Every build | No credential is committed |
| Dependency vulnerability scan | Every build + nightly on deployed artefacts | Known CVEs |
| Container scan | Every build | Base image and OS packages |
| **Prompt injection test suite** | Every build | A corpus of injection attempts against the ACL; every one must be neutralised to typed output |
| **Authorization matrix test** | Every build | Every role against every endpoint. Asserts `researcher` cannot trade, `auditor` cannot write |
| **Credential isolation test** | Every build | Assert no process other than Execution can construct a broker client |
| **Fail-closed chaos suite** | Every build | Kill each dependency, assert the platform refuses to trade rather than degrading open |
| Network policy test | Weekly | Assert CORE cannot reach the broker endpoint; assert OPS cannot reach VAULT except via the gateway |
| Penetration test | Annually, or before any material scope change | External review |
| DR and credential rotation drill | Quarterly | The procedures work |

The prompt-injection suite and the credential-isolation test are the two that are specific to this platform and would not appear in a generic security checklist. Both are cheap and both directly test a P0 threat.

---

## 11. Incident response, security-specific

Extends R12 §11. For a suspected compromise, the ordering differs from an operational incident:

```
1.  HALT. Trip the kill switch, platform scope.
2.  REVOKE at the broker directly (change the password at the broker,
    not through the platform). Assume platform-side revocation is
    compromised.
3.  ISOLATE. Disconnect the affected host from the network.
    Do not power it off: memory state is evidence.
4.  VERIFY positions at the broker via an independent channel
    (phone or the broker's web portal, not the platform).
5.  PRESERVE. Snapshot volumes, export the audit log to offline storage
    before anything is rebuilt.
6.  ASSESS. Use the audit log to determine the exposure window and
    every action taken within it.
7.  ROTATE every secret, not only the suspected one.
8.  REBUILD from a known-good artefact. Never clean in place.
9.  RECONCILE fully before resuming.
10. POST-MORTEM. Mandatory, written, with concrete control changes.
```

Steps 2 and 4 are the security-specific ones: during a suspected compromise, the platform's own view of the world cannot be trusted, so both revocation and verification must happen out of band.

---

## 12. Priority summary

| Priority | Controls |
|---|---|
| **P0, before any live capital** | Credential isolation to one process; the untrusted-text ACL; secrets out of git and out of logs; network segmentation with VAULT isolated; pinned and hashed dependencies; MFA on the operator role; the audit log |
| **P1, before scaling** | mTLS service identity; OPA authorization; dual control on the six privileged operations; artefact signing with deployment verification; the security test suite in CI; the compromise runbook |
| **P2** | Penetration test; internal package index; automated credential rotation; formal data classification enforcement |

---

## 13. Related

- `R00_Executive_Review.md` (B5)
- `R02_C4_Expansion.md` (§2 trust boundaries)
- `R03_Domain_Model_DDD.md` (§9 anti-corruption layers)
- `R04_Platform_Services.md` (PS-01, PS-02, PS-03)
- `R10_Committee_Architecture.md` (blast radius bounded by quorum and the CRO Gate)
- `R11_Risk_Architecture.md` (§10 operational risk)
