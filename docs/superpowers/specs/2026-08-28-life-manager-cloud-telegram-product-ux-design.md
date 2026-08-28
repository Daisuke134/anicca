# Life Manager Cloud Telegram-First Product UX Design

状態: APPROVED — on-time coreを先に完成させ、自由会話は後続phaseとして追加する

正本範囲: public QRから始まる初回体験、日常のTelegram体験、cloud/self-host共通境界、将来の会話runtime

実装契約と現在地:

- on-time coreのMUST/DO NOT → `2026-08-26-life-manager-cloud-on-time-core-design.md`
- atomic implementation order → `../plans/2026-08-28-life-manager-cloud-on-time-core-finish.md`
- 測定済みstatusとreceipt → `.superpowers/sdd/2026-08-26-life-manager-cloud-on-time-core/progress.md`

## 1. Telegramが製品で、Webは3分の設定画面に限定する

Telegramが製品である。

Life Manager Cloudは、ユーザーが予定表や乗換アプリを何度も開かなくても、次の予定へ時間どおり動ける状態を作る。日常の主画面はTelegramと電話で、Webは初回設定、接続状態、課金確認にだけ使う。

MVPではGoogle Calendarを予定の保存先として1回接続する。ユーザーはGoogle Calendarを毎日開く必要はない。Calendarそのものを不要にするには、後続phaseでTelegramから予定を作成・変更する会話機能を追加する。

```mermaid
flowchart TD
  QR[友達がpublic QRを読む] --> BOT[TelegramでLife Managerを開始]
  BOT --> APP[準備する Mini App]
  APP --> CAL[1/4 Calendarを接続]
  CAL --> HOME[2/4 自宅を登録]
  HOME --> NOTIFY[3/4 Telegram通知をON]
  NOTIFY --> PHONE{4/4 電話も使う?}
  PHONE -->|使わない| READY[3日trial開始]
  PHONE -->|使う| CALL[番号入力と明示opt-in]
  CALL --> READY
  READY --> VALUE[次の予定と最初の通知時刻を表示]
  VALUE --> DAILY[以後はTelegramと任意の電話だけ]
```

## 2. 初回画面は一画面一判断にする

迷わせない。

Telegramの署名済みactorがtenant identityになる。Supabase loginは表示しない。Google画面はCalendar consentの1回だけ開く。Telegram profileに名前があれば名前入力も表示しない。

### 2.1 QRから最初の価値まで

```text
┌─────────────────────────────┐
│ Telegram                    │
│                             │
│ Life Manager                │
│ 遅刻しないための準備を      │
│ 3分で終わらせます。          │
│                             │
│ [ 準備する ]                 │
└─────────────────────────────┘
                │
                ▼
┌─────────────────────────────┐
│ Life Manager          1 / 4 │
│                             │
│ カレンダーをつなぐ           │
│ 予定を読み、必要な時だけ      │
│ Telegramで知らせます。       │
│                             │
│ [ Calendarを接続 ]           │
└─────────────────────────────┘
                │
                ▼
┌─────────────────────────────┐
│ Life Manager          2 / 4 │
│                             │
│ 住んでいる場所               │
│ [ 東京都新宿区……………… ]    │
│                             │
│ [ 次へ ]                     │
│ 位置共有中は現在地を優先      │
└─────────────────────────────┘
                │
                ▼
┌─────────────────────────────┐
│ 準備できました ✓             │
│                             │
│ 次の予定                     │
│ 08:40  MUIT 出社             │
│                             │
│ ✓ 移動時間を自動追加          │
│ ✓ 出発5分前に乗換を送信       │
│ ✓ 電話ONならT-10/T-5に着信    │
│                             │
│ 無料期間  残り3日             │
│ [ Telegramへ戻る ]           │
└─────────────────────────────┘
```

### 2.2 画面契約

| 画面 | 主操作 | 表示してはいけないもの |
|---|---|---|
| Telegram `/start` | `準備する` | uid、chat ID、token、Google login |
| Calendar | `Calendarを接続` | Supabase login、別のaccount作成 |
| Home | 住所入力 | background GPSを取得しているという表現 |
| Notifications | `通知を有効にする` | 電話同意との抱き合わせ |
| Phone | 入力またはskip | 入力しただけでcall ON |
| Call | `電話で確認する`またはskip | default opt-in |
| Ready | 次予定、提供価値、trial期限 | 必須checkout、未検証の成功表示 |

## 3. 日常は三つの先回りだけに絞る

通知は三つだけでよい。

ユーザーが日常的に受け取るのは、移動block、Telegram乗換、任意の電話である。設定画面を開かせる通知や、価値のない定期メッセージは送らない。

```mermaid
sequenceDiagram
  participant U as ユーザー
  participant LM as Life Manager Cloud
  participant GC as Google Calendar
  participant TG as Telegram
  participant TX as Telnyx

  LM->>GC: [Travel] blockを自動作成
  Note over LM,GC: Google event IDをreceiptとして保持
  LM->>TX: 出発T-10 call
  TX-->>LM: call ID + signed webhook
  LM->>TX: 出発T-5 call
  TX-->>LM: call ID + signed webhook
  LM->>TG: 次予定 + provider由来の実乗換
  TG-->>LM: message ID
  LM->>LM: replay時はdurable claimで追加effect 0
  U-->>TG: 必要な時だけ設定変更または位置共有
```

### 3.1 Telegram本文

```text
🚆 次は 08:40「MUIT 出社」

08:14 出発 → 08:40 到着予定
目的地: MIRSUBISHI UFJ INFORMATION TECHNOLOGY

08:18 信濃町駅
中央・総武線 → 四ツ谷駅
丸ノ内線 → 赤坂見附駅
徒歩 6分 / 乗換 1回

[今から出る] [位置情報を送る] [通知設定]
```

表示するのはproviderが返した事実だけである。出口、最適車両、混雑を推測しない。元eventのtitle/locationは表示とclaim identityに残し、経路計算だけにautofill済み住所を使う。

## 4. 既存coreを守り、自由会話はsidecarとして足す

置き換えない。

on-time coreは決められた時刻に同じ結果を出す必要がある。LLMの自由判断をscheduler、dedupe、provider receiptへ混ぜない。将来の会話runtimeは、ユーザーの依頼を既存toolへ翻訳する入口として追加する。

```mermaid
flowchart LR
  subgraph CHANNELS[ユーザーが触る場所]
    TG[Telegram]
    MINI[Telegram Mini App]
    WEB[Web dashboard]
  end

  subgraph CLOUD[Life Manager Cloud]
    EDGE[Railway webhook / panel]
    ID[Telegram署名 → tenant UID]
    DB[(Supabase\n設定・trial・ledger)]
    CORE[Deterministic on-time core]
    CHAT[将来: conversation sidecar]
    TOOLS[許可されたLife Manager tools]
  end

  subgraph PROVIDERS[公式effect/readback]
    GC[Google Calendar]
    ROUTE[Transit / Google Route]
    TX[Telnyx]
    API[Telegram Bot API]
    STRIPE[Stripe]
  end

  TG --> EDGE
  MINI --> EDGE
  WEB --> EDGE
  EDGE --> ID --> DB
  DB --> CORE
  CORE --> GC
  CORE --> ROUTE
  CORE --> TX
  CORE --> API
  STRIPE -->|verified webhookだけ| DB
  TG -. Phase 2の自由会話 .-> CHAT
  CHAT --> TOOLS --> CORE
  CHAT -. DB/providerへ直接書かない .-> DB
```

### 4.1 OpenClawMU/Hermesの採用境界

OpenClaw本体はsingle-operator Gatewayである。Hermesはcloud VMからTelegramへ返答できる。OpenClawMUはtenant別session、memory、sandbox、cronを追加する。いずれも会話runtimeの候補だが、Life Managerのtenant、billing、effect ledgerの正本にはしない。

Phase 2で行うのは、固定SHAのOpenClawMUまたはHermesを隔離sidecarとして1 tenantで比較するspikeである。採用条件は次の四つに限定する。

1. Telegram actorから渡されたLife Manager UID以外を選べない。
2. Calendar、電話、Telegram送信、課金を直接実行できない。
3. 全effectがLife Managerのintent/claim/readback/receiptを通る。
4. sidecar停止中もon-time coreが通常どおり動く。

## 5. cloudとself-hostはdomain toolだけを共有する

cloudとlocalを一つのprocessへ統合しない。予定選択、出発時刻、route整形、effect keyの作り方を共通domain toolとして共有する。保存先と実行ownerは製品ごとに分ける。

```mermaid
flowchart TB
  SHARED[共有domain tools\n予定選択・時刻・route・effect key]

  subgraph HOSTED[Cloud product]
    RAIL[Railway]
    SUPA[(Supabase)]
    MULTI[複数tenant]
  end

  subgraph LOCAL[Self-host product]
    DAEMON[local daemon]
    LSTATE[(local state)]
    ONE[一人のowner]
  end

  SHARED --> RAIL --> SUPA --> MULTI
  SHARED --> DAEMON --> LSTATE --> ONE
```

local loopを一括移植しない。ユーザー価値が確認された機能を一つずつtool contractへ切り出し、cloud adapterを追加する。

## 6. trialは価値を体験した後に1回だけ課金を求める

Calendar consent、home、notificationsが揃った瞬間に、serverが`now + 3 days`を一度だけ保存する。phoneとcall opt-inはtrial開始の条件にしない。trial中はpaid userと同じon-time coreを使う。

期限切れ後はexternal effectを止め、Stripe checkoutを含むupgrade Telegramを最大1回送る。延長はしない。再scan、再onboarding、client時計、localStorageのどれも期限を変えられず、Stripe webhookだけが`paid`を書ける。

```mermaid
stateDiagram-v2
  [*] --> Setup
  Setup --> Trial: Calendar + home + notifications
  Trial --> Paid: verified Stripe webhook
  Trial --> Expired: server deadline到達
  Expired --> Expired: scheduler effect 0
  Expired --> Paid: verified Stripe webhook
  Expired --> UpgradeSent: Telegram message IDを1回記録
  UpgradeSent --> UpgradeSent: replay effect 0
  Paid --> Paid: scheduler継続
```

## 7. 証拠がそろうまで「完成」と表示しない

証拠が先である。

```mermaid
flowchart LR
  INTENT[effect intent] --> CLAIM[Supabase atomic claim]
  CLAIM --> SEND[providerへ1回送る]
  SEND --> READBACK[provider公式readback]
  READBACK --> RECEIPT[durable IDを保存]
  RECEIPT --> REPLAY[同じ入力を再評価]
  REPLAY --> ZERO[追加effect 0]
```

| ユーザー価値 | 完了証拠 |
|---|---|
| 移動block | Google Calendar event IDとstatus |
| T-10/T-5電話 | Telnyx call ID、signed webhook、Supabase wake ledger |
| T-5乗換 | Telegram message ID、route provider、travel ledger |
| tenant onboarding | Telegram initData、別UID、cross-actor read 0 |
| trial | Supabase期限、trial中effect、期限後effect 0 |
| 課金 | Stripe webhook event ID、paid readback |
| deploy | GitHub Deployment、Railway health、exact SHA |

## 8. 実装順はlaunch coreとconversationを混ぜない

```mermaid
flowchart TD
  A[Active 1\nTask 12 return誤帰属を閉じる] --> B[Active 2\n3日trialを実装]
  B --> C[Active 3\nPR merge + exact SHA deploy]
  C --> D[Active 4\n別Telegram actor QR E2E]
  D --> E[Active 5\n新しいfuture eventでprovider E2E]
  E --> F[Active 6\nreplay-zero + controlled event cleanup]
  F --> LAUNCH[友達betaを開始]
  LAUNCH --> SPIKE[Phase 2\nOpenClawMU/Hermes sidecar spike]
  SPIKE --> CHAT[自由会話を1 toolずつ追加]
```

Active TODOの測定済み状態と最新の一手はprogress.mdだけに置く。Phase 2はActive 1–6がprovider evidence付きで完了するまでproduction codeへ入れない。

## 9. Superpowersを毎回同じ順序で使う

```mermaid
flowchart LR
  GOAL[Goal\nユーザー価値とDone] --> DESIGN[Brainstorming\n設計承認]
  DESIGN --> SPEC[Spec\n正本を1つ]
  SPEC --> PLAN[Writing plans\natomic TODO]
  PLAN --> RED[TDD RED]
  RED --> GREEN[最小GREEN]
  GREEN --> REVIEW[Fresh read-only review]
  REVIEW --> VERIFY[Provider E2E + replay-zero]
  VERIFY --> STATE[Progress更新]
  STATE -->|次の1件| RED
```

primaryだけがspec、plan、progress、完了判定を更新する。workerは割当code/testだけ、reviewerはexact commitのread-onlyとする。各sliceはPonytail fullで既存再利用を先に通す。

## 10. 採用する設計と棄却する設計

| 論点 | 採用 | 棄却 |
|---|---|---|
| 主UI | Telegram | 常用Web dashboard、新しいmobile app |
| 初回identity | Telegram署名actor | raw query ID、Supabase Google login |
| Calendar | consent 1回、以後background | 毎日のCalendar操作 |
| 電話 | phone任意、別の明示opt-in | phone入力を同意扱い |
| trial | server-owned 3日、1回だけ | localStorage、再登録延長、usage meter新設 |
| 会話runtime | launch後のsidecar | on-time coreの置換、provider直接write |
| cloud/local共有 | domain tool contract | process/state/credentialの一体化 |
| 完了判定 | provider ID + durable ledger + replay-zero | local test、log文、process liveness |

## 11. Current launchの範囲外

- 自由会話、voice note、画像理解、email作業、browser作業。
- OpenClawMU/Hermesのproduction導入。
- Gmail connector、native event store、Google Calendar不要化。
- local loopの一括cloud移植。
- 新しいroute provider、agent memory DB、sandbox、quota service。
- annual plan、価格変更、usage-based billing。

## 12. 一次資料

- Poke: https://poke.com/ — messagingを主画面にし、接続serviceとmemoryから先回りする製品例。
- Town WhatsApp: https://www.town.com/features/whatsapp — text、photo、voiceから質問、research、routineを実行する製品例。
- OpenClaw fixed README: https://github.com/openclaw/openclaw/blob/90a9622a6cf5740ab4b9f6f65d9081d47ffbc4e4/README.md — single-operator Gateway境界。
- Hermes fixed README: https://github.com/NousResearch/hermes-agent/blob/a619db663374ab31f3c3e3c9197247e0636c4069/README.md — cloud VMとTelegram gateway境界。
- OpenClawMU multi-tenancy: https://docs.neullabs.com/openclawmu/multi-tenancy/ — tenant別session、memory、sandbox、cron。
- OpenClawMU fixed tenant registry: https://github.com/neul-labs/openclawMU/blob/f874b00ebf30b668ed7819f5ede2e0595433155d/src/tenants/registry.ts — file-backed tenant registry実装。
