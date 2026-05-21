# Feature Specification: x402 Factory Skill (to-agents-skill)

**Feature Branch**: `001-x402-factory`
**Created**: 2026-02-24
**Status**: Draft

---

## User Scenarios & Testing *(mandatory)*

### User Story 1 — Operator triggers skill production (Priority: P1)

Anicca (on Mac Mini) receives a skill production request containing `skill_name`, `description`, and `usecase`. The factory reads `to-agents-learning.md`, generates a new Railway endpoint using the buddhist-counsel pattern, tests it with `awal x402 pay`, produces a SKILL.md, publishes to ClawHub, posts to Moltbook, updates `to-agents-learning.md`, and reports completion to Slack `#metrics`.

**Why this priority**: This is the core production loop. Every other story depends on it.

**Independent Test**: Provide `skill_name=emotion-detector` → after factory runs, verify endpoint returns 200 on `awal x402 pay`, ClawHub listing exists, Moltbook post published, `to-agents-learning.md` has new entry, `#metrics` has completion report.

**Acceptance Scenarios**:

1. **Given** `skill_name + description + usecase` input, **When** factory runs, **Then** Railway endpoint at `/api/x402/<skill_name>` returns 402 on unauthenticated POST and 200 OK on `awal x402 pay`.
2. **Given** production completed, **When** `clawhub search <skill_name>` is run, **Then** skill appears in results.
3. **Given** production completed, **When** Moltbook feed is checked, **Then** a promotional post for the skill exists.
4. **Given** production completed, **When** `to-agents-learning.md` is read, **Then** a new entry exists with learnings from this run.
5. **Given** production completed, **When** Slack `#metrics` is checked, **Then** a report exists with endpoint URL + ClawHub ID + Moltbook post ID.

---

### User Story 2 — Factory proposes next skill from catalog (Priority: P2)

Anicca reads the skill catalog (10 skills in x402-nudge-api-spec.md), identifies the next unbuilt skill, and sends an approval proposal to Slack `#metrics`. Daisuke approves (✅) or rejects (❌). Only after approval does the factory enter production mode.

**Why this priority**: Approval gate prevents unsupervised production. Enables autonomous scheduling.

**Independent Test**: Run factory in `discover` mode → verify exactly one Slack proposal appears in `#metrics`. No endpoint created. Approve with ✅ → factory builds.

**Acceptance Scenarios**:

1. **Given** factory runs in `discover` mode, **When** execution completes, **Then** a Slack message in `#metrics` proposes one skill with name + description + rationale.
2. **Given** a proposal exists, **When** Daisuke reacts ✅, **Then** factory enters production mode (Story 1).
3. **Given** a proposal exists, **When** Daisuke reacts ❌, **Then** factory logs rejection and proposes the next skill in catalog on next run.
4. **Given** no response in 48h, **Then** proposal silently expires; factory proposes next skill on next scheduled run.

---

### User Story 3 — Factory improves underperforming skills (Priority: P3)

Weekly, the factory checks call counts for all live skills. Any skill with a 7-day moving average declining more than 20% vs the prior week triggers a diagnosis. Factory proposes one specific improvement (prompt change or SKILL.md update) to `#metrics`.

**Why this priority**: Prevents revenue decay. Closes the improvement loop.

**Independent Test**: Inject a mock skill with 0 calls for 7 days → factory identifies it, sends an improvement proposal to `#metrics` within the same run.

**Acceptance Scenarios**:

1. **Given** a skill's call count declines >20% over 7 days, **When** factory runs in `measure` mode, **Then** a Slack message in `#metrics` names the skill and proposes one change.
2. **Given** an improvement is approved, **When** factory applies it, **Then** endpoint is redeployed and ClawHub SKILL.md is updated.
3. **Given** a skill has 0 calls for 14 days after an improvement attempt, **Then** factory proposes deprecation to `#metrics`.

---

### Edge Cases

- What happens when `awal x402 pay` returns non-200? → Factory halts immediately. No ClawHub publish, no Moltbook post. Reports failure to `#metrics`. Never marks as complete without live 200 OK.
- What happens when the same `skill_name` endpoint already exists? → Factory skips creation and reports "already exists" to `#metrics`.
- What happens when ClawHub publish fails? → Factory retries once, then halts and reports error to `#metrics`.
- What happens when `to-agents-learning.md` write fails? → Factory logs a warning but does not block completion reporting.
- What happens if Daisuke does not respond to a proposal in 48h? → Proposal expires silently; next run proposes the next catalog skill.

---

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: Factory MUST accept `skill_name`, `description`, and `usecase` as input parameters.
- **FR-002**: Factory MUST read `to-agents-learning.md` before generating any code to extract the current best-practice pattern.
- **FR-003**: Factory MUST reuse the buddhist-counsel endpoint pattern verbatim: CORS → express.json → x402 middleware order, ExactEvmScheme, declareDiscoveryExtension, syncFacilitatorOnStart=false.
- **FR-004**: Factory MUST run `awal x402 pay` against the new endpoint and confirm 200 OK before any publish step. Zero tolerance for publishing untested endpoints.
- **FR-005**: Factory MUST generate a SKILL.md using the template in `x402-nudge-api-spec.md` (ehipassiko/karuna principles, endpoint URL, input/output schema, price, SAFE-T note).
- **FR-006**: Factory MUST publish to ClawHub via `clawhub publish` and capture the resulting skill ID.
- **FR-007**: Factory MUST post a Moltbook promotional post (via moltbook-interact skill) after successful ClawHub publish.
- **FR-008**: Factory MUST append a new learning entry to `to-agents-learning.md` after production completes.
- **FR-009**: Factory MUST send a completion report to Slack `#metrics` (C091G3PKHL2) with endpoint URL, ClawHub ID, and Moltbook post ID.
- **FR-010**: In `discover` mode, Factory MUST send a proposal to Slack `#metrics` and wait for explicit approval before building. Building without approval is forbidden.
- **FR-011**: In `measure` mode, Factory MUST check weekly call counts and report skills with declining performance (>20% MA drop) to `#metrics` with one proposed improvement.
- **FR-012**: Factory MUST be installed as an OpenClaw skill on Mac Mini at `/Users/anicca/.openclaw/skills/to-agents-skill/SKILL.md`.
- **FR-013**: Factory MUST run on a Cron job (`0 1 * * *` UTC = 10:00 JST daily).

### Key Entities

- **Skill Request**: `{ skill_name, description, usecase }` — input that initiates production.
- **x402 Endpoint**: Railway Express route at `/api/x402/<skill_name>` — the deployed revenue artifact.
- **SKILL.md**: OpenClaw/ClawHub skill file — how other agents discover and call the endpoint.
- **Learning Entry**: Row appended to `to-agents-learning.md` — makes the factory smarter over time.
- **Proposal Message**: Slack `#metrics` message — the human approval gate for autonomous mode.
- **Completion Report**: Slack `#metrics` message — confirms all artifacts exist with their IDs.

---

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A new skill goes from request to live ClawHub listing in a single uninterrupted factory run with no manual steps beyond the approval gate.
- **SC-002**: Every produced endpoint passes `awal x402 pay` (200 OK) before ClawHub publish — 100% pass rate required.
- **SC-003**: Factory produces at least 1 new live skill per week when run on schedule.
- **SC-004**: After 4 weeks of operation, at least 3 skills from the catalog are live on ClawHub with Moltbook posts.
- **SC-005**: Weekly measurement loop identifies and reports underperforming skills within 24h of the scheduled run.
- **SC-006**: `to-agents-learning.md` grows by at least 1 new entry per production run.

---

## Assumptions

- `buddhist-counsel` endpoint is already live on Railway mainnet (eip155:8453) and is the authoritative production pattern.
- Mac Mini has `awal`, `clawhub`, Node.js, and the `moltbook-interact` skill available at runtime.
- Railway staging is used for endpoint testing; mainnet environment is updated after 200 OK confirmation.
- Daisuke approves/rejects proposals via Slack emoji reaction (✅ / ❌) on the `#metrics` proposal message.
- The skill catalog (10 skills) in `x402-nudge-api-spec.md` is the authoritative priority list.

---

## Boundaries

### In Scope

- `to-agents-skill` SKILL.md (OpenClaw skill for Mac Mini)
- Cron job entry in `/Users/anicca/.openclaw/cron/jobs.json`
- Production flow: input → endpoint → `awal` test → SKILL.md → ClawHub → Moltbook → learning → `#metrics`
- Discover mode: catalog scan → Slack proposal → approval gate
- Measure mode: weekly call count → improvement proposal to `#metrics`

### Out of Scope

- Automatic approval without Daisuke's explicit ✅
- Producing skills that are not x402 pay-per-request endpoints
- iOS app changes
- Database schema changes
- Any npm package not already in `apps/api/package.json`
