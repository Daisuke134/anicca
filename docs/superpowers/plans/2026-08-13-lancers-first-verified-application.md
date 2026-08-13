# Lancers Canonical First Verified Application Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Life Manager の canonical main からだけ Lancers acquisition loop を配備し、既存の不確実な2応募を再送せず公式readbackしながら、別の利益性ある案件1件を一度だけ応募して公式 proposal ID と `ApplicationReceipt` 1件まで閉じる。

**Architecture:** entity の状態は直線だが、実行はlane単位である。このsliceは acquisition lane だけを実装し、既存JSON stateとmarketplace ledgerを再利用する。canonical sourceからcommit SHA固定releaseを組み立て、最初は全pending対象のreconcile-onlyで起動し、その検証後だけ通常discovery/submit modeへ切り替える。

**Tech Stack:** Python 3 stdlib、`jsonschema`、Playwright/CDP、既存 agent runner、既存 JSON state、既存 SQLite marketplace ledger、launchd、zsh。

## Global Constraints

- Ponytail `full`: 新DB、新common kernel、per-project process、resident straight-shot process、sales/fulfillment/finance実装を作らない。
- primary はplan/spec/最終検証を担当し、production code/test/SQLはLunaが書く。
- TDD: production変更より先に最小の失敗testを実行し、期待した理由でREDを観測する。
- Review budget: このsliceのfresh adversarial reviewは既に `fba8a3d83` に対して1/1を使用済み。追加reviewerを起動しない。同じLunaが3件のFIX_FIRSTを直し、primaryが機械検証する。
- application launchd `ai.anicca.lancers-revenue-application` はTask 5までdisabled/unloadedのままにする。
- `5585496` と `5586112` はreadback-only quarantineであり、submitterを呼ばず、claim/pendingを消さない。ただし公式proposal IDとtermsが一致した場合は既存transaction contractどおりreceipt化してよい。
- source、schema、tests、launchd template、installer、spec、planの正本はLife Manager mainだけに置く。
- credential、CDP session、`~/.local/state/anicca/lancers/application.json`、terminal state、SQLite ledger、planner evidenceは移動・削除・repo追加しない。
- launchdはworktree、feature branch、mutable untracked sourceを実行しない。exact main SHA release pathだけを実行する。
- 外部submitはintent永続化後に一度だけ行い、公式readback前にverified/receiptを作らない。
- reviewで指摘済みのsemantic ICP evidence、eligibility別schema、review前deploy事故をすべて閉じる。
- 意味あるcommitごとにfetch、commit、pushする。既存の無関係なdirty変更をrevertしない。

## Plan Size

| 要素 | files | 推定差分 |
|---|---:|---:|
| canonical Lancers/acquisition source snapshot | 10 | 既存runtime約4,600 LOCのbyte import。新規設計コードではない |
| canonical agent-runner isolation/config | 3 | test約45 LOC、production約35 LOC、config約10 LOC |
| reconcile-only all-pending | 3 | test約70 LOC、production約55 LOC |
| exact-SHA deploy/launchd | 3 | test約90 LOC、script/template約120 LOC |
| existing patch artifact | 1 | canonical source導入後に削除 |

3 files/100 LOCのsoft targetを超える主因は、repo外に散った既存production dependencyを正本へbyte importする一回限りの移行である。手書きbehavior changeは各taskを3 files以下、約100 LOC以下に保つ。

## Canonical File Map

次の相対配置は既存の `Path(__file__).parents[...]` contractを維持するため変更しない。

- Create `skills/earn/lancers/scripts/application_loop.py`: acquisition orchestration、planner validation、reconcile-only CLI。
- Create `skills/earn/lancers/scripts/application_tick.py`: provider submit/readback adapter。
- Create `skills/earn/lancers/scripts/status.py`: read-only public discovery。
- Create `skills/earn/lancers/scripts/lancers_adapter.py`: provider card normalization。
- Create `skills/_shared/marketplace-core/scripts/application_transaction.py`: claim/pending/receipt transaction。
- Create `skills/_shared/marketplace-core/scripts/contracts.py`: marketplace contract parsing。
- Create `skills/_shared/marketplace-core/scripts/ledger.py`: receipt-backed SQLite append。
- Create `skills/_shared/marketplace-core/schemas/event.schema.json`: `ApplicationReceipt` schema。
- Create `skills/_shared/marketplace-core/schemas/opportunity.schema.json`: normalized opportunity schema。
- Create `skills/gig-work/schemas/application_decisions.schema.json`: planner decision schema。
- Modify `runtime/agent-runner/agent_runner.py`: application-intent planner child isolation only。
- Modify `runtime/agent-runner/config.json`: `application-intent-planner` task class only。
- Create `runtime/agent-runner/tests/test_application_intent_isolation.py`: isolation regression。
- Modify `apps/lancers-revenue/tests/test_application_loop_hol.py`: canonical import、review regressions、all-pending reconcile regression。
- Create `apps/lancers-revenue/scripts/install-local.sh`: exact-SHA release install and plist rendering。
- Create `apps/lancers-revenue/launchd/ai.anicca.lancers-revenue-application.plist`: placeholder template。
- Create `apps/lancers-revenue/tests/test_install_local.py`: isolated installer test。
- Delete `ops/lancers/patches/0001-first-qualified-application.patch`: canonical sourceがpatchを置換する。

---

### Task 1: Import the minimal canonical acquisition runtime and close the existing review findings

**Files:**
- Modify: `apps/lancers-revenue/tests/test_application_loop_hol.py`
- Create: the 10 canonical source/schema files listed above
- Delete: `ops/lancers/patches/0001-first-qualified-application.patch`

**Interfaces:**
- Consumes: deployed source under `/Users/operator/.local/lib/anicca/lancers/skills/`; immutable state path remains external。
- Produces: `application_loop.run_loop(...) -> dict[str, object]` and the same relative dependency layout, now tracked in Life Manager。

- [ ] **Step 1: Preserve the current review-fix tests and point them at canonical source**

Change only the test import constant:

```python
REPO_ROOT = Path(__file__).resolve().parents[3]
CANONICAL_LOOP_PATH = REPO_ROOT / "skills/earn/lancers/scripts/application_loop.py"
```

Keep these load-bearing tests:

```text
test_uncertain_pending_is_quarantined_without_blocking_new_verified_application
test_rejects_projected_margin_below_seventy_percent_before_submit
test_rejects_semantically_empty_public_evidence_before_submit
test_claimed_pending_projects_are_excluded_before_planning_even_over_batch_limit
test_schema_and_runtime_share_eligibility_contract_matrix
```

- [ ] **Step 2: Run the focused test and verify RED**

Run:

```bash
/opt/homebrew/bin/python3 -m unittest apps/lancers-revenue/tests/test_application_loop_hol.py -v
```

Expected: ERROR/FAIL because `skills/earn/lancers/scripts/application_loop.py` is not present in canonical repo. The failure must not touch live state because every behavioral test passes a temporary state path and replaces provider calls.

- [ ] **Step 3: Commit and push the RED test state**

```bash
git fetch origin
git add apps/lancers-revenue/tests/test_application_loop_hol.py
git commit -m "test(lancers): bind acquisition regressions to canonical source"
git push
```

- [ ] **Step 4: Import the minimal dependency snapshot with the reviewed fixes**

Use `apply_patch` to add the exact currently deployed bytes for the 10 canonical files. Before adding them, record these source hashes in the task report:

```bash
shasum -a 256 \
  /Users/operator/.local/lib/anicca/lancers/skills/earn/lancers/scripts/{application_loop.py,application_tick.py,status.py,lancers_adapter.py} \
  /Users/operator/.local/lib/anicca/lancers/skills/_shared/marketplace-core/scripts/{application_transaction.py,contracts.py,ledger.py} \
  /Users/operator/.local/lib/anicca/lancers/skills/_shared/marketplace-core/schemas/{event.schema.json,opportunity.schema.json} \
  /Users/operator/.local/lib/anicca/lancers/skills/gig-work/schemas/application_decisions.schema.json
```

The imported `application_loop.py` must retain all of the following deterministic guards:

```python
SMALL_B2B_SIGNAL_RE = re.compile(r"(?:B2B|BtoB|法人|企業向け|事業者向け)", re.IGNORECASE)
SMALL_BUSINESS_SIGNAL_RE = re.compile(r"(?:小規模|中小|少人数|スタートアップ|ベンチャー|個人事業|代表)")
SNS_STAFF_SIGNAL_RE = re.compile(r"(?:専任(?:担当者|スタッフ)?(?:が)?(?:不在|いない|なし)|担当者(?:が)?(?:不在|いない|なし)|一人|1名|代表(?:者)?(?:または|と)?少人数.*兼務|少人数.*兼務|初めて(?:の)?SNS担当(?:募集)?|初のSNS担当(?:募集)?)")
```

It must validate exact public excerpts, price `>= 98000`, fee allowance `>= ceil(price * 20%)`, all costs as nonnegative integers, and:

```python
10 * (price - sum(costs)) >= 7 * price
```

The decision schema must enforce:

```text
eligible   => proposal string, price integer >= 98000, date string, qualification object
ineligible => proposal=null, price=null, date=null, qualification=null
```

Remove the patch artifact only after canonical files contain the same reviewed behavior.

- [ ] **Step 5: Run focused tests and source checks**

Run:

```bash
/opt/homebrew/bin/python3 -m unittest apps/lancers-revenue/tests/test_application_loop_hol.py -v
/opt/homebrew/bin/python3 -m py_compile \
  skills/earn/lancers/scripts/application_loop.py \
  skills/earn/lancers/scripts/application_tick.py \
  skills/earn/lancers/scripts/status.py \
  skills/earn/lancers/scripts/lancers_adapter.py \
  skills/_shared/marketplace-core/scripts/application_transaction.py \
  skills/_shared/marketplace-core/scripts/contracts.py \
  skills/_shared/marketplace-core/scripts/ledger.py
git diff --check
```

Expected: 5 tests PASS, compile PASS, diff check PASS. Verify test execution does not change live state/ledger hashes.

- [ ] **Step 6: Commit and push canonical runtime**

```bash
git fetch origin
git add skills/earn/lancers skills/_shared/marketplace-core skills/gig-work/schemas/application_decisions.schema.json apps/lancers-revenue/tests/test_application_loop_hol.py ops/lancers/patches/0001-first-qualified-application.patch
git commit -m "feat(lancers): canonicalize safe acquisition runtime"
git push
```

---

### Task 2: Isolate the application-intent planner while reusing the canonical agent runner

**Files:**
- Create: `runtime/agent-runner/tests/test_application_intent_isolation.py`
- Modify: `runtime/agent-runner/agent_runner.py`
- Modify: `runtime/agent-runner/config.json`

**Interfaces:**
- Consumes: `provider_process_env(provider, provider_config, environ=None, *, task_class=None)`.
- Produces: application-intent child environment with browser/CDP/WebSocket/loopback routes removed; other task classes retain current behavior。

- [ ] **Step 1: Write the isolation regression**

Add a unittest that passes this environment:

```python
source = {
    "PATH": "/usr/bin:/bin",
    "CODEX_HOME": "/tmp/codex",
    "LANCERS_CDP_URL": "http://127.0.0.1:9227",
    "PLAYWRIGHT_WS_ENDPOINT": "ws://localhost:9227/devtools/browser/secret",
    "MARKETPLACE_TOKEN": "fixture-token",
}
```

Assert for `task_class="application-intent-planner"` that `PATH`, `CODEX_HOME`, and `MARKETPLACE_TOKEN` remain, while both browser route variables are absent. Assert a normal task class preserves the original environment. Also load `config.json` and assert `application-intent-planner` has only Luna then Terra candidates, 24,576 reserved tokens, and 180-second timeout.

- [ ] **Step 2: Run the test and verify RED**

```bash
/opt/homebrew/bin/python3 -m unittest runtime/agent-runner/tests/test_application_intent_isolation.py -v
```

Expected: FAIL because the current runner neither accepts `task_class` nor contains the task class config.

- [ ] **Step 3: Add the minimal isolation and route**

Add one helper and one optional keyword:

```python
def _strip_browser_routes_for_planner(child_env: dict[str, str]) -> dict[str, str]:
    forbidden_names = ("BROWSER", "CDP", "WEBSOCKET", "PLAYWRIGHT", "PUPPETEER")
    loopback_values = ("localhost", "127.0.0.1", "[::1]", "//::1")
    return {
        name: value
        for name, value in child_env.items()
        if not any(token in name.upper() for token in forbidden_names)
        and not any(token in value.lower() for token in loopback_values)
    }
```

Pass the parsed task class to `provider_process_env`; apply this helper only for `application-intent-planner`. Add exactly this config entry, without modifying other task classes:

```json
"application-intent-planner": {
  "route": "luna-medium-isolated-application-intent",
  "token_reservation": 24576,
  "timeout_seconds": 180,
  "candidates": [
    {"provider": "codex", "model": "gpt-5.6-luna", "effort": "medium"},
    {"provider": "codex", "model": "gpt-5.6-terra", "effort": "medium"}
  ]
}
```

- [ ] **Step 4: Verify GREEN and no runner regression**

```bash
/opt/homebrew/bin/python3 -m unittest runtime/agent-runner/tests/test_application_intent_isolation.py -v
/opt/homebrew/bin/python3 -m unittest discover -s runtime/agent-runner/tests -p 'test_*.py' -v
git diff --check
```

Expected: all runner tests PASS.

- [ ] **Step 5: Commit and push**

```bash
git fetch origin
git add runtime/agent-runner/agent_runner.py runtime/agent-runner/config.json runtime/agent-runner/tests/test_application_intent_isolation.py
git commit -m "fix(agent-runner): isolate application intent planning"
git push
```

---

### Task 3: Reconcile every existing pending application without discovery or submit

**Files:**
- Modify: `apps/lancers-revenue/tests/test_application_loop_hol.py`
- Modify: `skills/_shared/marketplace-core/scripts/application_transaction.py`
- Modify: `skills/earn/lancers/scripts/application_loop.py`

**Interfaces:**
- Produces: `read_pending_descriptors(state_path) -> list[dict[str, object]]` sorted by durable marker。
- Produces: `run_reconcile_only(state_path, output_stream=None) -> dict[str, object]` with `reconciled_project_ids`, `verified_project_ids`, and `unresolved_project_ids`。
- Produces CLI: `application_loop.py --json --reconcile-only`。

- [ ] **Step 1: Add one all-pending reconcile regression**

Create a temporary state containing claims/pending for `5585496` and `5586112`. Patch `application_tick.run_live_tick` to record calls and return `submission_uncertain` for both. Patch discovery and any submit path to raise immediately if called.

Assert:

```python
self.assertEqual(called_project_ids, ["5585496", "5586112"])
self.assertEqual(result["reconciled_project_ids"], ["5585496", "5586112"])
self.assertEqual(result["verified_project_ids"], [])
self.assertEqual(result["unresolved_project_ids"], ["5585496", "5586112"])
self.assertFalse(result["submitted"])
self.assertEqual(json.loads(state_path.read_text()), original_state)
```

Also call `main(["--json", "--reconcile-only", "--state-path", str(state_path)])` and assert no discovery/submit occurs.

- [ ] **Step 2: Run the focused test and verify RED**

```bash
/opt/homebrew/bin/python3 -m unittest apps/lancers-revenue/tests/test_application_loop_hol.py -v
```

Expected: FAIL because `read_pending_descriptors`, `run_reconcile_only`, and `--reconcile-only` do not exist.

- [ ] **Step 3: Implement the smallest all-pending readback path**

In shared transaction code, make the existing singular helper delegate to the plural helper:

```python
def read_pending_descriptors(state_path: Path) -> list[Dict[str, object]]:
    _, pending = _read_state(Path(state_path))
    return [
        {key: pending[marker][key] for key in ("project_id", "amount_minor", "delivery_due_on")}
        for marker in sorted(pending)
        if _is_project_id(pending[marker].get("project_id"))
    ]

def read_pending_descriptor(state_path: Path) -> Optional[Dict[str, object]]:
    values = read_pending_descriptors(state_path)
    return values[0] if values else None
```

In `application_loop.py`, reconcile each descriptor through existing `_reconcile_pending`, whose submitter override already fails closed. Return one deterministic summary. Do not call `status.run_discovery`, planner, or submitter from this function. Add only the `--reconcile-only` boolean CLI flag and route to this function.

- [ ] **Step 4: Verify GREEN and unchanged live state**

```bash
before_state=$(shasum -a 256 /Users/operator/.local/state/anicca/lancers/application.json | awk '{print $1}')
before_ledger=$(shasum -a 256 /Users/operator/.local/state/anicca/lancers/marketplace-ledger.sqlite3 | awk '{print $1}')
/opt/homebrew/bin/python3 -m unittest apps/lancers-revenue/tests/test_application_loop_hol.py -v
test "$before_state" = "$(shasum -a 256 /Users/operator/.local/state/anicca/lancers/application.json | awk '{print $1}')"
test "$before_ledger" = "$(shasum -a 256 /Users/operator/.local/state/anicca/lancers/marketplace-ledger.sqlite3 | awk '{print $1}')"
git diff --check
```

Expected: tests PASS and live hashes unchanged.

- [ ] **Step 5: Commit and push**

```bash
git fetch origin
git add apps/lancers-revenue/tests/test_application_loop_hol.py skills/_shared/marketplace-core/scripts/application_transaction.py skills/earn/lancers/scripts/application_loop.py
git commit -m "feat(lancers): reconcile every pending application safely"
git push
```

---

### Task 4: Install an exact-main-SHA release and render the one launchd owner

**Files:**
- Create: `apps/lancers-revenue/tests/test_install_local.py`
- Create: `apps/lancers-revenue/scripts/install-local.sh`
- Create: `apps/lancers-revenue/launchd/ai.anicca.lancers-revenue-application.plist`

**Interfaces:**
- Consumes: `LANCERS_RELEASE_SHA` equal to repo `HEAD`, `LANCERS_INSTALL_ROOT`, `LANCERS_LAUNCH_AGENT_DIR`, `LANCERS_STATE_ROOT`, `LANCERS_INSTALL_MODE=reconcile-only|normal`。
- Produces: immutable `releases/<sha>/skills/...`, owner-only `deployment.json`, rendered plist whose ProgramArguments point to the exact release。
- Does not enable/bootstrap/kickstart launchd. Task 5 owns those state changes。

- [ ] **Step 1: Write the isolated installer test**

In a temporary directory, execute the installer with:

```text
LANCERS_RELEASE_SHA=<git rev-parse HEAD>
LANCERS_INSTALL_ROOT=<tmp>/install
LANCERS_LAUNCH_AGENT_DIR=<tmp>/LaunchAgents
LANCERS_STATE_ROOT=<tmp>/state
LANCERS_INSTALL_MODE=reconcile-only
LANCERS_SKIP_MAIN_ASSERT=1
```

Assert:

```text
release path is <install>/releases/<sha>/skills
application_loop.py and all declared dependencies exist
runtime/agent-runner is mapped to release skills/agent-runner
rendered plist ProgramArguments contains exact release application_loop.py, --json, --reconcile-only
manifest deployed_sha equals <sha> and lists SHA-256 for every installed file
manifest mode is 0600
no file under the supplied state root except deployment.json and logs is created
installer source contains no launchctl call
```

Run a second isolated install with `LANCERS_INSTALL_MODE=normal`; assert `--reconcile-only` is absent and `--json` remains.

- [ ] **Step 2: Run the installer test and verify RED**

```bash
/opt/homebrew/bin/python3 -m unittest apps/lancers-revenue/tests/test_install_local.py -v
```

Expected: FAIL because installer/template do not exist.

- [ ] **Step 3: Implement the exact-SHA installer**

The installer must:

```text
1. set -euo pipefail
2. resolve repo root from its own location
3. require LANCERS_RELEASE_SHA == git rev-parse HEAD unless test-only LANCERS_SKIP_MAIN_ASSERT=1
4. require git status --porcelain empty and the SHA to exist on origin/main unless test override is set
5. stage only the canonical files from Tasks 1-3 plus runtime/agent-runner/{agent_runner.py,token_budget.py,config.json}
6. compile/import from staging before install
7. atomically rename staging to releases/<sha>; refuse different bytes at an existing SHA
8. render plist with exact release path and external state log paths
9. include --reconcile-only only in reconcile-only mode
10. lint rendered plist with plutil
11. atomically write mode-0600 deployment.json containing deployed_sha, mode, installed_at, launchd label, and sorted file hash map
12. never read/write application.json, terminal state, SQLite ledger, credentials, or browser session
13. never call launchctl
```

The plist keeps one owner and this schedule:

```xml
<key>Label</key><string>ai.anicca.lancers-revenue-application</string>
<key>StartInterval</key><integer>1800</integer>
<key>ProcessType</key><string>Background</string>
<key>Umask</key><integer>63</integer>
```

Do not set `RunAtLoad`; Task 5 performs an explicit one-time `kickstart` after preflight.

- [ ] **Step 4: Verify installer GREEN**

```bash
/opt/homebrew/bin/python3 -m unittest apps/lancers-revenue/tests/test_install_local.py -v
/opt/homebrew/bin/python3 -m unittest apps/lancers-revenue/tests/test_application_loop_hol.py -v
/opt/homebrew/bin/python3 -m unittest discover -s runtime/agent-runner/tests -p 'test_*.py' -v
/bin/zsh -n apps/lancers-revenue/scripts/install-local.sh
plutil -lint apps/lancers-revenue/launchd/ai.anicca.lancers-revenue-application.plist
git diff --check
```

Expected: all PASS.

- [ ] **Step 5: Commit and push**

```bash
git fetch origin
git add apps/lancers-revenue/scripts/install-local.sh apps/lancers-revenue/launchd/ai.anicca.lancers-revenue-application.plist apps/lancers-revenue/tests/test_install_local.py
git commit -m "feat(lancers): install exact-sha acquisition releases"
git push
```

---

### Task 5: Primary mechanical verification, main integration, and reconcile-only production wake

**Files:**
- No production edit unless a mechanical verification failure returns to the same Luna.
- Update progress evidence in the existing spec/task ledger only after observed results。

**Interfaces:**
- Consumes: Tasks 1-4 pushed and clean; application launchd still disabled/unloaded。
- Produces: exact main SHA deployed, both pending officially read back without submit, service returned to disabled if any uncertainty appears。

- [ ] **Step 1: Primary verifies the one review’s three blockers mechanically**

Run focused tests, full relevant tests, schema/runtime matrix, mutation guard, secret scan, `git diff --check`, and verify application launchd remains disabled. Re-run the semantic evidence test with the signal validator removed in a temporary copy and confirm the test fails. Do not dispatch another reviewer.

- [ ] **Step 2: Integrate without touching another session’s dirty main checkout**

Fetch origin. Create a temporary clean integration worktree from `origin/main`, merge the feature branch with `--no-ff`, run the full relevant test set, commit the merge, and push `HEAD:main`. If origin/main advances, fetch/rebase or recreate the clean integration worktree and re-run tests. Never reset or clean the user’s main checkout.

- [ ] **Step 3: Install exact main SHA in reconcile-only mode**

Record pre-install SHA-256 for `application.json`, terminal state if present, and SQLite ledger. From the clean main integration checkout run:

```bash
LANCERS_RELEASE_SHA="$(git rev-parse HEAD)" \
LANCERS_INSTALL_MODE=reconcile-only \
apps/lancers-revenue/scripts/install-local.sh
```

Verify `deployment.json`, every installed file hash, plist lint, exact release ProgramArguments, and no worktree/branch path.

- [ ] **Step 4: Enable and trigger the existing launchd owner exactly once**

This changes production scheduler state; announce it immediately before execution. Use the rendered installed plist only:

```bash
launchctl enable "gui/$(id -u)/ai.anicca.lancers-revenue-application"
launchctl bootout "gui/$(id -u)/ai.anicca.lancers-revenue-application" 2>/dev/null || true
launchctl bootstrap "gui/$(id -u)" "$HOME/Library/LaunchAgents/ai.anicca.lancers-revenue-application.plist"
launchctl kickstart "gui/$(id -u)/ai.anicca.lancers-revenue-application"
```

Watch the one launchd-owned process to exit. Do not invoke a separate application executor.

- [ ] **Step 5: Accept only read-only reconciliation evidence**

Require output to name both `5585496` and `5586112` in `reconciled_project_ids`; require `submitted=false`; compare state/ledger deltas. A verified official proposal may move its own pending to exactly one receipt; otherwise pending/claims remain unchanged. No unrelated project may be discovered or submitted.

On any mismatch, immediately disable/bootout the label, retain state, and return the evidence to the same Luna under `receiving-code-review` plus `systematic-debugging`.

- [ ] **Step 6: Return the owner to disabled before normal-mode preparation**

```bash
launchctl disable "gui/$(id -u)/ai.anicca.lancers-revenue-application"
launchctl bootout "gui/$(id -u)/ai.anicca.lancers-revenue-application" 2>/dev/null || true
```

Commit/push any evidence-only spec status update. Do not start Task 6 unless reconciliation acceptance is complete.

---

### Task 6: Deploy normal acquisition mode and prove one new verified application

**Files:**
- No planned production edits. Any failure returns to the same Luna and requires a new RED test before a fix。

**Interfaces:**
- Consumes: G0.5 and reconcile-only acceptance complete; two legacy pending IDs remain protected by claim filtering。
- Produces: one new qualified project with one official proposal ID and exactly one `ApplicationReceipt`。

- [ ] **Step 1: Install the same exact main SHA in normal mode**

Run installer with `LANCERS_INSTALL_MODE=normal`; verify the only artifact difference is manifest mode and absence of `--reconcile-only` in ProgramArguments. Re-run installed-file hashes.

- [ ] **Step 2: Preflight the real acquisition boundary**

Require public discovery available, CDP `127.0.0.1:9227` reachable, account session ready, planner route available, no existing application process/lock, capacity below 100%, and current state/ledger readable. Capture ledger receipt count and both pending entries before the wake.

- [ ] **Step 3: Enable and kick the one official launchd owner once**

Announce the production scheduler state change, then enable/bootstrap/kickstart exactly as in Task 5. Do not run the Python entrypoint manually and do not trigger a second wake.

- [ ] **Step 4: Verify the external effect end to end**

Accept only if one newly discovered project has public evidence for Japanese small B2B plus SNS staff 0-1/proxy, price at least ¥98,000, conservative projected margin at least 70%, tailored proposal fields, one persisted intent, one provider submit, official proposal ID readback, and exactly one new unique `ApplicationReceipt`. Verify neither `5585496` nor `5586112` was resubmitted.

If no qualified project exists, report truthful `no_eligible_project`, leave net MRR unknown, keep the scheduled lane enabled for its normal 30-minute ticks, and continue watching future official wakes; do not weaken ICP/margin gates to manufacture a success.

- [ ] **Step 5: Close G1 and clean development workspace**

Update the spec with observed provider ID/receipt evidence without secrets or buyer-private text. Commit and push main. Confirm launchd ProgramArguments point to the exact main SHA release, git main is clean/upstream, and delete the temporary feature/integration worktrees only after deployment verification. Keep runtime state and ledger untouched except for verified transaction transitions.

---

## Deferred Plans After G1

Do not implement these in this plan. Create and execute one Superpowers plan at a time in this order:

1. G2 truthful acquisition/reporting: `brainstorming → writing-plans → TDD → Luna → one fresh adversarial review → verification`.
2. G3 profitable acquisition quotas/capacity/ranking: same workflow。
3. G4 sales/contract lane: buyer reply → offer → approval → active monthly contract。
4. G5 fulfillment lane: bounded scope → QA → official delivery readback。
5. G6 payment/finance lane: PaymentReceipt → payout batch → bank reconciliation → net MRR。
6. G7 target/self-improvement: only after real payment; optimize net MRR/retention/revision cost one variable at a time。

The reusable website pattern remains: per-entity straight state, lane-parallel scheduled ticks, one shared durable ledger/queue, one serialized account/browser mutation lock, and official receipt handoff between lanes.
