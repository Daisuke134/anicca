# F1 — publish-to-note.sh (one-command note publisher) — spec — 2026-06-24

Goal: turn the proven (but scattered) note-publish scripts into ONE idempotent, guarded command, with a
deterministic VERIFY gate that gathers evidence for the agent's vision check. "post this to note" = one call.

## Contract
```
publish-to-note.sh verify  <noteKey>
    → deterministic evidence + visitor screenshot, for the agent (me / claude -p) to LOOK at.
    Output: API fields (price, is_limited, can_read, eyecatch) + screenshot path + PASS/FAIL on the
    deterministic checks. NEVER trusts the owner view — screenshots with NO cookies (a real visitor).

publish-to-note.sh publish <markdown> [--key <noteKey>|new] [--price 500] [--paywall-before "<heading>"]
                   [--eyecatch <img>] [--toc-from h2] [--mode draft|go]
    Orchestrates, in order, the proven step scripts (each already in scripts/note-publish/):
      1. cookies   extract-note-cookies.py (re-extract if missing/stale)              [auth]
      2. render    note-stage1-render.py + note-stage2-publish.py (NEW article only)  [md→imgs→draft]
      3. eyecatch  set-eyecatch-republish.py                                          [見出し画像]
      4. toc       insert-toc-save.py + delete-toc-node.py (manual big-titles 目次)    [目次]
      5. gate      publish.py (無料 + メンバー全員に公開 + 試し読み line before --paywall-before)
                   --mode draft = STOP before 投稿/更新 ; --mode go = publish/update
      6. plan      publish-membership.py / toggle-plan.py (plan 公開 ON)              [¥price live]
      7. verify    = the `verify` command above.
    All step scripts read NOTE_KEY from the env (default = the Automaton article key).
```

## Guards (the anti-slop spine — same as the live edits)
- Every mutating step prints a before/after invariant; the orchestrator ABORTS (no 投稿/更新) if a guard fails:
  h2/h3 counts unchanged by non-structural steps, manual 目次 present, auto-`<table-of-contents>` absent,
  eyecatch set. (These caught 3 near-misses during the manual run.)
- `--mode draft` is the default. `--mode go` (publish) only after the agent's VISION verify passes.

## VERIFY = deterministic evidence + AGENT vision (the boundary)
- The SCRIPT gathers truth it can measure: note API `price/is_limited/can_read/eyecatch` + a NO-cookie
  visitor screenshot saved to ~/.cloak/note-work/verify-<key>.png. Deterministic PASS = eyecatch set AND
  (membership-gated → can_read=false) AND price as expected.
- The JUDGMENT "does it LOOK good" (layout, crushed images, 目次=big titles, headings intact, lang pure) is
  the AGENT's: me now, or claude -p in automation, by Read-ing the screenshot. The script CANNOT judge taste;
  it only stages the evidence. This is why the pipeline never ships slop: a vision check is mandatory before go.

## Files
- New: scripts/note-publish/publish-to-note.sh (the orchestrator).
- Reuses: the existing scripts/note-publish/*.py (parameterized via NOTE_KEY env).
- Data/screenshots: ~/.cloak/note-work/ (real, persistent; never /tmp).

## Acceptance (verify NOW)
- `publish-to-note.sh verify na3a631e63d1a` → PASS, prints eyecatch=set, can_read=false, price=0, and saves a
  visitor screenshot; the agent Reads it and confirms it looks right. (Full new-article publish path is wired;
  it gets its first real E2E on the next article — F4 / Dais's next post.)
