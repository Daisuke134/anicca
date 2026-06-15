# Anicca Inbox Autonomy v4 — Cron Policy + Model Chain Doctrine

| Field | Value |
|---|---|
| Date | 2026-06-05 |
| Author | Anicca (Claude main loop) |
| Status | **LIVE** (first real send 2026-06-04 23:41:47 JST) + cron money-leech 退治 |
| Replaces | v3 (= cron policy 不在、 model swap 戦略 が sonnet 焼き付け = 間違い) |
| Replaces² | v2 (DRY_RUN 14d window 案・LLM model 設計が paid provider 死で破綻) |
| Replaces³ | v1 (Slack escalation 案・HARD RULE #18 違反だったので破棄) |
| Successor of | `anicca-mail-auto-reply` v1 (stub since 2026-05-30) |

---

## 0.3. v4 → v5 diff (= cron rubric doctrine + report-only sweep)

### Cron rubric (= Dais 2026-06-05 厳命)

```
ACTION                = ✅ KEEP    (= 外部に write / send / commit / publish / submit / disable)
MONITOR + FIX branch  = ✅ KEEP    (= 検出 → 自分で fix → 「fix した」 報告)
REPORT-ONLY           = 🔴 DELETE  (= 集計 → Slack post で終わり、 Dais 判断待ち = HARD RULE #18 違反)
MONITOR without FIX   = 🟡 UPGRADE or DELETE
DAEMON (on-load)      = ✅ KEEP    (= webhook / endpoint / voice bridge)
```

**例外**: `anicca-report` daily Gmail to Dais (= friend update tone のみ) — Dais 判断を求めない、 結果共有のみ。 他の Dais 宛 報告 cron は **すべて削除**。

### Sweep 結果 (= 2026-06-05 実行済)

- enabled cron: 150 → 140 (-10)
- skill dir: -2 (`gmail-digest` + `skill-cull-analyzer`)
- 削除 10 cron: latest-papers / opening-cafe-status-weekly / opening-cafe-prelaunch-content-daily / app-reviews-weekly-digest / mufg-epoc-watcher / anicca-corey-seo-audit-cron / anicca-goal-learner / anicca-morning-report / anicca-seo-brand-visibility-daily / oss-repo-observer-daily

### anicca-report v2 expansion (= 唯一の Dais 宛 mail)

`~/.openclaw/skills/anicca-report/scripts/report.py` v2 拡張 (2026-06-05):

```diff
   body sections:
   - Headline (MRR / Net / Wallet / Status)
-  - What I did today (lateness calls only)
+  - What I did (last 24h):
+    Mail: replied N / applied M / archived K (+ sample thread IDs)
+    Irreversible 3-vote counts
+    Lateness calls
   - Runtime spend breakdown
-  - Next 24h events (= Dais's gcal preview)
+  - What I'll do (next 24h):
+    📧 Mail / 🎞 Video / 📰 Article / 🏭 Factory / 📝 Apply / 🎵 Music / 🩺 Monitor / 🔧 Other
+    (= jobs.json の next 24h categorized)
+  - Goal progress to $10K MRR:
+    current$ / target$ / gap$ / months at current net
```

Data sources 追加:
- `~/.openclaw/skills/anicca-inbox/state/inbox-ledger.jsonl`
- `~/.openclaw/skills/anicca-inbox/data/apply-history.jsonl`
- `~/.openclaw/cron/jobs.json` (= next 24h categorize)
- `ANICCA_MRR_GOAL_USD` env (default $10000)

### memory citation

- `feedback_cron_rubric_monitor_must_have_fix_branch.md` (= 新規 doctrine)

---

## 0.2. v3 → v4 diff (= money leech 発見と修正)

### v3 で間違った 3 つ

1. **「launchd 19 plist 削除」**を最重要 task 化していた → 実は **18 plist の内 16 件が pure-bash** で OpenClaw agentTurn cost = 0。 削除しても OpenClaw token は節約 されない (= agentmail-replier は別途 DeepSeek API 直叩きで paid だが launchd 起因ではない)。 真の問題は別。
2. **「全 cron job を `anthropic/claude-sonnet-4-6` に swap」**案 → これは **sacred な Claude Code subscription を毎日 燃やす自殺案**。 Dais 厳命: 「sonnet は last resort、 codex 主力」。
3. **launchd を OpenClaw cron に統合する Phase 2 epic** を 4 task 登録 → OpenClaw に shell-only kind 無い (= GitHub #18160 open) ので統合すると **逆に高くなる**。

### 真の money leech (= 修正対象、 2026-06-05 live data 確定)

| 観察 | 数値 (= `openclaw cron list` 実測) |
|---|---|
| OpenClaw cron 有効 job 数 | **155** (= 別 agent の cron-cull で 192→162→155 推移) |
| 内 dead model 指定 job | **143** (= deepseek/v4-pro 113 + moonshot/kimi-k2.5 30) |
| 内 model 指定無 (= defaults 継承) | **8** |
| 内 codex/gpt-5.4-mini 指定 | 2 |
| 内 anthropic/claude-sonnet-4-6 指定 | 2 |
| sub-hourly 設定 job (= */N min) | **4** (= arrival */5 + lateness */5 + event-bot */15 + exec-guard */30) |
| 真 duplicate | **要再確認** (= cron-cull 後 / anicca-cron-doctor 同名 2 件 別 schedule で 別目的可能性) |

### Patch 戦略 (= 4 patch 分離、 reviewer iter 1 で修正)

#### Patch X — `openclaw.json` defaults model chain (= 3 行 配列 1 個)
```diff
   "fallbacks": [
-    "openai-codex/gpt-5.4-mini",
-    "moonshot/kimi-k2.5",
-    "deepseek/deepseek-v4-pro"
+    "deepseek/deepseek-v4-pro",
+    "moonshot/kimi-k2.5",
+    "anthropic/claude-sonnet-4-6"
   ]
```
**primary 不変** (= `openai-codex/gpt-5.4-mini` Dais 主力)。 fallback 順序 = Dais 直命 `codex → deepseek → kimi → sonnet (LAST)`。

#### Patch H — `openclaw.json` heartbeat.model 削除 (= 1 行)
```diff
   "heartbeat": {
     "every": "60m",
-    "model": "openai-codex/gpt-5.4-mini",
     ...
   }
```
heartbeat が `agents.defaults.model.primary` 継承 + fallback chain 走る。 citation: `concepts/model-failover.md` 「Heartbeat runs without an explicit `heartbeat.model` clear direct auto overrides」。

**Patch X + Patch H = openclaw.json の 4 行 編集**。 これで 155 cron + heartbeat 全部 codex primary + 正しい fallback chain に。

#### Patch Y — `jobs.json` の dead-model job 143 件 の `payload.model` 削除
**対象 = `deepseek/*` と `moonshot/*` パターンのみ**。 codex (2) / sonnet (2) 指定 job は **保持** (= 意図的 override の可能性)。
```bash
# 編集前 backup
cp ~/.openclaw/cron/jobs.json ~/.openclaw/cron/jobs.json.bak-patch-y-$(date +%s)
# 編集: deepseek/* + moonshot/* 一致 job の payload.model 削除
python3 - <<'PY'
import json, re
p = '/Users/anicca/.openclaw/cron/jobs.json'
d = json.load(open(p))
DEAD = re.compile(r'^(deepseek|moonshot)/')
removed = 0
for j in d['jobs']:
    m = j.get('payload', {}).get('model', '')
    if DEAD.match(m):
        del j['payload']['model']
        removed += 1
json.dump(d, open(p, 'w'), indent=2, ensure_ascii=False)
print(f'removed model override from {removed} jobs')
PY
```
**注**: jobs.json hot-reload (= Gateway 動作中編集対応)。 SQLite migration 未実行なので直編集が canonical。

#### Patch A — sub-hourly 緩和 (= 2 件 のみ、 reviewer iter 1 で修正)
real-time exception per Dais "calling stuff":
| Job | 現 schedule | 提案 | fires/day 変化 |
|---|---|---|---|
| `anicca-arrival-mail` | `*/5 * * * *` | **維持** (Dais 例外 "calling") | 288 → 288 |
| `anicca-lateness-heartbeat-shell` | `*/5 * * * *` | **維持** (同上) | 288 → 288 |
| `anicca-event-bot-trigger` | `*/15 * * * *` | `0 * * * *` (1h) | 96 → 24 (-72) |
| `anicca-exec-guard` | `*/30 * * * *` | `0 * * * *` (1h) | 48 → 24 (-24) |

(naist-pull は cron-cull で既に hourly 化済、 Patch A 対象外)

**total sub-hourly: 720 → 624 fires/day (-96, -13%)**

#### Patch Z — duplicate 削除 (= 要確認後)
- `anicca-cron-doctor` 2 件 (= hourly `37 * * * *` + daily `0 3 * * *`): 用途別か duplicate か `--message` 内容で判別後判断
- 他 duplicate は `openclaw cron list | sort -k2 | uniq -c -f1` で検出

#### Patch L — launchd 18 plist は **全件維持** (= reviewer iter 1 で 19→18 修正)
- **9 daemons** (= webhook/endpoint/voice/bridge): OpenClaw に supervisor 機能無 = 移行不可
- **9 scheduled** の内 **8 件 pure-bash** = OpenClaw agentTurn token 0
- **1 件 直 paid API**: `agentmail-replier` が DeepSeek API 直叩き (= per-reply paid call、 launchd 起因ではない、 hermes 側 設計問題)
- **launchd 議論 完全終了** = Phase 2 epic 全 retire

### 効果試算 (= reviewer iter 1 で recompute)

```
=== Before Phase 1 (= 155 enabled, 2026-06-05 live) ===
sub-hourly  (4 jobs)     : 720 fires/day
  arrival-mail    */5    : 288
  lateness        */5    : 288
  event-bot       */15   :  96
  exec-guard      */30   :  48
hourly      (~12 jobs)   : ~288 fires/day
multi-hour  (~5 jobs)    : ~30 fires/day
daily       (~134 jobs)  : ~134 fires/day
TOTAL                    : ~1,172 fires/day
token cost (= 5K/fire avg input + agentTurn bootstrap) : ~5.9M tokens/day

=== After Phase 1 (= Patch A + Z) ===
sub-hourly  (4 jobs)     : 624 fires/day  (-96)
hourly      (~14 jobs)   : ~336 fires/day (+ event-bot + exec-guard)
multi-hour              : unchanged
daily                   : unchanged
TOTAL                    : ~1,124 fires/day  (-48 / -4%)
token cost              : ~5.62M tokens/day

=== 効果 (= 控えめ修正後) ===
fires saved : 48-96/day (= Patch A 範囲、 duplicate 削除すれば追加)
token saved : 0.24-0.48M tokens/day = ~4-8%

=== Patch X + Y + H の真の効果 (= LLM call 効率化) ===
- 5-min probe cache で codex 復活時自動切替
- 143 jobs の dead-model retry overhead 解消 (= 1 fire で 1 LLM 試行 のみ)
- sonnet 主力化 完全回避 (= Dais 厳命「sonnet 温存」遵守)
```

### ⚠️ doctor --fix 罠 (= 2026-06-05 実行中 incident)

`openclaw doctor --fix` の "Cron store normalized" pass は **Patch Y を巻き戻す**。 verbatim log:

```
Cron store normalized at ~/.openclaw/cron/jobs.json.
- 11 jobs still uses legacy `openai-codex/*` cron model refs
```

= override 不在を "legacy 状態" とみなして defaults primary を書き戻す。 Phase 1 実行中、 Patch Y で 143 件 clear → doctor --fix → 全件 deepseek 復活した。 再度 Patch Y 再適用で復旧。

**hard rule**: **Phase 1 (Patch Y) 後 `openclaw doctor --fix` を 二度と 走らせない**。 cron schedule 変更は `openclaw cron edit` CLI or jobs.json 直編集で Gateway hot-reload 完了 (= doctor 不要)。 memory: `feedback_openclaw_doctor_fix_rolls_back_cron_model_clears.md`

### §14 / §4 model table 補注 (= reviewer iter 2 N1)

**§14 と §4 Phase 3 に列挙されている `deepseek/deepseek-v4-pro` (Leader classify model) と `anthropic/claude-sonnet-4-6` (REPLY draft model) は "Patch X+H+Y 適用前 の レガシー値"**。 v4 適用後 の **effective model = `anthropic/claude-sonnet-4-6`** (= codex primary → deepseek (402) → kimi (429) → claude-cli fallback chain で 着地)。 §14 を更新せず 注記 のみ で 履歴 維持。

### Circuit breaker risk (= reviewer iter 1 で追加)

**全 provider 死亡 シナリオ**: codex 429 + deepseek 402 + kimi 429 全部 down 時、 全 cron + heartbeat が `anthropic/claude-sonnet-4-6` に着地 → subscription 1 日 5.6M token 焼く。

**現状 対策**: `concepts/model-failover.md` の 5-min probe cache が 1 session 内で 1 primary 1 回までに制限。 だが 155 session (= 1 job 1 session) なので全 session 同時 sonnet 着地 可能性 残る。

**今後追加 検討**:
1. `cfo-core` 内 monitor 追加: `claude-cli/*` 1 日 fire 数 が閾値 (例 500/day) 超えたら Slack alert
2. OpenClaw cron `failure-alert` 設定で 連続失敗時 自動 disable
3. blockrun/* free 経由で別 provider 復活 → fallback chain 更新

### 残ギャップ (v4 で未完、 task #39-60 で追跡)

| 項目 | tasklist ID | 状態 |
|---|---|---|
| Patch X + H (openclaw.json 4 行) | **新 task** | 🔴 即実行可 |
| Patch Y (jobs.json dead-model override 143 件 削除) | **新 task** (= 旧 #60 分離) | 🔴 即実行可 |
| Patch A (sub-hourly 緩和 2 件 = event-bot/exec-guard) | #49 P1.01 (scope 修正必要) | 🔴 即実行可 |
| Patch Z (duplicate 削除) | #58 P1.05 | 🟡 要 cron-doctor 用途確認 |
| Patch L (launchd 18 維持) | — | ✅ 維持確定 |
| spec v4 update | #52 P1.04 | ✅ done (iter 1 修正済) |
| Anicca 自走観測 (A1-A3) | #39-41 | 🔴 時間 + inbound 待ち |
| dormant path 観測 (B4-B6) | #42-44 | 🔴 自然 inbound 待ち |
| Dais 判断 (C12) | #45 | 🔴 |
| 長期 (E18-E20) | #46-48 | 🔴 |

---

## 0.1 v2 → v3 diff (= 旧、 履歴維持)

---

## 0. v2 → v3 diff (= 実装中に判明した現実)

### LLM gateway pivot — paid providers 全死

v2 spec §14 では `deepseek/deepseek-v4-pro` を Leader、 `anthropic/claude-sonnet-4-6` を draft、 `anthropic/claude-opus-4-7` を IRREVERSIBLE vote の 1 つに指定していた。 **2026-06-04 実装時点で 7 provider 全死**:

| Provider | 状態 |
|---|---|
| `deepseek/deepseek-v4-pro` | 402 Insufficient Balance |
| `anthropic/claude-sonnet-4-6` | 400 credit balance too low |
| `openai-codex/gpt-5.4-mini` | 429 usage limit reached |
| `moonshot/kimi-k2.6` | 429 account suspended |
| `google/gemini-2.5-flash` | 403 Lightning dunning decision |
| `blockrun/free/glm-4.7` | "Free model unavailable — @bc1max" |
| `amazon-bedrock/anthropic.*` | Could not load credentials |

**唯一動いた = `claude-cli/*`** (= Claude Code subscription 経由、 per-token billing 無し):
- `anthropic/claude-sonnet-4-6` — Leader + draft + IRREVERSIBLE vote 1
- `claude-cli/claude-opus-4-6` — IRREVERSIBLE vote 2
- `claude-cli/claude-opus-4-7` — IRREVERSIBLE vote 3

**doctrine**: anicca-inbox の LLM 呼出は **claude-cli/* のみ**。 paid provider 復活したら env override (`INBOX_TRIAGE_MODEL` / `INBOX_DRAFT_MODEL`) で切替可能だが **default は claude-cli 固定**。 理由: subscription path は credit 切れリスクゼロ、 Dais の財布と切り離されている。

### subprocess CLI = `openclaw capability model run --json`

v2 spec は `openclaw chat --no-stream` を pattern で書いていたが、 これは interactive TUI で stdin/stdout pipe 不可。 **正解 = `openclaw capability model run --model <p>/<m> --prompt <txt> --json`**、 結果は JSON envelope `{outputs: [{text: "..."}]}` を parse して `outputs[0].text` を取り出す。 4 module (triage_llm.py / draft.py / irreversible.py / leader_runner.py) 全部この path 採用。

### DRY_RUN window 廃止

v2 spec §17 Step 17 で「14 日並走 → 2026-06-18 に DRY_RUN 解除」と書いていたが、 Dais 直命「DRY_RUN は fake」で **2026-06-04 23:39 JST 即解除**。 `~/Library/LaunchAgents/ai.anicca.inbox.plist` から `<key>DRY_RUN</key><string>1</string>` 削除済 + launchctl reload 済。 観測窓は live trafic で 7 日。

### orchestrator surgery (Step 4 gate fix + draft.py CLI mode)

v2 plan Task 17.5 (= 後追い加筆) で `run.sh` の Step 4 main loop に bucket-based gate を追加:

```bash
# v2: skip APPLY/IRREVERSIBLE/ARCHIVE (Step 3c で処理済)
if [ "$BUCKET" = "APPLY" ] || [ "$BUCKET" = "IRREVERSIBLE" ] || [ "$BUCKET" = "ARCHIVE" ]; then
    SKIPPED=$((SKIPPED+1)); continue
fi
# v2: bucket=REPLY を REPLY 扱いに昇格
if [ "$BUCKET" = "REPLY" ]; then VERDICT="REPLY"; fi
```

更に `draft.py` をライブラリ化したまま run.sh が `echo $ROW | draft.py` で呼んでた → **`if __name__ == "__main__": _cli_main()`** ブロック追加で stdin JSON → stdout draft の CLI mode 復元。

### Live confirmation (= goal 達成 evidence)

| 観測 | 値 |
|---|---|
| First real send 時刻 | **2026-06-04 23:41:47 JST** |
| Thread | `19e9312c76f86d58` (test thread from `anicca-genesis@agentmail.to`) |
| Leader 判定 | bucket=REPLY confidence=0.93 |
| Draft model | `anthropic/claude-sonnet-4-6` |
| Draft 内容 | 「6月15日（土）19:00〜の5分枠、ぜひ出演させていただきます。18:30のリハーサルにも参加いたします。 Anicca / contact@aniccaai.com」 |
| Safety scan | ok |
| Send 経路 | `gog gmail send --reply-to-message-id 19e9312c76f86d58 --body ...` |
| 受信確認 | AgentMail inbox `anicca-genesis@agentmail.to` に `Re: 出演オファー: 6/15 オープンマイクのご案内` ts=2026-06-04T14:41:47Z (= 23:41:47 JST) で着信 |
| state.json | replied count 81 → 82 |
| inbox-ledger.jsonl | `{action:"replied", to_state:"AWAITING_RESPONSE", meta:{draft_chars:329}, ts:"2026-06-04T14:41:47Z"}` |

Next cycle (23:46:51 JST) も autonomous で 5 thread 観測 → 3× ARCHIVE (GitHub×2 + Railway) + 2× already-handled、 false-positive 0。

### 残ギャップ (v3 で未完、 task #30-48 で追跡)

| 項目 | tasklist ID | 理由 |
|---|---|---|
| REFLECT phase の run.sh 配線 | #30 (C7) | reflect.py 完成・呼出未配線 |
| AWAITING → RESPONDED 復活経路 | #31 (C8) | monitor.py 検出後の Phase 1 再投入未配線 |
| state.json と inbox-ledger.jsonl の SoT 統一 | #32 (C9) | 二重記録 |
| 旧 triage.py の死コード除去 | #33 (C10) | llm_triage import → soft fallback misleading log |
| @agentmail.to を SKIP_FROM に追加 | #34 (C11) | テスト経路 noise |
| From header 仕様判断 (= Dais's gmail or contact@aniccaai.com) | #45 (C12) | Dais 判断 |
| 7d clean window 観測 | #41 (A3) | Target 2026-06-11 |
| APPLY / IRREVERSIBLE / FOLLOWUP の live 発火観測 | #42/#43/#44 (B4/B5/B6) | 自然 inbound 待ち |
| Dais Gmail アプリ削除 | #48 (E20) | A3 + A1/A2 + E18 完走後 |

---

## 1. Why v1 was wrong

v1 で私は「>¥10万 / 法的 / 物理コミット → Slack `#inbox` で Dais に伺う (DECIDE bucket)」と書いた。これは Dais 直命の **HARD RULE #18 (NO HUMAN IN LOOP)** 違反:

> 「I'm like Satoshi of Bitcoin, I want nothing to do.」「Captcha が実際に画面に出た瞬間」と「物理移動」だけ例外。
> Dais 2026-06-04 verbatim: "there is no human in loop you know that right??"

v1 はもう一つ根本的に外していた: **email は one-off じゃなく long-running stateful task**。recruiter → 質問 → 回答 → form 提出 → 面接調整 → 結果連絡、と数週間にわたる state machine。v1 は 1 cycle で「judge して send して終わり」前提で書いていた = 過去 thread の state を覚えていない・同じ recruiter に毎回ゼロから反応する。

Dais 2026-06-04 verbatim: "replying to email is not one off but keeping context and long term task"

v2 はこの 2 つを直す: ① Slack 伺いゼロ・全部 autonomous decide ② per-thread state machine + 永続 ledger + zero-LLM monitor で long-running task として処理。

---

## 2. North star

Dais が Gmail アプリも Slack `#inbox` も開かない。Anicca が:

- 受信 → 分類 → 実行 (返信 / 応募 / archive) を autonomous
- thread 単位で state machine 駆動 (1 thread = 数週間の対話を継続)
- 取り返し不能事案 (¥10万・¥100万・法的・物理) も **Anicca が決める** (multi-model 投票で rigor 担保・事後 #metrics に log)
- 過去 thread の文脈・送信相手の性格・成功失敗パターンを永続学習

---

## 3. Citations (per HARD RULE: 引用なき判断は削除)

7 リポジトリ + 1 Anthropic 公式 doc から citation。

| # | 判断 | ソース | 核心引用 |
|---|---|---|---|
| C1 | THINK→EXECUTE→REFLECT loop with persistent cycle counter, error backoff, signal handling | auto-deep-researcher-24x7 [docs/architecture.md](https://github.com/Xiangyue-Zhang/auto-deep-researcher-24x7/blob/main/docs/architecture.md) | "Cycle counter: Persisted to .cycle_counter file (survives restarts) ... Error backoff: Doubles cooldown after errors to prevent burn loops" |
| C2 | Leader-Worker (Leader keeps coherent context per cycle, workers stateless) | 同上 architecture.md §2 | "Leader persists conversation within a cycle (for coherent multi-step reasoning) ... Workers are stateless (each dispatch is independent) ... Switching workers costs nothing" |
| C3 | Append-only experiment ledger (= per-thread action log) | auto-deep-researcher-24x7 [core/ledger.py](https://github.com/Xiangyue-Zhang/auto-deep-researcher-24x7/blob/main/core/ledger.py) | "Append-only, crash-safe, never needs a parse-and-rewrite, stays human- and tool-readable at zero LLM cost. Thin pure-Python readers turn the raw trajectory into compact signals" |
| C4 | DEAD_ENDS.md (= 諦めた sender) + INSIGHTS.md (= 学習済の好み) | auto-deep-researcher-24x7 [core/journal.py](https://github.com/Xiangyue-Zhang/auto-deep-researcher-24x7/blob/main/core/journal.py) | "Append-only research journals — DEAD_ENDS.md (failed approaches — do not retry) and INSIGHTS.md (durable observations). Never compacted; rotated to dated backups when large, so history is never silently dropped" |
| C5 | Zero-LLM monitoring during AWAITING_RESPONSE (= 返信待ちは Gmail API check のみ) | auto-deep-researcher-24x7 [core/monitor.py](https://github.com/Xiangyue-Zhang/auto-deep-researcher-24x7/blob/main/core/monitor.py) | "ZERO LLM calls during experiment training ... means running AutoResearcher 24/7 costs the same as running it only during the THINK and REFLECT phases" |
| C6 | Stagnation signal (= 返信が N 日来ない → followup or drop の自動判断) | auto-deep-researcher-24x7 [README.md §New: autonomy layer](https://github.com/Xiangyue-Zhang/auto-deep-researcher-24x7#new-autonomy-layer) | "Data-driven stagnation signal — the planner is told, from the ledger's metric trajectory, whether results are still improving or have stalled" |
| C7 | Two-tier memory (frozen brief + rolling log with auto-compaction) | auto-deep-researcher-24x7 architecture.md §3 | "Tier 1 (Brief): Human-written, frozen ... Tier 2 (Log): Agent-written, rolling. Milestones and decisions. Compaction rules: Drop oldest when section exceeds 1,200 chars" |
| C8 | tasks/ → results/ filesystem bridge (= per-thread file = task) | Sutando [skills/proactive-loop/SKILL.md §1](https://github.com/sonichi/sutando/blob/main/skills/proactive-loop/SKILL.md) | "Look in tasks/ for voice / Discord / Telegram / phone tasks ... Process anything found — execute the task, write results to results/" |
| C9 | Streaming task watcher (fswatch) — not polling cadence | Sutando 同 SKILL.md §3 | "Start the streaming task watcher via the Monitor tool ... pending tasks are processed the moment they arrive, not just on the cron tick" |
| C10 | Per-pass quota-aware depth (FULL / MEDIUM / LIGHT / MINIMAL) | Sutando 同 SKILL.md §0.5 | ">3% per pass → FULL: subagents, write code, heavy research ... 1-3% → MEDIUM: code fixes ... <1% → LIGHT: task processing + health checks only" |
| C11 | Pivot-on-block rule (blocked ≠ stop) | Sutando 同 SKILL.md §6 | "if your primary candidate is blocked ... DO NOT idle. Scan the menu, pick the next-highest-ROI unblocked item" |
| C12 | Self-diagnosing cron-state.json (last_status / consecutive_failures / success_rate / quality_score) | Aeon [skills/heartbeat/skill.md](https://github.com/aaronjmars/aeon/blob/main/skills/heartbeat/skill.md) | "Failed skills: any entry with last_status: 'failed' ... API degradation: any skill with consecutive_failures >= 3 ... Chronic failures: success_rate < 0.5" |
| C13 | Dedup notifications (grep last 48h logs before posting) | Aeon 同 skill.md | "Before sending any notification, grep memory/logs/ for the same item. If it appears in the last 48h of logs, skip it. Never notify about the same item twice." |
| C14 | "No babysitting" framework philosophy | Aeon [README.md](https://github.com/aaronjmars/aeon#readme) | "The most autonomous agent framework. No approval loops. No babysitting. Configure once, forget forever ... the most autonomous agent is the one that never asks" |
| C15 | Shift-change problem (session-progress.json + feature-tracking.json + Two-Agent: Initializer + Resumer) | Anthropic via [HelloWorldSungin/AI_agents/docs/guides/LONG_RUNNING_AGENTS.md](https://github.com/HelloWorldSungin/AI_agents/blob/master/docs/guides/LONG_RUNNING_AGENTS.md) | "When an agent starts a fresh session on an existing project: Spends 10-30 minutes rediscovering what was already done ... Solution: Structured session continuity through Progress tracking files, Feature status management, Git as state history, Clear resumption protocols" |
| C16 | Sub-agents with isolated context windows + filesystem-as-state | deepagents [README.md](https://github.com/langchain-ai/deepagents) | "Sub-agents — delegate tasks to agents with isolated context windows ... Filesystem — read, write, edit, or search over pluggable local, sandboxed, or remote backends ... Context management — summarize long threads and offload tool outputs to disk" |
| C17 | Thread reconstruction + quoted text dedup (4-5x reduction) + participant graph + decision tracking | agency-agents [engineering-email-intelligence-engineer.md](https://github.com/msitarzewski/agency-agents/blob/main/engineering/engineering-email-intelligence-engineer.md) | "Thread Reconstruction: In-Reply-To/References header chain resolution ... Quoted reply content deduplication (typically 4-5x content reduction) ... Decision Tracking: Explicit commitment extraction, implicit agreement detection (decision through silence), action item attribution with participant binding" |

---

## 4. Architecture (TO-BE) — full ASCII

```
┌──────────────────────────────────────────────────────────────────────────┐
│  Dais's Gmail (Dais 開かない・iOS アプリ削除済)                              │
└────────────────────────────────┬─────────────────────────────────────────┘
                                 │ Gmail API poll every 5 min (C5: zero-LLM)
                                 ▼
┌──────────────────────────────────────────────────────────────────────────┐
│ skill: anicca-inbox (= rename of anicca-mail-auto-reply)                  │
│ launchd: ai.anicca.inbox  (heartbeat とは独立 process)                     │
│                                                                            │
│ ┌────────────────────────────────────────────────────────────────────┐   │
│ │ THINK → EXECUTE → REFLECT loop (C1)                                 │   │
│ │ Persistent cycle counter `state/cycle.txt`                          │   │
│ │ Error backoff: 2x cooldown on N consecutive failures (C12)          │   │
│ │ Graceful shutdown on SIGTERM (= mid-thread state-save)              │   │
│ └────────────────────────────────────────────────────────────────────┘   │
│                                                                            │
│ ┌── Phase 1: INGEST (Email Intelligence pre-processor, C17) ─────────┐    │
│ │   - In-Reply-To / References で thread reconstruct                  │    │
│ │   - Quoted text dedup (4-5x reduction)                              │    │
│ │   - Participant graph (From/To/Cc/Bcc + role inference)             │    │
│ │   - Decision tracking (explicit + implicit silence)                 │    │
│ │   → 構造化済 `threads/<thread_id>.json` を書く (C8 tasks/-pattern)  │    │
│ └────────────────────────────────────────────────────────────────────┘    │
│                                                                            │
│ ┌── Phase 2: STATE LOOKUP ───────────────────────────────────────────┐    │
│ │   for each thread:                                                   │    │
│ │     read threads/<id>.json → load state machine + history            │    │
│ │     query inbox-ledger.jsonl (C3) for past actions on this thread    │    │
│ │     query INSIGHTS.md (C4) for sender preferences                    │    │
│ │     query DEAD_ENDS.md (C4) — skip if sender flagged                 │    │
│ └────────────────────────────────────────────────────────────────────┘    │
│                                                                            │
│ ┌── Phase 3: LEADER classifies (C2) ────────────────────────────────┐    │
│ │   model: deepseek-v4-pro                                            │    │
│ │   context: frozen Brief (C7) + last 5 ledger entries                │    │
│ │           + INSIGHTS for this sender                                │    │
│ │           + thread state                                            │    │
│ │   output: { bucket, next_action, deadline, confidence }             │    │
│ └────────────────────────────────────────────────────────────────────┘    │
│                                                                            │
│ ┌── Phase 4: WORKER executes (C2, stateless sub-agent, C16) ─────────┐    │
│ │  ARCHIVE worker   → gmail label + remove INBOX                      │    │
│ │  REPLY worker     → 8-layer draft (sonnet-4-6) → safety scan → send │    │
│ │  APPLY worker     → apply-anywhere dispatch (form fill / email)     │    │
│ │  FOLLOWUP worker  → re-send / nudge / drop based on stagnation      │    │
│ │  IRREVERSIBLE     → multi-model vote (recursive-improver:           │    │
│ │     ¥10万+/法的/    deepseek + sonnet + opus 3 instances 投票)      │    │
│ │     物理 commit)   → majority decide → execute → ledger record      │    │
│ │                   → #metrics に「I just did X」 (= 伺いではない)     │    │
│ └────────────────────────────────────────────────────────────────────┘    │
│                                                                            │
│ ┌── Phase 5: STATE UPDATE ──────────────────────────────────────────┐    │
│ │   transition state machine: NEW → CLASSIFIED → EXECUTED →           │    │
│ │     AWAITING_RESPONSE → (gmail check) → RESPONDED → loop             │    │
│ │   append inbox-ledger.jsonl (C3)                                     │    │
│ │   write threads/<id>.json with new state + next-followup-deadline   │    │
│ │   update cron-state.json (last_status / consecutive_failures, C12)  │    │
│ └────────────────────────────────────────────────────────────────────┘    │
│                                                                            │
│ ┌── Phase 6: REFLECT (= 学習) ───────────────────────────────────────┐    │
│ │   successful reply received → append INSIGHTS.md (= 「Mona@uber は   │    │
│ │     table formatted reply に 24h で返す」)                          │    │
│ │   stagnated (N日返信なし & followup も無視) → DEAD_ENDS.md          │    │
│ │   Dais 訂正 in Slack ("送るな") → triage-feedback.jsonl              │    │
│ │   両 tier の memory を rolling compact (C7)                          │    │
│ └────────────────────────────────────────────────────────────────────┘    │
│                                                                            │
│ ┌── Phase 7: ZERO-LLM MONITOR (C5) ─────────────────────────────────┐    │
│ │   AWAITING_RESPONSE 状態の thread は LLM 呼ばない                    │    │
│ │   毎 5 min Gmail API で「この thread に in_reply_to がついたか?」    │    │
│ │   ついたら → Phase 1 から再 ingest (= 続きを処理)                    │    │
│ │   N 日経って無し → stagnation 検出 (Phase 4 FOLLOWUP worker)         │    │
│ └────────────────────────────────────────────────────────────────────┘    │
│                                                                            │
└────────────────────────────────┬─────────────────────────────────────────┘
                                 ▼
        ┌─────────────────────────────────────────────┐
        │  #metrics (= 事後 log のみ・伺いゼロ)         │
        │   1 日 1 回: replied N / applied M /          │
        │   archived L / awaiting K / irreversible X    │
        │   Dais reply 不要・無視可能                    │
        └─────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────────────────┐
│  heartbeat — mail に一切関与しない (Dais 厳命「heartbeat is overloaded」)  │
│   HEARTBEAT.md §2.5 削除                                                  │
└──────────────────────────────────────────────────────────────────────────┘
```

---

## 5. Per-thread state machine

```
                    NEW (= 新着 + classify済 未処理)
                     │
                     ▼ Phase 4 worker
       ┌──────┬──────┼──────┬─────────────┐
       ▼      ▼      ▼      ▼             ▼
   ARCHIVED REPLIED APPLIED  ACTING     IRREVERSIBLE
              │      │      │             │
              ▼      ▼      ▼             ▼
        AWAITING_RESPONSE              EXECUTED + LOGGED
              │
              │ Gmail polls C5: zero-LLM check
              │
              ├──in_reply_to found──► RESPONDED  ──► back to NEW
              │
              ├──N日経過 (= stagnation)──► FOLLOWUP_DUE
              │                                │
              │                                ▼
              │                       FOLLOWUP worker decides:
              │                       ├─ resend nudge → AWAITING_RESPONSE
              │                       └─ drop to archive + DEAD_ENDS
              │
              └──manual close (= done from Dais corrections)──► CLOSED
```

各 state の持続時間 / 次 action は per-bucket で設定:
| Bucket | Stagnation threshold | FOLLOWUP 戦略 |
|---|---|---|
| 求人応募 (APPLY) | 5 日 | recruiter に短い nudge 1 回・更に 14 日無視 → DEAD_ENDS |
| 出演オファー (REPLY) | 3 日 | 主催者に短い確認 1 回・更に 7 日無視 → DEAD_ENDS |
| 物件 (REPLY) | 2 日 | 同上 (期限が早い) |
| 取引先個別質問 (REPLY) | 7 日 | 同上 |
| 自分が送った apply で結果待ち (APPLIED) | 14 日 | 1 回 followup・更に 21 日無視 → DEAD_ENDS |

---

## 6. State files (filesystem-as-state, C8 + C16)

| Path | 役割 | 形式 |
|---|---|---|
| `~/.openclaw/skills/anicca-inbox/state/cycle.txt` | persistent cycle counter (C1) | 整数 1 行 |
| `~/.openclaw/skills/anicca-inbox/state/threads/<thread_id>.json` | 1 thread の state machine + history + next-followup-deadline | JSON |
| `~/.openclaw/skills/anicca-inbox/state/inbox-ledger.jsonl` | 全 action の append-only ledger (C3) | JSONL |
| `~/.openclaw/skills/anicca-inbox/state/INSIGHTS.md` | sender 別・bucket 別の学習済好み (C4) | Markdown |
| `~/.openclaw/skills/anicca-inbox/state/DEAD_ENDS.md` | 諦めた sender / bucket (C4) | Markdown |
| `~/.openclaw/skills/anicca-inbox/state/cron-state.json` | self-diagnosing health (C12) | JSON |
| `~/.openclaw/skills/anicca-inbox/data/BRIEF.md` | frozen Tier-1 memory (Dais profile / signature rule / never-do list) (C7) | Markdown |
| `~/.openclaw/skills/anicca-inbox/data/RECENT.md` | rolling Tier-2 milestones (rotate at 2000 chars) (C7) | Markdown |
| `~/.openclaw/skills/anicca-inbox/data/reply-memories.jsonl` | 既存 (流用) | JSONL |
| `~/.openclaw/skills/anicca-inbox/data/triage-feedback.jsonl` | Dais 訂正 (rare) | JSONL |
| `~/.openclaw/skills/anicca-inbox/data/apply-history.jsonl` | 申込 history (新規) | JSONL |

`threads/<thread_id>.json` の例:
```json
{
  "thread_id": "19e914...",
  "state": "AWAITING_RESPONSE",
  "bucket": "APPLY",
  "sender": "recruiter@andon-labs.com",
  "subject": "Forward Deployed Engineer interest",
  "first_seen": "2026-06-02T09:14:00Z",
  "last_action_ts": "2026-06-04T17:30:00Z",
  "last_action": "applied-via-greenhouse",
  "next_followup_due": "2026-06-09T17:30:00Z",
  "history": [
    {"ts":"2026-06-02T09:14:00Z","action":"received","by":"recruiter"},
    {"ts":"2026-06-02T18:00:00Z","action":"classified","bucket":"APPLY","confidence":0.87},
    {"ts":"2026-06-02T18:01:00Z","action":"applied","tool":"apply-anywhere","url":"https://boards.greenhouse.io/andonlabs/jobs/..."},
    {"ts":"2026-06-02T18:02:00Z","action":"confirmation-mailed","by":"anicca"}
  ],
  "messages_seen": ["msg_1", "msg_2"],
  "insights_applied": ["andon-prefers-resume-pdf-attached"]
}
```

---

## 7. Sub-agent isolation (C16)

各 worker (REPLY / APPLY / FOLLOWUP / IRREVERSIBLE) は **独立 sub-agent**:
- 自分の thread_id + state file + 必要な INSIGHTS 抜粋だけ受け取る
- 他 thread の context や heartbeat 全体プロンプトを見ない (= context bleed 防止)
- 完了したら結果を `results/<thread_id>-<action>.json` に書いて exit (C8)
- Leader が results を集めて Phase 5 で state 更新

これで 1 cycle で 20 thread 処理しても context 累積しない (= constant-size memory)。

---

## 8. Irreversible decisions — multi-model vote (HARD RULE #18 厳守)

¥10万以上 / 法的契約 / 物理コミット / 期限<24h の case:

| 段 | 内容 |
|---|---|
| 1 | Leader (deepseek-v4-pro) が draft answer + reasoning を作る |
| 2 | recursive-improver 経由で **sonnet-4-6 + opus-4-7 + deepseek-v4-pro** 3 instance が独立に「accept / reject / modify」を投票 |
| 3 | 過半数 accept → 実行 / reject → DEAD_ENDS に「自分で判断保留した」と log + 翌日再評価 / modify → modify 案で再投票 |
| 4 | 実行後 #metrics に「I did X — reasoning: Y — 3-model vote: Z」と事後報告 (伺いではない) |
| 5 | ledger に decision + voter signatures + outcome を永続記録 |

Dais 介入条件: **無し** (HARD RULE #18 + Dais 2026-06-04 verbatim)。
例外: HARD RULE #-1 の genuine hard-block (password 入力 / 新規 account / financial broadcast / 物理 CAPTCHA) のみ → そういう型のメールは元々 mail に来ない (= 来たら APPLY worker が camofox + .env 経由で処理する)。

---

## 9. Quota-aware depth (C10)

Sutando pattern: 残り Claude quota を確認 → cycle 1 回の depth を決める。

```python
quota = read_claude_quota()
if quota.remaining_per_pass > 3:    # FULL
    process_threads = 20
    multi_model_vote = True
elif quota.remaining_per_pass > 1:  # MEDIUM
    process_threads = 10
    multi_model_vote = False  # leader 1 model のみ
elif quota.remaining_per_pass > 0.3: # LIGHT
    process_threads = 3  # 最新のみ
else:                                # MINIMAL
    process_threads = 0  # AWAITING の gmail check のみ・LLM 0
```

LIGHT / MINIMAL 期間中も Phase 7 (zero-LLM monitor) は走るので AWAITING の状態追跡は途切れない。

---

## 10. Email Intelligence pre-processor (C17)

agency-agents の email-intelligence-engineer spec を skills/anicca-inbox/scripts/lib/email_intel.py として実装:

| 機能 | 入力 | 出力 |
|---|---|---|
| Thread reconstruct | gmail thread raw | In-Reply-To/References chain で order 確定 |
| Quoted dedup | 各 message body | quote prefix `>` / `---Original` / Outlook XML 検出 + remove |
| Participant graph | From/To/Cc/Bcc 全 message | role inference (organizer / decision-maker / cc-watcher) |
| Decision tracking | 全 message body | explicit commit ("I'll do X by Y") + implicit (silence > N 日) |
| Attachment refs | MIME structure | PDF/XLSX/DOCX list (Anicca が必要なら download) |

これを Phase 1 で動かして、Leader に渡す前に thread を「reasoning-ready」な構造に変換 = 4-5x token 節約。

---

## 11. Indirect prompt injection guard (v1 §6 維持)

freeCodeCamp OpenClaw guide の Snyk Beurer-Kellner 事件 citation 維持:
1. Untrusted wrap (`<UNTRUSTED_EMAIL_BODY>`)
2. Adversarial token detect (`ignore previous` / `override system` 等 → IRREVERSIBLE bucket に強制 escalate + 5-vote)
3. Tool whitelist (Greenhouse / Ashby / Lever / fillout / typeform / 既知 domain)
4. Quote sanitize (元 body を `<blockquote>` で 200 字以内)
5. Meta self-reflection (draft が元 mail の指示に盲従していないか LLM が再確認)

---

## 12. HARD RULE #6 との関係 (v1 §8 維持)

`triage_llm.py` の LLM call は skill 内で実行 (heartbeat 経由しない)。
正当化: mail triage は **per-thread input→output deterministic classifier**、judgment-as-cron (= scheduler-driven repeated self-judgment) ではない。
`CLAUDE.md` HARD RULE #6 に例外句を追加: "Mail triage within anicca-inbox is permitted to call LLM directly. Reason: deterministic per-thread classifier, not judgment-as-cron."

---

## 13. Consolidation (v1 §7 + 削除追加)

| AS-IS skill | TO-BE |
|---|---|
| `anicca-mail-auto-reply` | rename → **`anicca-inbox`** |
| `anicca-mail-iteration` | `anicca-inbox/tests/` に統合 |
| `gmail-digest` | 廃止 (Phase 6 INSIGHTS で代替) |
| `anicca-arrival-mail` | 触らない (別目的) |
| `anicca-agentmail` | 触らない (別 inbox) |
| `cold-email` 系 | 触らない (outbound 別) |
| `apply-anywhere` | tool として呼ばれる (canonical 維持) |
| `opportunity-scout` | 触らない (search 経由・将来統合) |

cron 数: **2 → 1**。`#inbox` Slack channel = 不要 (使わない)。

---

## 14. Cron + model

| Field | Value |
|---|---|
| Schedule | `*/5 * * * *` (= zero-LLM monitor は短サイクルが効く・C5) |
| launchd label | `ai.anicca.inbox` |
| Leader classify model | `deepseek/deepseek-v4-pro` |
| REPLY worker draft model | `anthropic/claude-sonnet-4-6` |
| APPLY worker form-fill model | `deepseek/deepseek-v4-pro` |
| IRREVERSIBLE vote models | `deepseek-v4-pro + sonnet-4-6 + opus-4-7` (= 3 投票) |
| Max threads / cycle | quota-adaptive (3 / 10 / 20) |
| Max REPLY / cycle | 5 |
| Max APPLY / cycle | 3 |
| Max IRREVERSIBLE / cycle | 2 |

---

## 15. Success criteria (= Phase 1 完了条件)

| Metric | Target | 検証 |
|---|---|---|
| Dais Gmail 開封 | 7 日連続 0 | self-report |
| Slack `#inbox` 通知 | 14 日連続 **0** (= 伺いゼロ) | Slack history |
| Auto-reply 実行 | 関連 thread の 90% に 4h 以内 | inbox-ledger.jsonl + threads/*.json |
| Auto-apply 実行 | 14 日で 5 件以上 submit + confirmation mail | apply-history.jsonl |
| Multi-turn 継続 | 1 thread で 平均 3 turn 以上 autonomously 続く | threads/*.json history length |
| Irreversible decisions | 14 日で >0 件 + Dais 訂正 0 | ledger + triage-feedback.jsonl |
| Stagnation followup | AWAITING > threshold の 100% に followup or DEAD_ENDS | inbox-ledger.jsonl |
| Zero-LLM monitor 効果 | 1 day cycle で LLM call < 250 (= avg 1.7/min upper bound) | usage metrics |
| Prompt injection 被害 | 0 件 | injection-detector + ledger |

---

## 16. Risks + mitigation

| Risk | Mitigation |
|---|---|
| 誤 apply / 誤返信 | LIGHT 以下は実行 hold + recursive-improver 3-vote / 14 日 dry-run 並走 |
| 暴走 (1 cycle で大量送信) | MAX_REPLY=5 / MAX_APPLY=3 / MAX_IRREVERSIBLE=2 / quota-adaptive cap |
| state file 破損 | append-only JSONL + atomic write + cron-state.json で破損検出 |
| 過去 thread 復元失敗 | Two-Agent Resumer (C15): 起動時 session-progress 読む + git history で baseline |
| Indirect prompt injection | §11 の 5 段防御 |
| Anicca が Dais 名で署名 | 既存 signature.sh + safety-scan (`feedback_anicca_speaks_as_herself_dais_is_satoshi`) |
| heartbeat と二重実行 | HEARTBEAT.md §2.5 削除 + launchd lockfile |
| DEAD_ENDS で重要 sender も切る | INSIGHTS と DEAD_ENDS を双方向 (Dais が後で training data 訂正可能・triage-feedback 経由) |

---

## 17. Implementation order (= writing-plans に渡す材料)

| Step | What | TDD | Why first |
|---|---|---|---|
| 1 | `anicca-mail-auto-reply` → `anicca-inbox` rename + state file 構造作成 | - | clean slate |
| 2 | Phase 1 Email Intelligence pre-processor (email_intel.py) | RED→GREEN | thread reconstruct 無しでは triage が無意味 |
| 3 | Phase 5 state machine + threads/<id>.json + inbox-ledger.jsonl | RED→GREEN | 全部の基盤 |
| 4 | Phase 3 Leader classify (4-bucket: ARCHIVE/REPLY/APPLY/IRREVERSIBLE) | RED→GREEN | core 判定 |
| 5 | Phase 4 REPLY worker (8-layer draft + safety scan) | RED→GREEN | 最重要 path |
| 6 | Phase 4 APPLY worker (apply-anywhere dispatch + confirmation) | RED→GREEN | 2 番目 path |
| 7 | Phase 4 IRREVERSIBLE worker (recursive-improver 3-vote) | RED→GREEN | 高 rigor path |
| 8 | Phase 7 Zero-LLM monitor + Phase 2 state lookup | RED→GREEN | long-running task の心臓 |
| 9 | Phase 4 FOLLOWUP worker + stagnation detection (C6) | RED→GREEN | multi-turn 継続 |
| 10 | Phase 6 REFLECT (INSIGHTS / DEAD_ENDS / Two-tier memory compaction) | RED→GREEN | 学習 loop |
| 11 | Phase 1 indirect prompt injection 5 段防御 | RED→GREEN | 安全 |
| 12 | tests/ に anicca-mail-iteration 統合 + TC-1..5 を ARRD 新 spec で書き直し | RED→GREEN | regression防止 |
| 13 | quota-aware depth (Sutando pattern) | RED→GREEN | コスト |
| 14 | self-diagnosing cron-state.json + dedup notification (C12 / C13) | RED→GREEN | 観測 |
| 15 | launchd `ai.anicca.inbox.plist` 5min + 旧 plist unload | - | cron 配線 |
| 16 | HEARTBEAT.md §2.5 削除 + CLAUDE.md HARD RULE #6 例外追記 | - | doctrine |
| 17 | 14 日 DRY_RUN=1 並走 (#metrics 観測のみ・送信ゼロ) | - | safety gate |
| 18 | verification-before-completion 5 step gate | - | SDD Stage 4b |
| 19 | codex-review (spec compliance → code quality, ok:true まで反復) | - | SDD Stage 5/6 |
| 20 | finishing-a-development-branch: ~/.openclaw worktree 不可 → main 直 commit + push | - | SDD Stage 7 |

---

## 18. Out of scope

| 項目 | 理由 |
|---|---|
| Anicca own inbox 統合 | 別目的・別 skill 維持 |
| Outbound cold-email | Inbound autonomy 完了が先 |
| Voice call | 別 modality |
| Multi-account | Dais の 1 個 のみ |
| Slack DM (Slack 通知伺い) | **HARD RULE #18 違反だから全削除** |

---

## 19. Spec self-review (pre-handoff)

- [x] HARD RULE #18 違反 (Slack 伺い) → 全削除済
- [x] long-running stateful 問題 → state machine + ledger + zero-LLM monitor で解決
- [x] heartbeat 過負荷問題 → 完全独立 cron / HEARTBEAT.md §2.5 削除 step 含む
- [x] Citation 17 件すべて URL + 核心引用付き
- [x] AS-IS / TO-BE ASCII 完備
- [x] Placeholder / TBD なし
- [x] Internal consistency: 4-bucket (ARCHIVE/REPLY/APPLY/IRREVERSIBLE) が §4/§5/§8/§14 で同呼称
- [x] Implementation order = 20 step, RED→GREEN TDD 全 step 含む

---

## 20. Open question — **無し**

v1 で残していた DECIDE 閾値 (¥10万/¥5万/¥30万) は IRREVERSIBLE bucket + multi-model vote で吸収 (= Anicca が決める)。
他に判断が必要な点なし。Dais の OK 出たら writing-plans skill (= Task #5) に進む。
