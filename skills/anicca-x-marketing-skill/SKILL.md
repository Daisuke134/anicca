---
name: anicca-x-marketing-skill
description: End-to-end X (Twitter) marketing for Anicca empire. Channel A daily useful-info thread, Channel B weekly long-form, C launch, D cold-dm, E cross-post. You (the running LLM) ARE the writer — run the 7-step closed loop, never call an external LLM API. Posts via Postiz X integration (direct publish for production daily cron).
metadata:
  tags: x, twitter, marketing, postiz, closed-loop, all-products
  requires:
    bins: [bash, jq, curl, postiz]
    env: [POSTIZ_API_KEY, POSTIZ_X_INTEGRATION_ID]
---

# anicca-x-marketing-skill

You are the LLM running this skill via cron (HARD RULE #6: the skill IS the model — never `curl` OpenAI/Anthropic, never `claude -p`, never external LLM API; you write everything yourself). The bash scripts only do deterministic work (pillar/product rotation, Postiz posting). The thinking, research judgement, drafting, critique, humanizing — all you.

X numbers are near-zero today (best post ~36 impressions). The cause is one-shot AI slop. This skill fixes that with a mandatory **7-step closed loop**. No step may be skipped.

## Channel A — daily useful-info thread (cron `anicca-x-marketing-daily-info`, 08:20 JST)

This is the pilot channel. Run the 7-step loop, then post.

### STEP 0 — config (deterministic)
```bash
CFG=$(bash ~/.openclaw/skills/anicca-x-marketing-skill/scripts/channel-a-daily-info.sh --print-config)
DRAFT_FILE=$(echo "$CFG" | jq -r .draft_file)
echo "$CFG"   # {pillar, product, integration_id, draft_file}
```
```bash
DRAFT_FILE_EN="${DRAFT_FILE%.json}.en.json"   # EN 5-tweet thread JSON array
DRAFT_FILE_JP="${DRAFT_FILE%.json}.jp.json"   # JP 5-tweet thread JSON array
```
Capture `DRAFT_FILE`, `DRAFT_FILE_EN`, `DRAFT_FILE_JP` as shell variables and
use them downstream (do NOT hand-substitute a placeholder path). Today's
pillar+product anchor the thread. Both EN and JP are produced and drafted.

### STEP 1 — RESEARCH (read-only, you do this)
- Read `~/.openclaw/skills/_shared/state/hot-hooks.json` (refreshed daily 06:00 JST by hot-hooks-refresh from real Postiz analytics). Use the `x` section + `global_takeaways` to anchor STEP 2/3. If absent, skip silently.
- Recent X post analytics — run this EXACT command (env must be sourced for POSTIZ_API_KEY):
  ```bash
  set -a; source ~/.openclaw/.env; set +a
  /opt/homebrew/bin/postiz posts:list 2>&1 | sed -n '/^[\[{]/,$p' \
    | jq -r '(.posts // .) | map(select(.releaseURL!=null and (.releaseURL|test("twitter|x.com")))) | .[0:3][].id' \
    | while read pid; do echo "post $pid:"; /opt/homebrew/bin/postiz analytics:post "$pid" 2>&1 | sed -n '/^[\[{]/,$p'; done
  ```
  Note impressions vs zero (baseline is ~8-36 impr, 0-2 likes = dead; you must beat that).
- Read `~/.agents/skills/social/references/short-form-video.md` and the Twitter/X section of `~/.agents/skills/social/references/platforms.md` for current hook formulas (just Read the files; do not dispatch anything).
- Use your own up-to-date knowledge of what is going viral on X in AI / impermanence / autonomous-agent space (one-person AI company, agents running real businesses, etc.). Do NOT call any external API for this — you already know.
- Output: 1 short paragraph "what's resonating + what to avoid".

### STEP 2 — BOLD CLAIM
From today's `pillar` + `product`, extract ONE bold claim that answers all three: ① what is new ② why it matters ③ why it has never existed before. Generic = rejected. (Matt Epstein formula: 30 launches, 26 viral.)

### STEP 3 — 3 DRAFTS
Write the 5-tweet thread THREE times, different angle each:
- a) data-driven (a real number + proof)
- b) contrarian (kill a popular belief)
- c) story (first-person, specific, Anicca's lived empire)
Each tweet ≤ 270 chars. Tweet 1 = hook (no "excited to announce"). Tweet 5 = CTA with the product URL + `github.com/Daisuke134/anicca`.

### STEP 4 — CRITIQUE LOOP (recursive-improver)
Invoke the `recursive-improver` skill. Score each draft on: hook strength, invention novelty (≥7/10), copy intensity (≥7/10), 3-second-scroll survival, specificity/proof. Run 3 adversaries: skeptic CMO ("where's the proof?"), 3-second scroller ("do I stop?"), founder feed ("is this interesting to a founder/VC/AI engineer?"). Cut every filler line. Rewrite until the best draft clears all thresholds. Max 5 iterations. Pick the winner.

### STEP 5 — HUMANIZE
Invoke the `humanizer` skill (English). Strip AI tells: em-dash overuse, rule-of-three, promotional language, "in today's landscape", negative parallelism. The thread must read like a founder's own X account, not a content bot.

### STEP 6 — DELIVER (nano-banana figure + JP/EN, X = Postiz DIRECT type:now)

Delivery policy (Dais 2026-05-23, supersedes the 2026-05-19 draft policy): X is
**Postiz `type:"now"`** — the daily production cron PUBLISHES DIRECTLY to X (content
is quality-gated upstream by recursive-improver + humanizer). Exception: disabled
smoke/today-cron/manual e2e runs must still use `type:"draft"` (HARD RULE #9 — never
auto-post to @aniccaxxx during tests). Same content, JP + EN, two
drafts, staggered.

**6a. TWO nano-banana figures — EN figure AND JP figure (both, every run):**
Nano Banana 2 (the CLI) renders Japanese PERFECTLY (proven 2026-05-19) — so
generate a SEPARATE Japanese-text figure, do NOT reuse the English one. Each
= a real diagram (relation map / comparison / economics), zero-context-legible.
```bash
DIR="$(dirname "$DRAFT_FILE")"
cd ~/tools/nano-banana-2 && (set -a; . ~/.openclaw/.env; set +a; \
  bun src/cli.ts "<EN infographic prompt: ENGLISH title + 3-5 ENGLISH labelled callouts + product visual + aniccaai.com/<product>>" \
  -o xmkt_$(date +%Y%m%d)_en -s 2K -a 4:5 -d "$DIR")
cd ~/tools/nano-banana-2 && (set -a; . ~/.openclaw/.env; set +a; \
  bun src/cli.ts "縦4:5のクリーンなインフォグラフィック。日本語テキストを正確に。<日本語タイトル + 3-5個の日本語ラベル吹き出し + 製品ビジュアル + aniccaai.com/<product>>。完璧に読める日本語、箇条書きでなく実ダイアグラム" \
  -o xmkt_$(date +%Y%m%d)_ja -s 2K -a 4:5 -d "$DIR")
```
`Read` BOTH jpegs and verify (HARD RULE #8): EN legible+correct, JP legible+
correct Japanese (no mojibake/tofu). Bad → regenerate that one with a tighter
prompt.

**6b. EN thread + JP thread:** keep the 5-tweet EN thread (tweet 1 `🧵`).
Translate the SAME content to a JP 5-tweet thread (run `humanizer-ja`). EN
thread pairs the EN figure; JP thread pairs the JP figure.

**6c. POST as Postiz DRAFT — EN(EN figure) then JP(JP figure), staggered:**
```bash
INT="cmm6d7m5703rwpr0yr5vtme3w"   # {{profile.identity.{{profile.lateness.stakeholders.senderType}}Name}} X (only)
DIR="$(dirname "$DRAFT_FILE")"
set -a; . ~/.openclaw/.env; set +a
upimg(){ /opt/homebrew/bin/postiz upload "$1" 2>&1 | sed -n '/^{/,$p'; }
ENJ=$(ls -t "$DIR"/xmkt_*_en.jpeg 2>/dev/null | head -1); JPJ=$(ls -t "$DIR"/xmkt_*_ja.jpeg 2>/dev/null | head -1)
EN_U=$(upimg "$ENJ"); EN_PATH=$(echo "$EN_U"|jq -r '.path//empty'); EN_ID=$(echo "$EN_U"|jq -r '.id//empty')
JP_U=$(upimg "$JPJ"); JP_PATH=$(echo "$JP_U"|jq -r '.path//empty'); JP_ID=$(echo "$JP_U"|jq -r '.id//empty')
post_draft(){ # $1 thread JSON, $2 ISO date, $3 img path, $4 img id
  jq -nc --arg i "$INT" --arg d "$2" --arg p "$3" --arg id "$4" --slurpfile tw "$1" \
    '{type:"now",date:$d,shortLink:false,tags:[],posts:[{integration:{id:$i},
      value:[ $tw[0] | to_entries[] | {content:.value.content,
        image:(if .key==0 then [{id:$id,path:$p}] else [] end)} ],
      settings:{__type:"x",who_can_reply_post:"everyone"}}]}' \
  | curl -sS -X POST https://api.postiz.com/public/v1/posts \
      -H "Authorization: $POSTIZ_API_KEY" -H "Content-Type: application/json" -d @-
}
NOW=$(date -u +%Y-%m-%dT%H:%M:%S.000Z); LATER=$(date -u -v+5H +%Y-%m-%dT%H:%M:%S.000Z 2>/dev/null || date -u -d '+5 hours' +%Y-%m-%dT%H:%M:%S.000Z)
post_draft "$DRAFT_FILE_EN" "$NOW"   "$EN_PATH" "$EN_ID"   # EN draft + EN figure
post_draft "$DRAFT_FILE_JP" "$LATER" "$JP_PATH" "$JP_ID"   # JP draft + JP figure, +5h
```
Write the EN thread to `$DRAFT_FILE_EN` and JP to `$DRAFT_FILE_JP` (both = JSON
array of `{content}`; tweet 1 carries the figure). Both land as Postiz drafts
on X `cmm6d7m5703rwpr0yr5vtme3w`. No `type:"now"`, no IG, no publish gate.

### STEP 7 — VERIFY + LEARN
- Confirm BOTH drafts landed (HARD RULE #8): `postiz posts:list` → find the
  two new posts on `cmm6d7m5703rwpr0yr5vtme3w` → state should be `DRAFT`,
  thread = 5 tweets, tweet 1 has the figure. Also `Read` the nano-banana jpeg
  once more and confirm it is the legible diagram you intended.
- The shared `~/.openclaw/skills/_shared/state/hot-hooks.json` is refreshed by
  the hot-hooks-refresh cron (06:00 JST) from real Postiz analytics — you do
  NOT write it here.
- Final stdout line (cron delivery posts it to #metrics):
  `✅ A drafted: EN=<postId> JP=<postId> figure=<file> (pillar=<p> product=<pr>)`
  or `❌ A FAILED: <reason>`

## Other channels (same 7-step spine, different cron)

| cron | script | content |
|----|----|----|
| `anicca-x-marketing-weekly-article` (Mon 09 JST) | `scripts/channel-b-weekly-article.sh` | 12-tweet long-form article (run STEPS 1-7, 12 tweets) |
| `x-marketing-launch-trigger` (event) | `scripts/channel-c-launch-trigger.sh <slug>` | launch viral hook |
| `x-marketing-cold-dm-daily` (14 JST) | `scripts/channel-d-cold-dm-daily.sh` | ICP cold DM |
| `x-marketing-cross-post-daily` (16 JST) | `scripts/channel-e-cross-post-daily.sh` | TikTok/IG → X repost |
| `x-marketing-analytics-daily` (23 JST) | `scripts/analytics-daily.sh` | analytics → Slack |
| `x-marketing-finetune-weekly` (Mon 4 JST) | `scripts/finetune-weekly.sh` | empirical-prompt-tuning loop |

Channel B/C use the identical 7-step loop; only tweet count + length differ.

## DO NOT
- Do NOT call any external LLM API (`curl api.openai.com`, `claude -p`, etc). You are the model — HARD RULE #6.
- Do NOT one-shot. Skipping STEP 3/4/5 = the AI slop we are fixing.
- Do NOT publish to X on a test/e2e/today-* run — HARD RULE #9.
- Do NOT call Slack tools — cron delivery posts the final stdout line to #metrics.
- Do NOT edit the bash scripts.

## Files
```
skills/anicca-x-marketing-skill/
├── SKILL.md                       # this file (the loop you run)
├── data/config.json               # pillar + product rotation
├── scripts/channel-a-daily-info.sh # --print-config | <draft_file> post
├── scripts/channel-b-weekly-article.sh
├── scripts/lib/postiz.sh           # Postiz wrapper (deterministic)
└── state/hot-hooks.json            # winning hooks memory (closed loop)
```
