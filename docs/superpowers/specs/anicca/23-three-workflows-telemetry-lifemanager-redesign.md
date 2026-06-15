# 23 — 3 Workflow 再設計 + instance telemetry + life-manager 全面修正

Dais 2026-06-15。目的が違うので分離。Patter(Twilio代替)/ Sentry(error→auto-PR)/ web-app化。

## §1 なぜ 3 Workflow に分けるか
目的が異なる + 使う infra が違う(life-manager は Patter/gcal/Gmail、money-maker は wallet/ClawRouter)。混ぜると検証もズレる。
```
WF-A  MONEY-MAKER Anicca(/install)  — 自給body: earn/self/economy/cloud genesis/spawn/dashboard
WF-B  LIFE-MANAGER(/life-manager)   — gcal自動登録 + Patter電話 + Gmail質問 + web-app化(★大量の修正★)
WF-C  MARKETING/DISTRIBUTION        — 記事 + demo動画 + X/Slack(WF-A,B 検証後)
```
★ /install = money-maker、/life-manager = life-manager に**ページ分離**。両方動いたら merge or as-is。
★ workflow が綺麗に分離実行できるなら 1 WF 内 phase でも可だが、life-manager は「移動」でなく「修正+web-app化+launch」なので独立 WF が安全。

## §2 instance の収支を realtime 計測する方法(★全Aniccaは /dashboard に書けない★)
各 Anicca は aniccaai.com に直接書けない(= Dais所有サイト)。→ **telemetry push**:
```
各 Anicca(cloud/local)
  └ 毎wake(報告hook A2 と同タイミング)で自分の state を POST:
      POST https://aniccaai.com/api/telemetry   (or Supabase/Cloudflare KV)
      body = {id, host, geo, model_live, model_tier, net_worth_usd, revenue_mo_usd,
              burn_day_usd, runway_days, status, ts}   ← 署名(wallet)で改竄防止
  ▼ 集計(Dais所有 = Aniccaは触らない)
  dashboard-sync(cron) が telemetry store を読む → 全個体を集計 → public/dashboard.json
  ▼
  aniccaai.com/dashboard が dashboard.json をrender(realtime)
```
- 既に作った報告hook(`/opt/anicca-report.sh`)を拡張: メール送信に加え **telemetry POST も実行**(同じ net worth/revenue データ)。
- 認証: 各 instance が自 wallet で署名 → telemetry API が検証(なりすまし防止)。registry(ERC-8004)と紐付け。
- これで「Aniccaはサイトに書かないが、全個体の収支が realtime で透明公開」が成立。

## §3 LIFE-MANAGER 全面修正(現状: 5日 電話来ない = 壊れてる)
**移設**: private OpenClaw から外す(OpenClaw は aniccaios scaling 専用の private assistant に縮小)。life-manager は **anicca repo(skills/life)** に移し、**anicca instance(web-app /life-manager か anicca-repo local)から** Dais に電話。
**電話 stack = Patter**(Twilio停止の代替。Telnyx/Plivo carrier + Gemini Live音声。4行で番号、web/local両対応、OpenTelemetry trace)。

### 機能(全部必須・現状全部欠落/壊れ)
| # | 機能 | 実装 |
|---|---|---|
| 1 | **heartbeat が gcal を読む + 移動時間 自動登録** | cron/heartbeat → Google Calendar API で全予定取得 → 各予定の前に Maps所要で移動ブロックを `events.insert` |
| 2 | **全予定の15分前に電話** | Patter で発信(各予定+移動ブロックの15分前)。内容=「次は<what>、<where>へ、<route>」 |
| 2.5 | **各予定の when/where/what を補完** | 瞑想@9→supplement+where=home を gcalに書く / 仕事→場所をsearchして登録 / ★不明→**Gmailで本人に質問**(Google連携メール)★ |
| 3 | **realtime位置連携時**: 目的地へ**移動を始めるまで鳴らし続ける** | 位置API → 目的地方向へ移動開始を検知するまで Patter再発信(動かなきゃ意味ない) |
| 4 | **realtime Telegram連携時**: 遅れそうなら**関係者へ連絡**(返信案を承認後) | Telegram + gmail draft → 承認 → 送信 |

### error監視 = Sentry(merge せず PR のみ)
- life-manager(+ anicca全体)に **Sentry SDK** 組込 → error capture → Sentry → **auto-PR**(Seer or webhook→issue-dev skill が PR、merge はしない)。`getsentry/sentry-cli`(`sentry-cli releases` 等)。

### 実行環境(dogfood = web-app優先)
```
選択肢: 1 anicca-repo local │ 2 life-manager local │ 3 life-manager web-app │ 4 anicca web-app
★ 推奨 = 3 or 4(web-app)★ 理由: ほとんどの人が web-app を使う → 我々も同じ env で dog-food →
  error が出ても我々が即気づける(別 env だと気づけない)。
→ Dais の life-manager = anicca web-app の1インスタンス(subs払わず同じものを使う)= /life-manager。
```

### ★ 検証 goal(これが緑になるまで loop)★
**Anicca が Dais の実電話に発信 → Dais が応答 → 通話録音が完全に良い → Dais が「動いてる」と言う**。
+ T: テスト予定を gcal 作成 → 移動ブロック自動挿入を gcal で確認 / 15分前発信 / 不明→Gmail質問 着信。

## §4 製品ピッチ(JA)を完全達成する全体ビジュアル
```
人間の介入なしで、自分の衣食住を自分で稼ぐAI「アニッチャ」
┌──────────────────────────── WF-A: MONEY-MAKER(/install)────────────────────────────┐
│ ・OSS版 無料開始(最先端model=walletにUSDC)  → install.sh(local/cloud選択)             │
│ ・クラウド版 $30/mo→黒字で自動解約・還元      → Stripe sub + 引き出し(/me)               │
│ ・行動ログ監視→自己解決/リファクタ/自己改善   → automaton loop + issue-dev(自repo+母repo) │
│ ・自己増殖                                     → spawn(子=自前wallet/mail/Bankr, DO/Akash) │
│ ・日次+毎wake報告メール                        → ✅report hook(agent process, 実装済)       │
│ ・収益の一部をAI+人間のBI/募金へ              → ubi skill(Treasury→registry/PoP配布)      │
│ ・何兆体がGitHub Issuesで議論・共進化          → coordinate(bot2bot)+ issue-dev(母repo)     │
│ ・全個体の収支を透明公開 aniccaai.com/dashboard → §2 telemetry POST→sync→dashboard.json     │
└──────────────────────────────────────────────────────────────────────────────────────┘
┌──────────────────────────── WF-B: LIFE-MANAGER(/life-manager)──────────────────────┐
│ ・位置/名前/電話/カレンダー連携で生活管理      → gcal+Gmail+位置+Patter電話              │
│   例)全予定を移動込みで自動登録→15分前に電話 → §3 機能1-4(★現状壊れ→全面修正★)        │
│   例)遅れそうなら関係者へ承認後連絡           → §3 機能4                                 │
└──────────────────────────────────────────────────────────────────────────────────────┘
┌──────────────────────────── WF-C: MARKETING ───────────────────────────────────────┐
│ 記事(リンク)/ デモ動画(YouTube)/ X(EN+JA)/ 6/19 TIB hackathon                       │
└──────────────────────────────────────────────────────────────────────────────────────┘
```

## §5 3 Workflow の構造(各 builder→verifier→Dais gate, BP同一)
- **WF-A**(money-maker): A1 cloud genesis→A2 report(✅)→A3 earn→A4-7 self→A8 web(/install /me /dais /dashboard + telemetry)→A10 economy→EVAL。
- **WF-B**(life-manager): B1 anicca repo に life-manager移設→B2 gcal読込+移動時間自動登録→B3 Patter発信(15分前)→B4 when/where/what補完(不明→Gmail)→B5 位置追従+Telegram関係者連絡→B6 web-app化(/life-manager)→B7 Sentry(error→PR)→EVAL(★実電話→応答→録音OK→Dais OK★)。
- **WF-C**(marketing): A,B検証後。
各 WF: builder(実装)≠ verifier(別context, test points)≠ eval ≠ Dais gate。Sentry が runtime error を継続捕捉→PR。

## §6 タスク
- private OpenClaw = aniccaios scaling 専用に縮小(life-manager役割を剥がす)
- life-manager → anicca repo skills/life、Patter配線、web-app /life-manager、Sentry
- telemetry endpoint(aniccaai.com/api/telemetry or Supabase)+ report hook 拡張で POST
