# Lancers Planner Contract Recovery Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development to implement this plan as one bounded task. The primary owns this plan, acceptance, review, deployment, and SSOT state.

**Goal:** Make the canonical Lancers acquisition owner return a truthful complete planning result, independently veto unsafe candidates, submit at most one verified qualified application, and deploy all three owners from one exact Mr.bot main SHA.

**Architecture:** Keep the existing 30-minute acquisition owner, agent-runner, static schema, state, ledger, and one-submit bound. Derive an ephemeral per-tick strict schema from the canonical schema, use Luna for all decisions, use the existing Terra `diagnostic-agent` route only when the top candidate needs an independent safety decision, and keep deterministic code limited to structure, grounding, arithmetic, dedupe, and official readback. Extend the existing installer into the single production activation entrypoint through an explicit required activation mode; do not create another deploy script, service, database, queue, or schema SSOT.

**Tech Stack:** Python 3 stdlib, existing JSON Schema file, existing `runtime/agent-runner`, zsh, macOS launchd, unittest.

## Global Constraints

- Primary Sol writes and updates spec/plan/task state; implementer edits only the four assigned code/test files and runs the listed commands.
- Direct implementation first. Do not perform RED-first TDD and do not create a new test file.
- One fresh Sol adversarial review total after the whole task. No per-subtask review loop and no second broad review.
- One active item only: G3B.3 planner contract recovery. Do not change Storefront offers, ContractReceipt, capacity, fulfillment, or finance.
- Normal tick: one public query, one Luna planner call, zero or one conditional Terra safety call, at most one provider submit.
- Never hardcode semantic eligibility with keyword/regex/if-else. Model owns commerciality, ongoing outsourcing, and interaction requirements. Deterministic code owns exact-source grounding, IDs, dates, prices, fees, margin, claims, state, and receipts.
- Worktree and feature branch are authoring only. Runtime may execute only a read-only release archived from a clean commit reachable from `origin/main`.
- No new dependency, daemon, launchd label, database, queue, durable state format, or static schema file.
- State, browser profile, append-only ledger, secrets, and existing evidence outside the bounded planner root are not moved or deleted.
- External submission is performed only by the loaded launchd application owner after exact-release deployment; implementer does not run live Lancers submission or launchctl.
- Meaningful edits are committed and pushed only to `origin/feat/lancers-storefront-inventory`; primary alone advances `origin/main` and deploys.

## File Map and Size Budget

| File | Responsibility | Soft target |
|---|---|---:|
| `skills/earn/lancers/scripts/application_loop.py` | Dynamic planner contract, conditional Terra safety veto, sanitized failure stages, bounded evidence retention | 75–110 changed LOC |
| `apps/lancers-revenue/tests/test_application_loop_hol.py` | Update existing injected-planner checks to the new safety boundary; no new test file | 45–70 changed LOC |
| `apps/lancers-revenue/scripts/install-local.sh` | Required activation mode, report label in manifest, three-owner activation and exact-SHA verification | 25–40 changed LOC |
| `apps/lancers-revenue/tests/test_install_local.py` | Set activation off in isolated installs and assert the expanded manifest contract | 4–12 changed LOC |

Four files are necessary because existing regression expectations encode the removed semantic regex boundary and the existing installer test explicitly forbids launchctl. Keep total changed LOC at 150–220; if implementation exceeds 220, stop and shrink before commit.

---

### Task 1: Recover planner contract and exact-release activation

**Files:**
- Modify: `skills/earn/lancers/scripts/application_loop.py`
- Modify: `apps/lancers-revenue/tests/test_application_loop_hol.py`
- Modify: `apps/lancers-revenue/scripts/install-local.sh`
- Modify: `apps/lancers-revenue/tests/test_install_local.py`

**Interfaces:**
- Preserve: `run_loop(...) -> dict[str, object]`, `main(...) -> int`, `invoke_planner(prompt, evidence_dir) -> Mapping[str, object]`, `validate_decisions(...) -> list[str]`, existing CLI flags and state/ledger formats.
- Add injectable callable: `safety_verifier(prompt: str, evidence_dir: Path) -> Mapping[str, object]` as an optional keyword on `run_loop`, passed into `_plan_and_submit`; tests use it, CLI omits it.
- Add normal reasons/errors: `reason="safety_rejected"`; errors `planner_runner_failed`, `planner_contract_incomplete`, `planner_contract_invalid`, `safety_check_failed`.
- Add optional sanitized result fields: `planner_expected_count` and `planner_returned_count`, emitted only when known.
- Installer requires `LANCERS_ACTIVATE` with exact value `0` or `1`. `0` renders/verifies artifacts only; `1` additionally activates and verifies all three canonical owners.
- Manifest adds `report_launchd_label` alongside existing `launchd_label` and `work_sync_launchd_label`.

- [ ] **Step 1: Implement the per-tick planner output contract without changing the static schema**

In `application_loop.py`, load `PLANNER_SCHEMA`, copy it as JSON data, and write an ephemeral schema inside the current run evidence directory. For `N=len(rows)`:

```python
decisions = schema["properties"]["decisions"]
decisions["minItems"] = N
decisions["maxItems"] = N
decisions["items"]["properties"]["request_id"]["enum"] = request_ids
```

Use this path for the default agent-runner call. Do not edit `application_decisions.schema.json`. Keep `invoke_planner(prompt, evidence_dir)` callable for existing callers; it may derive IDs from the prompt snapshot or delegate to a private helper that accepts the runtime schema path. The runner remains `application-intent-planner`, Luna-first, one attempt unless the existing runner performs its already-defined transient fallback.

Before `_validate`, compare returned decision count to `N`. On mismatch return `planner_contract_incomplete` with expected/returned counts. Map runner nonzero/missing/failed summary to `planner_runner_failed`; map a schema-valid result rejected by deterministic validation to `planner_contract_invalid`. Do not emit prompt, proposal, description, buyer identity, cookie, provider raw stderr, or secret.

- [ ] **Step 2: Move semantic judgment out of deterministic regex while retaining grounding and money safety**

Keep the exact `依頼主の業種:` line and `依頼概要:` section parsing, exact-substring checks, Japanese text check, proposal safety, observed JPY budget, fee floor, cost non-negativity, 70% projected margin, delivery date, duplicate ID, claim, and receipt checks.

Remove only semantic keyword judgments from `_valid_qualification_evidence`: `COMMERCIAL_BUYER_SIGNAL_RE`, `SNS_SCOPE_SIGNAL_RE`, `ONGOING_SCOPE_SIGNAL_RE`, and `OUTSOURCING_SIGNAL_RE` must not decide eligibility. Delete constants that become unused. Do not replace them with other keywords or regexes.

Add two short canonical examples to `PLANNER_RULES`:

- A commercial organization explicitly seeking ongoing outsourced SNS operations may be eligible when all money/scope rules hold.
- A project requiring weekly meetings, Zoom interviews, live calls, physical attendance, personal voice/face recording, or another synchronous personal obligation is ineligible even when budget and SNS scope fit.

The examples guide judgment; they are not parsed by code.

- [ ] **Step 3: Add the conditional independent Terra safety veto using the existing runner**

After deterministic validation and projected-net ranking, but before `_submit`, inspect only the top candidate. If no eligible candidate exists, return existing `no_eligible_project` without a Terra call.

For a top candidate, build a concise prompt containing only its public row, primary decision, the explicit no-live/no-physical/no-recording/no-personal-identity policy, and instructions to return grounded JSON. Invoke the existing agent-runner with task class `diagnostic-agent`, its existing Terra route, a separate `evidence/safety` directory, read-only runner behavior, and an ephemeral schema equivalent to:

```json
{
  "type": "object",
  "additionalProperties": false,
  "required": ["safe_to_submit", "reason", "blocker_evidence"],
  "properties": {
    "safe_to_submit": {"type": "boolean"},
    "reason": {
      "enum": [
        "approved",
        "live_interaction_required",
        "physical_presence_required",
        "personal_identity_required",
        "recording_required",
        "other_policy_blocker",
        "uncertain"
      ]
    },
    "blocker_evidence": {"type": ["string", "null"], "maxLength": 240}
  }
}
```

Deterministically accept only `safe_to_submit is True`, `reason == "approved"`, and `blocker_evidence is None`. For any unsafe result, require a nonempty blocker quote that is an exact substring of the public description and return `ok=true`, `reason="safety_rejected"`, submitted false. Runner failure, malformed result, `uncertain`, or ungrounded blocker returns `ok=false`, `error="safety_check_failed"`, submitted false. Never fall through to submit on verifier ambiguity.

When a `safety_verifier` callable is injected, call it with `(prompt, safety_evidence_dir)` instead of the real runner. Do not call the injected primary planner as the safety verifier.

- [ ] **Step 4: Keep only bounded actionable evidence**

The existing root reset already removes the prior run. On successful `no_eligible_project`, `safety_rejected`, or verified application, delete the current planner root as before. On `planner_runner_failed`, `planner_contract_incomplete`, `planner_contract_invalid`, or `safety_check_failed`, retain only the current run under the existing planner root; the next tick's existing `_reset` replaces it. Do not create another evidence root or retention service.

The JSON owner output includes only the error/reason, expected/returned counts when available, and existing funnel fields. Agent-runner's own `summary.json`/`attempts.jsonl` remain the detailed local evidence.

- [ ] **Step 5: Update existing application regressions after production implementation**

Do not create a new test file and do not perform a RED-first cycle. Update only tests invalidated by the new interface:

- Existing successful injected-planner/submitter cases pass a safety verifier returning `{"safe_to_submit": true, "reason": "approved", "blocker_evidence": null}`.
- Existing staff-proxy, one-off, and semantically empty cases no longer expect deterministic regex rejection. Their injected primary planner may return eligible, but injected safety verifier returns a grounded rejection and the assertion checks `reason="safety_rejected"`, submitter not called.
- Existing grounding, ID, amount, date, cost, margin, schema, duplicate, pending, and one-submit checks remain unchanged.
- Update the direct `invoke_planner` argument check only as required by the private runtime-schema helper while preserving the public two-argument call.
- Add assertions inside the existing relevant methods, not a new method/file, that the generated provider schema has exact `minItems`, `maxItems`, and request ID enum, and that sanitized output contains expected/returned counts without public text.

- [ ] **Step 6: Make the existing installer the single activation boundary**

In `install-local.sh`:

1. Require `LANCERS_ACTIVATE` and accept only `0` or `1`.
2. Pass `REPORT_LABEL` into manifest generation and add `report_launchd_label`.
3. Preserve all current archive, byte comparison, immutable permissions, atomic plist, lint, and manifest file-hash behavior.
4. When activation is `1`, after all three plists pass lint and before writing the new manifest:
   - compute `DOMAIN="gui/$(id -u)"`;
   - `launchctl enable` each exact service target;
   - `launchctl bootout` each loaded service target, tolerating only the not-loaded case;
   - `launchctl bootstrap` each exact rendered plist;
   - capture `launchctl print` for application, report, and work-sync;
   - require each output to contain the exact `RELEASE_PATH` in ProgramArguments and WorkingDirectory;
   - exit nonzero before manifest replacement on any mismatch.
5. When activation is `0`, never invoke launchctl. This is the isolated installer-test path, not the production deployment path.

Do not kickstart any owner inside the installer. Primary performs one explicit application kick after hashes and loaded-owner convergence are recorded.

- [ ] **Step 7: Update existing installer regression and run verification**

In `test_install_local.py`, set `LANCERS_ACTIVATE=0` in `_run_install`, assert the manifest's `report_launchd_label`, and replace the obsolete source-text assertion that the installer contains no `launchctl` with an assertion that isolated activation-off install succeeds without changing the temporary state contract. Do not add a fake launchctl framework or a new test file; live activation is primary E2E.

Run exactly:

```bash
python3 -m unittest apps/lancers-revenue/tests/test_application_loop_hol.py
python3 -m unittest discover -s apps/lancers-revenue/tests -p 'test_*.py'
python3 -m unittest discover -s runtime/agent-runner/tests -p 'test_*.py'
python3 -m unittest apps/lancers-revenue/tests/test_install_local.py
python3 -m py_compile \
  skills/earn/lancers/scripts/application_loop.py \
  runtime/agent-runner/agent_runner.py
/bin/zsh -n apps/lancers-revenue/scripts/install-local.sh
plutil -lint apps/lancers-revenue/launchd/*.plist
git diff --check
```

Expected: every command exits 0; no live Lancers request, provider submission, launchctl mutation, state write outside temporary test directories, or ledger append occurs.

- [ ] **Step 8: Self-review, commit, push feature branch, and report**

Confirm the diff contains only the four owned files, total changed LOC is at most 220, no semantic keyword/regex replacement exists, no new dependency/service/state/schema exists, and no code path can call submit before an explicit safety approval.

Commit once:

```bash
git add \
  skills/earn/lancers/scripts/application_loop.py \
  apps/lancers-revenue/tests/test_application_loop_hol.py \
  apps/lancers-revenue/scripts/install-local.sh \
  apps/lancers-revenue/tests/test_install_local.py
git commit -m "fix(lancers): recover qualified application planning"
git push origin HEAD:feat/lancers-storefront-inventory
```

Write the raw evidence report requested by the SDD task brief. Do not edit spec, plan, SDD ledger, deployment state, launchd, or `origin/main`.

## Primary-only acceptance after implementation and the one review

Primary performs these steps; implementer and reviewer do not:

1. Inspect the exact diff and raw verification report.
2. Dispatch one fresh Sol adversarial verifier. If Critical/Important findings exist, return them once to the same implementer; do not dispatch a second adversarial review. Primary mechanically verifies the correction.
3. Run a submission-free saved/live `SNS投稿` contract check: 17 inputs produce 17 exact IDs and project `5585701` is rejected by the conditional Terra safety verifier with grounded weekly-MTG/Zoom evidence.
4. Re-run the full commands above freshly.
5. Fast-forward the reviewed commit to `origin/main` and use `install-local.sh` with `LANCERS_ACTIVATE=1`, exact main SHA, normal mode, canonical install/state/plist paths.
6. Confirm manifest and all three loaded owners point to the same exact SHA; no worktree/feature/mutable path appears.
7. Record application/listing/ledger pre-hashes, trigger the loaded application owner once with `launchctl kickstart`, wait for bounded exit, and inspect one-line JSON, stderr, process/orphan state, pending, and ledger.
8. Accept `no_eligible_project` or `safety_rejected` as a truthful no-op. If an actually qualified candidate passes both models, require at most one submit and official proposal ID/ApplicationReceipt before accepting the tick.
9. Update the SSOT with implementation SHA, review verdict, deployed SHA, owner convergence, real tick outcome, state/ledger delta, and next TODO; commit/push and send the Telegram milestone.

