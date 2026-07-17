# Security Report — fable5-config-slimdown (Phase 5, Formal Hardening)

Scope: this branch (`feature/fable5-config-slimdown`) touches a **public** repo
(`github.com/Daisuke134/anicca-products`), so any credential/secret leak into a tracked file or
commit is a real exposure the moment it's pushed. This report covers (1) a secrets scan of
everything this feature adds to the repo, (2) confirmation that the local backup store used by
the feature is outside git entirely, and (3) a scope check on every edited hook/config file to
confirm no new execution path was introduced.

## 1. Secrets scan — all commits in scope

Commits in scope (the 10 feature commits, `0142b4fa3~1..HEAD`, plus the docs-spec commit
`0142b4fa3` itself):

```
fc68caaf2 tier-2 E2E evidence
15e09d43c green evidence + enter phase 3
a2bc9d65d phase 2b GREEN — P1-P8 implemented
1d368dbcc red+regression markers, enter phase 2b
3a8087723 red evidence at canonical path, phase 2b
c487f8467 phase 2a — tests/verify.sh + RED evidence
ce5e8e4c6 spec review PASS at iteration 3
58cbca8f2 spec revision per iteration-2 findings
55f0c9e31 spec revision per iteration-1 findings
41125d727 phase 1a/1b — EARS spec + verification architecture
0142b4fa3 docs(spec): fable5-config-slimdown P1-P8 design spec
```

Full patch of these 11 commits (`git log -p 0142b4fa3~1..HEAD`, 2470 lines) was scanned for
credential-shaped strings:

```
grep -inE '(api[_-]?key|secret[_-]?key|token\s*[:=]|bearer [a-z0-9]|AKIA[0-9A-Z]{16}|
  -----BEGIN [A-Z]+ PRIVATE KEY-----|password\s*[:=]|CAP-[A-Za-z0-9]{10,}|
  sk-[a-zA-Z0-9]{16,}|ghp_[A-Za-z0-9]{20,}|xox[baprs]-[0-9A-Za-z-]+)' /tmp/fable5-diff-full.txt
```

Result: **0 matches.** The 30 files this feature adds/touches in the repo are all
`.vcsdd/features/fable5-config-slimdown/**` (specs, tests, evidence, review JSON), plus the two
`.claude/settings.json` files. None contain API keys, bearer tokens, AWS keys, private-key
blocks, passwords, CapSolver keys, or common vendor token prefixes.

`.claude/settings.json` (the one file this feature edits that lives inside the repo, for PROP-P6a)
diff is a single-line addition:

```diff
-  "outputStyle": "concise"
+  "outputStyle": "concise",
+  "effortLevel": "high"
```

No secret-shaped content; scanned with the same pattern set, 0 matches.

`evidence/p4-pre-hooks.json` / `evidence/p4-post-hooks.json` (the two files most likely to leak an
operational secret, since they're raw dumps of `~/.claude/settings.json`'s `.hooks` block) contain
only hook **script paths** and shell **command bodies** (cozempic/disk-guard/ssot-guard/
post-edit-check/stop-block invocation lines) — no embedded credentials. Verified by extracting
every `.command` string from both files and re-running the same secret-pattern grep plus a manual
read: 0 matches, no `Authorization:`, no `.env` content, no key material.

`evidence/e2e-2026-07-07.log` and `evidence/move-ref-check.log`: plain-text transcripts of a
context-string search and a grep-hit tally respectively; scanned, 0 matches.

## 2. Local backup store — confirmed outside git

`REQ-SAFE-1` requires 6 pre-edit backups under `~/.claude/backups/fable5-slimdown-2026-07-07/`.
Confirmed this directory is **not** part of the public repo's history or working tree:

- `~/.claude` itself is not a git repository (`git status` inside it returns "Not a git
  repository").
- `git ls-files | grep -i "backups/fable5"` inside the anicca-project worktree → no output (never
  tracked).
- `git status --porcelain | grep -i backup` → no output (not even untracked-and-visible; it's
  physically outside the repo directory tree at `/Users/anicca/anicca-project`).
- `find /Users/anicca/anicca-project -iname "*fable5-slimdown*"` → no results.

The backup directory holds full copies of `git-context-lite.sh`, `hooks.json`,
`loop-engineering.md`, `session-architecture.md`, `settings.json`, and `settings.json.worktree` —
all of which are themselves config/prose files with no embedded credentials (same secret-pattern
grep run directly against the backup directory: 0 matches) — but even if they had contained
anything sensitive, this confirms they can never reach the public remote through this feature's
git history.

## 3. New-execution-path check on every edited hook/config file

| File | Edit type | Verification |
|---|---|---|
| `git-context-lite.sh` | Text-only heredoc replacement | `bash -n` → syntax OK. `diff` vs SAFE-1 backup shows only prose lines changed inside a markdown heredoc (`### Never without explicit user request` block removed and replaced with a `### Commit/push policy` prose block; `Avoid \`git add -A\`` bullet removed). No new shell command, no new `eval`/`source`/subprocess call introduced — every changed line is inert text inside a printed/heredoc string. |
| `hooks.json` (superpowers) | Entry deletion only | `diff` vs SAFE-1 backup: the `SessionStart` array (one entry, `run-hook.cmd session-start`) was replaced with `[]`. This is strictly a **removal** — no hook entry was added, no command string changed. `jq .` parses cleanly. |
| `~/.claude/settings.json` | Entry deletion only | Per-key diff of `.hooks.{PostCompact,PostToolUse,PreCompact,PreToolUse,SessionStart,Stop,UserPromptSubmit}` between the SAFE-1 pre-edit backup and the live file: only `UserPromptSubmit` changed, and it changed from `[{"matcher":"*","hooks":[{"type":"command","command":"~/.claude/hooks/ssot-guard.sh"}]}]` to `[]` — a pure removal of the `ssot-guard.sh` invocation, confirmed against the feature's own `p4-pre-hooks.json`/`p4-post-hooks.json` snapshots. All 6 other hook categories (including `SessionStart`, which fires the cozempic checkpoint/guard chain) are byte-identical, so no new trigger surface exists there either. |
| `.claude/settings.json` (worktree, this repo) | Field addition | `+  "effortLevel": "high"` — a string-valued config field consumed by the harness's own reasoning-effort setting, not a command or path. No new execution surface. |
| `session-architecture.md` | Content replacement, size reduction 93→16 lines | This is a prose/markdown reference file injected into context by a hook, not itself executable; the hook that reads it (`git-context-lite.sh` family) is unchanged in *how* it reads the file, only the file's *content* shrank. No new code path. |
| `~/anicca/skills/**` (8 loop-CLI scripts) | Single-line self-referencing string append (`VAR="${VAR} ...PushNotification..."`) inside an existing variable used later as a `claude -p`/`tmux new-session` prompt argument | Confirmed via `git show HEAD:...` diff that the assign-span and the launch line are byte-identical to the pre-edit state; the only change is one inserted line in between that concatenates additional **prompt text** onto an existing string variable. This does not add a new shell command, branch, network call, or tool invocation — it changes what text is handed to the already-existing `claude -p`/`tmux` call, which was the intended effect (PROP-P7a/P7b). |
| `~/anicca/skills/_shared/adversary-daily.sh` | `--model opus` flag addition | Confirmed via `grep` — a CLI flag change on an existing `claude` invocation, not a new command. |

No file in this feature's scope had a `eval`, `curl | sh`, `source <(...)`, or similar
dynamic-execution pattern introduced. Every edit is either (a) a pure deletion of an existing hook
entry, (b) a single string-literal/flag addition consumed by an already-existing invocation, or
(c) a prose-content change to a non-executable markdown file.

## Conclusion

**PASS.** No secrets found in any commit, evidence file, or edited config file in this feature's
scope. The pre-edit backup store (`~/.claude/backups/fable5-slimdown-2026-07-07/`) is confirmed
local-only and outside git entirely, so it cannot leak to the public remote through this feature.
Every edited hook/settings file was diffed against its pre-edit backup and shown to be either a
pure removal or a scoped, non-executable content/flag change — no new execution path was
introduced.
