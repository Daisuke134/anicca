# Manager Control Plane v0.1 — Capital, Policy, Durable Operations (P10-2/P10-3/P10-4)

**Status:** RESEARCH SPEC + synthetic tests only. No deployment or production authorization.
**2026-11-07**. This is NOT a second operational or curriculum SSOT.
Operational owner: docs/superpowers/specs/2026-09-25-life-manager-unified-ssot.md.
Curriculum owner: docs/research/manager/masterclass/2026-11-04-p04-causal/ROADMAP_STATUS_JA.md.
Predecessor read-only unit-economics specification: products/manager/docs/specs/2026-11-07-manager-p10-1-unit-economics-projection.md.

## 1. Core thesis
Manager = (what-if prediction service + bounded planner) → independently enforced policy → existing owned executor/outbox → independent provider readback/verifier → evidence-based feedback → budget and value reporting.
Do not treat model confidence, simulation output, approved budget, grant fixture or a provider "200 OK" as actual effect, external permission, accounting revenue or human welfare.

Three independent planes:

### Research / Prediction plane
Uses public or permissioned human datasets, experiment IDs, frozen splits, baseline models, uncertainty reports. Public material may not contain sensitive user profiles, copyrighted media or gated weights. BFM-01/02 and INT-02 incomplete until independently reproduced.

### Control / Trust plane
Determines actual host authority, least privilege, user consent, tenant, target, expiry/revocation, versioned policy, funding cap and STOP. Must be enforced *outside* any LLM. LLM can propose but cannot mint permissions, change ledger totals or override a denial.

### Evidence / Accounting plane
Existing effect/outbox/audit and external readback, plus read-only provider bill and revenue records, with bounded work_item_id joins. Do not create another authoritative accounting ledger, invent "received payment" from provider status or imply that P10 synthetic dollars are company revenue.

## 2. Dataflow

  (observations, sources, permissions)
               |
     What-if prediction + Candidate Planner
               |
       Risk & Licensing Gate
               |
       Budget & Consent Gate
               |
        Policy Decision Point
            /        \
         DENY       policy-eligible
            \        |
           NO_ACTION | privileged host confirms authority
                     |
                Outbox reserve
                     |
           Privileged effect dispatch
                     |
           PRESENT / ABSENT / UNKNOWN
                     |
       Independent provider readback
                     |
       Verified outcome / missing proof
                     |
      P10-1 Unit Economics Projection
                     |
      P10-2 Capital Review (PROPOSE ONLY)
                     |
      independent product + safety eval
                     |
       next bounded improvement cycle

Important: the *new* P10-2/3/4 educational code does not implement the privileged host or dispatch paths in this diagram.

## 3. Reuse map (verified against repository)
- products/manager/manager_core/authority.py: offline HMAC test Grant; expressly not live legal authority.
- products/manager/manager_core/state_machine.py: typed transition states including NO_ACTION, UNKNOWN_EFFECT, MEASUREMENT_MISSING.
- products/manager/manager_core/outbox.py: sqlite durable intent, reserve budget, no resend under uncertainty.
- products/manager/manager_core/reconcile.py: provider lookup, status PRESENT/ABSENT/UNKNOWN; do not infer permission from absence.
- products/manager/manager_core/verifier.py: provider receipt is not independent evidence of real human result; fixture-only P0.
- products/manager/manager_core/audit.py: SHA-256 linked restricted public trace; not cryptographically tamper-proof against privileged storage changes.
- runtime/contracts/common-record.schema.json: Job, RuntimeEvent, Effect, Receipt, OutboxItem, FinancialRecord (retain existing identity semantics).

**Do not replace** their owners with a new schema/ORM. Adapt to the existing record formats at a read-only interface first.

## 4. P10-2 capital controller contract
Input = proposal IDs, source-versioned cash/budget, reserved commitments, forecast distributions, study/experiment rights, expiry, quality/harm guardrails.
Output = sorted PROJECT_PROPOSAL with cost cap and **evidence_tier=ESTIMATED**, or NO_ACTION. A proposal is NEVER a grant.
Rules:
- cumulative allocated and committed spend + new reservations must not exceed a previously-authorized cap; enforce atomically in owned host storage, never check-then-write in separate transactions.
- keep liquidity reserve; budgeted vs billed vs allocated vs unallocated must reconcile by currency and period.
- cap attempts/tokens/time/cost per work, per tenant, and per experiment.
- measure incremental contribution margin separately from hypothesis-resolution and nonmonetary welfare.
- online exploration of actual users only with ethics, licenses, informed consent and relevant independent study approval.
- unlicensed/gated foundation weights not connected to commercial inference.

The synthetic demo enumerates <=16 candidate sets to prove deterministic, bounded budget planning with reserve and rights filter. It does not claim optimal real-world investment or license clearance, and its assumed values are not estimates drawn from company history.

## 5. P10-3 policy decision / enforcement contract
Required: principal identity, authenticated service credential, tenant, target ownership, intended effect_class, allowed purpose, consent state, permissions, scope, expiry, current authoritative revocation version, risk tier, policy version, requested monetary reservation, data classification, evidence references.
Responses: DENY(reason_codes), NO_ACTION, or ELIGIBLE_FOR_HOST_AUTHORIZATION. Only a privileged host can translate eligibility into actual permission.

- Treat all prompt, website, model prediction and tool output as untrusted; tool parameters validated against schema and allowlist by executor.
- No policy change, policy key, credential, model self-issuance or budget amplification from the model.
- Separate identity authentication and action authorization.
- Enforce cross-tenant isolation at storage and provider adapter boundaries.
- Use time-bound, revocable privileges, KMS/secret store and restricted egress; audit every decision while stripping payload PII.
- HIGH-impact money/trade/health/publish/applications need predeclared authority and, where required by law or provider, qualified human oversight. "No human loop" never supersedes legal and safety requirements.
- Opt-out and revocation must take effect on new execution; pending effects move to reconcile/stop.
- External policy engines (OPA, OpenFGA, Cedar) are optional until an unmet measured requirement demands them. Their public specs are references, not proof of integration.

## 6. P10-4 reliability and effect contract
- Workflow IDs stable across workers, activity IDs stable across bounded retries.
- Pure computations/read-only queries can retry with bounded exponential backoff plus jitter and deadline.
- Nonidempotent external side effects may NOT be repeated after DISPATCHING/UNKNOWN until a provider-supported dedupe key and independent reconciliation prove safety.
- Provider receipts are not readbacks. No downstream effect represented as success without independent observation and timestamp.
- Separate compensation/rollback as a new authorized effect; rollback cannot erase irreversible acts.
- At-most-once dispatch at adapter boundary is not the same as exactly-once real world effect. Document every failure mode.
- Durable event store, heartbeat and replay if needed; Temporal only when current runtime shows a measurable gap. Existing outbox is first choice.
- Alert on UNKNOWN_EFFECT backlog, policy bypass/denial, cost burn, complaint/harm, SLO burn rate; critical risk triggers STOP/NO_ACTION.

## 7. Failure table

| Situation | State | Safe default |
|---|---|---|
| HTTP read fails transiently | READ_FAILED | bounded read-only retry |
| External effect timed out | UNKNOWN_EFFECT | no resend; provider read-only reconciliation |
| Provider acknowledges send | PRESENT/receipt | independent verification needed |
| Readback missing | MEASUREMENT_MISSING | no success claim, monitor |
| Permission revoked | REJECTED/NO_ACTION | block any *new* effect; reconcile older |
| Provider bill != allocation | UNALLOCATED_REMAINS | show unmatched cost, no "verified margin" |
| SLO budget exhausted | OUT_OF_ERROR_BUDGET | pause rollout / reliability remediation |
| User complaint/harm | SAFETY_ESCALATION | safe stop, documented redress, professional assistance where required |

## 8. Minimal actionable metric contract

North Star business: externally verified *incremental* contribution margin per eligible work item, with comparator and uncertainty.
North Star beneficiary: independently observed selected user goal / welfare + harm (not dollar conversion).
Supporting: cost per verified success, model efficacy on held-out groups, human rescue rate, cash runway (true cash source).
Guardrails: unauthorized effect count = 0, consent bypass = 0, ledger unallocated %, unknown-effect age, service SLO, harm complaint and redress time.
Source cutoffs, denominators, currency, policy version, budget version, missingness and evidence tiers must be retained on dashboards.

## 9. Explicit future production acceptance gates
G0: legal rights and owner/tenant/consent/scope validated for selected workflow.
G1: repeatable read-only projection of real work items and provider bills.
G2: shadow only; independent outcomes/financial reconciliation.
G3: bounded canary under independently enforced admission, stop/revoke and real verification; high impact only with appropriate approvals.
G4: randomized or credible comparator uplift, user welfare and harm, unit economics.
G5: independent security, privacy, and third-party reproducibility review.
G6: reliable operations + reconciliation + protected minimum cash reserve before any self-funding claim.

**This PR only satisfies educational/prototype tests, not G0-G6.**

## 10. Scientific/engineering references
- FinOps AI https://www.finops.org/wg/finops-for-ai-overview/
- FinOps budgeting https://www.finops.org/framework/capabilities/budgeting/
- ISPOR Value of Information https://pmc.ncbi.nlm.nih.gov/articles/PMC7373630/
- Constrained contextual bandits https://jmlr.org/beta/papers/v26/24-0267.html
- OPA policy engine https://www.openpolicyagent.org/docs
- OpenFGA https://openfga.dev/
- AWS Cedar Verified Permissions https://docs.aws.amazon.com/verifiedpermissions/latest/userguide/
- OWASP Agentic Top 10 https://genai.owasp.org/resource/owasp-top-10-for-agentic-applications-for-2026/
- NIST AI RMF https://www.nist.gov/itl/ai-risk-management-framework
- OpenTelemetry GenAI https://opentelemetry.io/docs/specs/semconv/registry/attributes/gen-ai/
- Temporal error handling https://docs.temporal.io/develop/python/best-practices/error-handling
- Google SRE SLO https://sre.google/workbook/implementing-slos/
- AWS CloudTrail integrity https://docs.aws.amazon.com/awscloudtrail/latest/userguide/best-practices-security.html
