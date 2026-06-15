# Build-in-Public Revival — daily X post, jargon-ban, LLM-removed

**Constitution**: HARD RULE #-3 (BP identical follow, no synthesis), HARD RULE 0.18 (clone-don't-template + history-aware), HARD RULE 0.24 (no dry run — POST_ID 必須), HARD RULE #0 (full SDD flow), HARD RULE 0.27 (X publish も irreversible 系、 fire-once verify は ok / 大量量産 は Dais verbatim "go").

## §1 Scope + Why

Anicca の X account `@aniccaxxx` (= Postiz integration `cmm6d7m5703rwpr0yr5vtme3w`) に ★ 1 日 1 ツイート ★ を build-in-public format で 投稿。 user verbatim 2026-06-07: 「今日が何日で、 どれぐらい作成したのか、 という内容と、 日報として渡している内容は同じです。 Anicca が それと同じように X にも投稿したりするのは、 ビルドインパブリックとしては問題ない」。

### Why revive (= 過去 死亡 の 真因 fix)

旧 cron `anicca-x-build-in-public-daily` (schedule `10 7 * * * Asia/Tokyo`) は 2026-05-28 に 死亡:

> `FallbackSummaryError: All models failed (3): openai-codex/gpt-5.4-mini: Provider openai-codex is in cooldown ... | anthropic/claude-sonnet-4-6: Provider anthropic has billing issue ... | github-copilot/gpt-5.1: Copilot token exchange failed: HTTP 404` (tuning ticket 20260528T170522Z verbatim)

★ 根本原因 ★ = ツイート 内 verb-action lines (`started / built / shipped`) を ★ 投稿のたびに LLM 推論 ★ で 生成 → 全 provider 落ちると即死 + LLM が dev-jargon dump (= 「cron trace」「daily-memory」「session state」 等 内部 用語 を そのまま 吐く) で readability 崩壊。

### Why ban list (= user 苦情 の 直接 fix)

過去 投稿 2026-04-15 verbatim (= `~/.openclaw/workspace/build-in-public/posts-2026-04-15.txt`):

```
4/15. Day 106 of building Anicca to $1k MRR.

$54 MRR. 2 trials.

started keeping today's cron trace grounded in daily-memory
built a minimal factual diary entry for the day
shipped a clean record of visible session state and cron outcome

Small signals compound.
```

`cron trace / daily-memory / session state / cron outcome` 全部 ★ 内部 system 用語 ★ で X 読者 に 意味不明、 「Anicca と は 何 を build している 人 か」 が 1 秒 で 分からない。

## §2 Existing reuse map (= reinvent ZERO)

| 既存 component | path | reuse 方法 |
|---|---|---|
| build-in-public skill body | `~/.openclaw/skills/build-in-public/SKILL.md` | 既存 Step 1-7 framework を踏襲、 jargon ban + LLM removal を patch |
| retry-postiz.py | `~/.openclaw/skills/build-in-public/scripts/retry-postiz.py` | reuse そのまま (30s × max 3 attempt) |
| thread-split.py | `~/.openclaw/skills/build-in-public/scripts/thread-split.py` | reuse そのまま (280 char 超 自動 thread 分割) |
| post-thread.sh | `~/.openclaw/skills/build-in-public/scripts/post-thread.sh` | reuse そのまま |
| pull-analytics.py | `~/.openclaw/skills/build-in-public/scripts/pull-analytics.py` | reuse そのまま (Postiz 分析 ループ、 cron `bip-postiz-pull` 経由) |
| Postiz integration ID | `cmm6d7m5703rwpr0yr5vtme3w` (= @aniccaxxx) | 既存 確定 (live `/integrations` で verify 済) |
| anicca-morning-gmail skill | `~/.openclaw/skills/anicca-morning-gmail/` (= T17b で build 中) | 完成 後 同 body を流用 (= 真実 single source)、 未 build 時 は diary fallback |
| daily-memory diary | `~/.openclaw/workspace/daily-memory/diary-YYYY-MM-DD.md` | fallback source、 last 3 verb-prefixed lines (`started / built / shipped / fixed / tested / published`) |
| RevenueCat v2 metrics API | `/v2/projects/projbb7b9d1b/metrics/overview` (= MRR + active_trials) | reuse そのまま |

## §3 Architecture (= LLM ZERO、 fail-closed jargon ban)

```
[07:10 JST daily cron]
        ↓
[Step 1   env load (.env / TZ Tokyo)                                 ]
        ↓
[Step 2   data fetch                                                 ]
        ├ Step 2a  morning Gmail body (= ~/.openclaw/skills/anicca-morning-gmail/state/sent-<date>.json) を try
        │           成功 → "今日 started / built / shipped" 3 行 verbatim 抽出
        │           失敗 → Step 2b へ fallback
        └ Step 2b  diary fallback (= ~/.openclaw/workspace/daily-memory/diary-<date>.md last 3 verb-prefixed lines)
        ↓
[Step 3   RevenueCat MRR + active_trials fetch (= 既存 logic そのまま) ]
        ↓
[Step 4   Day N compute (Day 1 = 2025-12-31 + delta)                 ]
        ↓
[Step 5   tweet body assemble (= fixed template、 LLM ZERO)          ]
        ↓
[Step 5a  ★ jargon ban scan ★ (fail-closed)                          ]
        ├ banned 検出 → exit 1 + Slack #metrics alert + Gmail to Dais
        └ pass     → Step 5b
        ↓
[Step 5b  ★ markdown strip ★ (backtick/asterisk/square-bracket/pipe) ]
        ↓
[Step 5c  thread-split.py (280 char 超 のみ)                          ]
        ↓
[Step 6   Postiz POST /public/v1/posts                               ]
        ├ POST_ID + releaseURL 戻る → Step 7
        └ 戻らず          → retry-postiz.py 30s × 3、 全失敗 → exit 1 + Slack 🚨 (HARD RULE 0.24)
        ↓
[Step 7   sent_<date>.json 永続化 + Slack #metrics (= 1 行 schema)    ]
```

## §4 Tweet body template (= 固定、 LLM 不要)

```
{MONTH_DAY}. Day {N} of building Anicca to $1k MRR.

{MRR_DISPLAY} MRR. {ACTIVE_TRIALS} trials.

started {line1_reader_friendly}
built {line2_reader_friendly}
shipped {line3_reader_friendly}

{tagline}
```

### §4.1 line1/2/3 source priority

1. **morning Gmail body** の 「今日」 section の verb-prefixed lines (= morning Gmail skill が 既に reader-tone で書く 想定、 T17b spec で 同 ban list 適用)
2. **diary** の last 3 verb-prefixed lines (= 自分で書いた reader-tone diary、 開発者 が 内部 用語 で書いた 行は §5 ban に引っ掛かり exit 1)

### §4.2 tagline (= Copyblogger 22 rotation、 既存 `headline-history.json` 経由)

既存 v0.2.0 の rotation 機構 reuse、 タグライン 1 行 のみ。

## §5 Jargon ban list (= fail-closed、 verbatim)

```
BANNED_TERMS = [
  "openclaw", "cron", "daily-memory", "session state", "session-state",
  "Postiz", "postiz", "integration", "hot-reload", "hot reload",
  "heartbeat", "skill", "runtime", "payload", "jobs.json", "state.json",
  ".env", "fallback", "retry", "gateway", "cron trace", "cron outcome",
  "diary entry", "diary-driven", "Slack delivery", "metrics check",
  "model fallback", "provider", "ledger", "TaskCreate", "TaskUpdate",
  "spec", "SDD", "delivery-queue", "subagent", "claude-cli", "Anthropic key"
]
```

検出 logic: tweet body (= Step 5 assemble 後、 Step 6 send 前) に対し `grep -i -F` で 1 件 でも hit → exit 1 + 以下:
- Slack `#metrics` に 「BUILD-IN-PUBLIC blocked by jargon: <hit term> in line <N>」 post
- Gmail to Dais (= `~/.openclaw/skills/anicca-morning-gmail/` の send wrapper 経由) に 「今日 の build-in-public が jargon ban で blocked、 line: 「<line>」、 fix 推奨: 「<term>」 を reader-tone に書換」 1 通

### §5.1 Reader-tone alternative table (= 強制 書換 ヒント)

| 内部用語 | reader-tone 代替 |
|---|---|
| `cron` | `daily job` / `the morning routine` |
| `daily-memory` | `today's diary` / `today's work log` |
| `session state` | `where I left off yesterday` |
| `Postiz` | `the posting pipeline` |
| `heartbeat` | `the morning check-in` |
| `skill` | `the part of Anicca that ___` |
| `state.json` | `the saved progress` |
| `hot-reload` | `instant restart` |
| `model fallback` | `backup AI` |
| `ledger` | `the log` |

★ table は ヒント ★、 自動 書換 は しない (= 違反 line を Dais に Gmail で投げ、 user か morning-gmail skill 側 で 修正、 build-in-public は ban 検出 で 即 STOP)。

## §6 Markdown strip (Step 5b)

```python
import re
BODY = re.sub(r'[`*\[\]|]', '', BODY)
BODY = re.sub(r'#{1,6} ', '', BODY)
BODY = re.sub(r'\n{3,}', '\n\n', BODY)
```

X (旧 Twitter) は markdown 解釈しない = backtick/asterisk が そのまま 表示 され 見づらい。 全部 strip。

## §7 Cron registration

| 項目 | 値 |
|---|---|
| name | `anicca-x-build-in-public-daily` |
| schedule | `10 7 * * * Asia/Tokyo` (= 07:10 JST 毎日、 anicca-morning-gmail 07:00 fire の 10 分後) |
| target | skill `build-in-public` |
| model | ★ なし ★ (= deterministic、 LLM 不要、 provider down で死なない) |
| delivery | none → slack:`C091G3PKHL2` (= `#metrics`) explicit |
| isolated | true |
| owner | anicca |

## §8 Verification (= fire-once、 HARD RULE 0.24 準拠)

```
Step 1  openclaw cron run anicca-x-build-in-public-daily --once
Step 2  observe stdout: POST_ID + releaseURL 戻る か?
        - 戻る   → camofox visit releaseURL → @aniccaxxx timeline 目視 → tweet 1 件 確認
        - 戻らず → exit 1、 Slack #metrics 🚨、 fix → re-fire
Step 3  jargon ban scan log を観察 (= Slack #metrics に 「passed jargon scan」 post 有無)
Step 4  sent_<date>.json が `~/.openclaw/workspace/build-in-public/` に 書込まれた か 確認
Step 5  POST_ID を `~/.openclaw/state/build-in-public-history.jsonl` に append (= history-aware per HARD RULE 0.18)
```

★ POST_ID 戻らない 場合 = 死、 mock / dry / "would have posted" log は HARD RULE 0.24 で 禁止 ★。

## §9 Single source of truth invariant

| invariant | 監視 方法 |
|---|---|
| `@aniccaxxx` への 投稿 は build-in-public cron だけ | `openclaw cron list | grep -iE "x-|tweet|twitter|aniccaxxx"` で entry 1 件 のみ |
| Postiz integration ID = `cmm6d7m5703rwpr0yr5vtme3w` で 別 ID は使わない | T1 (Postiz registry rebuild) で live `/integrations` と一致 verify |
| LLM 呼び出し ゼロ | SKILL.md grep "exec claude" "openai" "anthropic" "openclaw model" → 0 hit |

## §10 Cross-spec ordering invariants

| invariant | 理由 |
|---|---|
| T19/T20 (本spec) は T17b (anicca-morning-gmail) 完成 後 が 望ましい | morning Gmail body を Step 2a で参照、 未完成 時 は §3 Step 2b diary fallback で動く (= 必須依存 ではない、 上位優先のみ) |
| Step 5 jargon ban list は T17b morning-gmail spec の humanize 層 と 完全 一致 | 両者 が 同 ban list を使うことで、 morning Gmail で reader-tone 化 済 → X 投稿 も そのまま 通る (= drift 防止) |
| T18 (blog disable) と 本spec は 独立、 並列実行 OK | 別 skill / 別 channel |

## §11 Failure modes + handlers

| mode | handler |
|---|---|
| morning Gmail body 未存在 + diary も 未書込 | tweet を スキップ + Slack #metrics に 「no source today」 post + Gmail to Dais 「diary 書きそびれ」 |
| RevenueCat API 5xx | `$? MRR / ? trials` で fallback 投稿 (= 既存 logic) |
| Postiz API 4xx (= bad request) | retry 3 後 exit 1、 Slack 🚨、 Dais Gmail 「Postiz schema 変更?」 |
| jargon ban hit | Step 5a で fail-closed exit 1、 Slack + Gmail、 tweet は 投稿せず、 翌日 fix 後 自動 reattempt |
| thread-split が 5 tweet 超 | exit 1 (= 280 char ×5 = 1400 char 超え は build-log すぎ)、 body 圧縮 必要、 Dais Gmail |

## §12 BP citations (= verbatim)

| BP | URL / path | 引用 |
|---|---|---|
| Copyblogger headline formulas | `https://copyblogger.com/10-sure-fire-headline-formulas-that-work/` | 「8 out of 10 readers only read the headline」 — line 1 (Day N + MRR 行) が 全て、 残りは bonus |
| daily.dev build-in-public guide | (= SKILL.md 既存 引用) | 動詞 で始める / 数字 を使う / 絵文字 使わない |
| Anicca CLAUDE.md HARD RULE 0.24 | `~/anicca-project/CLAUDE.md` | 「fake / dry / mock / dummy / simulated」 言葉 が cron payload / skill script / 報告 mail に登場した瞬間 = 即 削除 + 再設計 |
| Anicca CLAUDE.md HARD RULE 0.18 | `~/anicca-project/CLAUDE.md` | CLONE-DON'T-TEMPLATE — 既存 build-in-public skill + scripts/ を template とせず clone 流用 |
| Anicca tuning ticket 20260528 | `~/.openclaw/workspace/tuning-skills/tickets/20260528T170522Z-anicca-x-build-in-public-daily.json` | 旧 cron 死亡 root cause = LLM provider 全 down → 新 spec は LLM ZERO |
| User verbatim 2026-06-07 | conversation | 「同じです。 Anicca が それと同じように X にも投稿したりするのは、 ビルドインパブリックとしては問題ない」 |

## §13 Out of scope

- `@aniccaxxx` 以外 の X account への投稿 (= 1 account 専用)
- 多言語 (= 英語 のみ、 既存 format 踏襲)
- 画像 添付 (= text-only)
- Reply / quote-tweet / DM (= 1 fresh post 専用)
- 過去 ツイート の analytics insight を 次 ツイート に LLM フィードバック (= 既存 v0.2.0 の rotation 機構 で十分、 ban list で readability gate)

## §14 BP 一致 自採点

| BP | 一致 |
|---|---|
| Dais verbatim 「ビルドインパブリックとしては問題ない、 morning Gmail と同 body」 | 100% (= §3 Step 2a で morning Gmail body 直 流用) |
| Dais verbatim 「見づらい部分を直してください」 | 100% (= §5 jargon ban + §6 markdown strip fail-closed) |
| HARD RULE 0.24 no dry run | 100% (= §8 POST_ID 必須、 戻らず → exit 1) |
| HARD RULE 0.18 clone-don't-template | 100% (= §2 既存 skill body + scripts/ 全部 reuse、 ban list + LLM removal のみ patch) |
| 旧 cron 死亡 root cause (= 2026-05-28 全 provider down) fix | 100% (= LLM ZERO、 deterministic flow) |
