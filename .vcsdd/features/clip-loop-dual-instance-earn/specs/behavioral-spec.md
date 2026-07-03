# Behavioral Spec — clip-loop-dual-instance-earn (Phase 1a)

## Context
The clip-earn pipeline (`~/anicca/skills/earn/clip/{producer,run,monitor}.sh`) currently runs on exactly
one identity ("myclaude", human-funded claude-p, wallet `xxKC33TY...`, account `@aiclipsvault`). A second,
self-funded identity (ClawRouter-driven, any AI) currently cannot run it at all — there is no isolation
layer, so a second caller would either collide on the same queue/accounts/ledger files (drain / duplicate
post risk — precedent: `reference_cost_free_selfpaying_agent_clawrouter_and_shared_wallet_drain.md`) or
require code that hardcodes which model/provider is calling it.

Mission (Dais 2026-07-03 verbatim intent): "you have to make sure it works for every AI... they find
affiliates that pay with crypto, they can make money themselves with no human loop, no human credentials
at all." The deterministic pipeline must be identity-agnostic; only the wallet/accounts/ledger differ per
caller. The JUDGMENT layer (which creator, which moment, which exit) stays natural-language per
`feedback_build_agents_not_hardcode_regex` — no model-specific branching in the shell/python tool layer.

## In scope (this feature)
- Path-isolation layer so the SAME deterministic scripts serve N independent identities with zero shared
  state (REQ-001..004).
- Proof that the tool layer is provider/model-agnostic (no `claude`-specific code in the deterministic
  scripts) — REQ-005.
- Proof that a second identity can be provisioned with zero credential/wallet overlap BY CONSTRUCTION
  (not just convention) — REQ-006.
- No-human-credential account provisioning reuses the already-proven `ig-account-create` flow — REQ-007.
- Safe empty-state behavior for a not-yet-provisioned second instance — REQ-008.

## Out of scope (separate follow-on features, not blocked by this one)
- Building a second, ClawRouter-specific persistent-loop LAUNCHER (analogous to `clip-cli.sh` but
  dispatching through the genesis `~/anicca` loop instead of a tmux `claude` process). This feature makes
  the WORKER layer launcher-agnostic (REQ-005); it does not itself write the second launcher. Tracked
  under task #3 / follow-on feature `clip-loop-clawrouter-provision`.
- Actually provisioning a full second live identity (new wallet + new IG/TikTok account + first live post)
  — this is a bigger, slower effort (account creation + warmup) tracked as task #3 / a future
  `clip-loop-clawrouter-provision` feature. This feature ships the ISOLATION LAYER that makes that future
  provisioning safe; it does not itself create the second account.
- The weekly self-improvement/scoring loop (task #4) and the promote.fun Sutando harness (task #5) — both
  depend on this isolation layer existing first, tracked as their own features.

## Requirements (EARS)

- **REQ-001**: WHEN `ANICCA_INSTANCE` is unset, THE SYSTEM SHALL resolve `CLIP_QUEUE`, `CLIP_POSTED`,
  `CLIP_ACCTS`, `CLIP_LEDGER` to byte-identical paths as the pre-feature hardcoded defaults
  (`~/clips/queue`, `~/clips/posted`, `~/.cloak/clip-accounts.json`,
  `~/.openclaw/state/clip-earn-ledger.jsonl`), so the already-live claude-p/myclaude loop has ZERO
  behavior change.
- **REQ-002**: WHEN `ANICCA_INSTANCE=<name>` is set, THE SYSTEM SHALL resolve `CLIP_QUEUE`/`CLIP_POSTED`/
  `CLIP_ACCTS`/`CLIP_LEDGER` (unless overridden per REQ-003) to paths suffixed with `-<name>`, distinct
  from the REQ-001 defaults — ledger is explicitly included, not just queue/posted/accounts, because
  REQ-004 requires ALL FOUR path types to never intersect across instances (a shared ledger would
  reintroduce the exact shared-state drain risk this feature exists to prevent).
- **REQ-003**: WHEN `EARN_LEDGER` is explicitly set, THE SYSTEM SHALL use that exact path for the ledger
  regardless of `ANICCA_INSTANCE` (existing override behavior preserved) — this is the ONLY sanctioned
  exception to REQ-002's ledger-suffixing.
- **REQ-004**: WHERE two or more instance names are configured **using the default (unset `EARN_LEDGER`)
  construction**, THE SYSTEM SHALL guarantee their resolved queue/posted/accounts/ledger paths never
  intersect (verified by an automated distinctness check across N instance names, not merely by naming
  convention). NOTE: REQ-003's `EARN_LEDGER` override is an explicit escape hatch outside this guarantee —
  if an operator manually sets the identical `EARN_LEDGER` value for two different instances, that is
  operator misuse (an explicit, intentional override), not a system defect; REQ-004 only covers the
  system's own default derivation, not a deliberately-collided manual override.
- **REQ-005**: THE SYSTEM SHALL contain no model/provider-specific branching (no conditional that checks
  which model/provider is calling) in the **shared deterministic WORKER layer** —
  `producer.sh`/`run.sh`/`monitor.sh`/`_instance_paths.sh` — so any calling agent (human-funded Claude Code
  session, self-funded ClawRouter process, or any future AI) can invoke these four scripts identically;
  only env vars (`ANICCA_INSTANCE`, `EARN_MODE`, etc.) differ.
  ★ Explicit scope carve-out (found by Phase-1c iteration-3 adversary): `clip-cli.sh` is NOT one of the
  four worker scripts above — it is the **persistent-loop LAUNCHER**, and by design each instance has its
  OWN launcher: `clip-cli.sh` legitimately hardcodes `claude --model sonnet` because it IS the claude-p
  (human-funded) instance's launcher. A self-funded ClawRouter instance needs a DIFFERENT launcher (e.g. a
  future `clip-cli-clawrouter.sh` that dispatches through the genesis `~/anicca` loop instead of a tmux
  `claude` process) — this is expected, not a violation, and REQ-005 does not apply to launcher scripts.
  Building that second launcher is out of scope for this feature (see "Out of scope" — task #3 / follow-on
  `clip-loop-clawrouter-provision`). This feature only guarantees the WORKER layer is launcher-agnostic.
- **REQ-006**: WHEN a second instance's credential set is generated, THE SYSTEM SHALL be checkable for zero
  overlap against every other known instance's wallet pubkey and account handles (an automated check, not
  a manual promise).
- **REQ-007**: WHEN provisioning a new instance's social account, THE SYSTEM SHALL rely only on already
  no-human-verified flows (`ig-account-create`: Gmail plus-address signup + `gog gmail` auto-OTP read) —
  no step in the documented flow requires a human to type a credential or code at runtime.
- **REQ-008**: IF a given instance's queue/accounts files do not yet exist, THEN `run.sh`/`monitor.sh`
  SHALL report an empty/"nothing to post" state for that instance and SHALL NOT read or fall back to a
  different instance's files.

## Non-functional constraints
- Zero regression to the live claude-p tmux loop (`anicca-clip-core`) — REQ-001 is the regression guard.
- No dry runs (HARD RULE 0.24): every acceptance check in Phase 2/3 must be a real execution with a real
  file-system side effect (paths actually created/read), not a mocked assertion.
