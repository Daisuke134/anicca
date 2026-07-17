# Life Manager (CLOUD) — 現状実測 + 11 issues + dev loop 設計 align（2026-07-17）

対象 = **cloud web app**（aniccaai.com/life-manager、Telegram `@LifeManagerBotbot`、$20/mo、Railway）。
local 版（`~/Projects/life-manager`、openclaw cron）は claude-p connector loop と共に段階的廃止 → cloud へ収斂。
Goal: 10k MRR → 10M MRR。「Your Dream Life, on Autopilot」= 金・体・心を AI が世話する。

## 1. 実測事実（2026-07-17、4 subagent 調査）

### 1a. Cloud 実体（`.worktrees/release-1.9.5/apps/life-call/` = 本番相当。origin/main とほぼ同一）
- Railway 常駐 1 プロセス（`node server.js`）: Telnyx↔Gemini Live(Charon) 音声ブリッジ + 60s tick scheduler（in-process。Inngest 併設だが `LIFE_RUN_LOOPS` 未設定時は in-process が主）。
- DB = Supabase: `lm_users / lm_wake_log / lm_travel_log / lm_ask_log / lm_route_cache / lm_user_places / lm_stripe_events`。migrations は `apps/life-call/migrations/*.sql` 手動適用。
- Google 連携 = Composio managed OAuth（`lib/transport/calendar-composio.js`）。`LIFE_TRANSPORT` で composio/gog 切替（#74 convergence 設計済み）。
- 実装済み: wake/pre-event call（T-10 firm / T-5 harsh、Telnyx+Gemini Live）、travel block 自動挿入（`lib/travel.js`、route cache 付き）、ask（`lib/ask.js`、Gemini+Places、不明時 TG/mail 質問）、遅刻連絡（`lib/notify.js`、**ユーザー申告時のみ**）、Telegram onboarding 5 段階、Stripe webhook（`lm_users.paid` 唯一 writer）。
- Gmail 連携 = v1 で意図的に省略。web 単独 onboarding = コードあり "Coming soon" gate。
- Web = Netlify（`apps/landing`、GHA `netlify-deploy.yml` のみ）。`/life-manager`=marketing、`/lm?tg=<chatId>`=実 onboarding。
- 収益実態（07-03 memory）: subs=0、lm_users=3（全部 Dais テスト）。
- **⚠ dev branch は life-call を丸ごと欠く（release/1.9.5 比 84 files +11542 行遅れ）。現 checkout（feature/clip-rewards）にも無い。本番コードの正 = origin/main。**

### 1b. Local 版との gap（cloud に無いもの）
- `locate/locate.js`（live-location motion gate）→ 自動遅刻検知が cloud に丸ごと欠落（cloud notify は受動型）。
- 3 段階 call（15/10/5 calm→firm→harsh）→ cloud は 2 段階（意図的簡略化、コメント明記）。

### 1c. claude-p 既存 loop（~/profitable-claude、コピー元 harness）
- 方式: launchd StartCalendarInterval plist → bash → `claude --model sonnet --dangerously-skip-permissions -p "<埋込prompt>"` 単発呼び出し（tmux 常駐 + CronCreate 自己登録は非 durable と実測済みで廃止）。
- `skills/life-manager/`（10:15 JST）= SELF-MARKETING ONLY（IG+Reddit 実投稿、logged-out 可視性再検証、ceo-report.py → `ledgers/loop-evaluations.jsonl`、Telegram 必須報告）。
- `skills/connector/`（07:50 fill-gaps + 09:10 独立日報）= Luma/connpass イベント発見→実登録 25 件 CONFIRMED。`register_and_calendar.py` が `event_apply_wrapper.py` の "registered" を経ないと CONFIRMED 行を書けない構造ゲート。cold outreach はコード済みだが `directives.json blockedActions:["outreach_send"]` で送信停止中（outreach.jsonl 0 行）。
- Dais 固有 hardcode: 実名/メール/平日 9-17 JST/東京/AI・crypto トピック（プロンプト直書き）→ cloud 汎用化時は per-user config 化。
- 転用パターン: ①launchd→bash→claude 単発 ②state/*.jsonl 台帳 + 冪等 init ③CLIProxyAPI auth fallback ④独立日報 plist ⑤blockedActions + I-confirm ゲート。

### 1d. 電話コスト実測（call-researcher、URL 引用付き）
| 経路 | 実測単価 | 180 call/月（6/日×1min）概算 |
|---|---|---|
| Twilio `<Say>` 固定 TTS | JP mobile **$0.1850/min**、JP local 番号 $4.75/mo（twilio.com/en-us/voice/pricing/jp 実測） | **$40–50/mo** |
| Retell（会話込み） | $0.07–0.31/min 全込み（retellai.com/pricing） | $12.6–55.8/mo |
| Vapi | hosting $0.05/min + telephony/LLM 実費（vapi.ai/pricing） | $50–80/mo |
| Bland | Start $0.14/min（bland.ai/pricing） | $25.2/mo + telephony |
| **現行実装 = Telnyx + Gemini Live (Charon)** | **未実測（TODO LM-19）** | — |
- JP 発信注意: Tokyo edge 必須（国際 GW 経由は Caller ID 剥奪、twilio.com/en-us/guidelines/jp/voice）。
- **margin リスク**: $20/mo サブに対し会話型 call を毎日数分×2 回焼くと通話コストがサブ額に迫る。方針案 = T-10/T-5 リマインダーは固定 TTS（安い）、会話型は wake call / 応答必要時のみ。要実測（LM-19）。

### 1e. Elite time management → autopilot 既定ルール（23 rules、全引用は調査ログ参照。核）
- カレンダー衛生: タイトル=文脈+目的 / 場所欄必須 / 色=種別固定 / 週次で時間配分チャート化（Double, SnackNation）。
- 哲学: maker/manager 判定、maker は半日ブロック死守（PG makersschedule）/ 朝一は予定禁止（Altman）/ deep work は実ブロック（Newport）/ 60min デフォルト禁止（Altman）/ 雑務はバッチ枠。
- 信頼: 移動前後に buffer 自動挿入 / 週 1 no-meeting day / 非必須依頼はテンプレ自動辞退。
- 体: 歯科 6 ヶ月毎（高リスクは 3 ヶ月、Colgate）/ 散髪 6–8 週毎（Everyday Health）→ **聞かずに自動予約、事後通知**。
- ループ: 夜間メトリクス記録 / 変更前に直近 2-3 ヶ月カレンダー監査 / 日次 digest / 四半期で年配分見直し。
- 「聞かずに実行」5 デフォルト: 非必須会議自動辞退・buffer 自動挿入・朝一保護・打診は終業前固定枠へ・定期メンテ自動予約。

## 2. 11 issues（Daisuke134/life-manager、全 open）× cloud 対応

| # | 内容 | 状態 |
|---|---|---|
| 10 | pre-event call 鳴らない | P0。cloud は実装済みのはず → Railway scheduler / lm_wake_log / Dais row を実測デバッグ |
| 11 | 場所を毎回聞く | P0。search-before-ask: web+Places で推定→closed question「XX は YY 開催?」のみ。open question 禁止（MUIT 事件） |
| 2 | travel wedge | ratio>=0.8 計測+台帳 |
| 3 | wake/leave/sleep/lateness guard | locate.js motion gate を cloud へ port |
| 1 | 最小質問 onboarding | context graph >=5 fields 推論 |
| 4 | Luma/connpass environment pull | connector 汎用化して cloud embed |
| 5 | connector/podcast outreach | per-user config + blockedActions ゲート |
| 6 | feedback→issue loop | 実装済み主張（commit 339d5e0)→ 検証 |
| 7 | product marketing loop | 既存 claude-p marketing loop を signups 追跡まで拡張 |
| 8 | cost/outcome ledgers | product API cost + outcome 台帳 |
| 9 | personal CEO | 設計文書のみ（スコープ外） |

## 3. TODO（TaskList 登録済み。P0→P3）

| ID | P | タスク | done 条件 |
|---|---|---|---|
| LM-1 | P0 | **claude-p dev loop**（`~/profitable-claude/skills/life-manager-dev/`、launchd、sonnet）: TG feedback→issue→worktree→spec 1p→TDD→impl→fresh adversary→main merge→Railway deploy 実測検証→台帳+TG 報告 | loop が issue 1 件を無人で fix→deploy→検証し TG 報告 |
| LM-2 | P0 | #10 call 不発火の真因実測+fix | 実イベントで T-10/T-5 着信、lm_wake_log に provider_call_id |
| LM-3 | P0 | #11 search-before-ask + closed question 化 | location_questions_per_physical_event<=0.2 |
| LM-4 | P1 | #2 travel metrics + 台帳 + TG 報告 | ratio>=0.8 計測可視 |
| LM-5 | P1 | #3 自動遅刻検知（locate.js port）+ leave/sleep call | 出発時刻超過→自動検知→承認→関係者連絡 |
| LM-6 | P1 | #1 最小質問 onboarding + context graph | 推論 fields>=5、blocking 質問<=1 |
| LM-7 | P1 | #8 cost/outcome ledger | api-cost 行>0、business_summary json |
| LM-8 | P2 | #4 connector cloud 汎用化（event discovery/apply、per-user ideal） | 台帳に実登録+gcal_event_id |
| LM-9 | P2 | #5 outreach（cold mail/podcast/meeting）config-gated | 送信は per-user opt-in、証跡台帳 |
| LM-10 | P2 | apply engine（jobs/accelerators/院。MadsLorentzen/ai-job-search copy+tweak） | 実応募 1 件の証跡 |
| LM-11 | P2 | health autopilot（歯科 6mo/散髪 6-8wk 自動予約 + Gmail から休眠課金サービス発掘=脱毛） | 自動予約 1 件+gcal 登録+事後 TG 通知 |
| LM-12 | P2 | daily affirmation + 夜 digest | 毎日 TG 送信、user 文脈個別化 |
| LM-13 | P2 | elite-defaults engine（23 rules: buffer 自動挿入/朝一保護/no-meeting day/色・タイトル衛生/週次時間チャート） | 3 rules 以上が実カレンダーに自動適用 |
| LM-14 | P3 | #6 feedback→issue loop 検証 | 実 TG feedback→issue 生成を実測 |
| LM-15 | P3 | #7 marketing loop→cloud signups 追跡 | signups_tracked=true |
| LM-16 | P3 | #9 personal CEO 設計文書 | doc 存在のみ |
| LM-17 | P3 | local→cloud convergence 完了 + openclaw 廃止準備 | local 専用機能ゼロ、SSOT=cloud repo |
| LM-18 | P1 | branch hygiene: dev に life-call 同期（main→dev） | dev で life-call ビルド可 |
| LM-19 | P1 | Telnyx JP 単価 + Gemini Live audio 従量実測、per-user margin model | $/user/mo 実測値が台帳に載る |

## 4. Architecture（現状→目標）

```
現状 (prod = origin/main)
User ─ TG @LifeManagerBotbot ─┐        aniccaai.com (Netlify)
User ─ ☎ Telnyx JP番号 ───────┤        ├ /life-manager  marketing (QR→TG)
                              ▼        └ /lm?tg=…  onboarding (gated)
        Railway: apps/life-call (node server.js 常駐)
        ├ scheduler.js 60s tick        ├ lib/billing  Stripe $20/mo
        ├ lib/wake  T-10/T-5 call      ├ lib/telegram-* onboarding/reply
        ├ lib/travel [Travel]挿入      ├ lib/ask  場所解決+質問
        ├ lib/notify 遅刻(受動のみ)    └ transport: Composio OAuth | gog
                              │
        Supabase (lm_users, lm_wake_log, lm_travel_log, …)

目標: 同一プロセスに autopilot modules 追加 + 外側に dev loop
        ├ connector/  event·outreach·apply (per-user ideal, gated)
        ├ health/     歯科·散髪·休眠サービス自動予約
        ├ mind/       affirmation + digest
        ├ policy/     elite-defaults 23 rules
        └ ledger/     api-cost + user-outcome

Dev loop (Mac mini, claude-p sonnet, launchd 日次):
feedback(TG)→issue→spec 1p→TDD→impl→adversary→main→Railway deploy→実測検証→TG報告
```

## 4b. E2E テスト経路（Dais 承認済み 2026-07-17）
- Dais の Telegram にログイン可 → dev loop は **実 Telegram で本物の E2E**（onboarding / feedback / call 確認 / 報告受信）を回せる。
- gated web onboarding（/lm?tg=…）もブラウザ E2E 可。
- E2E = 実 side-effect（TG 実受信・実 call 着信・gcal 実書込）を自分の目で確認するまで done と言わない。

## 4c. Dais align 回答（2026-07-17 追記）
- **feedback source = 全ユーザー**（Dais は one of them）。dev loop は Telegram intake 経由の全 user feedback を issue 化して食う。iteration speed = god speed。
- **vision 正本 = `docs/loop-engineering/46-life-manager-northstar-and-personal-loops.md`**（北極星: 財務/身体/精神 autopilot、local=OSS 無料 / cloud=subscription で**中身は同じコード**、profitable-claude の earn loops は最終的に Life Manager へ統合、FUTURE-MSG=メール triage 実返信、FUTURE-AFFIRM=mem0 型記憶で super-tailored affirmation）。
- **進め方**: 今日まず人力で全部一周 fix（プロセスを知らずに自動化はできない）→ そのプロセスを dev loop skill に焼いて無人化。
- **Mac mini worker 案は棄却**（スケールしない）。browser 基盤は cloud。`docs/loop-engineering/45-scale-hosting-and-session.md` が既に結論: 脳（agent プロセス）と手（browser）を分離、手 = **steel-browser（7.3k★, session/proxy/anti-detect/lifecycle が agent 向け）第一候補、browserless（13.5k★, 枯れた concurrency/lifecycle）が成熟度対抗、Browserbase = マネージド従量（Contexts で profile 永続）**。→ 2026-07-17 pricing 込み再調査完了、結論 = **Steel 一本**（下 §4d）。

## 4d. Browser 基盤の結論（2026-07-17 実測、引用付き）
**勝者 = Steel（steel-dev/steel-browser、7,345★、Apache-2.0）を丸ごと採用。混ぜない。**
- 決め手: ①OSS + **Railway 公式 self-host ガイドあり**（docs.steel.dev/overview/self-hosting/railway） ②cloud（steel.dev）と self-host が**同一 API**（`steel-sdk` npm、Playwright `.launch()`→`.connect(wss://)` 1 行差し替え）= MVP→scale を env 切替で書き直しゼロ ③Profiles API で user 毎 cookie/localStorage 永続（creds 永続の要件） ④従量が透明: Launch $0.10/hr（$30 無料 credit）/ Scale $250/mo+$0.08/hr（docs.steel.dev/overview/pricinglimits）。
- 段階コスト（2 session/user/日 × 5min = 5 browser-hr/user/月）: **MVP(1-10 users)=$0**（無料 credit 圏内）/ Growth(10k users, 50k hr)≈$4-5k/mo / Scale(1M)=self-host クラスタ+Enterprise バーストのハイブリッド、compute 床 ≈$100k/mo。
- 対抗比較: Browserbase Developer $20/mo 100hr込（成熟 Agent API、Stagehand 23.5k★だがコア非公開）/ browser-use Stealth $0.02/hr（最安の生ブラウザ、マネージド機能なし）/ Browserless 13.5k★（license=NOASSERTION、商用要確認）/ Anchor（認証特化 OmniConnect、最高価格）/ Lightpanda（AGPL copyleft + 描画なし=予約サイト不向き）/ Kernel（unikernel snapshot は魅力、料金非公開）。
- ⚠ 1M 規模では browser-hr 代より **residential proxy 帯域が支配的コスト**。対策 = サイト毎エスカレーション（datacenter/no-proxy で開始→ブロック実測したサイトのみ residential+stealth）。Growth 段階で pilot 実測してから Scale 精密試算。
- 統合: 1 job = 1 session = 1 context（user 間共有禁止）、session_id を job レコードに保存、user パスワードは暗号化保存→context へ直接注入（stdout/キーストローク中継禁止）、vendor concurrency 上限 = worker pool の back-pressure。
- **repo 収斂の提案**（Dais 判断待ち→ LM-20）: `apps/life-call` を `Daisuke134/life-manager` へ移し、**1 codebase = local(OSS, gog)/cloud(Railway, Composio) を `LIFE_TRANSPORT` env で切替**（#74 設計の完成形）。anicca-products は landing のみ残す。今日の P0 fix は現行 prod 経路（anicca-products/main）でやり、migration は fix 後。

## 5. Align 未決 3 点（Dais 判断待ち）
1. **issue 置き場**: 11 issues は Daisuke134/life-manager に立っているが実装先は anicca-products/apps/life-call。dev loop の issue SSOT をどちらに寄せるか（提案: anicca-products へ transfer、life-manager repo は OSS local 版として凍結）。
2. **connector系のブラウザ**: cloud で Luma 登録/求人応募にはブラウザ必要。Railway に CloakBrowser 無し → browserless/steel.dev 等のリモートブラウザ or Mac mini を worker にする hybrid。要決定。
3. **call コスト方針**: リマインダー=固定 TTS / 会話型=wake のみ、の 2 層化で margin 確保（LM-19 実測後確定）。

## 7. LM-2 真因（2026-07-17 実測確定。仮説ではない）
- **主因 = Telnyx 残高 $0.43 < preflight 最低額 $0.50（`lib/dial.js:39` hardcode）**。scheduler は Dais のイベントを正しく検出し departure 計算・dedup claim まで全通過、`placeCall()` の残高チェックで毎回弾かれ Telnyx 発信 API に到達すらしない。Railway 実ログ: `[scheduler] dial failed T-10 uid=lm_784ad279-: telnyx balance too low ($0.43)` 反復。2026-06-18 頃から約1ヶ月、アラート無しで全通話が無音で握り潰され続けた（lm_wake_log 334 行）。
- **副次バグ**: `claimWake()`（scheduler.js:123）が `placeCall()`（:126）より先に dedup INSERT し、dial 失敗時にロールバックしない → 失敗した (event,level) は**永久に再試行されない**。残高補充だけでは過去分は救えない。fix = dial 失敗時に claim 行を削除（dedup は維持）+ 残高低下時 Telegram アラート。
- **残高補充済み（2026-07-17 実測）**: Telnyx `GET /v2/balance` $0.43 → **$25.00**。auto-recharge 有効化（threshold $5 / refill $20、`PATCH /v2/payment/auto_recharge_prefs` 200）。API のみで完了、ブラウザ不使用。→ **preflight は今クリア = 次の対象イベント（location≠home）から T-10/T-5 call は本番で発火するはず**。過去に burn 済みの claim は fix branch merge まで復活しない。E2E = Dais の次の実イベントで着信確認（LM-2 の残り）。
- **旧仮説の訂正**: 07-17 朝の「cron 未登録が真因」仮説は **local 版の話で cloud には非該当**（cloud は in-process scheduler が正常稼働中と実測）。
- **⚠ セキュリティインシデント（2026-07-17）**: 調査 subagent が env 抽出時に Railway 全 secret（SUPABASE_SERVICE_ROLE_KEY / TELNYX_API_KEY / GEMINI / GROQ / RESEND / STRIPE_WEBHOOK_SECRET / LM_CALL_SECRET / LM_UID_SECRET / LM_TELEGRAM_BOT_TOKEN / LM_TELEGRAM_WEBHOOK_SECRET / UNIPILE_TOKEN / COMPOSIO_API_KEY / LM_INBOUND_SECRET）を tool 出力に平文表示。ルール（漏洩即 rotate）に従い**全キー rotate = LM-21 P0**。漏洩範囲はローカル transcript のみだが例外にしない。

## 8. TO-BE（2026-07-17 align 確定。実装は superpowers workflow で 1 件ずつ、都度 browser E2E）

### 8a. TO-BE folder tree（repo 収斂後 = Daisuke134/life-manager が product SSOT）
```
life-manager/
├ apps/
│ ├ web/                # landing + onboarding（現 apps/landing の LM 部分を移設）
│ └ core/               # 現 apps/life-call。Railway 常駐
│   ├ server.js         # webhooks: telegram / stripe / call ws bridge
│   ├ scheduler.js      # 60s tick
│   ├ engines/
│   │ ├ time/           # travel blocks · wake/leave/sleep calls · 自動遅刻検知(locate port)
│   │ ├ place/          # search-before-ask resolver（open question 禁止）
│   │ ├ connector/      # events(Luma/connpass) · outreach(gated) · apply(jobs/accelerators)
│   │ ├ health/         # 歯科6mo · 散髪6-8wk · 休眠課金サービス発掘
│   │ ├ mind/           # affirmation(mem0 記憶) · 夜 digest
│   │ ├ policy/         # elite-defaults 23 rules
│   │ └ ledger/         # api-cost · user-outcomes
│   ├ context/          # per-user context graph（ideal/home/work/regulars、Gcal+Gmail 推論）
│   ├ browser/          # steel-sdk（1 user task = 1 session = 1 profile）
│   ├ lib/              # telegram / billing / dial / transport(composio|gog)
│   └ migrations/
├ docs/                 # E2E-SPEC + specs
└ .github/
dev loop（別 repo）: ~/profitable-claude/skills/life-manager-dev/（全 user feedback→issue→fix→deploy→E2E→TG 報告）
```

### 8b. 10k MRR への道（$20/mo 基準）
| 段階 | payers | MRR | 何で到達 |
|---|---|---|---|
| S0 今 | 0 | $0 | P0/P1 fix + Dais dogfood が毎日 green（電話鳴る/travel入る/質問≤closed）= 売れる状態 |
| S1 | 10 | $200 | 既存配布 loop 起動済み（lm-video TikTok/IG cron 3本 + marketing loop IG/Reddit 日次）→ landing→TG 転換を実測・改善。build-in-public |
| S2 | 100 | $2k | onboarding 摩擦ゼロ（#1）、outcome 実感（週次「今週 AI がやったこと」）で churn 抑制、紹介導線 |
| S3 | **500** | **$10k** | 500×$20。必要流入試算: TG 転換 20%・訪問→TG 3% → 累計 ~8万訪問 = content loop の物量で到達可能圏 |
| S4 | — | $10M | ①Autopilot tier $49-99（connector/apply/health 全部入り）で ARPU↑ ②profitable-claude 統合 =「AI があなたの金を稼ぐ」（earn 額の % 課金）③EN 展開。500k 相当 subs or blended ARPU $50×200k |
- 前提: churn は outcome で殺す（電話が鳴った/予約された/応募された、が毎週見える）。$0 の真因は配布ゼロ（07-03 実測: wrong-link + zero distribution）でありプロダクト欠陥ではない。

### 8c-2. dev loop は段階導入（Dais 決定 2026-07-17 追記。「completely turn on」はスコープ外）
| Phase | loop に許すこと | 禁止 | 昇格条件 |
|---|---|---|---|
| **D0（開始点）** | feedback/issue 読解 → spec 1p + patch を feature branch に push → **PR 作成まで**。TG に PR URL 報告 | merge / deploy / migration 適用 | — |
| D1 | dev(staging) への merge + smoke E2E 実行 | prod promote | D0 で PR 品質が安定（人間 merge が連続で無修正） |
| D2 | prod auto promote（議論自体を D1 実績後に再開。**今はスコープ外**） | — | staging green 連続 10 PR 無事故の実測 |
全 phase 共通 guardrails: `directives.json` blockedActions（secret/billing/破壊的 migration/force push 禁止）、path allowlist = `apps/life-call/**` のみ、1 pass = 1 issue、Telegram 必須報告。connector loop の実証済み I-confirm/blockedActions パターンを流用。

### 8c. 実行方式（Dais 決定 2026-07-17）
- **実装は superpowers workflow**（brainstorming→writing-plans→worktree→subagent-driven→verification）で 1 issue ずつ。
- 検証 = 自分で実 browser/実 API E2E（adversary/vcsdd subagent は Dais が明示した時のみ）。
- 1 fix = 1 browser 検証 = 1 TG/call 実測、を積む。lm2-fixer の先行 branch `fix/lm-call-dial-burn`（commit f82010e65、push 済み・未 merge・worktree `.worktrees/lm-call-fix` 保持）: releaseWake（dial 失敗時に claim 解放、travel.js の unclaimTravel と同型）+ 低残高 TG アラート（新 env `LM_ADMIN_TELEGRAM_CHAT_ID` 要設定、6h throttle）。npm test 全 18 suite 173 tests pass 実測。superpowers 実行時にこの branch を素材として review/採用判断する（merge は superpowers の verification 後のみ）。

## 9. 全疑問・不確実性リスト（2026-07-17。A=Dais 決定待ち / B=実測すれば解ける / C=リスク監視）
| # | 種 | 問題 | 俺の意見（BP 根拠） |
|---|---|---|---|
| Q1 | A | repo 収斂（LM-20）: code の恒久住所 | life-manager repo 1 codebase、env 切替。monorepo 分割は drift 実証済み |
| Q2 | A | Gmail scope を onboarding 必須にするか（今は calendar のみ、v1 で意図的省略） | **必須にする**。health/休眠発掘/context graph/予約 OTP 全部 Gmail 依存。Gcal+Gmail = product の燃料 |
| Q3 | A | dev loop の auto-merge→本番 auto-deploy を許すか | staging(Railway environments)→smoke E2E→prod promote の2段。canary = Dais 自身。直 prod は課金ユーザーに事故る |
| Q4 | A | user feedback→GitHub issue、repo は public。PII が issue に載る | issue は要約+匿名化のみ、生 feedback は private store。個人情報を public repo に書かない |
| Q5 | A | call 2層化（T-10/T-5=固定TTS、会話=wakeのみ） | 賛成前提で LM-19 実測後確定 |
| Q6 | A | trial 設計（今 $20 即課金のみ） | 7日 trial or 初回 call 無料。S1 で決定、今は不要 |
| Q7 | B | Railway の deploy trigger（git auto-deploy? 手動?）未確認 | merge 前に必ず実測して spec に書く |
| Q8 | B | Telnyx+Gemini Live の per-min 実コスト（LM-19） | 実 call 数本で請求実測 |
| Q9 | B | Composio の per-user 課金 at scale | pricing 実測。高ければ自前 Google OAuth app へ（審査週単位なので Composio で時間を買うのは正しい） |
| Q10 | B | issue#6（feedback→issue）実装済み主張の検証（LM-14） | 使う前に実測。tool 出力捏造の前科がある領域 |
| Q11 | B | lm-video/marketing cron のリンク先が現 funnel か | 1回実測 |
| Q12 | C | 遅刻検知（LM-5）の位置情報源が cloud に無い（local は locate.js） | v1 = TG live location 要求 or call で「出た?」確認。motion gate は後 |
| Q13 | C | 予約系（歯科/散髪）の日本の実態 = HotPepper/EPARK/電話 | v1 = Steel で HotPepper/EPARK web 予約。電話予約は Telnyx outbound AI voice で後日（武器は既にある） |
| Q14 | C | 他人として行動する法務/ToS（メール送信・応募・予約） | 外向き action は per-user opt-in gate（connector の blockedActions パターン）+ onboarding で明示同意 |
| Q15 | C | Google OAuth 審査（Gmail sensitive scope、自前化する時 CASA） | Composio 経由の間は回避。自前化は S3 以降の課題 |
| Q16 | C | ask.js に web 検索 tool が無い（MUIT の根本） | Railway 上は Gemini grounded search か Programmable Search API を足す（crwl はローカル専用） |
| Q17 | C | dev loop の実行場所 = Mac mini（launchd）は LOCAL vs CLOUD 軸に逆行 | v1 Mac mini（存在する武器）、黒字後 cloud VM へ。GHA 追加は禁止ルールなので使わない |
| Q18 | C | 1M user 時の単一プロセス scheduler / Supabase | 1k user までは今の設計で持つ。早すぎる最適化はしない |
| Q19 | B | LM-21 rotate の実行タイミング | superpowers 実装開始の直前に ops として一括実行 |
| Q20 | C | E2E 用 TG が Dais 実アカウント依存 | 専用 test user アカウントを作って CI 化（dogfood と分離） |

## 10. Q1–Q20 解決（2026-07-17 実測+外部BP。§9 の問いに対する確定回答）

### 10a. 決定（A 系）
| Q | 決定 | 根拠 |
|---|---|---|
| Q1 | life-manager repo へ収斂（LM-20、P0 fix 後） | drift 実証済み |
| Q2 | **Gmail = Unipile（Composio ではない）**。onboarding に optional gmail stage 追加（skippable） | codebase 自身が証拠: `apps/landing/netlify/functions/unipile-connect.js:3-6`「Composio managed Google app は restricted gmail scope 未認証で consent が HARD-BLOCK（実ブラウザ実証）」。Unipile 経路は配線済み（unipile-connect→unipile-notify→`lm_users.gmail_account_id`→`lib/transport/mail-unipile.js`） |
| Q3+Q7 | **main push = 本番自動 deploy（実測: repo=anicca-products, branch=main, root=apps/life-call, watchPaths=apps/life-call/**, NIXPACKS）**。staging 環境は既存だが life-call 未配線 → LM-18 = 「staging に life-call を配線」（dev branch 追跡、secrets は staging 専用値=テスト bot/Telnyx、本番使い回し禁止）。flow: feature→PR→dev(staging auto)→smoke E2E exit 0→PR dev→main(prod auto)。main 直 push 運用は止めて PR 経由へ | railway status --json 実測 + docs.railway.com/environments |
| Q4 | issue = 匿名化要約のみ、生 feedback は private store | PII を public repo に置かない |
| Q5 | call 2層確定: T-10/T-5/リマインダー = 固定 TTS **$0.002–0.006/回**、会話型（wake/例外）= Gemini Live **≈$0.029/min（Gemini 側のみ、audio 32tok/s、in $3/M out $12/M）** = 10倍差 | ai.google.dev/gemini-api/docs/pricing + telnyx.com/pricing/voice-api（TTS $0.000003/char〜） |
| Q6 | trial は S1 で決定（保留） | 今は配布ゼロが真因 |
| Q14 | 外向き action（送信/応募/予約）= per-user opt-in gate + onboarding 明示同意 | connector blockedActions パターン |
| Q17 | dev loop v1 = Mac mini launchd、黒字後 cloud VM | GHA 追加禁止ルール |
| Q18 | 1k user までは現行単一プロセスで持つ | 早すぎる最適化禁止 |
| Q19 | LM-21 rotate = superpowers 実装開始の直前に一括 ops | — |
| Q20 | E2E 用専用 test TG user を作成（dogfood と分離） | — |

### 10b. 実測結果（B 系）
| Q | 実測 |
|---|---|
| Q8 | 会話型 1min ≈ $0.03–0.04（Telnyx JP 正確単価は動的ウィジェットで未取得 → 実 call 請求で実測 = LM-19 残）。固定 TTS 30s ≈ $0.002–0.006 |
| Q9 | **Composio 8/15 改定: 超過 $0.249/1k → $4/1k（16倍）**、Pro $29/mo=5万call。今や Composio 依存は calendar のみ（Gmail=Unipile）。scale 対応: calendar scope は sensitive（審査 10 営業日、CASA 不要）なので自前 OAuth 化が現実的な逃げ道。Gmail は Unipile 継続で restricted 審査+CASA（6週+費用非公開）を回避 | composio.dev/updated-pricing, support.google.com/cloud/answer/13463817 |
| Q10 | issue#6 = **IMPLEMENTED-NEVER-RAN**。feedback-to-issue.py 実在・tests 12/12 real pass（ただし gh は mock）。`state/issues.jsonl` 0 行 = 本番実行ゼロ。しかも daily.sh の scope lock で明示 OFF（2026-07-11）。issues #1-11 は別経路（agent の直 gh issue create）で作られた。→ LM-1 が本配線する |
| Q11 | funnel リンクは現行で正しい（landing→t.me/LifeManagerBotbot?start=lp、IG 投稿 cta=aniccaai.com/life-manager 実確認）。**穴 = TikTok lm-video: caption にリンクゼロ + bio link 管理なし = クリック経路ゼロ**（LM-22 新設）。Reddit は 07-11 から shadowban 中 |
| Q13 | **HotPepper Beauty / EPARK歯科 に予約 API 無し（実測: Recruit Web Service はグルメのみ、epark.jp/webservice 404）**。gh 上に実予約自動化例なし。→ **日本の予約 = 電話が本命 = Telnyx outbound + AI voice で店に電話する**（LM-11 の設計確定。武器は既存） |

### 10c. Patch sketches（LM-3/LM-5/LM-6 用。file:line 実読済み、UNVERIFIED 明記）
**共通前提（LM-23 新設）**: codebase に callback_query 対応が皆無（`lib/telegram.js:29-38` parseUpdate は message のみ、setWebhook も allowed_updates=["message"]）。Q16 の [はい/いいえ] と Q12 の [出た/まだ] の両方が依存。
```js
// lib/telegram.js — setWebhook に allowed_updates: ["message","callback_query"]、
// answerCallbackQuery 追加、parseUpdate が {kind:"callback", data, callbackQueryId} を返す分岐追加。
// server.js:241 の /telegram handler に if (u.kind==="callback") 分岐（prefix ask:/leave: で route）
```
**Q2 Gmail stage（LM-6 の一部）**: `lib/telegram-onboard.js:12-18` computeStage に `if (!row.gmail_account_id && !row.gmail_skipped) return "gmail"`（skippable、"スキップ" text で `gmail_skipped=true`）。migration: `ALTER TABLE lm_users ADD COLUMN IF NOT EXISTS gmail_skipped boolean NOT NULL DEFAULT false;`。`mail-unipile.js` に searchInbox(query) 追加（UNVERIFIED: Unipile 検索 param 名 q/search、docs 確認要）。
**Q16 search-before-ask（LM-3）**: `lib/ask.js:257-277` の ask 分岐で、送信前に `agentSearchCandidate(event)` — Gemini に google_search grounding tool + submit_candidate functionDecl（UNVERIFIED: grounding tool key 名、現 docs 確認要）+ Gmail searchInbox 結果を context 投入。候補あり → closed question「“{event}” は {candidate} で開催ですか？」+ inline [はい/いいえ]（callback_data `ask:yes/no:{event.id}:{replyToken}`）。metric: `ALTER TABLE lm_ask_log ADD COLUMN IF NOT EXISTS resolved_from text;`（location_field|description|gmail|web_search|user_answer）。
**Q12 leave-check（LM-5 v1、GPS 無し）**: ①`scheduler.js:81-92` buildStreamUrl の署名 ctx に uid+eventKey を追加（call site :125）②`server.js:152-169` ctxFromReq で検証 ③`server.js:438-444` Telnyx start frame で `lm_wake_log.answered_at` を PATCH ④scheduler の WAKE_LEVELS ループ後に T-0 分岐: T-5 が answered なら TG「出た？」[出た/まだ]（claimWake を `{uid}|{startIso}|leave` の擬似 level で再利用）⑤`leave:no` or 10min 無応答 → `lib/notify.js:36` sendLateNotice 直呼び（classifyLate 不要と実読確認）。migration: `ALTER TABLE lm_wake_log ADD COLUMN IF NOT EXISTS answered_at timestamptz, ADD COLUMN IF NOT EXISTS notified_late_at timestamptz;`（注: lm_wake_log の CREATE TABLE は migrations に無い=Supabase 直作成、IF NOT EXISTS で安全）。
**UNVERIFIED 3 点 → 2 点解決（07-17 Opus 裏取り済み）**:
1. ✅ Gemini grounding key = **`google_search`**（snake_case、REST v1beta generateContent。`googleSearch` は JS SDK 表記、`google_search_retrieval` は 1.5 世代の廃止名）。functionDeclarations 併用は公式 tool-combination ページ実在が一次証拠（制約文言は実装時に同ページ確認）。出典: ai.google.dev/gemini-api/docs/generate-content/google-search
2. ✅ Unipile 検索 param = **`search`**（件名+本文 free-text。Microsoft/IMAP では from/to/before 等との併用が invalid_request になる制約あり）。出典: developer.unipile.com/reference/mailscontroller_listmails
3. ✅ schema 実測（07-17 Supabase REST）: lm_wake_log = **(id, uid, event_key, called_at)** 337行 / lm_ask_log = (id, uid, event_id, asked_at, reply_token, answered_at) 149行 / lm_travel_log = (uid, event_key, leg, created_at) 82行。→ LM-5 の answered_at/notified_late_at migration は必須確定。
**V8 解決**: `git log 49135e3a..origin/main -- apps/life-call` = 0件 → prod は最新コード稼働中。
**V9 解決**: travel ratio ベースライン ≈ **88%（物理 8 件中 7 件に travel block、過去14日 59 行）** — 既に目標 0.8 超え。LM-4 の主задача = 計測の仕組み化と維持。
**V1 傍証（07-17 Railway 実ログ）**: 残高補充後、実イベント「KAG AI WEEK」で T-5 call が実成立: `carrier connected → Gemini Live opened → recording started → carrier closed in=6016 out=716 gotAudio=true`。$0.43 時代の dial failed 連発と対照。**V1 確定（07-17 20:0x JST、Dais 実証言）: 電話は鳴った = dial 経路完全復旧。ただし「出たが AI が無言」= 新バグ LM-24（音声 out 経路）。**issue #10 は「鳴らない」→「鳴るが無言」に進行。
**（誤記訂正 07-17 夜）**: 先の「out=716 bytes ≈ 無音」は誤り。`out=` は **frame 数カウンタ**（server.js:455 state.outFrames）= Gemini は 716 チャンク分**実際に喋って送信済み**。無音の原因は最終ホップ（Telnyx が発信者へ再生する所）。
**LM-24 RCA（07-17、コード全読）**: path = Gemini(PCM16@24k) → geminiPcm24ToTwilioMuLaw(8k μ-law, call-logic.js:161) → routeGeminiMessage(call-bridge.cjs:109) → `{event:"media",media:{payload}}` JSON を**ペーシング無しで**送信 → Telnyx(`stream_bidirectional_mode:"rtp"`, codec PCMU, stream_track inbound_track)。仮説: **H1 = ペーシング/フレームサイズ不整合**（commit 090b21094 で旧 playWakeClip の 20ms/frame ペーシングが削除され、等価ロジック未復元 — 状況証拠濃厚）/ H2 = "rtp" mode の wire format が JSON media frame でない可能性 / H3 = 送信試行 ≠ 実再生（Telnyx streaming イベント未購読）。fix 案: 160byte(20ms) 分割 + 20ms ペーシング復元（H1）、Telnyx docs 裏取りで H2 判定（調査中）。
**⚠ 追加漏洩（07-17 RCA 中）**: GEMINI_API_KEY 全体 + TELNYX_API_KEY 一部 + TELNYX_CONNECTION_ID/PHONE_NUMBER が別 agent の tool_result に平文出力。LM-21 の rotate 対象と同一（追加作業なし、rotate 必須度が上がった）。
**Unipile 料金確定（ページ埋込 JS `pricesUSD` 実測）**: 最低 $55/mo（10 acct 込み）→ 11-50 $5.50 → 51-200 $5.00 → 201-1k $4.50 → 1k-5k $4.00 → 5k+ $3.50 /acct/mo。無料枠なし（7日 trial のみ）。**⚠ margin 直撃: $20/mo サブの 17.5〜27.5% が Gmail 接続代**。手当て: ①Gmail stage は skippable 設計（済）②Gmail 必要機能を上位 tier（$49-99 Autopilot）に寄せて原価を tier 側で吸収 ③scale 後は自前 Gmail OAuth（restricted+CASA 6週）で $/user を潰す。出典: unipile.com/pricing-api

## 11. 未検証レジスタ（2026-07-17 時点で「まだ実測していない」もの。検証されるタスクを明記）
| # | 未検証 | いつ検証 |
|---|---|---|
| V1 | 残高復旧後、実イベントで本当に電話が鳴るか（post-fix の実着信を1度も観測していない） | LM-2 done 判定 = Dais の次の外出 or テストイベント |
| V2 | Telnyx JP 携帯向け実単価（動的ウィジェットで未取得） | LM-19 実 call 請求 |
| V3 | Gemini Live 実コスト/call（試算 $0.029/min は公表単価からの計算のみ） | LM-19 |
| V4 | Gemini grounding tool の key 名 / Unipile 検索 param / lm_wake_log 原型 schema（3点、patch 実装の前提） | LM-3/LM-5 実装冒頭 |
| V5 | **Unipile の pricing**（Gmail の生命線になったのに料金未調査） | LM-6 着手前に調査 |
| V6 | Composio 現契約プランと現在の月間 call 数（8/15 値上げの影響額が計算できない） | LM-19 と同時に実測 |
| V7 | Steel は研究採用のみ、実 PoC ゼロ（session 作成/profile 永続/JP サイト anti-bot 実挙動） | LM-8 着手前に 1 PoC |
| V8 | prod が最新 main を走っているか（最終 deploy 実測 = 07-04 commit 49135e3a。以降 apps/life-call に commit が無いだけか要確認） | LM-21 rotate 時に確認 |
| V9 | travel_blocks_ratio の現在値ベースライン（0.8 目標に対し今いくつか未計測） | LM-4 冒頭 |
| V10 | staging 用 test TG bot / test Telnyx 番号 / test user 一式が未作成 | LM-18 |
| V11 | mem0 採用（affirmation 記憶層）は文献根拠のみ、hands-on ゼロ | LM-12 着手前 |
| V12 | local locate.js の motion gate 実装詳細（v1 は GPS 無し設計にしたので port は v2） | LM-5 v2 |
| V13 | Reddit shadowban appeal 結果（07-11 から応答なし） | 週次で確認 |
| V14 | Stripe 課金フロー実 E2E（subs=0、本物の他人の決済を一度も観測していない） | S1 初売上 = 最初の実検証 |

### §11 更新（2026-07-17 夜）: V1✅(鳴った/無言=LM-24へ) V4✅ V5✅ V8✅ V9✅。残存+新規:
| # | 未検証 | いつ |
|---|---|---|
| V2/V3 | Telnyx JP 実単価 / Gemini Live 実コスト | LM-19 |
| V6 | Composio 現契約プラン + 月間 call 実数 | LM-19 |
| V7 | Steel 実 PoC ゼロ | LM-8 前 |
| V10 | staging 用 test bot/番号/user 未作成 | LM-18 |
| V11/V12/V13/V14 | mem0 hands-on / locate.js 詳細 / Reddit appeal / Stripe 実決済 | 各タスク時 |
| **U15** | **LM-24 真因（無言 call）**: bridge 診断ログ待ち。codec/ws close code/Gemini 応答生成のどれか未特定 | 診断報告→superpowers fix |
| U16 | Gemini google_search + functionDeclarations 併用の制約文言（tool-combination ページ本文未読） | LM-3 実装冒頭に 1 crwl |
| U17 | **Unipile は Gmail+Calendar を 1 アカウント扱い → Composio calendar を Unipile に統合すれば二重払い解消できる可能性**（$5.5 に calendar 込みなら Composio 解約可）。Unipile calendar API の機能十分性未検証 | LM-6 設計時に検証 |
| U18 | LM-21 rotate の実行 runbook リスク: 13 キー原子的更新・TG webhook secret 再登録・rotate 中の数分ダウン許容度 | LM-21 冒頭で runbook 化 |
| U19 | dev loop D0 の launchd headless auth（CLIProxyAPI fallback は connector で実証済みだが新 instance では未走行） | LM-1 初回パス |

## 12. E2E テストシナリオカタログ（QA 正本。全部 no-mock 実機、FAIL→fix→再走を PASS まで）
実行原則: 実 gcal イベント + 実 TG + 実着信 + Supabase 実 row で判定。mock/dry が payload に出たらやり直し。各シナリオ = 「仕込み → 期待 → 証拠の場所」。

### E-CALL（LM-2/LM-23/LM-5）
| # | シナリオ | 期待 | 証拠 |
|---|---|---|---|
| C1 | location≠home の実イベント（+25min）作成 | T-10 firm + T-5 harsh が実着信 | lm_wake_log 2行 + 実際に鳴る |
| C2 | location 無しイベント | call 発火しない（wake-filter で除外） | lm_wake_log 0行 |
| C3 | location=home のイベント | 発火しない（travel-only 既定） | 同上 |
| C4 | 終日イベント | 発火しない | 同上 |
| C5 | 電話に出ない | 再 dial はしない（level 毎1回）、T-0「出た？」は出ない（answered 無し） | answered_at null |
| C6 | T-5 に出た → T-0 | TG「出た？」[出た/まだ] が来る | callback row |
| C7 | 「まだ」タップ or 10min 無応答 | 遅刻連絡フロー（sendLateNotice） | notified_late_at + 実メール |
| C8 | イベントが call 前に削除/移動 | 旧時刻で鳴らない、新時刻で鳴る | lm_wake_log の event_key |
| C9 | Telnyx 残高を意図的に $0.50 未満（staging）| dial fail → claim 解放 → 残高回復後の次 tick で再試行 + 低残高 TG アラート1通（6h throttle） | staging ログ |
| C10 | 深夜イベント（tz 跨ぎ/JST 前提崩し） | 正しい JST 時刻に発火 | called_at のタイムスタンプ |
| C11 | back-to-back 2連イベント | 各イベントに独立して T-10/T-5（計4 call）or 設計上の抑制が仕様通り | lm_wake_log 4行 |
| C12 | paid=false / calendar 未接続 user | 一切発火しない | 0行 |

### E-ASK（LM-3: search-before-ask）
| # | シナリオ | 期待 | 証拠 |
|---|---|---|---|
| A1 | 「MUIT 集会」等、web で場所が特定できる曖昧タイトル | 質問無しで解決 or closed 質問「XXで開催ですか？[はい/いいえ]」 | resolved_from=web_search |
| A2 | Gmail に確認メールがあるイベント（Luma 登録等） | Gmail から解決、質問ゼロ | resolved_from=gmail |
| A3 | 完全に解決不能（造語タイトル・情報ゼロ） | open 質問は許容される最後の1形態のみ（自由記述 fallback）、頻度 ≤0.2/物理イベント | lm_ask_log 集計 |
| A4 | closed 質問に「いいえ」 | 自由記述で聞き直し → 回答が location に書き戻る | gcal event 更新 |
| A5 | 同名イベント複数会場（例: スタバ） | home/work/履歴から最寄り推定して closed 質問 | 候補の妥当性 |
| A6 | 英語イベント | 言語追従 | 質問文言語 |
| A7 | 同一イベントに2度質問しない | dedup | lm_ask_log 1行のみ |

### E-TRAVEL（LM-4）
| # | シナリオ | 期待 |
|---|---|---|
| T1 | 物理イベント → 🚆ブロック自動挿入、ratio≥0.8 | lm_travel_log + gcal 実表示 |
| T2 | イベント移動 → 旧 travel ブロック更新/削除（orphan 残さない） | gcal 実確認 |
| T3 | 90min 以内 back-to-back → origin=前イベント場所 | route の origin |
| T4 | 徒歩圏 vs 電車圏で mode 妥当 | route 内容 |
| T5 | Directions API 障害 → 質問でなく skip+ログ（無限質問しない） | ログ |

### E-ONBOARD（LM-6）
| # | シナリオ | 期待 |
|---|---|---|
| O1 | 新規 user /start → 完了まで blocking 質問 ≤1 + connector 接続のみ | 実 TG 通し |
| O2 | Gmail「スキップ」→ 後から接続可能 | gmail_skipped=true でも全機能（Gmail 依存以外）動く |
| O3 | OAuth 途中離脱 → 再 /start で続きから | stage 復元 |
| O4 | 決済失敗/離脱 → paid=false のまま、課金前に機能開始しない | Stripe test |
| O5 | context graph: 接続後 24h で home/work/かかりつけ ≥5 fields 推論 | lm_user_places |

### E-HEALTH（LM-11）/ E-CONNECTOR（LM-8/9/10）
| # | シナリオ | 期待 |
|---|---|---|
| H1 | Gmail に歯科履歴あり → 6ヶ月経過で AI が実電話予約 → gcal + 事後 TG | 通話録音 + gcal |
| H2 | 店が電話に出ない/満枠 → 再試行 or 代替提案、無限 call しない | call ledger |
| H3 | 履歴ゼロ → 近所の店を提案（勝手に契約はしない） | TG 提案 |
| H4 | 休眠課金（脱毛等）を Gmail から発掘 → 予約提案 | 発掘根拠の引用 |
| N1 | ideal 合致イベント発見→登録→gcal、本業時間と二重予約しない | applications ledger |
| N2 | outreach: opt-in OFF の user では draft 止まり、送信ゼロ | outreach ledger 0 send |
| N3 | 応募フォームで CAPTCHA/ログイン壁 → 諦めず tier 順試行、無理なら理由付き報告 | 試行ログ |

### E-OPS（常時）
| # | シナリオ | 期待 |
|---|---|---|
| P1 | Railway 再起動が tick 中に発生 → 二重 call しない（claim atomic） | lm_wake_log unique |
| P2 | 偽 TG webhook（secret 不一致）→ 401 | curl 実測 |
| P3 | 偽 ws ctx（署名改竄）→ 拒否 | curl 実測 |
| P4 | Supabase 一時障害 → クラッシュせず次 tick 回復 | ログ |
| P5 | staging deploy → smoke E2E green の時だけ main PR | CI exit code |

### 回し方（LM-1 dev loop に焼く）
1. 各 fix の PR 前に該当グループを実機で全走 → FAIL したら fix → 再走、**PASS まで merge しない**。
2. シナリオ実行は test TG user + staging（V10）で行い、C1 級の「本物の Dais 着信」は dogfood として本番でも1本走らせる。
3. 新しい失敗を見つけたらこの表に行を足してから直す（表に無いバグは存在しないことになる）。

## 13. 実コスト実測（2026-07-17 cost-prober、実 API レスポンス）
| 項目 | 実測値 | 含意 |
|---|---|---|
| **Telnyx JP 実レート** | **$0.002/分**（本日実通話 3 件の billed CDR、60 秒切上げ。record_type=call-control で取得） | Twilio 机上比較（$0.185）の 1/90。**電話代は margin 問題にならない**（6call/日でも月 ~$0.4/user）。相場より異常に安いので二重チェック推奨とだけ注記 |
| Telnyx 残高 | $24.84 | 補充+auto-recharge 生存確認 |
| Gemini Live 概算 | 121 秒通話で ≈$0.06（32tok/s × $3/$12 per 1M。★実トークン未ログ=推測モデル★） | 会話 call の支配コストは Gemini 側。それでも 2 層化後は月 $1-3/user 圏 |
| **Composio polling 経済** | **46,800 call/月/user 下限**（wake tick 60s ×1440/日 + travel 48 + ask 72、**キャッシュ皆無を実読確認**）。usage/billing API は存在しない（OpenAPI 72 パス全走査 0 件、ダッシュボードのみ） | **Free(20k) を 1 user で突破。100 user = 4.68M call/月 ≈ 旧価格 $896/mo、8/15 新価格なら万ドル級。→ 構造 fix 必須（LM-25）** |
- **結論: コスト危機は「電話」ではなく「カレンダー polling」。** Unipile はリクエスト無制限・per-account 課金（"No additional cost per request"）なので、U17 の完全置換可能判定と合わせ **Unipile 一本化（$5.5/user に Gmail+Calendar 込み）+ event cache** が経済的必然。
- 未測（正直）: Composio 現契約プランと今月実使用量（dashboard のみ）/ Gemini 実課金額（Cloud Console のみ）→ LM-19 でブラウザ実測。

## 6. 調査ソース
- issues: `gh issue view 1..11 -R Daisuke134/life-manager` 実読（07-17）。
- cloud: `.worktrees/release-1.9.5/apps/life-call/` 実読（07-17）。
- 電話価格: twilio.com/en-us/voice/pricing/jp（$0.1850/min JP mobile）、retellai.com/pricing、vapi.ai/pricing、bland.ai/pricing（crwl 実測 07-17）。
- time management: paulgraham.com/makersschedule.html、blog.samaltman.com/productivity、calnewport.com/on-metrics-and-resolve、withdouble.com/blog/best-practices-for-calendar-management、snacknation.com/blog/executive-calendar-management、colgate.com（歯科 6mo）、everydayhealth.com（散髪 6-8wk）。
