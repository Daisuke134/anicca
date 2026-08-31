# Lancers General Money Agent Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development
> (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use
> checkbox (`- [ ]`) syntax for tracking.

**Goal:** Prove that the resident provider-neutral Gig agent can restore Lancers from retained private
state, ground first-trust profile evidence and submit one review-bearing non-negative-net application
with an official proposal ID and replay duplicate zero, without a Lancers-specific brain or scheduler.

**Architecture:** Reuse the existing Portfolio CEO, Luna/Terra judgment, `market_form_operator.py`,
provider adapter records, resource-scoped effect fences, common project worker, independent verifier,
WorkEvents, Telegram outbox and money truth. Add only the common inventory primitive proven by Upwork
and Lancers plus a thin Lancers manifest. Production advances one official receipt at a time; buyer
waiting never blocks another job or market.

**Tech Stack:** Python 3.14 runtime-compatible standard library, existing Codex agent runner,
CloakBrowser/browser-harness ACI, JSON Schema, SQLite, pytest with plugin autoload disabled, immutable
Gig release and launchd-safe control plane.

**Specs:**
`docs/superpowers/specs/2026-08-22-mr-bot-gig-economy-loop-design.md` and
`docs/superpowers/specs/2026-08-13-lancers-20k-net-mrr-design.md` §18.

## Global Constraints

- The current execution cursor is Lancers, while Upwork and Coconala continue independently.
- Do not add a market scheduler, planner, proposal brain, inbox brain, project/QA system, Telegram
  transport, funnel/money ledger or learning agent.
- Luna/Terra decides feasibility, candidate lifetime EV, profile strategy, proposal content and browser
  actions from natural-language evidence. Deterministic code handles machine fields, arithmetic,
  reservations, dedupe, effect/readback and accounting only.
- A missing named Skill or provider adapter never blocks feasible general model-and-tool work.
- Provider-specific production additions stay within three files and about 300 LOC. Stop and extract a
  measured common primitive if that ceiling would be crossed.
- Use `~/.local/share/anicca/credentials.json` only through existing private runtime/login paths. Never
  place credential values, browser storage, customer material or PII in prompts, logs, fixtures,
  Telegram or Git.
- Never delete or move browser profiles, customer projects, ledgers, receipts or immutable releases.
- The first Lancers inventory slice has marketplace effects zero. Every later mutation requires
  authorization → immutable intent → presend reconcile → at most one effect → official readback →
  canonical receipt; replay must produce duplicate effect zero.
- Absolute cheapest is not the objective. The first-job target must carry an official principal review,
  remain non-negative after actual fee and execution cost, and have positive long-run utility.
- Lancers task work that does not affect the principal profile evaluation is not a reputation-bootstrap
  substitute.
- `Pending`, `Available`, estimated balance and application price are not cash. Only official payout
  `received`, joined to fee/cost/refund evidence, enters verified revenue.
- Preserve the existing common-policy work in Tasks 63 and 64 of
  `docs/superpowers/plans/2026-08-22-mr-bot-gig-economy-loop.md`; this plan supplies the Lancers
  vertical proof rather than duplicating those tasks.

---

### Task 1: Add the common authenticated market-inventory contract

**Files:**
- Create: `skills/_shared/marketplace-core/schemas/market-inventory.schema.json`
- Create: `skills/earn/gig/scripts/market_inventory.py`
- Test: `skills/earn/gig/tests/test_market_inventory.py`

**Interfaces:**
- Consumes: local `cdp_base`, provider name, official surface URLs and existing `agent_runner.py`.
- Produces: `collect_inventory(provider, cdp_base, surfaces, evidence_root) -> MarketInventory`.
- `MarketInventory` contains one account identity hash, login state, opportunities, messages,
  applications/listings, active work, earnings/payout state, official URLs, `observed_at`,
  `source_complete`, `marketplace_effect_count` and `evidence_hash`.

- [ ] **Step 1: Write the failing contract tests**

```python
def inventory(**overrides):
    value = {
        "provider": "lancers", "account_identity_hash": "a" * 64,
        "login_state": "authenticated", "opportunities": (), "messages": (),
        "applications": (), "active_work": (), "earnings": (),
        "official_urls": ("https://www.lancers.jp/mypage",),
        "observed_at": "2026-08-24T00:00:00Z", "source_complete": True,
        "marketplace_effect_count": 0, "evidence_hash": "b" * 64,
    }
    value.update(overrides)
    return MarketInventory(**value)

def test_inventory_requires_complete_zero_effect_authenticated_evidence():
    value = inventory()
    assert value.marketplace_effect_count == 0

def test_inventory_rejects_effect_or_incomplete_source():
    with pytest.raises(ContractViolation):
        inventory(marketplace_effect_count=1)
    with pytest.raises(ContractViolation):
        inventory(source_complete=False)

def test_inventory_operator_never_receives_credentials_or_mutation_language(tmp_path, monkeypatch):
    captured = install_fake_runner(monkeypatch, asdict(inventory()))
    collect_inventory("lancers", "http://127.0.0.1:9227", SURFACES, tmp_path)
    assert "password" not in captured["prompt"].lower()
    assert "submit" not in captured["prompt"].lower()
    assert captured["env"]["BU_CDP_URL"] == "http://127.0.0.1:9227"
```

`install_fake_runner` writes the schema-valid result and `summary.json` under the supplied evidence
directory, using the same complete subprocess stub shape already exercised by this test file.

- [ ] **Step 2: Run the focused tests and verify RED**

Run:
`PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python3 -m pytest -q skills/earn/gig/tests/test_market_inventory.py`

Expected: FAIL because `MarketInventory` and `collect_inventory` do not exist.

- [ ] **Step 3: Implement the minimum shared record and read-only agent operator**

```python
@dataclass(frozen=True)
class MarketInventory:
    provider: str
    account_identity_hash: str
    login_state: str
    opportunities: tuple[dict[str, Any], ...]
    messages: tuple[dict[str, Any], ...]
    applications: tuple[dict[str, Any], ...]
    active_work: tuple[dict[str, Any], ...]
    earnings: tuple[dict[str, Any], ...]
    official_urls: tuple[str, ...]
    observed_at: str
    source_complete: bool
    marketplace_effect_count: int
    evidence_hash: str
```

The agent prompt must tell Terra to use only the authenticated persistent default context at the exact
local endpoint, inspect every supplied official surface, perform no form submission or account change,
hash/redact identity and return the JSON Schema. The parent validates the result and file permissions.

- [ ] **Step 4: Run focused and adjacent provider tests**

Run:

```bash
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python3 -m pytest -q \
  skills/earn/gig/tests/test_market_inventory.py \
  skills/earn/gig/tests/test_provider_adapter.py \
  skills/earn/gig/tests/test_market_form_operator.py
python3 -m compileall -q skills/earn/gig/scripts/market_inventory.py
```

Expected: all tests PASS and compile exits 0.

- [ ] **Step 5: Commit and push Task 1**

```bash
git add skills/_shared/marketplace-core/schemas/market-inventory.schema.json \
  skills/earn/gig/scripts/market_inventory.py \
  skills/earn/gig/tests/test_market_inventory.py
git commit -m "feat(gig): add common market inventory"
git push
```

### Task 2: Restore Lancers read-only inventory through the common ACI

**Files:**
- Create: `skills/earn/gig/config/markets/lancers.json`
- Create: `skills/earn/gig/fixtures/redacted/lancers/inventory.json`
- Modify: `skills/earn/gig/tests/test_market_inventory.py`

**Interfaces:**
- Consumes: retained private profile at `~/.local/state/anicca/lancers/browser-profile`, exact CDP 9227,
  official authenticated surfaces and Task 1.
- Produces: two fresh inventory receipts with identical identities when provider state is unchanged.

- [ ] **Step 1: Add a redacted manifest/fixture test**

```python
def test_lancers_manifest_contains_transport_facts_not_strategy():
    manifest = json.loads(MANIFEST.read_text())
    assert manifest["provider"] == "lancers"
    assert manifest["currency"] == "JPY"
    assert set(manifest["surfaces"]) == {
        "profile", "opportunities", "messages", "applications",
        "active_work", "listings", "contracts", "earnings", "payouts",
    }
    forbidden = {"keywords", "minimum_price", "proposal_copy", "selectors", "credentials"}
    assert not forbidden.intersection(manifest)
```

- [ ] **Step 2: Run the test and verify RED**

Run: `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python3 -m pytest -q skills/earn/gig/tests/test_market_inventory.py`

Expected: FAIL because the Lancers manifest and fixture do not exist.

- [ ] **Step 3: Add only official routes/state vocabulary and a fully redacted fixture**

The fixture preserves structure, official state names and deterministic hashes. Replace names,
messages, proposal text, customer data, browser state and financial identifiers with typed redactions;
do not invent a positive contract or payment row.

- [ ] **Step 4: Declare and perform the production read-only recovery**

Use `bin/launchctl-safe` for every service mutation. Verify exact PID/profile/port ownership, then run
the common inventory operator twice. Do not kick Application, Storefront, Work Sync or Telegram owners.

Required evidence:

```text
login_state=authenticated
source_complete=true
marketplace_effect_count=0
account_identity_hash=<sha256>
two inventory evidence hashes or an explained official-state delta
owned_tab_count_after=0
```

- [ ] **Step 5: Run conformance and secret/PII checks**

Run:

```bash
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python3 -m pytest -q skills/earn/gig/tests/test_market_inventory.py
gitleaks dir skills/earn/gig --no-banner
python3 scripts/security/pii_shape_scan.py \
  skills/earn/gig/config/markets/lancers.json \
  skills/earn/gig/fixtures/redacted/lancers
```

Confirm zero credential, email, personal name, customer content, browser cookie and absolute operator
path findings.

- [ ] **Step 6: Update both canonical checkpoint sections, commit and push**

Record only fresh official counts/hashes/status, not raw DOM or PII. Advance Market Factory to `read`
with the inventory evidence hash. Commit the manifest, fixture, tests and measured spec rows.

```bash
git add skills/earn/gig/config/markets/lancers.json \
  skills/earn/gig/fixtures/redacted/lancers/inventory.json \
  skills/earn/gig/tests/test_market_inventory.py \
  docs/superpowers/specs/2026-08-13-lancers-20k-net-mrr-design.md \
  docs/superpowers/specs/2026-08-22-mr-bot-gig-economy-loop-design.md
git commit -m "feat(gig): read Lancers common inventory"
git push
```

### Task 3: Ground Lancers first-trust profile and external proof

**Files:**
- Modify: `skills/earn/gig/scripts/market_form_operator.py`
- Test: `skills/earn/gig/tests/test_market_form_operator.py`

**Interfaces:**
- Consumes: Task 2 inventory, factual private portfolio evidence, Lancers official profile and external
  achievements surface.
- Produces: one Luna decision and either an official profile/external-achievement receipt or a typed
  blocked/no-op result.

- [ ] **Step 1: Write tests proving profile work uses the same sealed operator/effect identity**

```python
def test_common_operator_accepts_a_sealed_profile_action(tmp_path, monkeypatch):
    captured = install_fake_runner(monkeypatch, status="ok")
    operate(
        provider="lancers", resource_id="profile:external-achievement",
        action="update_profile", form_url="https://www.lancers.jp/mypage/profile",
        sealed_intent={"evidence_hash": "a" * 64},
        cdp_base="http://127.0.0.1:9227", evidence_root=tmp_path,
    )
    assert "Action=update_profile" in captured["prompt"]
    assert "submit_proposal" not in captured["prompt"]
```

Also prove task-work approval is not treated as principal reputation and that raw external reviews are
never copied into prompts/fixtures.

- [ ] **Step 2: Run focused tests and verify RED**

Run:
`PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python3 -m pytest -q skills/earn/gig/tests/test_market_form_operator.py`

Expected: FAIL because `operate()` does not accept the sealed `action` field.

- [ ] **Step 3: Extend the existing operator only for sealed profile intents**

Do not add provider selectors or a new profile script. Luna decides whether existing evidence meets the
official Lancers import contract. Terra uses the common ACI. Deterministic code binds the intent and
verifies the official profile/external-achievement ID/state after at most one effect.

- [ ] **Step 4: Execute one factual canary or record official blocked evidence**

Require public before/after readback, exact provider identity, payload hash and replay effect zero.
Unsupported or unreviewable evidence results in no profile mutation.

- [ ] **Step 5: Update the Lancers checkpoint, run tests, commit and push**

```bash
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python3 -m pytest -q \
  skills/earn/gig/tests/test_market_form_operator.py
python3 -m compileall -q skills/earn/gig/scripts/market_form_operator.py
git add skills/earn/gig/scripts/market_form_operator.py \
  skills/earn/gig/tests/test_market_form_operator.py \
  docs/superpowers/specs/2026-08-13-lancers-20k-net-mrr-design.md
git commit -m "feat(gig): ground Lancers first trust"
git push
```

### Task 4: Judge and submit the first review-bearing Lancers canary

**Files:**
- Modify: `skills/earn/gig/scripts/application_planner.py`
- Test: `skills/earn/gig/tests/test_application_planner_focus.py`
- Update after receipt: `docs/superpowers/specs/2026-08-13-lancers-20k-net-mrr-design.md`

**Interfaces:**
- Consumes: fresh Lancers inventory, first-trust profile receipt, full public opportunity evidence and
  common feasibility policy from Task 63.
- Produces: one candidate-level Luna decision, sealed proposal intent, exact official proposal ID and
  duplicate-zero replay.

- [ ] **Step 1: Add conformance cases for lifetime-EV bootstrap judgment**

Use canonical natural-language cases, not keyword rules:

```python
CASES = (
    "A small review-bearing project with objective acceptance, credible buyer and positive net",
    "A cheaper task whose approval does not affect principal reputation",
    "A low-price project with unlimited revisions and negative expected net",
    "A larger bounded project with stronger repeat-client and reusable-proof value",
)
```

Assert every case reaches Luna, missing Skill never becomes a skip reason, and the chosen candidate has
an explicit long-run rationale plus deterministic numeric cost evidence.

- [ ] **Step 2: Run focused tests and verify RED**

Run:
`PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python3 -m pytest -q skills/earn/gig/tests/test_application_planner_focus.py`

Expected: FAIL because the shared prompt does not yet state the first-trust lifetime-EV contract.

- [ ] **Step 3: Add the right-altitude first-trust policy to the existing shared planner**

Tell Luna to consider official-review value, repeat-client value, reusable proof, market learning,
actual fee/cost and delivery risk. Do not add price thresholds, keyword rules, task-type routing or a
second planner call. The policy must explicitly state that absolute cheapest is not the objective and
that missing Skill is never refusal authority.

- [ ] **Step 4: Reuse the common Browser ACI and effect kernel without a Lancers submitter**

The Lancers manifest supplies only the target route/state vocabulary. Terra fills the measured live
form from the sealed intent. The parent independently reads proposal ID and official state. Native
automatic proposals remain disabled/inventory-only unless they expose candidate-level Luna intent and
readback under the same effect key.

- [ ] **Step 5: Execute one production canary and immediate replay**

Acceptance:

```text
candidate decision = submit with natural-language lifetime-EV rationale
external proposal effects = 1
official proposal ID = non-empty
ledger/application receipt = exactly 1
same sealed intent replay external effects = 0
Telegram event = exact proposal ID, no raw PII
```

- [ ] **Step 6: Run focused/common conformance tests, update spec, commit and push**

Run:

```bash
git diff --check
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python3 -m pytest -q \
  skills/earn/gig/tests/test_application_planner_focus.py \
  skills/earn/gig/tests/test_market_form_operator.py \
  skills/earn/gig/tests/test_provider_adapter.py
python3 -m compileall -q skills/earn/gig/scripts/application_planner.py
```

Record the exact proposal ID, release SHA, evidence hash, replay-zero result and remaining external
waits. Commit/push the shared policy, tests and measured Lancers checkpoint.

```bash
git add skills/earn/gig/scripts/application_planner.py \
  skills/earn/gig/tests/test_application_planner_focus.py \
  docs/superpowers/specs/2026-08-13-lancers-20k-net-mrr-design.md
git commit -m "feat(gig): bootstrap first market trust"
git push
```

## Later Subprojects

This plan intentionally stops at the first official Lancers proposal canary. The canonical remaining
order stays in `docs/superpowers/specs/2026-08-13-lancers-20k-net-mrr-design.md` §18.6:

1. Apply maximally with job-scoped concurrency and causal profile/proposal learning.
2. Close buyer message, offer and funded contract identities.
3. Run general-agent production, independent QA and official delivery.
4. Reconcile fee, refund, payout `received`, bank match and honest review.
5. Close Lancers provider conformance, redacted fixture, zero-spend installer, secret/PII scan and the
   second-market OSS stable gate.

Each subproject receives its own atomic plan only after the preceding official receipt exposes the real
provider shape. This prevents speculative Lancers files while preserving the complete end-to-end Done.

## Execution Rule

Start with Task 1 only. Do not implement Tasks 2–4 in the same slice. After each fresh official receipt,
update both canonical checkpoints, select the next row above, and continue. A missing buyer event blocks
only its resource; it does not justify a market-specific simulator, fake receipt or stopping independent
inventory/acquisition work.
