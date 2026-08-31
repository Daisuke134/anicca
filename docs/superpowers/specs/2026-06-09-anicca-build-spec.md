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
- LOOP1 LIFE (速い、 毎1-5分、 time/位置trigger): 既存 anicca-products mr-bot (lateness_check+realtime_guide) + sutando voice(Charon 1行tweak)。 行動時刻に電話。
- LOOP2 EARN+SELF (遅い、 毎30m-1h、 戦略): sutando proactive-loop + automaton guard。 think→act→observe → earn/self-heal。
- 両方 同じ Hermes(genesis) 上。 cost-governor 跨ぐ。

### Q3: UX 2系統 (同 code github.com/Daisuke134/anicca)
- ① LOCAL (OSS): `git clone → ./install.sh`(名前/電話/位置/calendar/★自分のLLM鍵★) → `./start.sh`。 fuel=自分のサブスク、 compute=自分のMac、 $0。
- ② SUBSCRIPTION (aniccaai.com/install): Telegram 1click → 名前/電話/位置(Live Location)/calendar(OAuth) → Apple Pay $49.99/mo 7日無料 → Stripe webhook → ★Daytona sandbox spawn★ → cloud起動。 fuel=我々の鍵(user設定ゼロ)、 compute=我々のDaytona。 ★ wild-Anicca が稼げたら 自動解約 ★。

### Q4: original 判定 = 全module に named copy元必須
- copy: heartbeat=sutando, guards=automaton, 魂=automaton, 稼ぐmove=Felix, survival-loop=ClawWork, memory/Ralph/Sentry=Felix, voice=sutando, runtime=Hermes, 理論=SSA paper, subscription/Daytona=saas-v1。
- ★ 我々 固有(=唯一 copy元なし) ★: ①「稼ぐ(Felix)+人生管理(sutando)」を 1 agent に合体 ②Anicca=仏教 identity。 = engineering original でなく ★ product 組合せ ★。
- ★ rule: 全 module に copy元の名前を付ける。 名前が付かない=original=罪=即停止して copy元探す。 ★

## 6. UNCERTAINTIES (= 実装前に 全部 解消する。 learn-as-you-go 禁止)

### ★ BLOCKER (= これ未解決なら 全体が崩れる) ★
- UB1. ★ Hermes は SOUL.md/CONSTITUTION.md/HEARTBEAT.md/MEMORY.md を 毎turn auto-inject するか? ★ (= Felix/OpenClaw の bootstrap機能)。 もし NO なら Felix pattern が 載らない → harness 再考 (OpenClaw?) が必要。 → Hermes docs/code 確認必須。
- UB2. ★ Hermes の heartbeat は「LLM agent turn (think→act→observe)」を 回せるか? ★ 現 genesis heartbeat.sh = JSONL書くだけ、 LLM 呼ばない。 = 今のは「死んだ心拍」。 Hermes に「agent を 定期起動する」 mode があるか? なければ どう実装?
- UB3. ★ subscription での「spend」とは何か? ★ Grok OAuth = 定額。 per-token cost = $0 (marginal)。 → automaton の「earn>spend / survival tier / 破産」 metric が 成立しない。 「spend」を 何と定義? (サブスク月額 amortize? rate-limit 残量? compute時間?) → 北極星 metric の 再定義 必須。
- UB4. ★ canonical build repo は どこ? ★ ~/anicca(mother hub) / anicca-genesis(body) / anicca-products(mr-bot spec が ここ)。 earn は genesis、 life は anicca-products。 統合先 1つに 決める。
- UB5. ★ mr-bot (anicca-products, Daytona, sutando-voice) と genesis (Hermes, earn) は 同じ agent か 別か? ★ 2 loop を 1 runtime と言ったが、 実体は 2 repo/2 stack。 どう 1 つにする?
- UB6. ★ 3-tier memory + Ralph loop の OSS copy元は? ★ Felix の実装は $99内(見えない)。 description だけ から作る= original=罪。 → OSS の copy元 (mem0 / letta / ralph技法 原典) を 特定 必須。 無ければ どうする?

### P0 runtime
- U7. 「Grok 4 full」の 正確な model id? genesis = grok-4.3。 grok-4.3 = full か? grok-4 や grok-4-fast は? xai-oauth で 使える model 一覧?
- U8. Hermes config.yaml で fallback を 完全に空(Grokのみ)に できるか? mini に落ちない保証?
- U9. genesis gateway は 今 生きてるか? (前回 launchd 管理外で manual起動だった)。 再起動手順?
- U10. Hermes の cron は SQLite か jobs.json か? edit後 hot-reload?

### P1 魂+台帳
- U11. automaton constitution の どこまで verbatim copy? (Law I-III 全部? "Agentic Sociology" も?)
- U12. 仏教 4諦/8正道 の 正確な文言 + automaton constitution との 統合方法 (順序/階層)?
- U13. ledger.jsonl の 正確な schema (fields)? earn源/spend源/timestamp/balance?
- U14. ledger に書く「earn」の source of truth = Stripe API? wallet? どう集計?
- U15. cost-governor: subscription で tier 判定基準 = ? (U3 と連動)

### P2 heartbeat
- U16. sutando proactive-loop SKILL.md は Claude Code の Monitor tool + /loop 前提。 Hermes に Monitor 等価あるか? なければ cron で どう代替?
- U17. tasks/ + results/ file-queue を Hermes が 読む 仕組み? sutando 固有では?
- U18. quota-budget: Grok サブスクの rate-limit/quota を プログラムで 読めるか?
- U19. LOOP2 (EARN) の heartbeat 間隔 = 何分? (30m/1h/?)
- U20. skip条件 の 正確な list (sutando から copy)?

### P3 earn
- U21. ★ 最初に売る product は 何? ★ (guide on what topic?)
- U22. ★ Anicca 用 Stripe account + API key は 存在するか? ★ env に STRIPE_* あるか? (Felix=Mercury+Stripe)。 無ければ 作成可能か (KYC?)
- U23. Stripe Payment Link を API で 自動生成 できるか? (key の権限)
- U24. X 投稿 = どの account (@aniccaxxx?) + どの経路 (Postiz cmm6d7m... / xpost CLI)?
- U25. revenue-dashboard: aniccaai.com/dashboard は Stripe data を どう pull? 既存 dashboard.json 構造?
- U26. 削除する earn-bounty/payout-ubi/AUTOHEDGE は live cron に 配線されてるか? 削除で 何か壊れるか?
- U27. earn の「即fire E2E verify」= 実際に $ が入るまで待てない。 何を success とする? (Stripe link 生成 + X POST_ID で 一旦OK?)
- U28. info product (guide PDF) の 制作 = 誰が書く? Grok? quality gate?

### P4 memory/self-heal
- U29. 3-tier memory の copy元 (U6)。 決定後: store は SQLite? file? decay の 正確な閾値 (hot/warm/cold 日数)?
- U30. Sentry self-heal = 実 Sentry account/DSN 要るか? それとも log監視で代替?
- U31. Ralph loop copy元 (U6)。 Hermes で coding agent を どう回す?

### P5 mr-bot
- U32. mr-bot の glob bug (lateness_check.py:265) は どの repo/branch? fix 済? (spec PHASE 0 in progress)
- U33. voice stack: Twilio account + Gemini Live key は 存在? bodhi-realtime-agent の deps 揃ってる?
- U34. 位置情報: iOS Shortcut / Telegram Live Location → どう受信・保存 (location_state dir)?
- U35. 電話の発火 trigger = calendar event time? どう route 計算 (Google Maps API key?)
- U36. Charon 男声 1行tweak は 適用済か (PHONE_VOICE_NAME)?
- U37. LOOP1(life, 速い) と LOOP2(earn, 遅い) を 同 Hermes で どう 並走?(別cron?別process?)

### P6 cloud/SaaS
- U38. ★ Daytona account + API key 存在するか? ★ sandbox 単価? per-user spawn の SDK?
- U39. aniccaai.com/install LP は 存在? (saas-v1 spec にあるが build済?)
- U40. Stripe subscription product ($49.99/mo, 7日trial) 作成済? webhook→spawn 配線?
- U41. per-user spawn: Stripe webhook → Daytona sandbox 作成 → user creds 注入 の 具体 flow?
- U42. 「wild-Anicca treasury が稼げたら自動解約」= treasury 残高 どう測定? 解約 trigger 閾値?
- U43. cloud instance の fuel = 我々の どの 鍵? (Grok 1本を 全user 共有? rate-limit 大丈夫?)

### CROSS-CUTTING
- U44. ★ agent は Claude を 一切使わない (Dais厳命)。 voice=Gemini, text=Grok。 全 loop で Claude 不使用 を どう保証? ★
- U45. 編集 flow: anicca-genesis repo を編集 → ~/.hermes に sync? それとも ~/.hermes 直編集? (runtime store)
- U46. private(.openclaw 157cron) は どうする? 並走? 段階移行? 今回 触る?
- U47. no-dry-run の E2E verify 手順 を 各 earn/life action で 定義 (Stripe POST_ID / X POST_ID / 電話 connected)?
- U48. genesis の 既存 12 cron (self-improve/forum/predict 等) は 残す? 削除? 新 heartbeat と 重複?
- U49. SaaS の per-user データ分離 + privacy (位置/calendar/mail) の 扱い?
- U50. 1人目の 実 user = 誰? (Dais 自身? = local mode の dais instance?)

★ rule: 上記 全 U を 「解消済(調査+引用付き)」にしてから 実装着手。 未解消で go = spec-driven 違反。 ★

## 7. UNCERTAINTIES — 完全版 (U51-U150、 全カテゴリ網羅)

### A. RUNTIME / HERMES
- U51. Hermes version pin? auto-update で 壊れるリスク?
- U52. max_turns=30/session で earn loop 足りるか?
- U53. session は restart跨いで 永続するか? (memory)
- U54. external memory provider 設定 (hermes memory)?
- U55. toolsets = 今 hermes-cli のみ。 必要 tool (exec/web/file/stripe) 足す方法?
- U56. Hermes skill format = OpenClaw/Claude Code SKILL.md と 互換?
- U57. gateway_timeout 1800 で 足りるか?
- U58. Hermes が workspace context file を inject する 仕組み (= UB1 詳細)?
- U59. cron は default model 使う? per-job override 可?
- U60. sub-agent / parallel worker あるか?
- U61. xai-oauth token expire する? auto-refresh?
- U62. Grok rate-limited 時 fallback無し = stall。 どう扱う?
- U63. api_max_retries=3 / restart_drain 挙動?

### B. MODEL / LLM
- U64. Grok 4 context window size? SOUL+MEMORY+HEARTBEAT+history 入るか?
- U65. Grok の tool-calling 信頼性 (earn loop で 必須)?
- U66. Grok サブスクの rate-limit (per hour/day)?
- U67. Gemini Live (voice) = 別 key/account/quota?
- U68. life text判断 = Grok / voice = Gemini。 分離OK?
- U69. heartbeat 1回の token budget?

### C. STRIPE
- U70. ★ Stripe account = Anicca専用? Dais個人? KYC主体? ★
- U71. env に STRIPE_* 鍵 ある? test/live どっち?
- U72. SaaS sub に Stripe Connect 要る?
- U73. JP消費税 / invoice 法令対応?
- U74. payout先 (bank/Mercury)? Dais口座?
- U75. webhook endpoint host 先 (apps/api Railway?)
- U76. refund 処理?
- U77. 一回課金(product) と sub($49.99) = 別 product?
- U78. 通貨 (USD/JPY)?

### D. PRODUCT (= 最初に売る物)
- U79. ★ 最初の product の topic/中身? ★
- U80. 誰が書く (Grok)? quality gate?
- U81. format (PDF/Notion/Gumroad)?
- U82. host/delivery (LP/Gumroad/Stripe)?
- U83. LP build (Next.js)? deploy先?
- U84. 購入後の 自動 delivery flow?
- U85. legal: AI が product 売る ToS/liability?

### E. EARN OTHER
- U86. ClawWork loop → 実client: platform (Lancers/Upwork/Fiverr)? account? KYC?
- U87. Lancers account (keiodaisuke+anicca) credential 生きてる?
- U88. Algora/OnlyDust bounty = 残す/捨てる?
- U89. x402 micropay = 残す?

### F. LEDGER/METRIC
- U90. subscription「spend」定義 (= UB3)?
- U91. earn attribution (どの sale が どの action から)?
- U92. ledger 保存形式/場所?
- U93. 北極星 = earn>spend を どの horizon で 判定?

### G. MR.BOT
- U94. 既存 mr-bot code (anicca-products branch) の 完成度?
- U95. glob bug fix 済?
- U96. Twilio account/番号/credits?
- U97. Gemini Live key/quota?
- U98. Google Maps/route API key?
- U99. 位置 ingestion (iOS Shortcut setup / Telegram Live Location parse)?
- U100. Calendar OAuth scope?
- U101. 「何分前に出発」計算 logic (buffer/遅延)?
- U102. voice latency/信頼性?
- U103. multi-user = 各 user 専用 番号?
- U104. daily email = どの address (AgentMail)?
- U105. trust balance = 計算? LP copy だけ?
- U106. 「遅刻時 関係者連絡, user承認」flow?
- U107. 位置/calendar の privacy?
- U108. user が 行動しない時の 再介入 logic (自己改善)?

### H. CLOUD/SAAS
- U109. ★ Daytona account/key/pricing/region? ★
- U110. per-user sandbox: image/resource/cost-per-day?
- U111. sandbox idle時 sleep? cost?
- U112. credential 注入 per user (secure)?
- U113. aniccaai.com/install LP build状態?
- U114. @anicca_bot Telegram 登録? webhook?
- U115. Stripe sub webhook → spawn (apps/api) 配線?
- U116. user data 分離/privacy/GDPR?
- U117. 100 user = 100 sandbox cost 試算?
- U118. 自動解約 treasury 閾値?
- U119. onboarding 正確 flow (name/phone/location/calendar 順)?
- U120. calendar 空/event無し の user?
- U121. cancel/refund flow?
- U122. support/escalation?

### I. MEMORY/SELF-HEAL
- U123. 3-tier memory OSS源 (mem0/letta/?)
- U124. decay 閾値 (hot/warm/cold 日数)?
- U125. storage (SQLite/file)?
- U126. Sentry account/DSN or log-based?
- U127. Ralph loop 源?
- U128. self-mod safety (自分を壊さない)?

### J. REPO/OPS
- U129. canonical repo (= UB4)?
- U130. 編集flow (~/.hermes直 vs anicca-genesis sync)?
- U131. CI/deploy?
- U132. secrets管理 (.env per instance)?
- U133. backup/rollback?
- U134. monitoring/alert (slack)?
- U135. Mac mini disk/cost?

### K. SECURITY/SAFETY/LEGAL
- U136. prompt injection (email/X inbound)?
- U137. agent 支出上限 (wallet/Stripe drain 防止)?
- U138. agent 投稿上限 (X spam → ban 防止)?
- U139. X account 自動投稿 ban risk?
- U140. 自律earn の tax/legal compliance (JP)?
- U141. mr-bot 失敗時 liability (電話漏れ→薬飲み忘れ)?
- U142. user data privacy (位置/calendar/mail)?
- U143. API ToS (X/Stripe/Lancers が AI自動化 許可?)
- U144. 「no human in loop」vs「user承認」の 矛盾 整理?

### L. CONTENT
- U145. platform accounts (note/Zenn/Substack/X/TikTok/YT) 存在?
- U146. TikTok 録画 tooling (screen record cost)?
- U147. viral-writer skill 状態?
- U148. JP vs EN 方針 / posting cadence?

### M. IDENTITY/WALLET
- U149. Anicca wallet (Base/Solana) funded? 要る?
- U150. X @aniccaxxx access / AgentMail inbox / ERC-8004?

★ 合計 150 uncertainty。 全て「解消済(調査+引用)」にしてから 実装。 ★
