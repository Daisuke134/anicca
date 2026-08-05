
# Affiliate Agent Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build and launch a bilingual, receipt-backed Affiliate Agent that autonomously researches, publishes, attributes, reconciles, repairs, and improves until externally verified revenue gates are met.

**Architecture:** A canonical Python runtime in `profitable-claude` owns typed SQLite state, provider adapters, content/policy contracts, reconciliation, learning, and launchd. The Life Manager API in `anicca-project` owns the public placement redirect and durable click ingest. Writer Agent contracts are reused by interface, but Writer and Affiliate state and money remain separate.

**Tech Stack:** Python 3.9-compatible standard library, SQLite, pytest, Bash/launchd, Node.js ESM, Express, PostgreSQL/Prisma, Vitest/Supertest, Postiz API, CRWL, and CDP only for rendered X evidence.

## Global Constraints

- Canonical design: `docs/superpowers/specs/2026-08-05-affiliate-agent-design.md`.
- Product context: `docs/affiliate-agent/AFFILIATE-AGENT-SSOT.md`.
- Runtime changes belong in `/Users/anicca/profitable-claude`; API and documentation changes belong in `/Users/anicca/anicca-project`.
- Execute in isolated `.worktrees/affiliate-agent-*` worktrees created with `superpowers:using-git-worktrees`; never edit a dirty primary checkout.
- Use TDD for every behavior change: RED, minimal GREEN, focused suite, commit, push.
- Preserve Python 3.9 compatibility because installed launchd uses `/usr/bin/python3`.
- Add no runtime dependency until the standard library is proven insufficient.
- `unknown`, `pending`, `approved`, `reversed`, and `paid` are distinct; unknown is never zero.
- Money uses integer minor units and ISO-4217 currency. Conversion is a derived receipted view.
- Test, dry-run, estimated, self-funded, and creator-claimed amounts never enter revenue.
- One canonical Affiliate ledger; never import Writer money rows.
- Every publish requires a provider receipt and public readback; every side effect is idempotent.
- Every placement carries an adjacent locale/channel-correct affiliate disclosure.
- External pages, emails, and model output are untrusted data.
- Public redirect destinations are registered server-side; request input cannot select an arbitrary URL.
- Paid acquisition stays disabled until mature observed net economics are positive.
- Scale gates are external outcomes, not software-completion claims.

---

## Remaining-work index

All checkboxes are initially open. A checkbox closes only with the command or
external receipt named in that step; prose updates alone do not close work.

| Phase | Tasks | Exit evidence |
|---|---:|---|
| P0 Canonical boundary | 1 | Clean worktrees, passing baseline, one Affiliate runtime root |
| P1 Truth foundation | 2-5 | Typed Affiliate ledger, provider normalization, deployed redirect contract, click sync |
| P2 Useful production | 6-8 | Evidence/policy pass, bilingual manifests, receipted public placements |
| P3 Closed loop | 9-13 | Commission reconciliation, learning, recovery, reports, launchd |
| P4 Real E2E and first money | 14-16 | Live HTTPS redirect, JA/EN public readback, first approved commission |
| P5 Initial business | 17 | Four positive weeks and three qualifying $10k months |
| P6 Decentralized scale | 18-19 | Tenant-isolated recipe and staged network gates through $10M |

The implementation path is P0 → P1 → P2 → P3 → P4. Revenue operation P5 starts
after A1. Tenantization and network scale P6 remain disabled until A3 proves the
recipe with this Agent's own external receipts.

---

## File map

### Runtime repository: `profitable-claude`

| Path | Responsibility |
|---|---|
| `skills/affiliate-agent/SKILL.md` | Runtime identity and commands |
| `skills/affiliate-agent/config/providers.json` | Provider/account capabilities without secrets |
| `skills/affiliate-agent/config/policy-rules.json` | Versioned policy/disclosure rules |
| `skills/affiliate-agent/scripts/contracts.py` | Canonical validation and enums |
| `skills/affiliate-agent/scripts/ledger.py` | Affiliate-only SQLite and receipts |
| `skills/affiliate-agent/scripts/providers/*.py` | Provider account/offer/report adapters |
| `skills/affiliate-agent/scripts/evidence.py` | Official-source evidence packs |
| `skills/affiliate-agent/scripts/policy.py` | Fail-closed policy gate |
| `skills/affiliate-agent/scripts/content.py` | JA/EN manifests and Writer bridge |
| `skills/affiliate-agent/scripts/publisher.py` | Owned/Postiz publication and readback |
| `skills/affiliate-agent/scripts/click_sync.py` | Life Manager placement/click API client |
| `skills/affiliate-agent/scripts/reconcile.py` | Conversion/commission reconciliation |
| `skills/affiliate-agent/scripts/allocator.py` | Exploration and concentration allocation |
| `skills/affiliate-agent/scripts/learning.py` | Mature one-variable experiments |
| `skills/affiliate-agent/scripts/recovery.py` | Same-run resume and quarantine |
| `skills/affiliate-agent/scripts/orchestrator.py` | Hourly/daily state machine |
| `skills/affiliate-agent/scripts/report.py` | Web/Telegram canonical snapshot |
| `skills/affiliate-agent/scripts/install.sh` | launchd install and kickstart |
| `skills/affiliate-agent/launchd/*.plist` | Production worker definitions |
| `skills/affiliate-agent/tests/` | Unit, contract, recovery, and fixture tests |

### API repository: `anicca-project`

| Path | Responsibility |
|---|---|
| `apps/api/prisma/schema.prisma` | Placement and click tables |
| `apps/api/prisma/migrations/*_affiliate_click_attribution/migration.sql` | Database migration |
| `apps/api/src/services/affiliateClickService.js` | Placement/token/click operations |
| `apps/api/src/routes/affiliate/index.js` | Route composition |
| `apps/api/src/routes/affiliate/click.js` | Public redirect |
| `apps/api/src/routes/affiliate/internal.js` | Authenticated placement/click API |
| `apps/api/src/routes/affiliate/__tests__/click.test.js` | Route tests |
| `apps/api/src/routes/index.js` | `/affiliate` mount |

---

### Task 1: Establish isolated baselines and the Affiliate skill root

**Files:**
- Create: `profitable-claude/skills/affiliate-agent/SKILL.md`
- Create: `profitable-claude/skills/affiliate-agent/config/providers.json`
- Test: `profitable-claude/skills/affiliate-agent/tests/test_skill_contract.py`

**Interfaces:**
- Consumes: Writer Agent canonical paths and the design spec.
- Produces: the only Affiliate runtime root and provider schema version `1`.

- [ ] **Step 1: Create clean worktrees from current pushed canonical branches**

```bash
cd /Users/anicca/profitable-claude
git fetch --all --prune
git worktree add .worktrees/affiliate-agent-runtime -b feature/affiliate-agent-runtime origin/main
cd /Users/anicca/anicca-project
git fetch --all --prune
git worktree add .worktrees/affiliate-agent-api -b feature/affiliate-agent-api origin/dev
```

- [ ] **Step 2: Record baseline status and test results**

```bash
git -C /Users/anicca/profitable-claude/.worktrees/affiliate-agent-runtime status --short
python3 -m pytest /Users/anicca/profitable-claude/.worktrees/affiliate-agent-runtime/skills/writer-agent/tests -q
git -C /Users/anicca/anicca-project/.worktrees/affiliate-agent-api status --short
npm --prefix /Users/anicca/anicca-project/.worktrees/affiliate-agent-api/apps/api test -- --run
```

Expected: both worktrees are clean and existing suites pass before Affiliate edits.

- [ ] **Step 3: Write the failing identity test**

```python
def test_affiliate_skill_has_one_canonical_runtime_root():
    root = Path(__file__).resolve().parents[1]
    assert "Affiliate Agent" in (root / "SKILL.md").read_text()
    payload = json.loads((root / "config/providers.json").read_text())
    assert payload == {"schema_version": 1, "providers": []}
```

- [ ] **Step 4: Run RED**

```bash
python3 -m pytest skills/affiliate-agent/tests/test_skill_contract.py -q
```

Expected: FAIL because the skill and config do not exist.

- [ ] **Step 5: Add the minimal skill and registry**

`SKILL.md` names the design, separates Writer revenue, lists `hourly`, `daily`,
`reconcile`, `report`, and `status`, and forbids money without external receipts.
`providers.json` exactly matches the test fixture.

- [ ] **Step 6: Run GREEN, commit, and push**

```bash
python3 -m pytest skills/affiliate-agent/tests/test_skill_contract.py -q
git add skills/affiliate-agent
git commit -m "feat(affiliate): establish canonical runtime root"
git push -u origin feature/affiliate-agent-runtime
```

### Task 2: Implement canonical contracts and the immutable Affiliate ledger

**Files:**
- Create: `profitable-claude/skills/affiliate-agent/scripts/contracts.py`
- Create: `profitable-claude/skills/affiliate-agent/scripts/ledger.py`
- Test: `profitable-claude/skills/affiliate-agent/tests/test_ledger.py`

**Interfaces:**
- Produces: `AffiliateLedger`, account/offer/placement/click/commission/payout append methods, and `snapshot()`.
- Consumes: integer amounts, ISO currency, external IDs, hashes, and timezone-aware timestamps.

- [ ] **Step 1: Write failing money invariant tests**

```python
def test_unknown_commission_is_not_zero(tmp_path):
    ledger = AffiliateLedger(tmp_path / "affiliate.sqlite")
    ledger.append_commission({**commission_fixture(), "status": "pending", "amount_minor": None})
    assert ledger.snapshot()["approved"] == {}

def test_reversal_appends_without_mutating_approval(tmp_path):
    ledger = AffiliateLedger(tmp_path / "affiliate.sqlite")
    approved = ledger.append_commission(commission_fixture())
    ledger.append_commission(reversal_fixture(approved["receipt_id"]))
    assert ledger.receipt(approved["receipt_id"])["status"] == "approved"
    assert ledger.count("commission_receipts") == 2

def test_external_transaction_replay_is_idempotent(tmp_path):
    ledger = AffiliateLedger(tmp_path / "affiliate.sqlite")
    a = ledger.append_commission(commission_fixture())
    b = ledger.append_commission(commission_fixture())
    assert a["receipt_id"] == b["receipt_id"]
    assert ledger.count("commission_receipts") == 1
```

- [ ] **Step 2: Run RED**

```bash
python3 -m pytest skills/affiliate-agent/tests/test_ledger.py -q
```

- [ ] **Step 3: Implement the schema and validators**

Create all records from design section 7. Enforce foreign keys, WAL, busy timeout,
account-scoped provider transaction uniqueness, append-only reversal linkage,
source SHA-256, and timezone-aware timestamps.

- [ ] **Step 4: Implement currency-separated snapshots**

`snapshot()` returns approved, paid, reversed, pending, fee, and net maps keyed by
currency. It excludes test/self-funded rows and performs no implicit FX.

- [ ] **Step 5: Run GREEN and Python 3.9 compilation**

```bash
python3 -m pytest skills/affiliate-agent/tests/test_ledger.py -q
/usr/bin/python3 -m py_compile skills/affiliate-agent/scripts/contracts.py skills/affiliate-agent/scripts/ledger.py
```

- [ ] **Step 6: Commit and push**

```bash
git add skills/affiliate-agent
git commit -m "feat(affiliate): add receipt-backed commission ledger"
git push
```

### Task 3: Normalize provider accounts, offers, and transaction reports

**Files:**
- Create: `profitable-claude/skills/affiliate-agent/scripts/providers/base.py`
- Create: `profitable-claude/skills/affiliate-agent/scripts/providers/amazon.py`
- Create: `profitable-claude/skills/affiliate-agent/scripts/providers/rakuten.py`
- Create: `profitable-claude/skills/affiliate-agent/scripts/providers/tabular.py`
- Create: `profitable-claude/skills/affiliate-agent/scripts/provider_registry.py`
- Test: `profitable-claude/skills/affiliate-agent/tests/test_providers.py`

**Interfaces:**
- Produces: `read_account()`, `list_offers()`, and `read_transactions(cursor)`.
- Consumes: provider-owned API/report/auth readbacks; directories supply candidates only.

- [ ] **Step 1: Write failing provider contract tests**

```python
def test_logged_out_account_is_not_executable():
    account = AmazonAdapter(FakeTransport("sign-in-page.html")).read_account()
    assert account.auth_state == "AUTH_REQUIRED"
    assert account.executable is False

def test_offer_requires_terms_and_allowed_channel():
    offer = RakutenAdapter(FakeTransport("rakuten-offer.json")).list_offers()[0]
    assert offer.source_sha256
    assert offer.allowed_channels == ("owned_web", "sns")

def test_reversal_retains_external_transaction_identity():
    rows = TabularAdapter("afb", "afb-reversed.csv").read_transactions(None).rows
    assert rows[0].status == "reversed"
    assert rows[0].external_transaction_id == "tx-100"
```

- [ ] **Step 2: Run RED**

```bash
python3 -m pytest skills/affiliate-agent/tests/test_providers.py -q
```

- [ ] **Step 3: Implement fail-closed account and offer normalization**

An offer is executable only with account identity, official terms, freshness,
affiliate ID/tag, allowed channel, and verified destination host.

- [ ] **Step 4: Implement report normalization and cursor state**

Normalize pending, approved, reversed, and paid while retaining raw payload hash.
Never infer a missing amount.

- [ ] **Step 5: Run GREEN, commit, and push**

```bash
python3 -m pytest skills/affiliate-agent/tests/test_providers.py skills/affiliate-agent/tests/test_ledger.py -q
git add skills/affiliate-agent
git commit -m "feat(affiliate): normalize provider accounts and offers"
git push
```

### Task 4: Build the public placement redirect and internal click API

**Files:**
- Modify: `anicca-project/apps/api/prisma/schema.prisma`
- Create: `anicca-project/apps/api/prisma/migrations/20260805090000_affiliate_click_attribution/migration.sql`
- Create: `anicca-project/apps/api/src/services/affiliateClickService.js`
- Create: `anicca-project/apps/api/src/routes/affiliate/index.js`
- Create: `anicca-project/apps/api/src/routes/affiliate/click.js`
- Create: `anicca-project/apps/api/src/routes/affiliate/internal.js`
- Test: `anicca-project/apps/api/src/routes/affiliate/__tests__/click.test.js`
- Modify: `anicca-project/apps/api/src/routes/index.js`

**Interfaces:**
- Produces: placement create/disable, cursor click reads, and `GET /api/affiliate/c/:token`.
- Consumes: registered placement/destination, expiry, HMAC secret, and internal auth.

- [ ] **Step 1: Write failing redirect and open-redirect tests**

```javascript
it('persists a click and redirects only to the registered destination', async () => {
  const response = await request(app).get('/api/affiliate/c/opaque-token');
  expect(response.status).toBe(302);
  expect(response.headers.location).toBe('https://approved.example/product?subid=click-1');
  expect(store.clicks).toHaveLength(1);
});

it('ignores attacker-controlled destination input', async () => {
  const response = await request(app).get('/api/affiliate/c/opaque-token?url=https://evil.example');
  expect(response.headers.location).not.toContain('evil.example');
});
```

Also cover missing `404`, disabled/expired `410`, persistence failure `503`,
internal auth rejection, and public rate limiting.

- [ ] **Step 2: Run RED**

```bash
npm --prefix apps/api test -- src/routes/affiliate/__tests__/click.test.js
```

- [ ] **Step 3: Add Prisma models and migration**

Create `AffiliatePlacement` and append-only `AffiliateClick` with opaque token
hash, active/expiry state, destination, sub-ID capability, artifact/experiment
lineage, timestamps, and unique click ID. Store no raw IP.

- [ ] **Step 4: Implement service and routes**

Append a click before `302`, add sub-ID only from provider configuration, rate
limit public clicks, and protect internal routes with existing agent auth.

- [ ] **Step 5: Run focused and route suites**

```bash
npm --prefix apps/api test -- src/routes/affiliate/__tests__/click.test.js src/routes/agent/__tests__/agent.test.js
```

- [ ] **Step 6: Commit and push the API slice**

```bash
git add apps/api/prisma apps/api/src/routes/affiliate apps/api/src/services/affiliateClickService.js apps/api/src/routes/index.js
git commit -m "feat(api): add affiliate redirect and click receipts"
git push -u origin feature/affiliate-agent-api
```

### Task 5: Connect runtime placement creation and click ingestion

**Files:**
- Create: `profitable-claude/skills/affiliate-agent/scripts/click_sync.py`
- Test: `profitable-claude/skills/affiliate-agent/tests/test_click_sync.py`

**Interfaces:**
- Produces: `create_placement()` and `sync_clicks(cursor)`.
- Consumes: internal Life Manager API and Affiliate ledger.

- [ ] **Step 1: Write failing idempotency and cursor tests**

```python
def test_create_replay_returns_same_token(fake_api, ledger):
    a = create_placement(placement_fixture(), fake_api, ledger)
    b = create_placement(placement_fixture(), fake_api, ledger)
    assert a.token == b.token
    assert fake_api.create_calls == 1

def test_cursor_advances_only_after_page_commit(fake_api, ledger):
    fake_api.fail_on_row = 2
    with pytest.raises(SyncFailure):
        sync_clicks("cursor-1", fake_api, ledger)
    assert ledger.get_cursor("clicks") == "cursor-1"
```

- [ ] **Step 2: Run RED and implement authenticated time-bounded requests**

```bash
python3 -m pytest skills/affiliate-agent/tests/test_click_sync.py -q
```

- [ ] **Step 3: Hash API receipts and commit each page atomically**

Validate returned placement identity and advance the cursor only after the whole
page commits.

- [ ] **Step 4: Run GREEN, commit, and push**

```bash
python3 -m pytest skills/affiliate-agent/tests/test_click_sync.py skills/affiliate-agent/tests/test_ledger.py -q
git add skills/affiliate-agent
git commit -m "feat(affiliate): sync placements and click receipts"
git push
```

### Task 6: Implement official evidence packs and fail-closed policy

**Files:**
- Create: `profitable-claude/skills/affiliate-agent/config/policy-rules.json`
- Create: `profitable-claude/skills/affiliate-agent/scripts/evidence.py`
- Create: `profitable-claude/skills/affiliate-agent/scripts/policy.py`
- Test: `profitable-claude/skills/affiliate-agent/tests/test_evidence_policy.py`

**Interfaces:**
- Produces: `EvidencePack`, `PolicyDecision`, and `evaluate()`.
- Consumes: CRWL/provider bodies, hashes, TTL, disclosure, and channel rules.

- [ ] **Step 1: Write failing freshness and disclosure tests**

```python
def test_stale_price_fails_closed():
    decision = evaluate(manifest(), offer(), evidence(price_age_days=8, ttl_days=7))
    assert decision.status == "FAIL"
    assert "stale_price" in decision.reasons

def test_disclosure_must_precede_first_affiliate_cta():
    decision = evaluate(manifest(disclosure_offset=400, first_cta_offset=120), offer(), evidence())
    assert decision.status == "FAIL"
    assert "disclosure_after_cta" in decision.reasons
```

- [ ] **Step 2: Run RED and implement exact claim-to-source binding**

```bash
python3 -m pytest skills/affiliate-agent/tests/test_evidence_policy.py -q
```

- [ ] **Step 3: Implement locale/channel disclosures and category quarantine**

Include JA/EN general disclosure, Amazon statement, channel allowlists, prohibited
brand bidding, unsafe-category default denial, and source freshness. A model
cannot override deterministic failure.

- [ ] **Step 4: Run GREEN, commit, and push**

```bash
python3 -m pytest skills/affiliate-agent/tests/test_evidence_policy.py -q
git add skills/affiliate-agent
git commit -m "feat(affiliate): gate evidence claims and disclosures"
git push
```

### Task 7: Build bilingual content manifests and the Writer bridge

**Files:**
- Create: `profitable-claude/skills/affiliate-agent/scripts/content.py`
- Test: `profitable-claude/skills/affiliate-agent/tests/test_content.py`
- Reuse by interface: `profitable-claude/skills/writer-agent/scripts/publication_contract.py`
- Reuse by interface: `profitable-claude/skills/writer-agent/scripts/artifact_attribution.py`

**Interfaces:**
- Produces: immutable `ContentManifest` and Writer input bundle.
- Consumes: reader job, primary offer, up to two alternatives, evidence, locale, disclosure, and experiment.

- [ ] **Step 1: Write failing reader-job/localization tests**

```python
def test_manifest_rejects_three_alternatives():
    with pytest.raises(ContentInvariant):
        build_manifest(**fixture(alternative_offer_ids=["a", "b", "c"]))

def test_ja_and_en_require_independent_offer_snapshots():
    with pytest.raises(ContentInvariant, match="locale offer snapshot"):
        build_pair(ja_offer=ja_offer(), en_offer=ja_offer())
```

- [ ] **Step 2: Run RED and implement hash-bound manifests**

```bash
python3 -m pytest skills/affiliate-agent/tests/test_content.py -q
```

- [ ] **Step 3: Add the narrow Writer bridge**

Pass reader job, evidence, structure, locale, and output paths. Record the Writer
contract/version/hash. Never read or write Writer money/topic state.

- [ ] **Step 4: Run Affiliate and Writer contract tests**

```bash
python3 -m pytest skills/affiliate-agent/tests/test_content.py -q
bash skills/writer-agent/tests/editorial-citation-contract.sh
bash skills/writer-agent/tests/cta-publication-boundary.sh
```

- [ ] **Step 5: Commit and push**

```bash
git add skills/affiliate-agent
git commit -m "feat(affiliate): create bilingual decision manifests"
git push
```

### Task 8: Publish owned and Postiz placements with public readback

**Files:**
- Create: `profitable-claude/skills/affiliate-agent/scripts/publisher.py`
- Test: `profitable-claude/skills/affiliate-agent/tests/test_publisher.py`

**Interfaces:**
- Produces: `PublishIntent`, provider publish receipt, and `PublicReadback`.
- Consumes: policy-passed content, redirect token, channel adapter, and protected Postiz API key.

- [ ] **Step 1: Write failing duplicate/readback tests**

```python
def test_replay_does_not_create_second_post(fake_postiz, ledger):
    publish(placement(), fake_postiz, ledger)
    publish(placement(), fake_postiz, ledger)
    assert fake_postiz.create_calls == 1

def test_readback_requires_disclosure_and_redirect(fake_postiz, ledger):
    fake_postiz.public_body = "content without disclosure"
    assert publish(placement(), fake_postiz, ledger).status == "RECOVER"
```

- [ ] **Step 2: Run RED and implement the idempotent intent journal**

```bash
python3 -m pytest skills/affiliate-agent/tests/test_publisher.py -q
```

- [ ] **Step 3: Implement Postiz and owned-page adapters**

Require API publication ID/URL and rendered public readback. X account identity
must match the configured dedicated account receipt.

- [ ] **Step 4: Run GREEN and Writer isolation regression**

```bash
python3 -m pytest skills/affiliate-agent/tests/test_publisher.py -q
bash skills/writer-agent/tests/platform-dispatch-isolation.sh
```

- [ ] **Step 5: Commit and push**

```bash
git add skills/affiliate-agent
git commit -m "feat(affiliate): publish receipted Postiz placements"
git push
```

### Task 9: Reconcile conversions, commissions, reversals, and payouts

**Files:**
- Create: `profitable-claude/skills/affiliate-agent/scripts/reconcile.py`
- Test: `profitable-claude/skills/affiliate-agent/tests/test_reconcile.py`

**Interfaces:**
- Produces: `matched`, `unmatched`, `conflict`, and cursor receipts.
- Consumes: normalized transactions, placements, clicks, and ledger.

- [ ] **Step 1: Write failing match and reversal tests**

```python
def test_subid_match_beats_time_proximity(ledger):
    receipt = reconcile(transaction(sub_id="click-b"), ledger_with_clicks("click-a", "click-b"))
    assert receipt.click_id == "click-b"

def test_missing_subid_does_not_guess_by_time(ledger):
    assert reconcile(transaction(sub_id=None), ledger).status == "unmatched"

def test_reversal_preserves_approval_receipt(ledger):
    reconcile(approved_transaction(), ledger)
    reconcile(reversed_transaction(), ledger)
    assert ledger.count("commission_receipts") == 2
```

- [ ] **Step 2: Run RED and implement deterministic precedence**

```bash
python3 -m pytest skills/affiliate-agent/tests/test_reconcile.py -q
```

- [ ] **Step 3: Implement cursor-safe batches and conflict quarantine**

Provider cursor advances only after all rows append. Conflicting identity,
amount, or currency becomes explicit conflict and never overwrites.

- [ ] **Step 4: Run GREEN twice, commit, and push**

```bash
python3 -m pytest skills/affiliate-agent/tests/test_reconcile.py skills/affiliate-agent/tests/test_ledger.py -q
git add skills/affiliate-agent
git commit -m "feat(affiliate): reconcile provider commissions"
git push
```

### Task 10: Implement allocation and bounded learning

**Files:**
- Create: `profitable-claude/skills/affiliate-agent/scripts/allocator.py`
- Create: `profitable-claude/skills/affiliate-agent/scripts/learning.py`
- Test: `profitable-claude/skills/affiliate-agent/tests/test_learning.py`

**Interfaces:**
- Produces: allocation, experiment assignment, and `KEEP|REVERT|INCONCLUSIVE`.
- Consumes: mature cohorts, costs, concentration, exploration rate, and one changed field.

- [ ] **Step 1: Write failing exploration/concentration/causal tests**

```python
def test_allocator_reserves_twenty_percent_exploration():
    result = allocate(portfolio(), capacity=10)
    assert len([x for x in result if x.mode == "explore"]) >= 2

def test_candidate_cannot_change_two_fields():
    with pytest.raises(ExperimentInvariant):
        assign(baseline(), candidate(hook="new", cta="new"))

def test_reversal_harm_forces_revert():
    assert decide(cohort(net_delta=100, reversal_delta=2)).decision == "REVERT"
```

- [ ] **Step 2: Run RED and implement uncertainty-aware allocation**

```bash
python3 -m pytest skills/affiliate-agent/tests/test_learning.py -q
```

- [ ] **Step 3: Implement maturity and strategy-consumption receipts**

Require same-age comparable cohorts and ten mature placements unless a stronger
paid outcome closes deterministically. Only `KEEP` changes active strategy.

- [ ] **Step 4: Run GREEN, commit, and push**

```bash
python3 -m pytest skills/affiliate-agent/tests/test_learning.py -q
git add skills/affiliate-agent
git commit -m "feat(affiliate): allocate from mature net receipts"
git push
```

### Task 11: Implement durable orchestration, waits, and recovery

**Files:**
- Create: `profitable-claude/skills/affiliate-agent/scripts/orchestrator.py`
- Create: `profitable-claude/skills/affiliate-agent/scripts/recovery.py`
- Test: `profitable-claude/skills/affiliate-agent/tests/test_orchestrator.py`
- Test: `profitable-claude/skills/affiliate-agent/tests/test_recovery.py`

**Interfaces:**
- Produces: `hourly_wake()`, `daily_wake()`, `resume(run_id)`, legal transitions, and quarantines.
- Consumes: prior components through explicit interfaces.

- [ ] **Step 1: Write failing crash and isolation tests**

```python
def test_crash_after_publish_receipt_resumes_without_repost(harness):
    harness.crash_after("provider_receipt")
    with pytest.raises(SimulatedCrash):
        harness.daily()
    harness.resume()
    assert harness.postiz.create_calls == 1
    assert harness.state == "MEASURE"

def test_auth_failure_quarantines_one_account(harness):
    harness.amazon.auth_fails = True
    result = harness.hourly()
    assert result.accounts["amazon-jp"] == "QUARANTINED"
    assert result.accounts["rakuten-jp"] == "ACTIVE"
```

- [ ] **Step 2: Run RED and implement legal state transitions**

```bash
python3 -m pytest skills/affiliate-agent/tests/test_orchestrator.py skills/affiliate-agent/tests/test_recovery.py -q
```

- [ ] **Step 3: Implement durable wait/retry ownership**

Store external reason, owner, retry time, attempt count, and independent work.
Honor `Retry-After`; move permanent failures to quarantine.

- [ ] **Step 4: Run crash matrix GREEN, commit, and push**

```bash
python3 -m pytest skills/affiliate-agent/tests/test_orchestrator.py skills/affiliate-agent/tests/test_recovery.py -q
git add skills/affiliate-agent
git commit -m "feat(affiliate): add same-run recovery"
git push
```

### Task 12: Generate one money-first Web/Telegram snapshot

**Files:**
- Create: `profitable-claude/skills/affiliate-agent/scripts/report.py`
- Test: `profitable-claude/skills/affiliate-agent/tests/test_report.py`

**Interfaces:**
- Produces: `latest.json`, `index.html`, Telegram text, and one semantic SHA-256.
- Consumes: ledger, runs, waits, quarantines, experiments, public URLs, and gates.

- [ ] **Step 1: Write failing parity/currency tests**

```python
def test_web_and_telegram_share_hash(tmp_path):
    output = build_report(fixture(), tmp_path)
    assert output.web_hash == output.telegram_hash

def test_multicurrency_has_no_unreceipted_total(tmp_path):
    output = build_report(multicurrency_fixture(), tmp_path)
    assert output.snapshot["total_usd"] is None
    assert output.snapshot["by_currency"] == {"JPY": 5000, "USD": 40}
```

- [ ] **Step 2: Run RED and implement canonical rendering**

```bash
python3 -m pytest skills/affiliate-agent/tests/test_report.py -q
```

- [ ] **Step 3: Render money, health, gates, and next action**

Separate approved, paid, reversed, pending, unknown, net, and cost. Show public
URLs, run, quarantine, retry, software/A1/A3/$10M gates, and next owner action.

- [ ] **Step 4: Run GREEN, inspect 390px fixture, commit, and push**

```bash
python3 -m pytest skills/affiliate-agent/tests/test_report.py -q
git add skills/affiliate-agent
git commit -m "feat(affiliate): report money and runtime health"
git push
```

### Task 13: Install and verify launchd ownership

**Files:**
- Create: `profitable-claude/skills/affiliate-agent/launchd/ai.anicca.affiliate-hourly.plist`
- Create: `profitable-claude/skills/affiliate-agent/launchd/ai.anicca.affiliate-daily.plist`
- Create: `profitable-claude/skills/affiliate-agent/launchd/ai.anicca.affiliate-report.plist`
- Create: `profitable-claude/skills/affiliate-agent/scripts/install.sh`
- Test: `profitable-claude/skills/affiliate-agent/tests/test_launchd_wiring.py`

**Interfaces:**
- Produces: installed labels, locks, logs, status receipts, and immediate kickstart.
- Consumes: protected env, canonical root, and Python 3.9 entrypoints.

- [ ] **Step 1: Write failing plist tests**

```python
def test_plists_use_canonical_root_and_run_at_load():
    for path in PLISTS:
        payload = plistlib.loads(path.read_bytes())
        assert payload["RunAtLoad"] is True
        assert "/skills/affiliate-agent/" in " ".join(payload["ProgramArguments"])
        assert payload["StandardOutPath"] != payload["StandardErrorPath"]
```

- [ ] **Step 2: Run RED; implement plists and idempotent installer**

```bash
python3 -m pytest skills/affiliate-agent/tests/test_launchd_wiring.py -q
```

- [ ] **Step 3: Run GREEN and Python 3.9 compilation**

```bash
python3 -m pytest skills/affiliate-agent/tests/test_launchd_wiring.py -q
/usr/bin/python3 -m compileall -q skills/affiliate-agent/scripts
```

- [ ] **Step 4: Commit and push before live state changes**

```bash
git add skills/affiliate-agent
git commit -m "feat(affiliate): install autonomous workers"
git push
```

- [ ] **Step 5: Install, kickstart, and observe real exits**

```bash
bash skills/affiliate-agent/scripts/install.sh
launchctl kickstart -k gui/$(id -u)/ai.anicca.affiliate-hourly
launchctl kickstart -k gui/$(id -u)/ai.anicca.affiliate-daily
launchctl print gui/$(id -u)/ai.anicca.affiliate-hourly
launchctl print gui/$(id -u)/ai.anicca.affiliate-daily
```

Expected: jobs exist; last exit is `0` or explicit receipted external wait; no
duplicate placement is produced.

### Task 14: Deploy the redirect and prove live HTTPS click E2E

**Files:**
- Modify only if evidence requires: `anicca-project/railway.toml`
- Update: `anicca-project/docs/affiliate-agent/AFFILIATE-AGENT-SSOT.md`

**Interfaces:**
- Produces: deployment hash, placement receipt, click receipt, and `302` readback.
- Consumes: merged API slice and protected HMAC/internal auth.

- [ ] **Step 1: Push the API slice through the configured deployment branch**

```bash
git fetch --all --prune
git log -1 --format=%H
git push origin HEAD:dev
```

- [ ] **Step 2: Verify Railway's exact deployment commit and health**

Repository presence alone is insufficient; deployment state/logs are authority.

- [ ] **Step 3: Create one short-lived `test=true` placement**

Use a controlled HTTPS destination. Test clicks never enter revenue.

- [ ] **Step 4: Call the public URL and verify redirect plus durable click**

```bash
test -n "$AFFILIATE_API_BASE"
test -n "$AFFILIATE_TEST_TOKEN"
curl -sS -D /tmp/affiliate-click-headers.txt -o /dev/null \
  "$AFFILIATE_API_BASE/api/affiliate/c/$AFFILIATE_TEST_TOKEN"
```

Verify `302`, exact destination, and internal cursor endpoint click ID. Repeat and
confirm two click IDs but one placement.

- [ ] **Step 5: Record only sanitized hashes and deployment evidence; commit/push**

No token, credential, raw IP, or personal identifier enters git.

### Task 15: Execute the first bilingual production publication E2E

**Files:**
- Runtime state: `profitable-claude/skills/affiliate-agent/state/` (gitignored)
- Update: `anicca-project/docs/affiliate-agent/AFFILIATE-AGENT-SSOT.md`

**Interfaces:**
- Produces: one live JA and one live EN decision asset with policy, publish, readback, redirect, and click receipts.
- Consumes: actually authenticated executable offers.

- [ ] **Step 1: Read back provider ownership and executable offers**

Store account identity hash, official terms hash, channel rules, destination,
tag/sub-ID capability, and auth state. Logged-out Amazon/Rakuten stays
`AUTH_REQUIRED`; use another authenticated provider rather than invent readiness.

- [ ] **Step 2: Build one current JA and one current EN evidence pack**

Bind official claims, locale availability, reader problem, primary offer,
alternatives, disclosure, TTL, and exact hashes.

- [ ] **Step 3: Publish through owned content and approved Postiz/X**

Capture provider publication ID/URL. This is a real side effect, not a dry run.

- [ ] **Step 4: Perform public readback and marked test clicks**

Verify rendered disclosure, redirect, destination, placement lineage, and durable
clicks. Mark test clicks so they cannot count as revenue.

- [ ] **Step 5: Prove isolated crash resume**

Use a sandbox adapter to crash after provider receipt; resume the same intent
without duplicate. Do not stop an unrelated production loop.

- [ ] **Step 6: Run complete Affiliate and Writer suites**

```bash
python3 -m pytest skills/affiliate-agent/tests -q
python3 -m pytest skills/writer-agent/tests -q
```

- [ ] **Step 7: Record sanitized receipts, commit, and push both repositories**

A0 closes only when both languages have public readback and click lineage.
Revenue remains zero/unknown until an external transaction.

### Task 16: Close A1 with the first external approved commission

**Files:**
- Runtime receipt state only.
- Update: `anicca-project/docs/affiliate-agent/AFFILIATE-AGENT-SSOT.md`.

**Interfaces:**
- Produces: transaction, commission, attribution/unmatched, and payout-state receipts.
- Consumes: a real non-test provider report.

- [ ] **Step 1: Keep hourly reconciliation active until a transaction appears**

Independent publishing, health checks, and reports continue. Reporting delay does
not become zero revenue.

- [ ] **Step 2: Import the transaction twice**

First import creates one canonical receipt. Replay returns the same receipt and
row count.

- [ ] **Step 3: Verify attribution strength**

Join by provider transaction and sub-ID/click where available. Otherwise retain
`unmatched`; never guess from time.

- [ ] **Step 4: Verify money state**

Pending does not close A1. Approved non-test commission closes A1. Paid requires
a payout receipt. Later reversal appends and changes net reporting.

- [ ] **Step 5: Verify report parity and record sanitized gate evidence**

Commit/push provider, currency, artifact, receipt IDs/hashes, state, and observed
time without secrets.

### Task 17: Operate the $1k and $10k gates

**Files:**
- Runtime ledgers/reports only.
- Update gate rows: `anicca-project/docs/affiliate-agent/AFFILIATE-AGENT-SSOT.md`.

**Interfaces:**
- Produces: four positive weeks, then three qualifying $10k months.
- Consumes: mature net cohorts and bounded experiments.

- [ ] **Step 1: Require four net-positive closed weeks before capacity growth**

Verify approved gross, reversals, fees, compute, acquisition, net, unmatched
transactions, and publication health.

- [ ] **Step 2: Promote only receipted combinations**

Every promotion links baseline/candidate, mature window, one changed variable,
decision, rollback hash, and later strategy consumption.

- [ ] **Step 3: Improve terms only after measured fit**

Use actual volume, approval rate, reversal rate, and reader fit for ASP special
rates/direct partner deals. Advertised payout alone gains no capacity.

- [ ] **Step 4: Add one budget-capped pod at a time**

A pod is language/region, buyer problem, content cluster, and provider portfolio.
No pod exceeds canary capacity before mature positive net evidence.

- [ ] **Step 5: Close each month from provider receipts**

Keep currencies separate. A displayed USD equivalent requires a dated FX receipt.
A month passes only with complete approved/reversal state and visible net.

- [ ] **Step 6: Close A3 after three consecutive qualifying months**

Generate gross, approved, paid, reversal, fee, net, unmatched, concentration,
uptime, and manual-intervention evidence; commit/push the SSOT summary.

### Task 18: Package the proven recipe for operator-owned installations

**Files:**
- Create after A3: `profitable-claude/skills/affiliate-agent/scripts/tenant_contract.py`
- Test after A3: `profitable-claude/skills/affiliate-agent/tests/test_tenant_contract.py`
- Create after A3: `anicca-project/docs/affiliate-agent/OPERATOR-INSTALL-CONTRACT.md`

**Interfaces:**
- Produces: isolated accounts, state, disclosure identity, payout ownership, spend cap, and report.
- Consumes: the proven A3 contracts, never shared global credentials.

- [ ] **Step 1: Write failing tenant isolation tests**

```python
def test_tenants_cannot_share_accounts_or_money():
    a, b = tenant("a"), tenant("b")
    assert a.state_path != b.state_path
    with pytest.raises(TenantInvariant):
        b.import_receipt(a.provider_receipt())
```

- [ ] **Step 2: Implement identity/KYC/payout/spend-cap gates**

Each operator owns accounts and payouts. Stop at `AUTH_REQUIRED` for personal
contractual actions; never copy cookies, IDs, receipts, or audience data.

- [ ] **Step 3: Implement export/deletion and tenant reports**

Money, clicks, experiments, and credentials are isolated. Product copy promises
auditable automation, not income.

- [ ] **Step 4: Run adversarial isolation tests and canary one installation**

Do not roll out publicly until the canary reproduces software E2E under its own
accounts without original-Agent state access.

### Task 19: Scale a diversified network from $10k to $10M

**Files:**
- Extend after A3: `profitable-claude/skills/affiliate-agent/scripts/allocator.py`
- Extend after A3: `profitable-claude/skills/affiliate-agent/scripts/report.py`
- Test: `profitable-claude/skills/affiliate-agent/tests/test_scale_controller.py`
- Update: `anicca-project/docs/affiliate-agent/AFFILIATE-AGENT-SSOT.md`

**Interfaces:**
- Produces: budget-capped pod creation, staged promotion, rollback, and network receipts.
- Consumes: proven economics, cash receipts, partner capacity, policy modules, and tenant isolation.

- [ ] **Step 1: Write failing scale-cap and concentration tests**

```python
def test_unproven_pod_cannot_exceed_canary_budget():
    assert scale(pod(mature=False), requested=1000).approved <= pod().canary_cap

def test_provider_share_over_forty_percent_blocks_scale():
    assert scale(network(provider_share=0.41), requested=100).status == "BLOCKED_CONCENTRATION"
```

- [ ] **Step 2: Implement staged pod promotion and rollback**

Stages are sandbox, canary, limited, production, and scaled. Mature net evidence
advances a stage; reversal, policy, or margin harm rolls back.

- [ ] **Step 3: Close $100k monthly without a dimension above 40%**

Require three months, direct-partner evidence, cost, compliance, and recovery
capacity before adding regions or regulated verticals.

- [ ] **Step 4: Close $1M monthly with direct contracts and multi-region operations**

Receipt provider postbacks/APIs, contract terms, approval delays, finance,
privacy, and legal/KYC boundaries. Search/X cannot be a single point of failure.

- [ ] **Step 5: Grow 25-50 independently proven pods**

Every pod keeps its own economics and rollback. Aggregate volume cannot override
local net-loss, reversal, policy, or concentration stops.

- [ ] **Step 6: Close $10M monthly net only from external receipts**

Require one closed month at $10M equivalent net, no provider/offer/channel/
language above 40%, no internal/self payments, explicit legal/KYC exceptions,
and no routine human production or repair. Publish a sanitized audit; never
claim the result is guaranteed for each operator.

---

## Final verification commands

```bash
cd /Users/anicca/profitable-claude/.worktrees/affiliate-agent-runtime
/usr/bin/python3 -m compileall -q skills/affiliate-agent/scripts
python3 -m pytest skills/affiliate-agent/tests -q
python3 -m pytest skills/writer-agent/tests -q

cd /Users/anicca/anicca-project/.worktrees/affiliate-agent-api
npm --prefix apps/api test -- --run

git status --short
git log -1 --oneline
```

Expected final software evidence:

- focused and regression suites pass;
- redirect deployment matches the pushed commit;
- one live JA and one live EN placement have policy, publish, readback, redirect,
  and click receipts;
- launchd workers run without chat and resume without duplicates;
- Web and Telegram use one snapshot hash;
- money remains truthful when external commission is absent;
- A1, A3, and $10M stay open until their exact external receipt contracts pass.
