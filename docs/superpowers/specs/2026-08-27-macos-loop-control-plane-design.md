# macOS Mr.bot Loop Control Plane

**Status:** Account auto complete — global current invariant, full-fleet OSS E2E, and security backlog remain
**TODO ID:** `MACOS-LOOP-CONTROL-PLANE-1`  
**Canonical registry:** `config/loop-registry.json`  
**Scope:** macOS launchd only

## 1. Overview

Mr.bot will operate hundreds of loops across physical life, mental life,
financial life, trading, bounties, marketplaces, mobile-app revenue, marketing,
and system maintenance. Today those loops are installed, released, started,
observed, and cleaned through several independent manifests, plist families,
scripts, release roots, and log formats. That fragmentation makes runtime truth
hard to read and makes a new loop easy to install incorrectly.

`MACOS-LOOP-CONTROL-PLANE-1` makes the Mr.bot repository the single source
for every macOS loop. `config/loop-registry.json` becomes the only operational
registry. One CLI renders launchd jobs from it, applies an immutable repository
release, and provides the same lifecycle and observability commands for every
loop. Mutable business state, credentials, logs, evidence, and receipts remain
outside the repository and outside immutable releases.

The control plane manages lifecycle. Existing loop adapters continue to own
business effects through `plan → execute → reconcile → verify → report`.
Individual loops MUST NOT implement their own installer, account switcher,
release selector, monitor, or global cleanup policy.

```mermaid
flowchart TD
    Repo[Mr.bot repository\ncanonical source] --> Release[Immutable release\nexact main commit]
    Registry[config/loop-registry.json\nall loop definitions] --> CLI[bin/lm-loop]
    Release --> CLI
    CLI --> Plists[Generated LaunchAgents]
    Plists --> Launchd[macOS launchd]

    Launchd --> P[PHYSICAL loops]
    Launchd --> M[MENTAL loops]
    Launchd --> F[FINANCIAL loops]
    Launchd --> E[EARN loops\ntrading, bounty, marketplaces]
    Launchd --> G[GROWTH loops\napps, marketing, content]
    Launchd --> S[SYSTEM loops\nhealth, cleanup, release]

    P --> Events[Uniform runtime events]
    M --> Events
    F --> Events
    E --> Events
    G --> Events
    S --> Events
    Events --> Watch[lm-loop status / watch]

    Router[Single provider/profile router] --> P
    Router --> M
    Router --> F
    Router --> E
    Router --> G
```

## 2. Acceptance Criteria

1. `config/loop-registry.json` contains every Mr.bot-owned macOS launchd
   label. No second manifest is authoritative for installation or lifecycle.
2. Every registry entry has exactly one stable loop ID, launchd label, domain,
   repository-relative entrypoint, cadence, effect class, state root, log root,
   cleanup contract, and provider route.
3. `bin/lm-loop apply` validates the complete registry, resolves one exact
   immutable release, generates every plist, loads changed jobs through
   `launchctl-safe`, and reads the loaded arguments back. Invalid entries cause
   zero launchd mutation.
4. `bin/lm-loop start|stop|restart <loop-id|all>` is the only lifecycle command
   documented for operators. `all` expands from the registry and records every
   label result without stopping after the first failure.
5. `bin/lm-loop status [<loop-id|all>]` reports loop ID, domain, launchd state,
   PID when present, installed release SHA, provider/profile alias, last pass,
   last terminal result, next eligible run, and current blocker.
6. `bin/lm-loop watch [<loop-id|all>]` continuously renders the same fields and
   updates from uniform runtime events. It does not infer business success from
   PID existence or exit code alone.
7. Every loop emits JSONL events using one envelope: `version`, `event_id`,
   `timestamp`, `loop_id`, `domain`, `run_id`, `phase`, `status`, `release_sha`,
   `provider`, `profile_alias`, `effect_class`, `effect_status`, `blocker`, and
   `evidence_refs`. Secret values and credential identifiers are forbidden.
8. All model execution goes through one shared provider/profile router. Loop
   code cannot read or replace `auth.json`, choose `CODEX_HOME`, or implement
   account fallback independently.
9. Each loop owns bounded cleanup of its regenerable run artifacts using the
   registry cleanup contract. The central cleanup owner handles only shared
   releases, shared caches, and orphaned artifacts. State ledgers, receipts,
   active releases, protected sessions, and credentials are never cleanup
   candidates.
10. A new loop becomes operable by adding one registry entry plus its tested
    repository-relative entrypoint. No handwritten plist or new monitoring
    integration is required.
11. At least 500 valid registry entries validate and render deterministically;
    `status all` completes within five seconds on the target Mac without starting
    a model or browser.
12. Migration never stops all production loops together. Each label moves only
    after its generated plist, immutable entrypoint, state path, and loaded
    arguments pass readback; failure retains the prior loaded job.
13. After a Mac reboot, enabled loops return through launchd, `doctor` reports no
    unmanaged Mr.bot labels, and a natural scheduled pass emits a uniform
    event from the installed release.
14. Every loop change follows `skills/loop-development/SKILL.md`: one locked
    worktree, one registry owner, repository-contained source, state outside the
    release, test-first change, exact release apply, loaded readback, natural
    event, and replay-zero. `AGENTS.md` and `CLAUDE.md` route agents to that
    contract rather than duplicating it.

### Operator interface

```text
bin/lm-loop apply
bin/lm-loop doctor
bin/lm-loop start <loop-id|all>
bin/lm-loop stop <loop-id|all>
bin/lm-loop restart <loop-id|all>
bin/lm-loop status [<loop-id|all>]
bin/lm-loop watch [<loop-id|all>]
```

### Registry contract

```json
{
  "schema_version": 2,
  "loops": {
    "fundraiser": {
      "label": "ai.anicca.fundraiser",
      "domain": "earn",
      "entrypoint": "skills/fundraiser-agent/runtime/run.sh",
      "cadence": {"start_interval_seconds": 60},
      "effect_class": "application",
      "state_root": "~/.local/state/mr-bot/fundraiser",
      "log_root": "~/.local/state/mr-bot/fundraiser/logs",
      "cleanup": {"max_runs": 100, "max_age_days": 14},
      "provider_route": "shared-agent-runner"
    }
  }
}
```

The example defines the contract shape; implementation validates allowed domain,
effect, cadence, and route values centrally. Registry values never contain
credential paths or credential contents.

Allowed values are closed and versioned with the registry schema:

- `domain`: `physical`, `mental`, `financial`, `earn`, `growth`, `system`
- `effect_class`: `none`, `publish`, `message`, `money`, `application`, `trade`,
  `account_mutation`
- `provider_route`: `deterministic`, `shared-agent-runner`
- `cadence`: exactly one of `start_interval_seconds`, `calendar_interval`,
  `run_at_load`, or `keep_alive`

## 3. As-Is / To-Be

| Concern | As-Is | To-Be |
|---|---|---|
| Registry | `config/loop-registry.json`, Gig manifest, job-search plists, and independent plist families | `config/loop-registry.json` only |
| Install | Per-loop installers and direct plist edits | `bin/lm-loop apply` |
| Runtime source | Several release roots and some working-tree paths | One exact immutable Mr.bot commit per applied generation |
| Lifecycle | Raw `launchctl`, individual scripts, label knowledge | `lm-loop start/stop/restart` by loop ID |
| Observation | PID, logs, ledgers, and provider receipts inspected separately | Uniform event envelope plus official effect evidence |
| Provider/profile | Per-loop `CODEX_HOME`, auth file, or runner config | One shared provider/profile router |
| Cleanup | Central cleanup plus inconsistent local retention | Per-loop bounded cleanup plus central shared-artifact GC |
| Scaling | Adding a loop requires bespoke plumbing | One registry row plus entrypoint |
| Runtime truth | plist text or working tree can be mistaken for production | loaded launchd args + release SHA + event/effect readback |

## 4. Test Matrix

| # | To-Be | Test name | Cover |
|---:|---|---|---|
| 1 | One authoritative registry | `test_registry_covers_all_mr_bot_launchagents` | OK |
| 2 | Complete validated entry | `test_registry_rejects_missing_or_secret_fields` | OK |
| 3 | Atomic apply and loaded readback | `test_apply_is_atomic_and_reads_loaded_arguments` | OK |
| 4 | One lifecycle interface | `test_lifecycle_all_collects_every_label_result` | OK |
| 5 | Uniform status | `test_status_reports_runtime_and_business_truth_separately` | OK |
| 6 | Uniform watch | `test_watch_updates_from_event_envelopes` | OK |
| 7 | Event contract | `test_event_envelope_rejects_secret_and_unknown_fields` | OK |
| 8 | Shared provider router only | `test_loop_entrypoints_do_not_select_auth_or_codex_home` | OK |
| 9 | Cleanup ownership | `test_cleanup_preserves_receipts_active_releases_and_sessions` | OK |
| 10 | One-row onboarding | `test_new_registry_loop_needs_no_handwritten_plist` | OK |
| 11 | 500-loop scale | `test_render_500_loops_and_status_under_five_seconds` | OK |
| 12 | One-label migration safety | `test_failed_migration_retains_prior_loaded_job` | OK |
| 13 | Reboot recovery | `test_bootstrap_generation_has_enabled_recoverable_jobs` | OK |
| 14 | Natural runtime E2E | `test_natural_pass_reports_installed_release_and_effect_state` | OK |
| 15 | Safe loop development | `skills/loop-development/SKILL.md` plus completion audit | OK |

### E2E judgment

| Item | Value |
|---|---|
| UI変更 | なし（terminal CLIのみ） |
| 結論 | Maestro: 不要（iOS UIを変更しない） |
| 必須E2E | clean macOS user install、launchd loaded readback、Mac reboot、自然scheduled pass、`status/watch` readback |

## 5. Boundaries

- macOS launchd only. Linux, Windows, Kubernetes, and cross-platform scheduler
  abstractions are out of scope.
- No new daemon, database, web dashboard, TUI framework, or message bus.
- The mutable repository checkout is never a production entrypoint.
- Business decisions remain inside loop agents and adapters; the control plane
  does not decide trades, applications, publications, messages, or spending.
- The control plane does not count PID, process liveness, local PASS, or model
  output as a completed external effect.
- Credentials remain in private per-profile stores. The repository contains
  aliases and route names only.
- The router does not combine personal ChatGPT subscriptions to circumvent
  provider usage limits. Provider-supported API capacity and explicit profile
  selection remain separate concerns.
- Account/profile management is not duplicated inside loop definitions.
- Historical logs and specs are not rewritten; only current runtime authority
  moves to this control plane.

## 6. Execution Steps and Ordered TODO

| Order | TODO | Done evidence |
|---:|---|---|
| 1 | ✅ Inventory every installed `ai.anicca.*` Mr.bot label and classify owner/domain/effect/state/release | `docs/evidence/runtime/2026-08-28-macos-loop-control-plane-inventory.{md,json}`; 226 installed labels, 208 classified Mr.bot-owned, 14 disabled/unloaded installed ambiguous, loaded/disabled-only rows retained |
| 2 | ✅ Upgrade `config/loop-registry.json` to schema v2 and import all active definitions without changing launchd | 169/169 active classified labels, one external and two retired labels; fixture SHA-256 `35e3b1ae25ed87a815772b14c00c4a87e7e38a87e125bba98f1c04661b9b6c49`; `docs/evidence/runtime/2026-08-28-macos-loop-control-plane-schema-v2.md` |
| 3 | ✅ Implement `bin/lm-loop doctor/status/watch` as read-only commands | five focused tests; live 172-row status/watch; runtime/effect truth separated; `docs/evidence/runtime/2026-08-28-macos-loop-control-plane-readonly-cli.md` |
| 4 | ✅ Implement plist generation and fail-closed `apply` using `launchctl-safe` | five focused tests; production invalid generation zero mutation; isolated exact loaded argv readback and cleanup; `docs/evidence/runtime/2026-08-28-macos-loop-control-plane-atomic-apply.md` |
| 5 | ✅ Implement `start/stop/restart` for one ID and `all`, collecting every return code | four focused tests; isolated one-label start/restart/stop; real collect-all `[0,2,0]`; cleanup remaining 0; `docs/evidence/runtime/2026-08-28-macos-loop-control-plane-lifecycle.md` |
| 6 | ✅ Add the uniform runtime event envelope at the shared runner boundary | exact 15-field schema; private idempotent JSONL; shared-runner integration; invalid-event spoof rejection; existing ledgers unchanged; `docs/evidence/runtime/2026-08-28-macos-loop-control-plane-runtime-events.md` |
| 7 | ✅ Consolidate all model/profile selection into the shared provider router | one explicit `acct2` profile; account rotation and caller provider override 0; duplicate runner 0; active entrypoint direct auth/CODEX_HOME selection 0; Writer normal/repair/session delegated; `docs/evidence/runtime/2026-08-28-macos-loop-control-plane-provider-boundary-progress.md` |
| 8 | ✅ Add per-loop cleanup contracts and central shared-artifact GC reconciliation | immutable loop-run wrapper; marker/terminal/protected gates; loaded/current release protection; isolated 2,097,203-byte pressure recovery; protected deletion 0; `docs/evidence/runtime/2026-08-28-macos-loop-control-plane-cleanup.md` |
| 9 | ✅ Migrate active labels one by one: system, growth, earn, financial, mental, physical | reboot candidate 168/168 exact generated plist and loaded argv; unsafe AutoHedge subsequently retired; current managed 167, retired 43 |
| 10 | ⚠️ Remove superseded installers/manifests only after registry parity and replay-zero | Tier1 is retired, but obsolete `hf-gig-release-watch` was retained and currently exits 2 every five minutes; retire it instead of integrating it |
| 11 | ✅ Run 500-loop scale test and clean-user install E2E | persistent scale test; isolated empty-user 168/168 install/readback; no model/browser starts |
| 12 | ✅ Run reboot and natural scheduled-pass E2E on the target Mac | boot ID changed; 168/168 recovered from existing release; doctor PASS; 356 boot-window events across 72 loops; process/effect truth separated |
| 13 | ✅ Make safe loop development discoverable to every coding agent | `skills/loop-development/SKILL.md`; one-line routing in `AGENTS.md` and `CLAUDE.md`; worktree locked against prune/remove |

Implementation commands are standardized by this spec:

```bash
python3 -m unittest discover -s runtime/loop/tests -p 'test_*.py'
node --test apps/mr-bot/lib/loop-adapter-registry.test.js
bin/lm-loop doctor
bin/lm-loop apply
bin/lm-loop status all
bin/lm-loop watch all
```

No user GUI task is required. Authentication stays in existing private profile
stores; this control-plane slice never creates or copies credentials.

### TODO 7 execution state

Account rotation and per-caller provider overrides are removed. Gig, Job
Search, Connector, Mr.bot daily, Lancers portable releases, and all X
model calls use the canonical runner with one explicit `acct2` profile. The
duplicate Gig runner is removed after token-budget/history/context parity is
moved. Writer opportunity discovery/response use the shared adapter, while the
legacy Writer CLI delegates production normal and repair/session modes to the
canonical router. Direct active-entrypoint auth/profile selection is zero. Evidence:
`docs/evidence/runtime/2026-08-28-macos-loop-control-plane-provider-boundary-progress.md`.

### TODO 9–13 execution state

The 168-label reboot candidate recovered through the same launchd control plane
after a real Mac reboot. AutoHedge was then found to bypass the shared provider
boundary while being misclassified as effect `none`, so it was retired rather
than silently left unsafe. Current registry truth is 167 managed, 43 retired,
and 20 explicit external labels. Runtime source, dependencies, argv, cleanup, provider
routing, and terminal events resolve through immutable releases. Natural
boot-window events keep process status separate from official effect status;
failed business loops remain visible rather than being counted as healthy.
The final merged release applies 167/167 labels, emits 167/167 install events,
and gives every registered loop an event at the installed SHA. `doctor` passes
with unmanaged, missing-entrypoint, and installed-retired counts all zero.

Loop development now has one repository contract:
`skills/loop-development/SKILL.md`. Agents work in locked linked worktrees,
change one registry TODO, keep source in this repository and state outside the
release, use only `lm-loop` for lifecycle, and require exact loaded readback plus
a natural event before Done. Completion evidence:
`docs/evidence/runtime/2026-08-28-macos-loop-control-plane-completion.md`.

### Post-completion operational repair cursor

> Current scope override: this cursor owns only Account auto rollout and OSS
> startup. Marketplace-specific repair (including Lancers and CrowdWorks) is
> outside this session. Business work is always performed by the owning loop;
> Codex repairs source/spec/releases, triggers that real loop, and observes
> authoritative readback.

The control plane is complete; business-loop repair continues one loop at a
time from `lm-loop status all`. Current measured inventory is 167 rows: 36
loaded-running and 131 loaded-idle. Terminal history contains 61 pass, 80 fail,
and 26 without a terminal result. A terminal failure is retained as audit
history while a KeepAlive process is running, so 80 is not by itself an
actionable repair count.

#### Target operating model

- Coconala remains the working local reference and is never stopped merely to
  generalize the system. The shared job-doing kernel owns goal, capability,
  context, effect fence, delivery, official readback, replay-zero, and revenue;
  marketplace-specific URLs, selectors, fees, message rooms, and receipts stay
  in thin adapters.
- Upwork remains intentionally off. Its code may serve as implementation
  evidence, but its retired launchd labels are not restarted and it is not an
  activation TODO.
- Lancers and CrowdWorks remain separate marketplace backlogs. They are not
  Account auto or OSS-startup tasks and are not touched by this cursor.
- Delivery order is local-first, then the same contract on the cloud worker,
  then an OSS setup that a new user can start with a few documented commands.
  The current `scripts/local-up.sh` starts only the Docker API, scheduler, and
  worker; it does not install or run all 167 macOS loops. The clean-user launchd
  test renders and reads back jobs without starting workloads. Therefore
  few-command full-loop OSS startup is not yet implemented.
- Account 1 primary to Account 2 fallback is implemented in the shared runner.
  Expansion uses `account_profile_order=[acct1,acct2]`; Account 2 is attempted
  only for transient quota/auth failure with no fresh result, agent message,
  tool item, or external effect. PR #2983 proves Account 1 success and a
  controlled Account 1 quota to real Account 2 success with effect 0.

#### Daily operation and repair

1. Build one resolver view containing managed, external, retired, and unmanaged
   labels. Continuous jobs are healthy only while loaded-running. Scheduled
   jobs are healthy while loaded-idle only when their next eligible time is not
   overdue and their latest due pass has a valid terminal event.
2. Remove unused jobs instead of healing them. Retirement removes the registry
   owner, installed job, legacy installer/recreator, and active process while
   preserving audit receipts and proving recreation zero.
3. Rank the remaining queue: unmanaged or duplicate owners first, overdue
   external-effect loops second, failed deterministic support loops third, and
   missing-event classification last. Work one loop at a time.
4. Repair in a locked worktree, merge main, cut one immutable release, apply one
   label, and prove loaded argv plus natural runtime event. Never restart all
   loops to repair one.
5. For messages, applications, publication, delivery, payment, or trade, require
   official provider/account readback and replay-zero. Process exit zero is not
   business success.
6. Send one daily Telegram summary with resolver totals, deleted unused jobs,
   the one repaired loop, official effect evidence, remaining cursor, and any
   fail-closed blocker.

Completed implementation history:

Completed evidence: `affiliate-browser` is repaired by PRs #2946, #2947, and
#2949. Account 1 primary/Account 2 pre-effect fallback is merged by PR #2983
and deployed at `3d69c74b`; real controlled reads prove `acct1` success and
`acct1 quota -> acct2 success` with effect 0. Obsolete `hf-gig-release-watch`
is retired by PR #2986, not loaded, not installed, and has no production
recreator. Completed items are not part of the remaining queue.

1. ✅ Implement Account 1 to Account 2 pre-effect fallback in the shared runner.
   PR #2983 is merged; controlled real readback proves both primary success and
   quota-triggered fallback success.
2. ✅ Finish loop-owned Account auto rollout. `mr-bot-dev` now cuts pushed
   main into a complete immutable release and reconciles only
   `shared-agent-runner` rows that are `loaded-idle`; `loaded-running` rows are
   reported and untouched. PRs #3010, #3012, and #3015 are merged. A real owner
   pass completed `eligible=63`, `failed=0`, and `skipped_running=12`. The final
   capability audit covers all 78 consumers: installed SHA missing 0 and every
   installed release is a descendant of Account auto merge `3d69c74b`. Current
   runtime state is 61 loaded-idle, 16 loaded-running, and 1 unloaded; exact
   equality with mutable `current` is not a capability gate while main advances.
3. ✅ Make the portable OSS subset startup truthful: a few commands provision local-only state,
   secrets, choose supported loops, start local scheduler/workers, install the
   platform-appropriate supervisor, and show runtime ownership. PR #3024 makes
   `scripts/local-up.sh` build the shared runtime image once, then starts the
   Compose stack without duplicate builds; it also makes `lm-loop apply
   --help` fail before mutation. A clean Colima run created the local-only
   password and brought API, scheduler, worker, liveness, Postgres, and object
   store to healthy from one command.
4. ✅ Prove the portable OSS supervisor owns parallel work after the initiating shell
   exits. PR #3025 extends `local-up.sh status` with scheduler owner,
   `loops_enabled`, effect scheduler flags, worker capabilities, and liveness
   last-poll readback. After the start shell exited, all six services remained
   healthy; scheduler PID 3176 and worker PID 3193 were distinct and both used
   `restart=unless-stopped`. Default supported capabilities were
   `runtime.noop,marketing.liveness.telegram`; financial and all marketing
   external-effect schedulers read back false. Do not claim every private Dais
   loop is portable; unsupported or unconfigured capabilities remain
   explicitly off.
5. ✅ Track repo-wide nonrequired security-CI debt separately from loop health.
   Latest main measures OSS self-contained boundary 336 findings (stale source
   root and absorbed-source inventories), PII shape gate 28 redacted findings,
   Python syntax failures 0, and production dependency audit 24 findings (17
   low, 2 moderate, 5 high, 0 critical). The high findings are transitive
   OpenTelemetry, `brace-expansion`, and `fast-uri` paths. These are a separate
   security/consolidation backlog; they do not change Account auto, local
   supervisor health, or external-effect receipts, and are not silenced with a
   blanket allowlist or breaking `npm audit fix --force`.

#### Current measured state and remaining TODO — execute only in this order

Current registry has 166 managed rows and unmanaged labels 0. Account auto is
present in all 78 shared-runner consumers with installed SHA missing 0. Current
runtime has 61 loaded-idle, 16 loaded-running, and 1 unloaded shared-runner
consumer. Every installed release SHA contains Account auto merge `3d69c74b`. The
controlled proof remains Account 1 success plus Account 1 quota/auth failure to
real Account 2 success with external effect 0. Clean-user launchd E2E is not an
Account auto acceptance gate.

The global release invariant remains red after the earlier recovery. Active
`current` is sparse `c38659a4` with paths limited to control/runtime, shared
browser, Gig, and Writer code. `lm-loop doctor` reports 107 missing
entrypoints, unmanaged 0, and retired-installed 0. Existing loops
continue from their installed immutable releases, so this does not remove
Account auto, but new fleet-wide operations cannot use `current` as a complete
release. The two-file invariant fix is committed and pushed as `dc8d165b` in
PR #3108. Its merge-result checks are all green, including Loop control, OSS
self-contained, PII shape, Python, shell, gitleaks, and TruffleHog. This is not
production completion until PR #3108 is merged, a full release is deployed,
and live readback stays green after a later sparse cut.

Full-fleet OSS startup is partially implemented by PR #3047. The existing
`scripts/local-up.sh` now provides `loops-up <id>...`, `loops-status`, and
`loops-down`. Selection is explicit with default zero, saved as a local
mode-600 profile, and supervised by existing launchd/`lm-loop`; unknown IDs and
missing or mis-permissioned user credential stores fail before release or
launchd mutation. Docker behavior is unchanged. Completion remains unproven:
PR #3049 adds `loops-init`, which atomically creates or validates the canonical
version-1 `credentials` list without adding or printing values. An isolated
clean HOME proves parent mode 700, file mode 600, and byte-identical replay.
The clean-user natural-run E2E remains and is required only for the public
full-fleet OSS claim. Production labels are not reused for this proof.

Security gates on PR #3108 already prove OSS self-contained, PII shape, Python
syntax, shell syntax, and secret scans green for its merge result. The remaining
security acceptance is the production dependency audit: critical and high must
both read 0 without `npm audit fix --force` or compatibility regression.

| Order | Remaining TODO | Done evidence | Working-time estimate |
|---:|---|---|---|
| 1 | Close the global `current` invariant. Merge PR #3108; a sparse cut must leave `current` byte-identical, target-specific apply may use its explicit immutable release, and all-label apply must still require the full current release. Then cut/deploy one full main release through the owner without restarting running loops. | `current/RELEASE.json` is `ALL`; sparse-cut replay leaves its symlink unchanged; `lm-loop doctor` is green with missing 0, unmanaged 0, and retired-installed 0; every installed argv points to an existing immutable release; running loops were not restarted. | 30–90 minutes, including full release build and live readbacks. |
| 2 | Finish full-fleet OSS startup by running the clean-user natural E2E for the implemented profile, credential initialization, and launchd supervisor commands. This is not required to re-prove Account auto. Never reuse a production label, bundle Dais credentials, or claim private provider loops work without user-owned setup. | From an isolated macOS user/domain: documented few-command setup, user-owned secret initialization, selected effect-none loop starts, initiating shell exits, supervisor retains it, a natural terminal event carries the installed SHA, and the resolver separates liveness, blocker, terminal result, and effect status; test-only state is removed afterward. | 30–60 minutes after an isolated macOS user/domain is available. |
| 3 | Close the remaining security backlog without blanket allowlisting or `npm audit fix --force`: remeasure production dependencies, then upgrade only the parent packages responsible for critical/high findings. | Current merge-result OSS/PII/Python/shell/secret gates stay green; dependency audit critical 0 and high 0; focused runtime compatibility checks pass. | 1–3 hours, depending on transitive upgrade compatibility. |

### TODO 1 execution state

The read-only capture joins installed plist text with loaded and disabled
launchd readback. It records the complete 266-label union, including 40 labels
without an installed plist, rather than treating plist presence as runtime
truth. The installed set contains 208 classified Mr.bot-owned labels. The
169 loaded jobs are represented by schema-v2 entries; 39 disabled jobs remain
migration inventory. Fourteen installed disabled/unloaded labels and 29
loaded/disabled-only labels remain explicitly ambiguous. Unknown releases,
mutable checkout paths, and three invalid plists fail closed for migration. No
launchd mutation or cleanup occurred during inventory.
