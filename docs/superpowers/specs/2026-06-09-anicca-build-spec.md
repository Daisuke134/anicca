# Anicca BUILD SPEC — the first OSS self-funding, life-managing AI (no dry runs)

| Field | Value |
|---|---|
| Date | 2026-06-09 |
| Status | BUILD — implement on genesis (Hermes, free Grok sub) |
| Rule | ★ NO DRY RUN ★ + ★ Grok 4 full (mini禁止) ★ + ★ edit→commit→push 即 ★ |

## 1. 各ソースから CODE する もの (= 具体的、 実装単位)

### FELIX (= core、 production-proven engineering patterns)
| # | Felix の capability | 我々が CODE する module |
|---|---|---|
| F1 | Three-Tier Memory (PARA + timeline + tacit, hot/warm/cold decay, 削除しない) | `memory/` — 3-tier store + decay。 cold は active context から落ちるが永続 |
| F2 | Ralph Loops (coding: 毎iteration fresh context で retry, stall/bloat 防止) | `lib/ralph-loop.sh` — coding agent wrapper |
| F3 | Sentry Auto-Fix (error 監視 → 自己修復) | `skills/self-heal/` — error 検出 → patch → verify |
| F4 | Heartbeat self-healing (crash 検出 → 無確認 auto-restart) | `lib/watchdog.sh` — process 監視 + restart |
| F5 | Session discipline (hanging = #1 失敗、 tmux stable socket で長agent) | `lib/tmux-session.sh` — `~/.tmux/sock` |
| F6 | Verify-before-fail (failure宣言前に git log+diff+process log 必須) | `lib/verify-before-fail.sh` (= HARD RULE 0.31 と同根) |
| F7 | Email Fortress (injection-proof mail) | `skills/mail/` — injection guard 付き |
| F8 | X/Twitter agent (xpost CLI) | `skills/post-x/` |
| F9 | Revenue + metrics dashboard (daily) | `skills/revenue-dashboard/` → aniccaai.com |
| F10 | Ownership prompt: 「何すべき?」でなく「goalに近づくのは?」 | SOUL.md に焼く |
| F11 | Anti-patterns hard rules (mail=command禁止, build前push, git確認前にfail宣言禁止) | SOUL.md / HEARTBEAT.md |

### SUTANDO (= proactive heartbeat discipline)
| # | sutando pattern | 我々が CODE する |
|---|---|---|
| S1 | Proactive loop (5min cron → Monitor で tasks/ 監視 → 毎pass 最高ROI仕事、 idleしない) | `cron` heartbeat + `HEARTBEAT.md` |
| S2 | tasks/ + results/ file-queue (channel ↔ agent) | `state/tasks/` + `state/results/` |
| S3 | Quota-aware pacing (残quota読み → pass毎budget → 仕事深さ調整) | `lib/quota-budget.sh` |
| S4 | Skip条件 (idleが許される唯一の理由を明示、 それ以外は必ず働く) | HEARTBEAT.md |

### AUTOMATON (= agent loop + survival)
| # | automaton pattern | 我々が CODE する |
|---|---|---|
| A1 | ReAct loop: think→act→observe→persist (MAX_TOOL_CALLS=10, MAX_ERR=5, loop-detector MAX_REPEAT=3) | core loop (Hermes が提供、 guard 追加) |
| A2 | Survival tiers (normal/low/critical/dead by balance → 残高低→安model+heartbeat遅) | `lib/cost-governor.sh` |
| A3 | SOUL.md self-authored + genesis-alignment (自己編集、 初期promptとの乖離測定) | `skills/reflect-soul/` |
| A4 | Constitution「Earn your existence / honest work others pay for」(immutable) | CONSTITUTION.md に verbatim copy |
| A5 | spend-tracker (毎inference cost記録) | `state/ledger.jsonl` |

### CLAWWORK (= 経済survival loop、 但しincome=sim → 実client差替)
| # | ClawWork pattern | 我々が CODE する |
|---|---|---|
| C1 | decide(work/learn) → deliverable → submit → evaluate → cost→balance→破産判定 | `lib/earn-loop.sh` (= ledger 連動) |
| C2 | GDPVal 220職 task catalog (AIが出来る仕事一覧 + BLS時給) | `data/work-catalog.json` (参照) |
| C3 | ★ submit を LLM採点でなく 実client(Lancers/Stripe)に差替 ★ | `skills/earn-*/` の出口 |

## 2. ★ Anicca の 美しい・シンプルな architecture ★

```
  ANICCA = 1 heartbeat、 2 仕事 (稼ぐ + 人生管理)、 dry-run ゼロ

  ┌─────────────────────────────────────────────────────────────────┐
  │  HEARTBEAT (every N min、 never idle)         ← sutando S1        │
  │       │                                                          │
  │       ▼                                                          │
  │  THINK → ACT → OBSERVE → PERSIST              ← automaton A1      │
  │       │  (guards: max-tools 10 / max-err 5 / loop-detect 3)      │
  │       │                                                          │
  │  reads ─┬─ SOUL.md      (who am I + earn魂 + ownership) ← A3/A4/F10│
  │         ├─ MEMORY 3-tier (PARA + decay)                ← F1       │
  │         ├─ LEDGER       (earn vs spend = 北極星)        ← A5/C1    │
  │         └─ KANBAN/tasks  (what to do)                  ← S2       │
  │       │                                                          │
  │       ├──► EARN job   (条件: 金が要る)                            │
  │       │      ├ product 作る → Stripe で売る + X 投稿  ← F8/F9     │
  │       │      ├ paid task → 実client(Lancers)に納品   ← C1/C3     │
  │       │      └ revenue を dashboard に                ← F9        │
  │       │                                                          │
  │       ├──► LIFE job   (条件: user が要る)             ← Anicca固有 │
  │       │      └ 10分前到着 / mail先回り / gcal heal               │
  │       │                                                          │
  │       └──► SELF-HEAL  (常時)                          ← F3/F4/F6  │
  │              └ error監視 → auto-fix → git log+diff で verify     │
  │       │                                                          │
  │       ▼                                                          │
  │  COST GOVERNOR (survival tier)                ← automaton A2     │
  │     残高低 → 安いstep / heartbeat遅く。 破産=停止。               │
  └─────────────────────────────────────────────────────────────────┘

  土台 = genesis (Hermes、 Grok サブスク無料) ← 既存、 これに 上を 載せる
  頭脳 = Grok 4 full (mini 禁止)
  出力 = slack + mail 報告 (= dry-run の逆、 実action の証跡)
```

★ 一文 ★: **1つの heartbeat が、 SOUL/記憶/台帳/kanban を読み、 毎回「稼ぐ・人生管理・自己修復」のどれかを 実action で やり、 cost governor で 生存を守る。 dry-run なし。**

## 3. FULL TODO (= ordered、 実装)

```
PHASE 0 — 土台確認 (genesis = Hermes + Grok、 既存)
 T0. genesis 稼働確認 + Grok 4 full に固定 (mini fallback 禁止)

PHASE 1 — 魂 + 台帳 (= 方向と生存)
 T1. CONSTITUTION.md: automaton "Earn your existence" verbatim + 仏教4諦/8正道
 T2. SOUL.md: ownership prompt(F10) + anti-patterns(F11) + life+earn mission
 T3. state/ledger.jsonl: earn vs spend 記録 (A5/C1) — 毎heartbeat
 T4. lib/cost-governor.sh: survival tier (A2)

PHASE 2 — heartbeat 規律 (= never idle, no dry-run)
 T5. HEARTBEAT.md: think→act→observe + 最高ROI選択(S1) + skip条件(S4) + dry-run禁止
 T6. state/tasks + results file-queue (S2)
 T7. lib/verify-before-fail.sh (F6) + watchdog(F4) + tmux session(F5)

PHASE 3 — 稼ぐ engine (= 実金、 dry-run 廃止)
 T8. ★ 既存 earn-bounty/payout-ubi/AUTOHEDGE/dry-run cron を 全削除 ★
 T9. skills/earn-info-product: guide作る→Stripe Payment Link→X投稿→実販売(F8/F9)
 T10. lib/earn-loop.sh: decide→deliver→submit→ledger (C1)、 出口=実Stripe/client(C3)
 T11. skills/revenue-dashboard → aniccaai.com (F9)
 T12. ★ 即1fire → 実 side-effect (Stripe link + X POST_ID) verify ★ (HARD 0.31)

PHASE 4 — 記憶 + 自己修復
 T13. memory/ 3-tier + decay (F1)
 T14. skills/self-heal (F3) + lib/ralph-loop.sh (F2)

PHASE 5 — 人生管理 (= Anicca 差別化)
 T15. skills/life: 10分前 + mail先回り + gcal heal

PHASE 6 — 統合 + cloud
 T16. private(.openclaw)+public(genesis) → 1 base, SOUL env切替
 T17. cloud: DigitalOcean droplet + per-user spawn (SaaS)

CONTENT (並行、 手動、 Dais=editor)
 K1. 解説→実験→正直review: Felix/automaton/sutando/ClawWork/OpenAlice/AutoHedge
 K2. 失敗記事「自律AIに金稼がせて$0だった話」
 K3. 理論: self-sovereign-agent paper 解説
 K4. 旅: 自己資金AIを作る公開実験 (TikTok JP first)
```

## 4. heartbeat の 決定 (= engine vs 中身、 Dais 質問 2026-06-09)

★ heartbeat = 2層 ★:
| 層 | 決定 | 理由 |
|---|---|---|
| ENGINE (鳴らす土台) | ★ Hermes (genesis) ★ | 既に Grok サブスクで 無料稼働中。 載せ替えない |
| 中身 (毎beat何する) | sutando + automaton を copy → HEARTBEAT.md | idleしない最高ROI(sutando) + think→act→observe+survival(automaton) |

各 harness の真実:
- Felix = ★ engine 無し ★ = OpenClaw の上の persona/config (Hermes でも動く)
- automaton = 自前 engine だが ★ API key+USDC 必須 (OAuthサブスク非対応) ★ → 不可
- sutando = 自前 engine だが ★ macOS 専用 (cloud不可) ★ → 不可
- Hermes(genesis) = 自前 engine、 ★ Grok サブスク無料で 既に稼働 ★ → ★採用★
- OpenClaw(Dais private) = 自前 engine、 サブスク対応 (private 側の選択肢)

★ 決定: engine = Hermes(genesis)。 Felix/automaton/sutando の engine は使わない。 中身(規律)だけ copy。 ★

## 5. heartbeat copy元 + 2-loop + UX + original判定 (Dais 4Q 2026-06-09)

### Q1: heartbeat 中身は どこから copy
- ★ sutando `skills/proactive-loop/SKILL.md` を copy ★ (= 公開text、 番号付きloop完成品) + automaton guard (max-tools10/err5/loop3)。 ★ 自分で書く=original=罪、 やらない ★。 Felix の HEARTBEAT は $99内で 見えない→copyしない。

### 2-loop 決定 (= 1 runtime, 2 loop)
- LOOP1 LIFE (速い、 毎1-5分、 time/位置trigger): 既存 anicca-products life-manager (lateness_check+realtime_guide) + sutando voice(Charon 1行tweak)。 行動時刻に電話。
- LOOP2 EARN+SELF (遅い、 毎30m-1h、 戦略): sutando proactive-loop + automaton guard。 think→act→observe → earn/self-heal。
- 両方 同じ Hermes(genesis) 上。 cost-governor 跨ぐ。

### Q3: UX 2系統 (同 code github.com/Daisuke134/anicca)
- ① LOCAL (OSS): `git clone → ./install.sh`(名前/電話/位置/calendar/★自分のLLM鍵★) → `./start.sh`。 fuel=自分のサブスク、 compute=自分のMac、 $0。
- ② SUBSCRIPTION (aniccaai.com/install): Telegram 1click → 名前/電話/位置(Live Location)/calendar(OAuth) → Apple Pay $49.99/mo 7日無料 → Stripe webhook → ★Daytona sandbox spawn★ → cloud起動。 fuel=我々の鍵(user設定ゼロ)、 compute=我々のDaytona。 ★ wild-Anicca が稼げたら 自動解約 ★。

### Q4: original 判定 = 全module に named copy元必須
- copy: heartbeat=sutando, guards=automaton, 魂=automaton, 稼ぐmove=Felix, survival-loop=ClawWork, memory/Ralph/Sentry=Felix, voice=sutando, runtime=Hermes, 理論=SSA paper, subscription/Daytona=saas-v1。
- ★ 我々 固有(=唯一 copy元なし) ★: ①「稼ぐ(Felix)+人生管理(sutando)」を 1 agent に合体 ②Anicca=仏教 identity。 = engineering original でなく ★ product 組合せ ★。
- ★ rule: 全 module に copy元の名前を付ける。 名前が付かない=original=罪=即停止して copy元探す。 ★
