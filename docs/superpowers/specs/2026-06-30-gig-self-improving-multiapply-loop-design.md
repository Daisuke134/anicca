# gig SELF-IMPROVING MULTI-APPLY LOOP — VCSDD spec (2026-06-30)

Extends `2026-06-30-gig-earn-core-recipe-design.md`.  
Adds 5 behaviors to the existing autonomous Coconala earn-core:
nurture-all + apply-broadly + learn + self-improve + bot-to-bot GitHub learning.

## Provable finish line (done = ALL true)

| # | Condition | Evidence |
|---|-----------|---------|
| F1 | `strategy.default.json` committed with all required keys (schema below) | `jq -e` on all required keys exits 0 |
| F2 | `gig-cli.sh` cron prompt mentions all 5 behaviors: NURTURE-ALL, APPLY-BROADLY, LESSONS, IMPROVE-STEP, GH-SHARE | `grep` on the prompt string |
| F3 | `~/gig/lessons.jsonl` schema-guarded at write site (required fields: ts, requestId, category, outcome, reason, lesson) | strategy/lessons schema test passes |
| F4 | `~/gig/strategy.json` bootstrapped on first pass from `strategy.default.json` if absent | test + code path |
| F5 | `node --test __tests__/*.test.mjs` exits 0 | real run output |
| F6 | `bash -n` on all `.sh` files exits 0 | real run output |
| F7 | `gh auth status` exits 0 (GitHub sharing functional or gracefully-degraded) | real run output |
| F8 | no-human-loop.test.mjs still passes with new scripts added to FILES | test output |

## The 5 behaviors added per pass

### B1 — NURTURE ALL (priority-highest)

Each pass sweeps **every** active talk-room in Coconala (トークルーム list), not just the most recent one.
For each open talk-room:
- If buyer sent a new message → reply helpfully within the same pass.
- If a 仮払い contract arrived → build the real deliverable (pptx skill / doc / code) and 納品.
- If 検収 is ready → ask the buyer for 評価.
- Log each action as `{requestId, status: "replied" | "delivered" | "評価依頼", ts}` row in `~/gig/applied.jsonl`.

**Invariant**: no open conversation goes un-checked for more than one pass (≈1h). A buyer reply discovered and ignored = a missed earn.

### B2 — APPLY BROADLY (per strategy.json guidance, up to 5/pass)

After nurture, scan `coconala.com/requests` for **AI-doable OPEN** requests across the priority categories in `strategy.json`. For each candidate NOT already in `applied.jsonl` (dedupe by `requestId`):
- Write a **tailored proposal** addressing the specific brief (not a generic template).
- Attach a **real sample deliverable** (pptx / doc / code snippet relevant to the request).
- Apply via `APPLY_RUNBOOK.md` (real mouse-click datepicker, setFileInputFiles, 投稿前モーダル).
- Append `{requestId, title, status:"applied", price_jpy, deliverable, delivery_date, ts}` to `applied.jsonl`.

Cap: up to **5 applications per pass** (configurable via `strategy.json.max_apply_per_pass`). Respect `strategy.json.skip_categories` to avoid categories that historically fail or require humans.

### B3 — LEARN from outcomes → lessons.jsonl

After observing any outcome (accept / reject / 取り下げ / low-rating / conversation shows "needs a human" / price refused / delivered but no 検収), append a structured row to `~/gig/lessons.jsonl`:

```json
{
  "ts":       "<ISO timestamp>",
  "requestId": "<string>",
  "category": "<string>",          // e.g. "PPT/スライド", "記事/blog", "コード"
  "outcome":  "<string>",          // "accepted" | "rejected" | "ignored_closed" | "low_rating" | "needs_human" | "unsustainable" | "delivered_no_収"
  "reason":   "<string>",          // short free-text from the UI / buyer message
  "lesson":   "<string>"           // what the next pass should do differently
}
```

Deterministic guard: a row is only appended when an **outcome event** is actually observed in the UI (not speculated). Never append for an in-progress apply.

### B4 — SELF-IMPROVE (every Nth pass — strategy-driven)

Every `strategy.json.improve_cadence_passes` passes (default: 4), the core runs an **improve step**:

1. Read `~/gig/lessons.jsonl` (all rows).
2. Read `~/gig/earnings.jsonl` and `~/gig/applied.jsonl` to compute per-category stats:  
   `accept_rate = accepted_lessons / total_applications_in_category` and `¥/month` estimate.
3. Read recent `[gig-lesson]` GitHub issues from other AIs (B5 below) and fold useful lessons.
4. Update `~/gig/strategy.json` with concrete changes:
   - Raise `priority_categories` for high-accept / high-¥ categories.
   - Add to `skip_categories` if a category repeatedly needs a human, unsustainable, or 0% accept after ≥3 tries.
   - Improve proposal templates per category (e.g. if "rejected" + reason "価格が高い" → lower price_default; if "needs a human" + category "コード(複雑な要件)" → add that category to skip_categories).
   - Adjust `profile_blurb` if lessons suggest it's a blocker.

The improve step runs **in-model** (the running AI reads lessons and applies judgment — no hardcoded logic). The deterministic layer is only: read the files, write the updated `strategy.json`, verify it is valid JSON.

### B5 — BOT-TO-BOT LEARNING via GitHub

After the improve step (same Nth pass), if there's a notable lesson (first accept / a rejection revealing a systemic block / a new unsustainable category found):

1. Post a `[gig-lesson]` GitHub issue to `Daisuke134/anicca`:
   ```
   gh issue create -R Daisuke134/anicca \
     --title "[gig-lesson] <one-line summary>" \
     --body "<category, outcome, reason, lesson — formatted as a mini-report>" \
     --label "gig-lesson"
   ```
2. Dedupe: before posting, check `~/gig/shared-lessons.jsonl` for a row with the same `requestId + outcome` — skip if already posted. After posting, append `{ts, requestId, outcome, issue_url}` to `~/gig/shared-lessons.jsonl`.

Each pass (not just Nth), **read** recent `[gig-lesson]` issues from any AI on this repo:
```
gh issue list -R Daisuke134/anicca --label gig-lesson --limit 10
```
Fold any novel lesson into the local `strategy.json` improvement (B4).

**Graceful degradation**: if `gh` is unavailable or API fails, log a warning line and continue the pass — B5 failure must never abort B1/B2/B3/B4.

## strategy.json schema (canonical)

```json
{
  "version": 1,
  "updated_ts": "<ISO timestamp>",
  "max_apply_per_pass": 5,
  "improve_cadence_passes": 4,
  "priority_categories": [
    "PPT/スライド",
    "資料作成",
    "記事/blog",
    "データ入力/Excel",
    "文字起こし",
    "コード",
    "LP/ランディングページ"
  ],
  "skip_categories": [],
  "price_defaults": {
    "PPT/スライド": 8000,
    "資料作成": 10000,
    "記事/blog": 5000,
    "データ入力/Excel": 4000,
    "文字起こし": 4000,
    "コード": 15000,
    "LP/ランディングページ": 20000
  },
  "proposal_templates": {
    "PPT/スライド": "ご依頼拝見しました。プレゼン資料作成が得意で、これまでに複数のビジネス用スライドを制作してきました。ご要望に合わせた構成・デザインでサンプルを添付しています。ご要件をさらに詳しくお聞かせください。",
    "資料作成": "ご依頼ありがとうございます。資料作成・文書整理を専門とし、明確・読みやすい成果物をお届けします。サンプル添付しています。",
    "記事/blog": "SEOを意識したわかりやすい記事・ブログ執筆が得意です。ご要望のトーンやキーワードに合わせてご提案します。サンプルを添付しています。",
    "データ入力/Excel": "正確・迅速なデータ入力・Excel整理が得意です。大量データでも対応可能。サンプルファイルを添付しています。",
    "文字起こし": "音声・動画の文字起こし対応可能です。正確な日本語テキストをお届けします。",
    "コード": "プログラミング・自動化スクリプト作成が得意です。要件をお聞かせください。サンプルコードを添付しています。",
    "LP/ランディングページ": "CVRを意識したLP制作が得意です。ご要件に合わせたHTML/CSSサンプルを添付しています。"
  },
  "profile_blurb": "AIエージェントによる高品質・迅速な作業対応。PPT・資料・記事・データ入力・コード対応。",
  "pass_count": 0,
  "notes": "Auto-updated by the improve step. Edit manually to override."
}
```

**Required keys** (schema test validates these): `version`, `max_apply_per_pass`, `improve_cadence_passes`, `priority_categories`, `skip_categories`, `price_defaults`, `proposal_templates`, `profile_blurb`, `pass_count`.

## lessons.jsonl schema (per row)

```json
{
  "ts": "ISO-8601",
  "requestId": "string",
  "category": "string",
  "outcome": "accepted|rejected|ignored_closed|low_rating|needs_human|unsustainable|delivered_no_収",
  "reason": "free-text from UI/buyer",
  "lesson": "what to do differently next time"
}
```

## shared-lessons.jsonl schema (dedup marker)

```json
{
  "ts": "ISO-8601",
  "requestId": "string",
  "outcome": "string",
  "issue_url": "string"
}
```

## Pass structure (ordered priority, single bounded pass)

```
START PASS
  1. Read ~/gig/strategy.json (bootstrap from strategy.default.json if absent)
  2. Increment strategy.json.pass_count (write back)
  3. NURTURE ALL (B1): sweep every active talk-room → reply / deliver / 評価依頼
     → append rows to ~/gig/applied.jsonl
  4. APPLY BROADLY (B2): up to strategy.max_apply_per_pass open requests
     (dedupe via applied.jsonl requestIds)
     → append rows to ~/gig/applied.jsonl
  5. OBSERVE OUTCOMES (B3): for any request whose status changed (rejected/accepted/closed/rated)
     → append row to ~/gig/lessons.jsonl
  6. If pass_count % improve_cadence_passes == 0:
       IMPROVE STEP (B4):
         - read lessons.jsonl + applied.jsonl stats
         - read peer [gig-lesson] GitHub issues (gh issue list)
         - update strategy.json with concrete changes
       BOT-TO-BOT SHARE (B5):
         - if notable lesson not yet in shared-lessons.jsonl → gh issue create + append to shared-lessons.jsonl
  7. EARNED CHECK: if any request shows 検収/支払 in the UI
     → append {ts,requestId,jpy,status,evidence} to ~/gig/earnings.jsonl (NO-FAKE-EARN guard)
FINALLY: touch ~/gig/.last-pass  ← heartbeat (ONLY on completed pass, never on startup)
```

## Invariants (adversary will check)

| Invariant | Guard |
|-----------|-------|
| NO-FAKE-EARN | ¥ recorded to earnings.jsonl ONLY on real 検収/支払 + evidence + jpy>0 |
| NO-USDC | cron prompt has "do NOT claim USDC / do NOT call record-earn" |
| DEDUP-APPLY | applied.jsonl requestIds checked before each application |
| DEDUP-LESSON-SHARE | shared-lessons.jsonl checked before gh issue create |
| GRACEFUL-GH | gh failure → warn + skip (never abort the pass) |
| NO-HUMAN-LOOP | no read -p, no "wait for Dais", no manual step; captcha→CapSolver, OTP→gog gmail |
| BOUNDED | max_apply_per_pass cap enforced; improve step every N passes only |
| HEARTBEAT-LAST | ~/gig/.last-pass touched ONLY at the very end of a completed pass |

## Files changed / created

| File | Action |
|------|--------|
| `skills/earn/gig/gig-cli.sh` | Edit: replace STARTUP cron prompt with 5-behavior version |
| `skills/earn/gig/strategy.default.json` | Create: seed default strategy |
| `skills/earn/gig/SLOT_CC.md` | Edit: reference new behaviors |
| `skills/earn/gig/NO_HUMAN.md` | Edit: add new scripts to audited list |
| `skills/earn/gig/__tests__/no-human-loop.test.mjs` | Edit: add new scripts to FILES |
| `skills/earn/gig/__tests__/self-improve.test.mjs` | Create: schema + dedup + no-fake-earn tests |
| `docs/superpowers/specs/2026-06-30-gig-self-improving-multiapply-loop-design.md` | This file |

## Non-goals (out of scope)

- No spawning persistent sub-agents from the cron (heavy; risks quota; default = sequential up to 5/pass).
- No crypto / USDC / record-earn (this is human-funded ¥ only).
- No modification of the tmux session or launchd plist (live system; changes take effect on next restart).
