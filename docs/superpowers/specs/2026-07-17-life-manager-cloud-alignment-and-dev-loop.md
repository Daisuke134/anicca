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

## 5. Align 未決 3 点（Dais 判断待ち）
1. **issue 置き場**: 11 issues は Daisuke134/life-manager に立っているが実装先は anicca-products/apps/life-call。dev loop の issue SSOT をどちらに寄せるか（提案: anicca-products へ transfer、life-manager repo は OSS local 版として凍結）。
2. **connector系のブラウザ**: cloud で Luma 登録/求人応募にはブラウザ必要。Railway に CloakBrowser 無し → browserless/steel.dev 等のリモートブラウザ or Mac mini を worker にする hybrid。要決定。
3. **call コスト方針**: リマインダー=固定 TTS / 会話型=wake のみ、の 2 層化で margin 確保（LM-19 実測後確定）。

## 6. 調査ソース
- issues: `gh issue view 1..11 -R Daisuke134/life-manager` 実読（07-17）。
- cloud: `.worktrees/release-1.9.5/apps/life-call/` 実読（07-17）。
- 電話価格: twilio.com/en-us/voice/pricing/jp（$0.1850/min JP mobile）、retellai.com/pricing、vapi.ai/pricing、bland.ai/pricing（crwl 実測 07-17）。
- time management: paulgraham.com/makersschedule.html、blog.samaltman.com/productivity、calnewport.com/on-metrics-and-resolve、withdouble.com/blog/best-practices-for-calendar-management、snacknation.com/blog/executive-calendar-management、colgate.com（歯科 6mo）、everydayhealth.com（散髪 6-8wk）。
