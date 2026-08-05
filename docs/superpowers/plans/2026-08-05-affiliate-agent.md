
# Affiliate Agent Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build and launch a bilingual, receipt-backed Affiliate Agent that autonomously researches, publishes, attributes, reconciles, repairs, and improves until externally verified revenue gates are met.

**Architecture:** The existing `profitable-claude/skills/affiliate` runtime is migrated into a hybrid Agent: Terra-high observes and plans through a semantic CloakBrowser/API tool harness, while a deterministic Python/SQLite kernel owns policy, budgets, idempotency, receipts, money, recovery, and Telegram delivery. The Life Manager API in `anicca-project` owns the public placement redirect and durable click ingest. Writer/Gig/shared-browser contracts are reused by interface, but every money/state ledger remains isolated.

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
- Migrate the existing `skills/affiliate` tree in place; preserve legacy
  commission watermark, lessons, queue/posted history, and wrapper entrypoints.
- Runtime market/browser/content/recovery judgment uses `gpt-5.6-terra` at
  `high`; Luna cannot make money-affecting or publication decisions initially.
- Sol-high requires a one-use trigger receipt for legal/financial claims,
  high-value publication, new-provider or prompt promotion, and adversarial samples.
- The model proposes one typed semantic action; the deterministic kernel executes
  only allowlisted tools and verifies the result.
- Exact prompt copying requires a compatible license and provenance receipt;
  public creator workflows are paraphrased patterns, not claimed prompt copies.
- Every meaningful action creates a Japanese natural-language `ActionEvent` and
  durable Telegram outbox row; ambiguous delivery is never blindly resent.
- Implementation uses one isolated Terra-max engineer per task packet. The root
  session owns task selection, diff inspection, tests, SSOT, and live verification.

---

## Remaining-work index

All checkboxes are initially open. A checkbox closes only with the command or
external receipt named in that step; prose updates alone do not close work.

| Phase | Tasks | Exit evidence |
|---|---:|---|
| P0 Agent foundation | F1-F6, 1 | Legacy migration, Terra brain, prompt registry, CloakBrowser harness, durable queue, Telegram action outbox, one runtime root |
| P1 Truth foundation | 2-5 | Typed Affiliate ledger, provider normalization, deployed redirect contract, click sync |
| P2 Useful production | 6-8 | Evidence/policy pass, bilingual manifests, receipted public placements |
| P3 Closed loop | 9-13 | Commission reconciliation, learning, recovery, reports, launchd |
| P4 Real E2E and first money | 14-16 | Live HTTPS redirect, JA/EN public readback, first approved commission |
| P5 Initial business | 17 | Four positive weeks and three qualifying $10k months |
| P6 Decentralized scale | 18-19 | Tenant-isolated recipe and staged network gates through $10M net, then an explicitly receipted $100M horizon |

The implementation path is P0 → P1 → P2 → P3 → P4. Foundation tasks are
sequential because they establish shared contracts. Revenue operation P5 starts
after A1. Tenantization and network scale P6 remain disabled until A3 proves the
recipe with this Agent's own external receipts.

---

## File map

### Runtime repository: `profitable-claude`

| Path | Responsibility |
|---|---|
| `skills/affiliate/SKILL.md` | Runtime identity and commands |
| `skills/affiliate/runtime/model-runner.sh` | Terra-high/Sol-high process boundary |
| `skills/affiliate/config/model-routing.json` | Receipt-tested model/effort policy |
| `skills/affiliate/config/providers.json` | Provider/account capabilities without secrets |
| `skills/affiliate/config/policy-rules.json` | Versioned policy/disclosure rules |
| `skills/affiliate/scripts/contracts.py` | Canonical validation and enums |
| `skills/affiliate/scripts/ledger.py` | Affiliate-only SQLite and receipts |
| `skills/affiliate/scripts/agent_brain.py` | Bounded context packet and one-action Terra turn |
| `skills/affiliate/scripts/prompt_registry.py` | Licensed/public-pattern provenance and prompt versions |
| `skills/affiliate/scripts/browser_harness.py` | Semantic CloakBrowser/CDP observation/action/verification |
| `skills/affiliate/scripts/action_events.py` | Natural-language action envelopes |
| `skills/affiliate/scripts/telegram_report.py` | Immediate/digest reporting and message receipts |
| `lib/telegram_outbox.py` | Shared at-most-once Telegram delivery primitive |
| `skills/affiliate/scripts/providers/*.py` | Generic browser/API/report provider protocol |
| `skills/affiliate/config/provider-playbooks/*.json` | Versioned learned semantic playbooks |
| `skills/affiliate/scripts/evidence.py` | Official-source evidence packs |
| `skills/affiliate/scripts/policy.py` | Fail-closed policy gate |
| `skills/affiliate/scripts/content.py` | JA/EN manifests and Writer bridge |
| `skills/affiliate/scripts/publisher.py` | Owned/Postiz publication and readback |
| `skills/affiliate/scripts/click_sync.py` | Life Manager placement/click API client |
| `skills/affiliate/scripts/reconcile.py` | Conversion/commission reconciliation |
| `skills/affiliate/scripts/allocator.py` | Exploration and concentration allocation |
| `skills/affiliate/scripts/learning.py` | Mature one-variable experiments |
| `skills/affiliate/scripts/recovery.py` | Same-run resume and quarantine |
| `skills/affiliate/scripts/orchestrator.py` | Hourly/daily state machine |
| `skills/affiliate/scripts/report.py` | Web/Telegram canonical snapshot |
| `skills/affiliate/scripts/install.sh` | launchd install and kickstart |
| `skills/affiliate/launchd/*.plist` | Production worker definitions |
| `skills/affiliate/tests/` | Unit, contract, recovery, and fixture tests |

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

## Context-saving execution protocol

For each task, the root session creates one compact task packet containing only:

1. design requirement and current checkbox;
2. exact owned files and forbidden files;
3. consumed/produced interfaces;
4. baseline commit and current failing test;
5. required commands and expected evidence;
6. related prior receipt hashes, not the full conversation.

A fresh Terra-max engineer receives that packet with no full-history fork, works
only in the named worktree/files, runs RED→GREEN, and returns commit plus test
evidence. The root inspects the diff, reruns focused tests, performs any real E2E,
updates this plan/SSOT, and closes the task. Sol-high review is added only for
irreversible external action, money-loss risk, legal/financial claims, uncertain
strategy promotion, or the periodic adversarial sample. Tasks sharing runtime
state, auth, a browser profile, or a branch never execute concurrently.

---

### Task F1: Characterize and migrate the legacy Affiliate loop without losing truth

**Files:**
- Create: `profitable-claude/skills/affiliate/scripts/legacy_migration.py`
- Test: `profitable-claude/skills/affiliate/tests/test_legacy_migration.py`
- Modify after parity: `profitable-claude/skills/affiliate/run.sh`
- Modify after parity: `profitable-claude/skills/affiliate/affiliate-cli.sh`
- Preserve: `profitable-claude/skills/affiliate/measure_commission.py`
- Preserve: `profitable-claude/skills/affiliate/state/`

**Interfaces:**
- Produces: `LegacyInventory`, content-addressed migration receipt, and compatibility wrappers.
- Consumes: existing watermark, lessons, queue/posted directories, tmux/launchd state, and legacy tests.

- [ ] **Step 1: Capture read-only baseline evidence**

```bash
bash skills/affiliate/affiliate-cli.sh --status
python3 skills/affiliate/tests/test_affiliate_verify.py
python3 skills/affiliate/tests/test_measure_commission.py
find skills/affiliate -maxdepth 3 -type f -print0 | sort -z | xargs -0 shasum -a 256
```

Expected current runtime fact: core is `DEAD`; the two legacy focused suites pass
or any failure is recorded before migration.

- [ ] **Step 2: Write the failing state-preservation tests**

```python
def test_legacy_watermark_is_imported_as_unattributed_history(tmp_path):
    result = migrate(fixture_tree(tmp_path), target_db=tmp_path / "affiliate.sqlite")
    assert result.watermark_class == "legacy_unattributed"
    assert result.new_revenue_minor == 0

def test_migration_replay_is_byte_stable(tmp_path):
    first = migrate(fixture_tree(tmp_path), target_db=tmp_path / "affiliate.sqlite")
    second = migrate(fixture_tree(tmp_path), target_db=tmp_path / "affiliate.sqlite")
    assert first.receipt_sha256 == second.receipt_sha256
    assert second.rows_added == 0

def test_legacy_files_are_not_deleted(tmp_path):
    root = fixture_tree(tmp_path)
    before = tree_hashes(root)
    migrate(root, target_db=tmp_path / "affiliate.sqlite")
    assert tree_hashes(root) == before
```

- [ ] **Step 3: Run RED**

```bash
python3 -m pytest skills/affiliate/tests/test_legacy_migration.py -q
```

Expected: FAIL because `legacy_migration.py` does not exist.

- [ ] **Step 4: Implement inventory and append-only import**

Record path/hash/size/state for legacy artifacts. Import aggregate commission
watermark as `legacy_unattributed`, lessons as historical observations, and
queue/posted entries as legacy artifacts. Never manufacture click or placement
lineage.

- [ ] **Step 5: Run GREEN and legacy regression**

```bash
python3 -m pytest skills/affiliate/tests/test_legacy_migration.py -q
python3 skills/affiliate/tests/test_affiliate_verify.py
python3 skills/affiliate/tests/test_measure_commission.py
```

- [ ] **Step 6: Convert legacy entrypoints to compatibility wrappers only after parity**

`affiliate-cli.sh --status` reports the new orchestrator plus migration state.
`run.sh` delegates one bounded wake. The old fixed Instagram/Amazon behavior
remains callable only through an explicitly named legacy fixture path and is not
scheduled.

- [ ] **Step 7: Commit and push**

```bash
git add skills/affiliate
git commit -m "refactor(affiliate): preserve and migrate legacy loop state"
git push
```

### Task F2: Build the Terra Agent brain and receipt-gated model boundary

**Files:**
- Create: `profitable-claude/skills/affiliate/config/model-routing.json`
- Create: `profitable-claude/skills/affiliate/runtime/model-runner.sh`
- Create: `profitable-claude/skills/affiliate/scripts/agent_brain.py`
- Test: `profitable-claude/skills/affiliate/tests/test_model_runner.py`
- Test: `profitable-claude/skills/affiliate/tests/test_agent_brain.py`

**Interfaces:**
- Produces: `make_context_packet(state) -> ContextPacket` and `propose_action(packet) -> ActionProposal`.
- Consumes: bounded state/receipt/tool schemas; never raw credential files or complete logs.

- [ ] **Step 1: Write the failing model-routing tests**

```python
def test_strategic_agent_defaults_to_terra_high(fake_codex):
    result = run_model(role="strategy", prompt="one action", codex=fake_codex)
    assert result.model == "gpt-5.6-terra"
    assert result.effort == "high"

def test_luna_cannot_receive_money_or_publication_role():
    with pytest.raises(ModelRoutingInvariant):
        route(role="publication_decision", requested_model="gpt-5.6-luna")

def test_sol_requires_matching_one_use_trigger(tmp_path):
    receipt = sol_receipt(tmp_path, trigger="new_provider_promotion")
    first = run_model(role="sol_audit", trigger_receipt=receipt)
    assert first.model == "gpt-5.6-sol"
    with pytest.raises(TriggerAlreadyClaimed):
        run_model(role="sol_audit", trigger_receipt=receipt)
```

- [ ] **Step 2: Write the failing one-action output tests**

```python
def test_agent_returns_exactly_one_typed_action(fake_model):
    proposal = propose_action(context_packet(), model=fake_model)
    assert proposal.tool in ALLOWLISTED_TOOLS
    assert proposal.idempotency_key
    assert proposal.verification_plan
    assert proposal.human_summary_ja

def test_context_packet_excludes_secrets_and_full_logs():
    packet = make_context_packet(state_with_secret_fixture())
    encoded = packet.to_json()
    assert "POSTIZ_API_KEY" not in encoded
    assert len(encoded) <= 60000
```

- [ ] **Step 3: Run RED**

```bash
python3 -m pytest skills/affiliate/tests/test_model_runner.py skills/affiliate/tests/test_agent_brain.py -q
```

- [ ] **Step 4: Implement the isolated runner**

Port the proven Writer runner contract into Affiliate-owned state. Terra-high is
the only default strategic route. Sol-high accepts declared one-use triggers.
Provider failure returns an explicit retryable receipt; it never silently routes
a strategic call to Luna.

- [ ] **Step 5: Implement bounded context and JSON-schema output**

The packet contains goal, state hash, eligible offers, recent receipts, waits,
budget, last lesson, and tool schemas. Reject multiple actions, unknown tools,
missing risk/idempotency/verification, and non-Japanese human summary.

- [ ] **Step 6: Run GREEN and process-boundary replay**

```bash
python3 -m pytest skills/affiliate/tests/test_model_runner.py skills/affiliate/tests/test_agent_brain.py -q
/usr/bin/python3 -m py_compile skills/affiliate/scripts/agent_brain.py
```

- [ ] **Step 7: Commit and push**

```bash
git add skills/affiliate
git commit -m "feat(affiliate): add Terra-high agent brain"
git push
```

### Task F3: Create the prompt provenance registry and licensed seed pack

**Files:**
- Create: `profitable-claude/skills/affiliate/scripts/prompt_registry.py`
- Create: `profitable-claude/skills/affiliate/config/prompt-seeds.json`
- Create: `profitable-claude/skills/affiliate/prompts/system.md`
- Create: `profitable-claude/skills/affiliate/prompts/research.md`
- Create: `profitable-claude/skills/affiliate/prompts/content.md`
- Create: `profitable-claude/skills/affiliate/prompts/recovery.md`
- Test: `profitable-claude/skills/affiliate/tests/test_prompt_registry.py`

**Interfaces:**
- Produces: immutable `PromptVersion`, active role mapping, mutation proposal, and rollback hash.
- Consumes: licensed prompt sources or paraphrased public workflow evidence.

- [ ] **Step 1: Write the failing provenance tests**

```python
def test_exact_copy_requires_compatible_license(tmp_path):
    with pytest.raises(PromptProvenanceInvariant):
        registry(tmp_path).register(seed(exact_copy=True, license="unknown"))

def test_public_creator_pattern_is_marked_paraphrase(tmp_path):
    row = registry(tmp_path).register(seed(
        source_url="https://www.smartpassiveincome.com/blog/5-figure-jv-affiliate-promotion/",
        evidence_class="public_workflow",
        exact_copy=False,
    ))
    assert row.adaptation_kind == "paraphrased_pattern"

def test_prompt_mutation_changes_one_field_and_keeps_rollback(tmp_path):
    base = registry(tmp_path).register(seed_fixture())
    candidate = registry(tmp_path).mutate(base.prompt_id, {"cta_rule": "one measurable CTA"})
    assert candidate.changed_fields == ("cta_rule",)
    assert candidate.parent_sha256 == base.prompt_sha256
```

- [ ] **Step 2: Run RED**

```bash
python3 -m pytest skills/affiliate/tests/test_prompt_registry.py -q
```

- [ ] **Step 3: Register seed provenance**

Use MIT-licensed Affitor prompt structures as exact-copy candidates only after
recording repository URL, license, source file, and source hash. Store Pat Flynn,
Michelle, Rakuten, afb, and X creator material only as paraphrased workflow
patterns with evidence class and URL.

- [ ] **Step 4: Implement immutable activation and rollback**

Active role mapping points to hashes, not mutable files. Activation requires an
evaluation receipt; rollback restores the prior hash. Unknown-source prompt text
cannot enter a production packet.

- [ ] **Step 5: Run GREEN, commit, and push**

```bash
python3 -m pytest skills/affiliate/tests/test_prompt_registry.py -q
git add skills/affiliate
git commit -m "feat(affiliate): register licensed prompt provenance"
git push
```

### Task F4: Build the semantic CloakBrowser tool harness

**Files:**
- Create: `profitable-claude/skills/affiliate/scripts/browser_harness.py`
- Create: `profitable-claude/skills/affiliate/config/browser-tools.json`
- Test: `profitable-claude/skills/affiliate/tests/test_browser_harness.py`
- Reuse: `profitable-claude/skills/_shared/browser/ensure_browser.sh`
- Reuse: `profitable-claude/skills/_shared/browser/scripts/cdp_context_lease.py`
- Reuse: `profitable-claude/skills/_shared/browser/scripts/scout.py`

**Interfaces:**
- Produces: `observe`, `navigate`, `act`, `download`, `verify`, and `BrowserReceipt`.
- Consumes: one task-owned CDP lease or one dedicated configured profile, semantic action schema, and expected change.

- [ ] **Step 1: Write the failing lease and identity tests**

```python
def test_browser_action_requires_owned_lease(fake_cdp):
    with pytest.raises(BrowserInvariant, match="lease"):
        BrowserHarness(fake_cdp).act(action_fixture())

def test_side_effect_requires_expected_account_identity(fake_cdp):
    harness = BrowserHarness(fake_cdp, expected_identity="@anicca_en")
    fake_cdp.identity = "@someone_else"
    with pytest.raises(BrowserInvariant, match="identity"):
        harness.act(post_action())
```

- [ ] **Step 2: Write the failing semantic verification tests**

```python
def test_model_cannot_supply_raw_javascript(fake_cdp):
    with pytest.raises(BrowserInvariant):
        BrowserHarness(fake_cdp).act({"operation": "evaluate", "script": "fetch('/x')"})

def test_dom_drift_returns_replan_not_selector_retry(fake_cdp):
    fake_cdp.change_dom_after_observe = True
    result = BrowserHarness(fake_cdp).act(click_semantic("Export report"))
    assert result.status == "REPLAN_REQUIRED"
    assert result.attempts == 1
```

- [ ] **Step 3: Run RED**

```bash
python3 -m pytest skills/affiliate/tests/test_browser_harness.py -q
```

- [ ] **Step 4: Implement tool allowlist and browser receipts**

Public observation invokes CRWL. Authenticated observation/action acquires a CDP
context lease or dedicated profile, verifies identity, records before/after URL
and observation hashes, expected/actual change, and always releases/heartbeats
the lease. Selectors and raw CDP stay inside the harness.

- [ ] **Step 5: Add recovery tests**

Cover dead `:9222`, expired lease, orphan GC, login loss, CAPTCHA/auth-required,
download timeout, and changed DOM. Each returns a typed wait/quarantine/replan
state instead of an infinite retry.

- [ ] **Step 6: Run GREEN, commit, and push**

```bash
python3 -m pytest skills/affiliate/tests/test_browser_harness.py -q
git add skills/affiliate
git commit -m "feat(affiliate): add semantic CloakBrowser harness"
git push
```

### Task F5: Journal every meaningful action and deliver natural-language Telegram receipts

**Files:**
- Create: `profitable-claude/lib/telegram_outbox.py`
- Modify: `profitable-claude/skills/gig-work/scripts/telegram_outbox.py`
- Create: `profitable-claude/skills/affiliate/scripts/action_events.py`
- Create: `profitable-claude/skills/affiliate/scripts/telegram_report.py`
- Test: `profitable-claude/skills/affiliate/tests/test_action_events.py`
- Test: `profitable-claude/skills/affiliate/tests/test_telegram_outbox.py`
- Regression: `profitable-claude/skills/gig-work/tests/test_telegram_outbox.py`

**Interfaces:**
- Produces: `ActionEvent`, `enqueue_event()`, immediate/digest delivery, and provider `message_id`.
- Consumes: action proposal, execution/verification receipts, money delta, and next automatic action.

- [ ] **Step 1: Write the failing natural-language envelope tests**

```python
def test_external_action_message_explains_full_boundary():
    event = build_event(external_action_fixture())
    assert event.human_message_ja
    for field in ("見た", "選んだ", "結果", "証拠", "次"):
        assert field in event.human_message_ja

def test_low_level_browser_steps_group_under_one_semantic_action():
    event = build_event(browser_steps_fixture(count=7))
    assert event.kind == "provider_report_download"
    assert event.low_level_step_count == 7
    assert event.telegram_message_count == 1
```

- [ ] **Step 2: Write the failing at-most-once tests**

```python
def test_same_event_is_sent_once_and_stores_message_id(outbox, transport):
    outbox.enqueue(event_fixture())
    first = outbox.dispatch(transport)
    second = outbox.dispatch(transport)
    assert first.message_id == "tg-9001"
    assert second.status == "queue_empty"
    assert transport.calls == 1

def test_ambiguous_send_is_not_blind_retried(outbox, ambiguous_transport):
    outbox.enqueue(event_fixture())
    assert outbox.dispatch(ambiguous_transport).status == "delivery_unknown"
    assert outbox.dispatch(ambiguous_transport).status == "queue_empty"
```

- [ ] **Step 3: Run RED**

```bash
python3 -m pytest skills/affiliate/tests/test_action_events.py skills/affiliate/tests/test_telegram_outbox.py -q
```

- [ ] **Step 4: Extract the proven shared outbox with compatibility import**

Move the Gig Work implementation to `lib/telegram_outbox.py`; leave its original
module as a compatibility import. Preserve fencing tokens, leases, send-started,
`delivery_unknown`, provider ACK reconciliation, file mode `0600`, and existing
Gig behavior.

- [ ] **Step 5: Implement immediate and ordered-digest routing**

External side effects, failure, money, safety, quarantine, model escalation, and
KEEP/REVERT enqueue immediately. Successful internal observation actions keep
their own ledger row and enter the same-hour ordered digest. Every message stores
the same event key and snapshot hash as the Agent feed.

- [ ] **Step 6: Run GREEN and Gig regressions**

```bash
python3 -m pytest skills/affiliate/tests/test_action_events.py skills/affiliate/tests/test_telegram_outbox.py -q
python3 -m pytest skills/gig-work/tests/test_telegram_outbox.py skills/gig-work/tests/test_telegram_reporting.py -q
```

- [ ] **Step 7: Commit and push**

```bash
git add lib/telegram_outbox.py skills/gig-work/scripts/telegram_outbox.py skills/affiliate
git commit -m "feat(affiliate): report every semantic action to Telegram"
git push
```


### Task F6: Implement the durable work queue and bounded replanner

**Files:**
- Create: `profitable-claude/skills/affiliate/scripts/work_queue.py`
- Create: `profitable-claude/skills/affiliate/scripts/planner.py`
- Create: `profitable-claude/skills/affiliate/scripts/action_guard.py`
- Test: `profitable-claude/skills/affiliate/tests/test_work_queue.py`
- Test: `profitable-claude/skills/affiliate/tests/test_planner.py`

**Interfaces:**
- Produces: `WorkItem`, `claim_next()`, `complete()`, `wait()`, `resume_expired()`, and `AgentPlan`.
- Consumes: goal/state hashes, dependencies, budgets, action proposals, and verification receipts.

- [ ] **Step 1: Write the failing lease/fencing tests**

```python
def test_two_wakes_claim_one_item_once(queue):
    item = queue.enqueue(work_fixture())
    first = queue.claim_next(owner="wake-a", now=100)
    second = queue.claim_next(owner="wake-b", now=100)
    assert first.work_id == item.work_id
    assert second is None

def test_expired_lease_resumes_same_item_and_idempotency(queue):
    item = queue.enqueue(work_fixture(idempotency_key="publish:abc"))
    queue.claim_next(owner="dead", now=100, lease_seconds=30)
    resumed = queue.claim_next(owner="wake-b", now=131)
    assert resumed.work_id == item.work_id
    assert resumed.idempotency_key == "publish:abc"
    assert resumed.fencing_token == 2
```

- [ ] **Step 2: Write the failing independence and budget tests**

```python
def test_waiting_auth_does_not_block_research(queue):
    queue.enqueue(work_fixture(kind="provider_auth", state="WAITING", retry_at=500))
    queue.enqueue(work_fixture(kind="market_research", state="READY"))
    assert queue.claim_next(owner="wake", now=100).kind == "market_research"

def test_publication_budget_does_not_block_reconciliation(planner):
    plan = planner.plan(state(publication_budget_remaining=0))
    assert "publish" not in [x.kind for x in plan.work_items]
    assert "reconcile" in [x.kind for x in plan.work_items]

def test_planner_cannot_schedule_unknown_tool(planner):
    with pytest.raises(ActionGuardInvariant):
        planner.accept(model_plan(tool="arbitrary_shell"))
```

- [ ] **Step 3: Run RED**

```bash
python3 -m pytest skills/affiliate/tests/test_work_queue.py skills/affiliate/tests/test_planner.py -q
```

- [ ] **Step 4: Implement SQLite queue and legal transitions**

Use `BEGIN IMMEDIATE`, one lease owner, monotonic fencing token, dependency checks,
bounded attempts, explicit `READY/CLAIMED/WAITING/VERIFIED/FAILED/QUARANTINED`,
and append-only transition receipts.

- [ ] **Step 5: Implement the bounded replanner**

The planner may order eligible work and request one Agent action. The action guard
checks tool, origin, current state, budget, idempotency, and verification before
the executor sees it. Replanning cannot delete money/recovery work.

- [ ] **Step 6: Run GREEN, crash replay, commit, and push**

```bash
python3 -m pytest skills/affiliate/tests/test_work_queue.py skills/affiliate/tests/test_planner.py -q
git add skills/affiliate
git commit -m "feat(affiliate): add durable agent work queue"
git push
```


### Task 1: Establish isolated baselines and the Affiliate skill root

**Files:**
- Create: `profitable-claude/skills/affiliate/SKILL.md`
- Create: `profitable-claude/skills/affiliate/config/providers.json`
- Test: `profitable-claude/skills/affiliate/tests/test_skill_contract.py`

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
python3 -m pytest skills/affiliate/tests/test_skill_contract.py -q
```

Expected: FAIL because the skill and config do not exist.

- [ ] **Step 5: Add the minimal skill and registry**

`SKILL.md` names the design, separates Writer revenue, lists `hourly`, `daily`,
`reconcile`, `report`, and `status`, and forbids money without external receipts.
`providers.json` exactly matches the test fixture.

- [ ] **Step 6: Run GREEN, commit, and push**

```bash
python3 -m pytest skills/affiliate/tests/test_skill_contract.py -q
git add skills/affiliate
git commit -m "feat(affiliate): establish canonical runtime root"
git push -u origin feature/affiliate-agent-runtime
```

### Task 2: Implement canonical contracts and the immutable Affiliate ledger

**Files:**
- Create: `profitable-claude/skills/affiliate/scripts/contracts.py`
- Create: `profitable-claude/skills/affiliate/scripts/ledger.py`
- Test: `profitable-claude/skills/affiliate/tests/test_ledger.py`

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
python3 -m pytest skills/affiliate/tests/test_ledger.py -q
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
python3 -m pytest skills/affiliate/tests/test_ledger.py -q
/usr/bin/python3 -m py_compile skills/affiliate/scripts/contracts.py skills/affiliate/scripts/ledger.py
```

- [ ] **Step 6: Commit and push**

```bash
git add skills/affiliate
git commit -m "feat(affiliate): add receipt-backed commission ledger"
git push
```

### Task 3: Build generic provider connectors and verified playbooks

**Files:**
- Create: `profitable-claude/skills/affiliate/scripts/providers/base.py`
- Create: `profitable-claude/skills/affiliate/scripts/providers/api_connector.py`
- Create: `profitable-claude/skills/affiliate/scripts/providers/browser_connector.py`
- Create: `profitable-claude/skills/affiliate/scripts/providers/report_connector.py`
- Create: `profitable-claude/skills/affiliate/scripts/providers/recipe_registry.py`
- Create: `profitable-claude/skills/affiliate/config/provider-playbooks/amazon-jp.json`
- Create: `profitable-claude/skills/affiliate/config/provider-playbooks/rakuten-jp.json`
- Test: `profitable-claude/skills/affiliate/tests/test_providers.py`

**Interfaces:**
- Produces: connector protocol, candidate/verified/retired `ProviderRecipe`, `read_account()`,
  `list_offers()`, and `read_transactions(cursor)`.
- Consumes: provider-owned API/report/auth readbacks and semantic browser receipts;
  directories and model proposals supply candidates only.

- [ ] **Step 1: Write failing connector and recipe tests**

```python
def test_logged_out_account_is_not_executable():
    account = BrowserConnector(amazon_recipe(), FakeBrowser("sign-in-page.html")).read_account()
    assert account.auth_state == "AUTH_REQUIRED"
    assert account.executable is False

def test_verified_browser_recipe_adds_provider_without_python_module(registry):
    registry.verify(recipe(provider="new-asp", connector="browser"), verification_receipt())
    assert registry.connector_for("new-asp").list_offers()[0].source_sha256

def test_generated_recipe_cannot_expand_allowed_origins(registry):
    with pytest.raises(OriginPolicyError):
        registry.propose(recipe(origins=("https://untrusted.example",)))

def test_ui_drift_quarantines_only_one_recipe(registry):
    result = registry.execute("amazon-jp", changed_dom_receipt())
    assert result.state == "RECIPE_QUARANTINED"
    assert registry.state("rakuten-jp") == "VERIFIED"
```

- [ ] **Step 2: Run RED**

```bash
python3 -m pytest skills/affiliate/tests/test_providers.py -q
```

- [ ] **Step 3: Implement fail-closed connector and recipe contracts**

Keep provider identity and mutable browser/API steps in signed JSON recipes, not
provider-specific Python modules. A candidate recipe becomes executable only after
origin, auth, selector/readback, terms, and rollback verification. Expired or drifted
recipes re-enter discovery and cannot silently broaden permissions.

- [ ] **Step 4: Implement normalized accounts, offers, reports, and cursor state**

An offer requires account identity, current official terms, affiliate ID/tag,
allowed channel, and verified destination host. Normalize pending, approved,
reversed, and paid while retaining raw payload hash and external transaction ID.
Never infer a missing amount.

- [ ] **Step 5: Run GREEN, commit, and push**

```bash
python3 -m pytest skills/affiliate/tests/test_providers.py skills/affiliate/tests/test_ledger.py -q
git add skills/affiliate
git commit -m "feat(affiliate): add verified provider playbooks"
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
- Create: `profitable-claude/skills/affiliate/scripts/click_sync.py`
- Test: `profitable-claude/skills/affiliate/tests/test_click_sync.py`

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
python3 -m pytest skills/affiliate/tests/test_click_sync.py -q
```

- [ ] **Step 3: Hash API receipts and commit each page atomically**

Validate returned placement identity and advance the cursor only after the whole
page commits.

- [ ] **Step 4: Run GREEN, commit, and push**

```bash
python3 -m pytest skills/affiliate/tests/test_click_sync.py skills/affiliate/tests/test_ledger.py -q
git add skills/affiliate
git commit -m "feat(affiliate): sync placements and click receipts"
git push
```

### Task 6: Implement official evidence packs and fail-closed policy

**Files:**
- Create: `profitable-claude/skills/affiliate/config/policy-rules.json`
- Create: `profitable-claude/skills/affiliate/scripts/evidence.py`
- Create: `profitable-claude/skills/affiliate/scripts/policy.py`
- Test: `profitable-claude/skills/affiliate/tests/test_evidence_policy.py`

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
python3 -m pytest skills/affiliate/tests/test_evidence_policy.py -q
```

- [ ] **Step 3: Implement locale/channel disclosures and category quarantine**

Include JA/EN general disclosure, Amazon statement, channel allowlists, prohibited
brand bidding, unsafe-category default denial, and source freshness. A model
cannot override deterministic failure.

- [ ] **Step 4: Run GREEN, commit, and push**

```bash
python3 -m pytest skills/affiliate/tests/test_evidence_policy.py -q
git add skills/affiliate
git commit -m "feat(affiliate): gate evidence claims and disclosures"
git push
```

### Task 7: Build bilingual content manifests and the Writer bridge

**Files:**
- Create: `profitable-claude/skills/affiliate/scripts/content.py`
- Test: `profitable-claude/skills/affiliate/tests/test_content.py`
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
python3 -m pytest skills/affiliate/tests/test_content.py -q
```

- [ ] **Step 3: Add the narrow Writer bridge**

Pass reader job, evidence, structure, locale, and output paths. Record the Writer
contract/version/hash. Never read or write Writer money/topic state.

- [ ] **Step 4: Run Affiliate and Writer contract tests**

```bash
python3 -m pytest skills/affiliate/tests/test_content.py -q
bash skills/writer-agent/tests/editorial-citation-contract.sh
bash skills/writer-agent/tests/cta-publication-boundary.sh
```

- [ ] **Step 5: Commit and push**

```bash
git add skills/affiliate
git commit -m "feat(affiliate): create bilingual decision manifests"
git push
```

### Task 8: Publish owned and Postiz placements with public readback

**Files:**
- Create: `profitable-claude/skills/affiliate/scripts/publisher.py`
- Test: `profitable-claude/skills/affiliate/tests/test_publisher.py`

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
python3 -m pytest skills/affiliate/tests/test_publisher.py -q
```

- [ ] **Step 3: Implement Postiz and owned-page adapters**

Require API publication ID/URL and rendered public readback. X account identity
must match the configured dedicated account receipt.

- [ ] **Step 4: Run GREEN and Writer isolation regression**

```bash
python3 -m pytest skills/affiliate/tests/test_publisher.py -q
bash skills/writer-agent/tests/platform-dispatch-isolation.sh
```

- [ ] **Step 5: Commit and push**

```bash
git add skills/affiliate
git commit -m "feat(affiliate): publish receipted Postiz placements"
git push
```

### Task 9: Reconcile conversions, commissions, reversals, and payouts

**Files:**
- Create: `profitable-claude/skills/affiliate/scripts/reconcile.py`
- Test: `profitable-claude/skills/affiliate/tests/test_reconcile.py`

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
python3 -m pytest skills/affiliate/tests/test_reconcile.py -q
```

- [ ] **Step 3: Implement cursor-safe batches and conflict quarantine**

Provider cursor advances only after all rows append. Conflicting identity,
amount, or currency becomes explicit conflict and never overwrites.

- [ ] **Step 4: Run GREEN twice, commit, and push**

```bash
python3 -m pytest skills/affiliate/tests/test_reconcile.py skills/affiliate/tests/test_ledger.py -q
git add skills/affiliate
git commit -m "feat(affiliate): reconcile provider commissions"
git push
```

### Task 10: Implement allocation and bounded learning

**Files:**
- Create: `profitable-claude/skills/affiliate/scripts/allocator.py`
- Create: `profitable-claude/skills/affiliate/scripts/learning.py`
- Test: `profitable-claude/skills/affiliate/tests/test_learning.py`

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
python3 -m pytest skills/affiliate/tests/test_learning.py -q
```

- [ ] **Step 3: Implement maturity and strategy-consumption receipts**

Require same-age comparable cohorts and ten mature placements unless a stronger
paid outcome closes deterministically. Only `KEEP` changes active strategy.

- [ ] **Step 4: Run GREEN, commit, and push**

```bash
python3 -m pytest skills/affiliate/tests/test_learning.py -q
git add skills/affiliate
git commit -m "feat(affiliate): allocate from mature net receipts"
git push
```

### Task 11: Implement durable orchestration, waits, and recovery

**Files:**
- Create: `profitable-claude/skills/affiliate/scripts/orchestrator.py`
- Create: `profitable-claude/skills/affiliate/scripts/recovery.py`
- Test: `profitable-claude/skills/affiliate/tests/test_orchestrator.py`
- Test: `profitable-claude/skills/affiliate/tests/test_recovery.py`

**Interfaces:**
- Produces: `hourly_wake()`, `daily_wake()`, `resume(run_id)`, legal transitions, and quarantines.
- Consumes: the F6 queue/planner, one guarded Agent action at a time, and prior
  components through explicit interfaces.

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

def test_hourly_wake_claims_one_durable_item_not_a_fixed_script(harness):
    result = harness.hourly()
    assert result.claimed_work_id == harness.queue.first_ready_id
    assert result.semantic_actions_executed == 1
```

- [ ] **Step 2: Run RED and implement legal state transitions**

```bash
python3 -m pytest skills/affiliate/tests/test_orchestrator.py skills/affiliate/tests/test_recovery.py -q
```

- [ ] **Step 3: Implement durable wait/retry ownership**

Store external reason, owner, retry time, attempt count, and independent work.
Honor `Retry-After`; move permanent failures to quarantine.

- [ ] **Step 4: Run crash matrix GREEN, commit, and push**

```bash
python3 -m pytest skills/affiliate/tests/test_orchestrator.py skills/affiliate/tests/test_recovery.py -q
git add skills/affiliate
git commit -m "feat(affiliate): add same-run recovery"
git push
```

### Task 12: Generate one money-first Web/Telegram snapshot

**Files:**
- Create: `profitable-claude/skills/affiliate/scripts/report.py`
- Test: `profitable-claude/skills/affiliate/tests/test_report.py`

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
python3 -m pytest skills/affiliate/tests/test_report.py -q
```

- [ ] **Step 3: Render money, health, gates, and next action**

Separate approved, paid, reversed, pending, unknown, net, and cost. Show public
URLs, run, quarantine, retry, software/A1/A3/$10M gates, and next owner action.

- [ ] **Step 4: Run GREEN, inspect 390px fixture, commit, and push**

```bash
python3 -m pytest skills/affiliate/tests/test_report.py -q
git add skills/affiliate
git commit -m "feat(affiliate): report money and runtime health"
git push
```

### Task 13: Install and verify launchd ownership

**Files:**
- Create: `profitable-claude/skills/affiliate/launchd/ai.anicca.affiliate-hourly.plist`
- Create: `profitable-claude/skills/affiliate/launchd/ai.anicca.affiliate-daily.plist`
- Create: `profitable-claude/skills/affiliate/launchd/ai.anicca.affiliate-report.plist`
- Create: `profitable-claude/skills/affiliate/scripts/install.sh`
- Test: `profitable-claude/skills/affiliate/tests/test_launchd_wiring.py`

**Interfaces:**
- Produces: installed labels, locks, logs, status receipts, and immediate kickstart.
- Consumes: protected env, canonical root, and Python 3.9 entrypoints.

- [ ] **Step 1: Write failing plist tests**

```python
def test_plists_use_canonical_root_and_run_at_load():
    for path in PLISTS:
        payload = plistlib.loads(path.read_bytes())
        assert payload["RunAtLoad"] is True
        assert "/skills/affiliate/" in " ".join(payload["ProgramArguments"])
        assert payload["StandardOutPath"] != payload["StandardErrorPath"]
```

- [ ] **Step 2: Run RED; implement plists and idempotent installer**

```bash
python3 -m pytest skills/affiliate/tests/test_launchd_wiring.py -q
```

- [ ] **Step 3: Run GREEN and Python 3.9 compilation**

```bash
python3 -m pytest skills/affiliate/tests/test_launchd_wiring.py -q
/usr/bin/python3 -m compileall -q skills/affiliate/scripts
```

- [ ] **Step 4: Commit and push before live state changes**

```bash
git add skills/affiliate
git commit -m "feat(affiliate): install autonomous workers"
git push
```

- [ ] **Step 5: Install, kickstart, and observe real exits**

```bash
bash skills/affiliate/scripts/install.sh
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
- Runtime state: `profitable-claude/skills/affiliate/state/` (gitignored)
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
python3 -m pytest skills/affiliate/tests -q
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
- Create after A3: `profitable-claude/skills/affiliate/scripts/tenant_contract.py`
- Test after A3: `profitable-claude/skills/affiliate/tests/test_tenant_contract.py`
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

### Task 19: Scale a diversified network from $10k through $10M to the $100M horizon

**Files:**
- Extend after A3: `profitable-claude/skills/affiliate/scripts/allocator.py`
- Extend after A3: `profitable-claude/skills/affiliate/scripts/report.py`
- Test: `profitable-claude/skills/affiliate/tests/test_scale_controller.py`
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

- [ ] **Step 7: Keep $100M as a separately receipted horizon**

Do not relabel GMV, clicks, pending commissions, tenant sales, or projections as
affiliate revenue. The gate closes only for one externally settled month at $100M
equivalent net affiliate commission, with audited currency conversion, reversals,
costs, concentration, policy, partner-capacity, and tenant isolation. Until that
receipt exists, the report must say `HORIZON_OPEN`, never “achieved” or “expected.”

---

## Final verification commands

```bash
cd /Users/anicca/profitable-claude/.worktrees/affiliate-agent-runtime
/usr/bin/python3 -m compileall -q skills/affiliate/scripts
python3 -m pytest skills/affiliate/tests -q
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
