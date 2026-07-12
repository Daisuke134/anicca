# Article Loop (#7) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** A daily loop that writes one researched article (JP + EN) and posts it as an unpublished DRAFT to all five platforms (note / Zenn / Substack / X / dev.to), reports every draft URL to Dais on Telegram, and never publishes anything by itself.

**Architecture:** A launchd job (06:00 JST) runs `article-daily.sh`, a thin driver with no timeout that shells out to a single `claude -p` pass. That pass invokes the existing `ai-entity-article-writer` skill, runs its existing quality gates, calls each platform's existing `publish-to-*.sh` in draft mode, opens each draft in the already-logged-in daily-driver Chromium (CDP :9222) to confirm it exists in a draft (not published) state, and finally reports every draft URL over `openclaw message send --channel telegram`. Before any of that, `post-devto.py` — the one code path that flips `published: true` — is hard-wired to `False` so an auto-publish is not merely discouraged but impossible.

**Tech Stack:** bash, launchd, Python 3 (dev.to REST API), Claude Code headless (`claude -p`), CDP/agent-browser on :9222, openclaw Telegram plugin.

**Why these three defects are designed out (learned the hard way on gig / connector / capafy / life-manager today):**
1. A `CronCreate` the agent registers for itself is never persisted anywhere — the loop runs once and sleeps forever. → launchd is the only scheduler.
2. A `timeout` kills the pass mid-work (capafy died at CP1, life-manager posted nothing at all, both rc=124). → no timeout; the pass runs until the work is done.
3. `PushNotification` silently no-ops when Remote Control is inactive, so Dais is never told anything. → `openclaw message send --channel telegram --target 8547730585`, whose real messageId we verify.

---

### Task 1: Make auto-publish to dev.to impossible

`post-devto.py:70` currently sends `"published": not DRY_RUN`, i.e. a real (non-dry) run publishes the article live. That is the single line standing between an AI-slop draft and the public internet. Nothing else in the loop can be trusted to "remember" not to publish, so we remove the capability.

**Files:**
- Modify: `~/.openclaw/skills/article-writer/scripts/post-devto.py:70`
- Test: `~/profitable-claude/tests/art/test_devto_never_publishes.sh`

- [ ] **Step 1: Write the failing test**

Create `~/profitable-claude/tests/art/test_devto_never_publishes.sh`:

```bash
#!/usr/bin/env bash
# The dev.to poster must NEVER be able to publish. A draft that goes live for even a
# moment is indexed and syndicated via RSS -- there is no taking it back. This test
# asserts the payload is hard-coded to published:false, not merely defaulted to it.
set -uo pipefail
SRC="$HOME/.openclaw/skills/article-writer/scripts/post-devto.py"
FAIL=0

if grep -qE '"published"[[:space:]]*:[[:space:]]*not DRY_RUN' "$SRC"; then
  echo "FAIL: payload still publishes on a non-dry run (\"published\": not DRY_RUN)"
  FAIL=1
fi

if ! grep -qE '"published"[[:space:]]*:[[:space:]]*False' "$SRC"; then
  echo "FAIL: payload does not hard-code \"published\": False"
  FAIL=1
fi

if [ "$FAIL" -eq 0 ]; then echo "PASS: dev.to poster is draft-only"; fi
exit "$FAIL"
```

Make it executable:

```bash
mkdir -p ~/profitable-claude/tests/art
chmod +x ~/profitable-claude/tests/art/test_devto_never_publishes.sh
```

- [ ] **Step 2: Run test to verify it fails**

Run: `bash ~/profitable-claude/tests/art/test_devto_never_publishes.sh`
Expected: FAIL, printing `FAIL: payload still publishes on a non-dry run` and `FAIL: payload does not hard-code "published": False`, exit 1.

- [ ] **Step 3: Write minimal implementation**

In `~/.openclaw/skills/article-writer/scripts/post-devto.py`, replace line 70:

```python
            "published": not DRY_RUN,
```

with:

```python
            # DRAFT-ONLY, permanently (Dais 2026-07-12): this loop must never put an
            # unreviewed article on the public internet. dev.to honours published:false
            # as an unlisted draft that only the author can open. Publishing is a human
            # decision made from the dev.to dashboard after reading the draft -- there is
            # deliberately no code path here that can set this to True.
            "published": False,
```

- [ ] **Step 4: Run test to verify it passes**

Run: `bash ~/profitable-claude/tests/art/test_devto_never_publishes.sh`
Expected: PASS, printing `PASS: dev.to poster is draft-only`, exit 0.

- [ ] **Step 5: Commit**

```bash
cd ~/.openclaw && git add skills/article-writer/scripts/post-devto.py && git commit -m "fix(article): dev.to poster is draft-only, publishing is now impossible

The payload sent published:true on any non-dry run, so a single loop pass would put an
unreviewed article on the public internet, where it is immediately indexed and pushed to
RSS. Hard-coded to False: publishing is a human decision made from the dashboard after
reading the draft."
cd ~/profitable-claude && git add tests/art/test_devto_never_publishes.sh && git commit -m "test(article): assert the dev.to poster can never publish"
```

---

### Task 2: The daily driver script

**Files:**
- Create: `~/profitable-claude/skills/human-funded/article/article-daily.sh`
- Test: `~/profitable-claude/tests/art/test_article_daily_contract.sh`

- [ ] **Step 1: Write the failing test**

Create `~/profitable-claude/tests/art/test_article_daily_contract.sh`:

```bash
#!/usr/bin/env bash
# The three defects that silently killed four other loops today, asserted as code:
#   1. a self-registered CronCreate is never persisted -> the loop must not rely on one
#   2. a timeout kills the pass mid-work (capafy rc=124 at CP1, life-manager posted nothing)
#   3. PushNotification silently no-ops -> Dais is never told anything
# Plus the one rule specific to this loop: it must never publish.
set -uo pipefail
SRC="$HOME/profitable-claude/skills/human-funded/article/article-daily.sh"
FAIL=0

[ -f "$SRC" ] || { echo "FAIL: $SRC does not exist"; exit 1; }

bash -n "$SRC" || { echo "FAIL: syntax error"; FAIL=1; }
[ -x "$SRC" ] || { echo "FAIL: not executable"; FAIL=1; }

if grep -qE '^[[:space:]]*timeout ' "$SRC"; then
  echo "FAIL: has a timeout -- it will kill the pass mid-work"; FAIL=1
fi
if grep -q 'CronCreate' "$SRC"; then
  echo "FAIL: relies on a self-registered cron, which is never persisted"; FAIL=1
fi
if grep -q 'PushNotification' "$SRC"; then
  echo "FAIL: uses PushNotification, which never reaches Dais"; FAIL=1
fi
if ! grep -q 'openclaw message send --channel telegram --target 8547730585' "$SRC"; then
  echo "FAIL: does not report to Dais on the telegram channel that actually delivers"; FAIL=1
fi
if ! grep -q 'lockdir' "$SRC"; then
  echo "FAIL: no exclusive lock -- concurrent runs will fight over the :9222 browser tab"; FAIL=1
fi
for word in draft note zenn substack dev.to; do
  grep -qi -- "$word" "$SRC" || { echo "FAIL: prompt never mentions $word"; FAIL=1; }
done
if grep -qiE 'mode go|--publish|published: true' "$SRC"; then
  echo "FAIL: contains a publish path -- this loop must only ever create drafts"; FAIL=1
fi

if [ "$FAIL" -eq 0 ]; then echo "PASS: article-daily.sh honours the loop contract"; fi
exit "$FAIL"
```

Make it executable:

```bash
chmod +x ~/profitable-claude/tests/art/test_article_daily_contract.sh
```

- [ ] **Step 2: Run test to verify it fails**

Run: `bash ~/profitable-claude/tests/art/test_article_daily_contract.sh`
Expected: FAIL with `FAIL: /Users/anicca/profitable-claude/skills/human-funded/article/article-daily.sh does not exist`, exit 1.

- [ ] **Step 3: Write minimal implementation**

Create `~/profitable-claude/skills/human-funded/article/article-daily.sh`:

```bash
#!/usr/bin/env bash
# article-daily.sh — one daily pass of the article loop. DRAFTS ONLY: this loop writes and
# stages, a human publishes. Nothing here may put an unreviewed article on the internet.
#
# Three defects, found the hard way on four other loops today, are designed out:
#   1. The agent used to register its own cron ("I'll wake at 9am"), which was never persisted
#      anywhere -- the loop ran once and slept forever. launchd is now the only scheduler.
#   2. A `timeout` killed the pass mid-work (capafy died inside CP1, life-manager posted
#      nothing at all, both rc=124). There is no timeout here; the pass runs until it is done.
#   3. PushNotification silently no-ops when Remote Control is inactive, so Dais was never
#      actually told anything. We use the openclaw telegram channel, which returns a real id.
export PATH="/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin:$HOME/.local/bin:$PATH"
set -uo pipefail
CLAUDE="$(command -v claude || echo "$HOME/.local/bin/claude")"
LOG="$HOME/.openclaw/logs/article-daily.log"
STATE="$HOME/profitable-claude/skills/human-funded/article/state"
mkdir -p "$(dirname "$LOG")" "$STATE"
TS="$(date '+%F %T %Z')"

# Exclusive lock. Every loop that drives the shared daily-driver browser (:9222) must hold this
# kind of lock: capafy ran without one and two schedulers raced on the same tab five times in
# 90 minutes, each seeing the other's half-edited DOM and dying on max-turns. mkdir is atomic on
# any POSIX filesystem and needs no extra binary (macOS ships no `flock`).
LOCK_DIR="$STATE/.article_daily.lockdir"
if mkdir "$LOCK_DIR" 2>/dev/null; then
  trap 'rmdir "$LOCK_DIR" 2>/dev/null' EXIT
else
  # A lock older than 6h means a previous run died without cleaning up. Steal it rather than
  # wedging the loop shut forever.
  AGE=$(( $(date +%s) - $(stat -f %m "$LOCK_DIR" 2>/dev/null || echo 0) ))
  if [ "$AGE" -gt 21600 ]; then
    rmdir "$LOCK_DIR" 2>/dev/null; mkdir "$LOCK_DIR" 2>/dev/null
    trap 'rmdir "$LOCK_DIR" 2>/dev/null' EXIT
  else
    echo "=== $TS article-daily SKIPPED — another instance holds the lock (age ${AGE}s) ===" >>"$LOG"
    exit 0
  fi
fi

echo "=== article-daily run $TS ===" >>"$LOG"

PROMPT='You are the Anicca article loop (claude-p, one daily pass, no human in the loop until the very end). This pass was triggered by a real launchd schedule (ai.anicca.article-daily) — you do NOT need to register a cron for yourself, and any cron you tried to register would not persist anyway.

★★ THE ONE INVIOLABLE RULE: YOU CREATE DRAFTS. YOU NEVER PUBLISH. ★★ Dais reads the drafts and publishes by hand. An unreviewed article on the public internet is indexed and syndicated within minutes and cannot be taken back, so never pass --mode go, never set published:true, never click a publish button. If you are ever unsure whether an action publishes, do not take it.

STEP 1 TOPIC: read ~/.claude/skills/ai-entity-article-writer/state/topic-queue.md and the recent state/ files to see what has already been covered, then pick ONE topic about AI entities (AI that earns money with little or no human in the loop). Do not repeat a topic already written.

STEP 2 RESEARCH: research it properly — firecrawl for the web, context7 for library docs, and where the topic is a tool or repo, actually RUN it and report what really happened. A claim you have not verified does not go in the article.

STEP 3 WRITE: write the article in Japanese AND in English (same topic, each written natively rather than translated). Then run the existing quality gates and fix what they flag: bash ~/.claude/skills/ai-entity-article-writer/scripts/language-purity-gate.sh, bash ~/.claude/skills/ai-entity-article-writer/scripts/seo-gate.sh, bash ~/.claude/skills/ai-entity-article-writer/scripts/freshness-gate.sh. Then use the stop-ai-slop-jp skill on the Japanese draft — em-dashes and pet phrases are the least of it; the tells that matter are an absent author, propositional headings, false balance, and uniformly-metered sentences.

STEP 4 STAGE FIVE DRAFTS (all five, every pass — a pass that stages three is a failed pass):
  note     — bash ~/.claude/skills/ai-entity-article-writer/scripts/note-publish/publish-to-note.sh publish <ja.md> --mode draft
  zenn     — bash ~/.claude/skills/ai-entity-article-writer/scripts/zenn-publish/publish-to-zenn.sh draft <slug>   (pushes published:false)
  substack — bash ~/.claude/skills/ai-entity-article-writer/scripts/substack-publish/publish-to-substack.sh publish <md> --title "T" --mode draft   (run it for JA and again for EN)
  X        — bash ~/.claude/skills/ai-entity-article-writer/scripts/x-publish/publish-to-x.sh publish <md> --mode draft
  dev.to   — bash ~/.claude/skills/ai-entity-article-writer/scripts/publish-devto.sh --markdown-file <en.md> --title "T" --meta <m>   (the poster is hard-wired to published:false; it cannot publish even if you ask it to)
Capture every draft URL / draft id these print.

STEP 5 VERIFY EACH DRAFT WITH YOUR OWN EYES: open every draft URL in the already-logged-in daily-driver Chromium (CDP :9222, e.g. agent-browser --auto-connect) and confirm two things on the real page: the draft exists, and it is NOT public (it shows as a draft / unpublished / unlisted). A tool that returned 200 is not evidence — look at the page. Today the Reddit loop taught us the inverse of this lesson: a post can look fine to the account that made it and be invisible to everyone else, and nobody noticed for a week because nobody looked.

STEP 6 REPORT TO DAIS — MANDATORY, every pass, success or failure: openclaw message send --channel telegram --target 8547730585 --message "<report>" --json. The message must carry the topic, all five draft URLs (say plainly which ones failed if any did), what you verified on each page with your own eyes, and the honest state — if a gate rejected the article and you staged nothing, say that. Never report a draft you did not actually see. Confirm the send returned a real messageId; if it fails, retry once, then record the failure in the state dir.

STEP 7 RECORD: append one honest row per platform to '"$STATE"'/articles.jsonl: {ts, topic, platform, lang, draft_url, state:"draft"|"failed:<reason>", verified_logged_in:true|false, published:false}. published is always false — if you ever find yourself writing true, something has gone very wrong and you should stop and report it.

A blocked platform is not a reason to stop: stage the others, report the failure honestly, and fix the cause in the code so tomorrow it works. Never fake a draft URL, never claim a verification you did not perform.'

env -u ANTHROPIC_API_KEY "$CLAUDE" --model sonnet --dangerously-skip-permissions --add-dir "$HOME" -p "$PROMPT" >>"$LOG" 2>&1
RC=$?
echo "=== article-daily done rc=$RC $(date '+%F %T %Z') ===" >>"$LOG"
touch "$HOME/.openclaw/state/.article-loop-last-pass" 2>/dev/null || true
exit 0
```

Make it executable:

```bash
chmod +x ~/profitable-claude/skills/human-funded/article/article-daily.sh
```

- [ ] **Step 4: Run test to verify it passes**

Run: `bash ~/profitable-claude/tests/art/test_article_daily_contract.sh`
Expected: PASS, printing `PASS: article-daily.sh honours the loop contract`, exit 0.

- [ ] **Step 5: Commit**

```bash
cd ~/profitable-claude && git add skills/human-funded/article/article-daily.sh tests/art/test_article_daily_contract.sh && git commit -m "feat(article): daily driver — five drafts, zero publishes

Writes one researched article (JP+EN) and stages it as an unpublished draft on note, Zenn,
Substack, X and dev.to, verifies each draft on the real page in the logged-in browser, and
reports every URL to Dais on Telegram. It cannot publish: there is no publish path in the
prompt and the dev.to poster is hard-wired to published:false.

Designs out the three defects that killed four other loops today: no self-registered cron
(never persisted), no timeout (it killed capafy inside CP1 and left life-manager with nothing
posted), and no PushNotification (it silently never reached Dais)."
```

---

### Task 3: Wire the launchd schedule

06:00 JST, before every other browser-driving loop wakes (connector 07:50, capafy 08:10, life-manager 10:15), so the article pass — the longest of them — has the daily-driver to itself.

**Files:**
- Create: `~/Library/LaunchAgents/ai.anicca.article-daily.plist`
- Test: `~/profitable-claude/tests/art/test_article_launchd.sh`

- [ ] **Step 1: Write the failing test**

Create `~/profitable-claude/tests/art/test_article_launchd.sh`:

```bash
#!/usr/bin/env bash
# launchd is the only scheduler this loop may have. Assert the job is loaded, points at the
# real driver, and fires at 06:00 -- ahead of every other loop that drives the shared browser.
set -uo pipefail
PLIST="$HOME/Library/LaunchAgents/ai.anicca.article-daily.plist"
FAIL=0

[ -f "$PLIST" ] || { echo "FAIL: $PLIST does not exist"; exit 1; }
plutil -lint "$PLIST" >/dev/null || { echo "FAIL: malformed plist"; FAIL=1; }

if ! launchctl list | grep -q 'ai.anicca.article-daily'; then
  echo "FAIL: job is not loaded into launchd"; FAIL=1
fi
if ! /usr/libexec/PlistBuddy -c "Print :ProgramArguments" "$PLIST" 2>/dev/null | grep -q 'article-daily.sh'; then
  echo "FAIL: does not point at article-daily.sh"; FAIL=1
fi
H="$(/usr/libexec/PlistBuddy -c "Print :StartCalendarInterval:Hour" "$PLIST" 2>/dev/null)"
[ "$H" = "6" ] || { echo "FAIL: fires at hour '$H', expected 6"; FAIL=1; }

if [ "$FAIL" -eq 0 ]; then echo "PASS: article-daily is scheduled at 06:00"; fi
exit "$FAIL"
```

Make it executable:

```bash
chmod +x ~/profitable-claude/tests/art/test_article_launchd.sh
```

- [ ] **Step 2: Run test to verify it fails**

Run: `bash ~/profitable-claude/tests/art/test_article_launchd.sh`
Expected: FAIL with `FAIL: /Users/anicca/Library/LaunchAgents/ai.anicca.article-daily.plist does not exist`, exit 1.

- [ ] **Step 3: Write minimal implementation**

Create `~/Library/LaunchAgents/ai.anicca.article-daily.plist`:

```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0"><dict>
  <key>Label</key><string>ai.anicca.article-daily</string>
  <key>ProgramArguments</key>
  <array><string>/bin/bash</string><string>/Users/anicca/profitable-claude/skills/human-funded/article/article-daily.sh</string></array>
  <key>StartCalendarInterval</key><dict><key>Hour</key><integer>6</integer><key>Minute</key><integer>0</integer></dict>
  <key>StandardOutPath</key><string>/Users/anicca/.openclaw/logs/article-daily.out</string>
  <key>StandardErrorPath</key><string>/Users/anicca/.openclaw/logs/article-daily.err</string>
</dict></plist>
```

Load it:

```bash
plutil -lint ~/Library/LaunchAgents/ai.anicca.article-daily.plist
launchctl bootstrap gui/$(id -u) ~/Library/LaunchAgents/ai.anicca.article-daily.plist
```

- [ ] **Step 4: Run test to verify it passes**

Run: `bash ~/profitable-claude/tests/art/test_article_launchd.sh`
Expected: PASS, printing `PASS: article-daily is scheduled at 06:00`, exit 0.

- [ ] **Step 5: Commit**

```bash
cd ~/profitable-claude && git add tests/art/test_article_launchd.sh && git commit -m "test(article): assert the launchd job is loaded and fires at 06:00

launchd is the only scheduler this loop may have -- an agent-registered cron is never
persisted, which is exactly how capafy and life-manager ended up asleep for a day."
```

---

### Task 4: Prove it end to end, with my own eyes

A green test suite is not evidence that a loop works. The only evidence that counts is five real drafts I opened and looked at.

**Files:**
- Run: `~/profitable-claude/skills/human-funded/article/article-daily.sh`
- Create: `~/anicca-project/docs/superpowers/evidence/07-article.md`

- [ ] **Step 1: Run the loop for real**

```bash
bash ~/profitable-claude/skills/human-funded/article/article-daily.sh
```

This has no timeout and will take a while (research + two languages + five platforms). Watch it:

```bash
tail -f ~/.openclaw/logs/article-daily.log
```

Expected: the log ends with `=== article-daily done rc=0 ... ===`.

- [ ] **Step 2: Read what it claims it did**

```bash
cat ~/profitable-claude/skills/human-funded/article/state/articles.jsonl
```

Expected: five rows (note, zenn, substack, x, devto), each with a real `draft_url` and `"published": false`.

- [ ] **Step 3: Verify every draft myself — do not trust the report**

For each of the five `draft_url` values, open it in the logged-in daily-driver and look at the page:

```bash
agent-browser open "<draft_url>"
agent-browser wait --load networkidle
agent-browser screenshot ~/anicca-project/docs/superpowers/evidence/screenshots/07-article-<platform>.png
```

Then Read each screenshot. Expected on every one: the article exists, and the page says draft / unpublished / unlisted. If any page shows a live public article, that is a P0 — stop, unpublish it immediately, and fix the code path that published it before doing anything else.

- [ ] **Step 4: Confirm dev.to specifically is not public**

The dev.to draft is the one that could actually be indexed, so check it from outside the browser too:

```bash
curl -s -o /dev/null -w '%{http_code}\n' "<devto_draft_url>"
```

Expected: `404` (dev.to returns 404 for an unpublished article to anyone who is not the author). A `200` means it is live — unpublish it immediately.

- [ ] **Step 5: Confirm Dais actually got the Telegram report**

```bash
grep -i 'messageId' ~/.openclaw/logs/article-daily.log | tail -1
```

Expected: a real numeric messageId. No id means Dais was told nothing, which is the exact failure PushNotification was silently committing on two other loops.

- [ ] **Step 6: Write the evidence file and commit**

Write `~/anicca-project/docs/superpowers/evidence/07-article.md` recording: the topic, the five draft URLs, what each screenshot showed, the dev.to 404, the Telegram messageId, and — honestly — anything that failed. Then:

```bash
cd ~/anicca-project && git add docs/superpowers/evidence/07-article.md docs/superpowers/evidence/screenshots/07-article-*.png && git commit -m "docs(evidence): #7 article — five drafts staged and verified, nothing published"
```

- [ ] **Step 7: Close the task in the SSOT**

Update the `[ ] #7 article` line in `~/anicca-project/docs/loop-engineering/00-SSOT.md` to `[x]`, recording what was verified and what the honest revenue is (¥0 until Dais publishes and a paid article sells). Commit and push.

---

## Self-Review

**Spec coverage:** launchd 06:00 (Task 3) · no timeout (Task 2, asserted in test) · no self-registered cron (Task 2, asserted) · Telegram not PushNotification (Task 2 asserted, Task 4 step 5 verified) · five platforms in draft (Task 2 prompt, Task 4 verified) · dev.to made incapable of publishing (Task 1) · logged-in draft verification (Task 2 STEP 5, Task 4 step 3) · quality gates + stop-ai-slop-jp (Task 2 STEP 3) · mkdir lock against browser contention (Task 2, asserted) · evidence file (Task 4). Every requirement maps to a task.

**Placeholder scan:** No TBDs. Every code step contains the literal code or command. The `<draft_url>` / `<platform>` placeholders in Task 4 are runtime values the executor substitutes from `articles.jsonl` — they are not unwritten decisions.

**Type consistency:** `articles.jsonl` fields (`ts, topic, platform, lang, draft_url, state, verified_logged_in, published`) are written in Task 2 STEP 7 and read back in Task 4 step 2 with the same names. `LOCK_DIR`, `LOG`, `STATE` are defined once and used consistently. The test in Task 2 greps for `lockdir`, which matches the `.article_daily.lockdir` path. The launchd Label `ai.anicca.article-daily` matches between the plist, the test, and the prompt.
