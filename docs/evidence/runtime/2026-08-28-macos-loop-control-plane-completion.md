# macOS Loop Control Plane Completion Evidence

## Current production truth

- Current registry: 167 managed labels, 20 explicit external labels, 43
  explicit retired labels. AutoHedge was retired after reboot evidence exposed
  a direct provider boundary and incorrect effect classification.
- Final reboot candidate: main commit
  `b9d38b84f01aaa027772b8e553e468aeb448fe73`, immutable release
  `~/loops/releases/20260828T102650-b9d38b84`.
- Pre-reboot: 168/168 enabled and loaded with exact generated argv; dependency
  imports present; `doctor` passed with unmanaged 0, missing entrypoint 0, and
  installed retired 0.
- Boot identity changed from `{ sec = 1787876433, usec = 786621 }` to
  `{ sec = 1787880781, usec = 949890 }`.
- Post-reboot candidate: 168/168 labels loaded from the same existing immutable release;
  every referenced release root existed; `doctor` passed.
- Natural boot window: 356 valid events across 72 loop IDs; latest outcomes
  were 41 pass and 31 fail. Twenty-one non-`none` effect loops reported
  `effect_status=unknown`, proving process completion was not promoted to an
  official external effect without readback.
- Merged-main final release:
  `~/loops/releases/20260828T114714-bcba782a`, commit
  `bcba782a4ee0217924df29618ebc3ca028d081f4`. After AutoHedge retirement,
  167/167 generated plists and loaded argv referenced this existing release;
  apply wrote 167/167 plan/install events, and `status all` returned the same
  full 40-character SHA for all 167 rows.
- Final `doctor`: unmanaged 0, missing entrypoint 0, installed retired 0.
- Final runtime table: 132 loaded-idle and 35 loaded-running at readback;
  terminal/effect failures remained visible rather than being promoted to
  success.
- Final cleanup replay: errors 0, protected deletions 0, loaded release
  protected. Active entrypoint scan: worktree source 0, direct provider 0,
  sibling managed launchd mutation 0. Deduplicated runtime event validation:
  7,436 valid, invalid 0, secret-shaped violations 0; the final release has an
  event for every one of 167 loop IDs. Current-tree gitleaks: 0.

The 31 failures are visible business-loop repair work, not control-plane
successes. The control plane reports them through `status/watch`; it does not
silently count them healthy.

## Migration and incident proof

- Every label moved separately with generated plist, immutable entrypoint,
  loaded argv, release SHA, state-path, and rollback readback.
- The old Gig release watcher overwrote `hf-gig-paid-direct`. Its watch path is
  now build/publish/GC only; launchd lifecycle remains with `lm-loop`.
- Existing plist environment, working directory, process type, RunAtLoad,
  throttle, umask, and nice attributes were preserved during migration without
  copying secrets into the registry.
- A slow browser teardown reproduced `bootstrap` EIO. Retry settle increased
  from 1 to 3 to 10 seconds and passed the real Gig browser migration.
- A release-pruning regression left 157 plists pointing at a removed release.
  Loaded release discovery, protected release GC, and read-only-tree removal
  tests now pass; recovery apply restored the fleet before the next cadence.
- Release builds now install locked root and AgentMail production dependencies
  before the read-only seal. Runtime state defaults were moved outside releases.
- `lm-loop-run` emits terminal events and forwards SIGTERM/SIGINT to the whole
  entrypoint process group, preventing orphaned model/browser descendants.
- AgentMail replier/nudge use the shared `reply-semantic-agent`, not a direct
  provider API. Automated mail is ignored with a durable replay-zero ledger.

## Scale and clean-user evidence

- `test_render_500_loops_and_status_under_five_seconds` renders 500 validated
  entries and builds 500 status rows under five seconds without starting a
  model or browser.
- `test_clean_user_installs_every_generated_job_without_starting_workloads`
  exports an exact Git commit into an isolated release, starts from an empty
  LaunchAgents directory, installs every generated job, and reads every loaded
  argv back through an isolated launchctl boundary.
- Control-plane suite reached 65 passing tests after full-SHA status readback,
  process-group, and runtime replay hardening. Focused AgentMail tests reached
  4/4 and the loop-adapter registry reached 13/13.

## External sources and code comparison

- Apple, *Creating Launch Daemons and Agents*:
  https://developer.apple.com/library/archive/documentation/MacOSX/Conceptual/BPSystemStartup/Chapters/CreatingLaunchdJobs.html
  — launchd is the central administrator surface, loads user LaunchAgents at
  login, and sends SIGTERM at shutdown. Adopted: generated Label/argv, login
  recovery, and signal-aware wrapper.
- Git, *git-worktree*:
  https://git-scm.com/docs/git-worktree
  — linked worktrees isolate branches and `worktree lock` prevents prune,
  move, or deletion. Adopted after the active control-plane worktree was
  externally removed once.
- Twelve-Factor, *Build, release, run*:
  https://12factor.net/build-release-run
  — dependencies belong to build, releases are immutable, and runtime should
  have few moving parts. Adopted: locked dependency build before seal, exact
  commit release, external mutable state, atomic current selector.
- `nix-darwin/nix-darwin` commit
  `4cff07de74b50e64bdd68cd4e722ab5b6b35ee48`: declarative launchd job mapping
  and the rule that plist text alone is not loaded-state proof. Adopted the
  declarative single registry and live launchd readback; rejected a Nix
  migration because it would add an unrelated system dependency.
- `different-ai/opencode-scheduler` commit
  `cd0b62364792f53e8687db53bc2c2c0261c9cf17`: atomic job-state writes,
  terminal status, cleanup inventory, and best-effort rollback. Adopted atomic
  receipts/status/rollback concepts; rejected its direct plist write and
  `launchctl load/unload` pattern because Life Manager requires one owner and
  loaded-argv verification.

## Permanent development contract

`skills/loop-development/SKILL.md` is the detailed SSOT. `AGENTS.md` and
`CLAUDE.md` contain only a mandatory routing line. The contract requires a
locked worktree, one registry row plus repository entrypoint, state outside the
release, shared provider routing, test-first implementation, complete registry
preflight, one-label migration, loaded readback, natural event, effect
readback, cleanup replay, and no raw managed launchd mutation.
