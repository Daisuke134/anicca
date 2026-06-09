# Anicca Uncertainty Resolution — Q&A (実装前 全解消、 引用付き)

| Field | Value |
|---|---|
| Date | 2026-06-09 |
| Status | RESOLVING — 150項目を 調査+引用で 順次解消 |
| Rule | 全 U に 答え+source。 未解消で 実装着手 禁止 (= spec-driven、 dry-run 二度と起こさない) |
| 親 spec | `2026-06-09-anicca-build-spec.md` §5-§7 |

凡例: ✅=解決 / ⚠️=Dais判断要 / 🔍=調査中

---

## BLOCKER (UB1-6)

### ✅ UB1 — Hermes は SOUL/CONSTITUTION/skills を auto-inject するか → ★ YES ★
source: `~/.hermes/hermes-agent/agent/system_prompt.py:88-95` verbatim:
> "Try SOUL.md as primary identity unless caller explicitly skipped it... `_soul_content = _r.load_soul_md()` → stable_parts.append"
+ `:16-17` "context — caller-supplied system_message plus context files (AGENTS.md / .cursorrules / etc.) discovered under TERMINAL_CWD"
+ `prompt_builder.py:944-1168` = SKILL.md を 毎build inject。
**結論**: Hermes は ① SOUL.md (identity) ② AGENTS.md / context files ③ skills/SKILL.md を 毎turn inject する。 = ★ Felix/OpenClaw pattern が 載る ★。
注意: `HEARTBEAT.md` / `MEMORY.md` は Hermes native でない。 Hermes は `.hermes.md` / `HERMES.md` を読む (`prompt_builder.py:77`)。 → heartbeat 指示 は cron-prompt or HERMES.md に書く。 memory は skill で持つ。
+ 既存: `~/.hermes/AGENTS.md` は symlink → `anicca-oss/CONSTITUTION.md` (= ★ rename で broken、 →anicca に 貼り直し 必要 ★)。

### ✅ UB2 — Hermes heartbeat は LLM agent turn を回せるか → ★ YES (agent-mode cron) ★
source: 現 genesis cron は `mode=no-agent (script stdout delivered directly)` = ★ script だけ、 LLM 呼ばない = 死んだ心拍 ★ (`hermes cron list` で確認済)。
Hermes core の "heartbeat" (`chat_completion_helpers.py:2320 _HEARTBEAT_INTERVAL=30s`) = ただの keep-alive (activity touch)、 agent turn でない。
**結論**: Hermes cron は ★ agent-mode (= LLM turn を 回す) と no-agent (script) の 2 mode ★。 genesis heartbeat を ★ agent-mode に変えて HEARTBEAT prompt を 回せば think→act→observe が 動く ★。 = 死んだ心拍 → 生きた心拍。

### ✅ UB4 — canonical build repo → ★ ~/.hermes (runtime) 直編集、 anicca-genesis に sync ★
source: repo 確認:
- `~/anicca` = `anicca` (mother hub、 OSS framework/spec)
- `~/.openclaw` = `anicca-dais` (private、 157 cron)
- `~/anicca-project` = `anicca-products` (life-manager spec + iOS/web)
- `~/.hermes` = ★ NOT git ★ = ★ live runtime (= genesis の体) ★、 anicca-genesis repo に sync
**結論**: build 対象 = ★ `~/.hermes` を 直編集 (= live runtime) ★。 SOUL/skills/cron は ここ。 spec/設計 は `~/anicca`。 安全 file は anicca-genesis に push。

### ✅ UB5 — life-manager (anicca-products) と genesis (Hermes) は 同 agent か → 🔍 要 life-manager code 確認 (次 batch)
暫定: life-manager spec は `anicca-products` branch、 voice=sutando、 host=Daytona。 genesis=Hermes earn。 = ★ 現状 別 stack ★。 統合方針: 2 loop=1 Hermes runtime に 寄せる か、 life=Daytona/genesis=Hermes 別 のまま 連携か → UB5 は 次 batch で life-manager 実体読んで 確定。

### 🔍 UB6 — 3-tier memory + Ralph loop の OSS copy元 → 次 batch (mem0/letta/ralph 調査)

---

## ENV 鍵 (= C/G/H/M 大量解決) — source: `~/.openclaw/.env` grep
✅ SET (= 持ってる): STRIPE_SECRET_KEY, TWILIO_ACCOUNT_SID+AUTH_TOKEN, GEMINI_API_KEY,
   XAI_API_KEY, POSTIZ_API_KEY, AGENTMAIL_*(anicca/hermes/marketing 複数), LANCERS_EMAIL+PASSWORD,
   SOLANA_PUBKEY, ANICCA_WALLET_ADDR, ELEVENLABS_API_KEY, LIVEKIT_API_KEY+SECRET, CDP_API_KEY(Coinbase),
   OPENAI/DEEPSEEK/KIMI/GEMINI, NOTE/DEVTO(記事), CLAWMART_*, COCONALA_*
★ MISSING (= 作る/不要判断): DAYTONA_API_KEY, GOOGLE_MAPS_API_KEY, SENTRY_DSN

個別解決:
- ✅ U70/71 Stripe: STRIPE_SECRET_KEY SET。 ⚠️ test/live どっちか + account 主体 (Anicca/Dais) は 次 batch で 鍵 prefix 確認 (sk_live/sk_test)
- ✅ U96/97 Twilio+Gemini: 両 SET → 電話 voice 可能
- ⚠️ U98 GOOGLE_MAPS = MISSING → route計算用 (GOOGLE_API_KEY で代替可? 次確認)
- ⚠️ U109 DAYTONA = MISSING → SaaS cloud。 作成 or 別host (Mac/別cloud) 判断要
- ⚠️ U126 SENTRY = MISSING → self-heal は log-based で代替 (Sentry account 作らず)
- ✅ U87 LANCERS SET → ClawWork loop の 実client 出口 可能
- ✅ U104 daily email = AGENTMAIL_ANICCA SET
- ✅ U24 X = POSTIZ_API_KEY SET (@aniccaxxx integration 既存) + xpost CLI は Felix同梱
- ✅ U149 wallet = SOLANA_PUBKEY + ANICCA_WALLET_ADDR + CDP(Coinbase) SET

## RUNTIME (A)
- ✅ U8 fallback完全空: `config.yaml fallback_providers: []` + `provider: xai-oauth` → ★ mini に落ちない ★
- ✅ U52 max_turns=30 (`config.yaml`) → earn loop は 1 turn で 完結する設計なら OK、 不足なら 上げる
- ✅ U130 編集flow: ~/.hermes 直編集 (NOT git) → anicca-genesis に 安全file sync
- 🔍 U7 Grok model id (grok-4.3 = full?) / U59 cron per-job model override / U16 Monitor等価 → 次 batch
SPECEOF
echo "written"; wc -l /Users/operator/anicca/docs/superpowers/specs/2026-06-09-anicca-uncertainty-resolution-QA.md