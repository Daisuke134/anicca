# Behavioral Spec — promote-gate-claude-bin-fix

## Context

`skills/earn/self-improve/lib/promote_gate_run.py::_resolve_claude_bin()` is the single
place the self-improve harness locates the `claude` CLI binary before shelling out to a
fresh Opus adversary for candidate promotion (REQ-RH4 step 3).

Observed failure (2026-07-10, run `run-20260710T004921Z`, launchd-triggered
`ai.anicca.self-improve-evolve`): a genuinely eligible candidate
(`combined_score=3.9947`, `mean_oos_net_usd=$13.9994`, all three OOS windows positive,
`tripwire_clear=true`) reached the adversary-invocation step and failed with
`"claude binary not found (tried /opt/homebrew/bin/claude)"`. Every promotable candidate
since has hit the same fail-closed path — the self-improve loop can propose and evaluate
candidates but can never promote one, because:

1. `shutil.which("claude")` returns `None` under launchd's minimal `PATH` (no
   `~/.local/bin` entry), and
2. the hardcoded fallback `"/opt/homebrew/bin/claude"` does not exist on this machine —
   the real npm-installed binary lives at `~/.local/bin/claude` (confirmed via
   `zsh -lc 'type claude'` → `/Users/operator/.local/bin/claude`; `~/.zshrc` only aliases
   flags onto that same binary, it does not create it).

This is a self-heal gap in the harness itself (fail-closed is correct *behavior* when the
binary truly cannot be found, but the fallback path was simply wrong), not an economic
decision — no wallet, ledger, or spend-cap code is touched.

## Requirements (EARS)

- REQ-CB1: WHEN `_resolve_claude_bin()` is called AND `shutil.which("claude")` finds a
  binary on `PATH`, THE SYSTEM SHALL return that path (unchanged behavior — no regression
  for environments where `PATH` is already correct, e.g. interactive shells or CI).
- REQ-CB2: WHEN `_resolve_claude_bin()` is called AND `shutil.which("claude")` returns
  `None`, THE SYSTEM SHALL check an ordered list of known-good absolute install paths
  (in order: `~/.local/bin/claude`, `/opt/homebrew/bin/claude`, `/usr/local/bin/claude`)
  and return the first one that exists on disk (`os.path.isfile` + executable bit, via
  `os.access(path, os.X_OK)`).
- REQ-CB3: WHEN none of `shutil.which` nor any known-good path resolves to an existing,
  executable file, THE SYSTEM SHALL return the same final fallback string as today
  (`"/opt/homebrew/bin/claude"`) so the existing `FileNotFoundError` → `{"ok": False,
  "error": f"claude binary not found (tried {claude_bin})"}` fail-closed path in
  `_invoke_adversary` is preserved byte-for-byte (REQ-CB3 is a pure no-op path; it must
  not silently swallow the "truly not installed anywhere" case).
- REQ-CB4: THE SYSTEM SHALL NOT change any other behavior of `promote_gate_run.py`
  (prompt construction, subprocess invocation, JSON parsing, promotion decision logic) —
  this is a single-function, additive fix.

## Purity Boundary

- `_resolve_claude_bin()` is impure (reads `PATH` env + filesystem `stat`/`access`
  calls) — same purity class as today, no change in kind, only in which paths it probes.
- All existing pure decision logic (`lib/promote_gate.py::assess_candidate` /
  `decide_promotion` / `promote_if_approved`) is untouched.

## Out of Scope

- No change to `.env`, wallet keys, `ledger.mjs`, spend caps, or
  `.vcsdd/features/anicca-agent-economy/**`.
- No change to the adversary prompt content or the `--max-budget-usd` cap.
- Not re-running the actual promote gate against the live candidate — this fix targets
  the *mechanism*; the next scheduled `self-improve-evolve` launchd tick will naturally
  exercise it against whatever candidate it produces (paper-only, no live money).
