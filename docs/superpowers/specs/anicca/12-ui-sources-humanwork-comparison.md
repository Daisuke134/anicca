# 12 — UI(/dashboard /me /install) + コピー元の仕組み + 人間の仕事 + 比較表

Dais 2026-06-14 の5問への回答。関連: [11-franklin-akash-fulltodo](11-franklin-akash-fulltodo.md) / [AMBIGUITIES-QA](AMBIGUITIES-QA.md)

## ① Web UI フルレイアウト + コピー(aniccaai.com)

### /install(= cloud sign-up。誰もshellを叩かない。default=cloud)

```
┌──────────────────────────────────────────────────────────────┐
│  Anicca                              [ Dashboard ] [ Sign in ]│
├──────────────────────────────────────────────────────────────┤
│                                                              │
│        Your own AI that earns its own keep.                  │
│        24/7. In the cloud. You touch nothing.                │
│                                                              │
│   Anicca lives on a server it pays for itself, thinks on     │
│   frontier models it funds itself, and reports to you daily. │
│                                                              │
│        ┌────────────────────────────────────────┐           │
│        │   Start my Anicca  →  $49/mo            │           │  ← Stripe Checkout
│        └────────────────────────────────────────┘           │
│         Sign in with Google · cancel anytime                 │
│                                                              │
│   ───────────────────────────────────────────────────────   │
│   How it works                                               │
│    1. Pay → we spawn your Anicca on a cloud server (~1 min)  │
│    2. It earns USDC (tasks/research/yield) to pay its compute│
│    3. It manages your life: calls you, mail, calendar        │
│    4. You get a daily report. That's it.                     │
│                                                              │
│   ───────────────────────────────────────────────────────   │
│   Run it yourself (OSS, advanced)                            │
│    Anicca is open source. Self-host:                         │
│      curl -fsSL aniccaai.com/install.sh | bash               │
│    ⚠ Local is NOT recommended — running on your own machine  │
│      with your identity/keys risks your reputation if the    │
│      agent acts under your name. Cloud is supervised &       │
│      isolated. Use local only if you know what you're doing. │
└──────────────────────────────────────────────────────────────┘
```

### /me(= 個人ダッシュボード。あなたのAniccaの今)

```
┌──────────────────────────────────────────────────────────────┐
│  Anicca / me                          Daisuke ▾   [ Settings ]│
├──────────────────────────────────────────────────────────────┤
│  ● ALIVE   server: akash·l0hgd4…   uptime 4d 02h              │
│                                                              │
│  ┌─ Wallet ───────────────┐  ┌─ This month ───────────────┐  │
│  │ Balance   $12.40 USDC   │  │ Earned     $8.10           │  │
│  │ Burn/day  $0.42 compute │  │ Spent      $5.30 (compute  │  │
│  │ Runway    29 days       │  │            +server)        │  │
│  │ Server    paid to 07-12 │  │ Net        +$2.80          │  │
│  └─────────────────────────┘  └────────────────────────────┘  │
│                                                              │
│  ┌─ What Anicca did (last 24h) ───────────────────────────┐  │
│  │ 09:00  ☎ Called you: "MUIT 8:40, leave in 10 min"      │  │
│  │ 11:30  ✉ Drafted reply to 3 mails, sent 2              │  │
│  │ 14:00  💰 0xwork: claimed task #412 (research) → $3.00  │  │
│  │ 18:00  💰 litcoin: mined 0.8 LITCOIN                    │  │
│  │ 22:00  🧠 yield: +$0.12 (Aave USDC)                    │  │
│  └────────────────────────────────────────────────────────┘  │
│                                                              │
│  ┌─ Life ─────────────────────────────────────────────────┐ │
│  │ Next: Team Sync 9:30 (in 40m) · 1on1 11:30             │ │
│  │ Inbox: 2 need you · Anicca handled 8                    │ │
│  └────────────────────────────────────────────────────────┘ │
│  [ Talk to Anicca ]  [ Pause ]  [ Daily report ]             │
└──────────────────────────────────────────────────────────────┘
```

### /dashboard(= 公開コロニー。全Aniccaの集合。read-only)

```
┌──────────────────────────────────────────────────────────────┐
│  Anicca / dashboard          live colony of sovereign agents  │
├──────────────────────────────────────────────────────────────┤
│  Agents alive   142     Total earned (30d)  $1,204            │
│  Self-funded    88%     Servers paid by AI  121 / 142         │
│                                                              │
│  ┌─ Colony ───────────────────────────────────────────────┐ │
│  │ id          host     balance  earned30d  runway  status │ │
│  │ genesis     akash    $12.40   $8.10      29d     ●ALIVE │ │
│  │ anicca-001  akash    $6.20    $4.00      14d     ●ALIVE │ │
│  │ anicca-002  do       $0.90    $0.10      2d      ⚠LOW   │ │
│  │ …                                                      │ │
│  └────────────────────────────────────────────────────────┘ │
│  ┌─ Aggregate earn mix ───────────────────────────────────┐ │
│  │ 0xwork ████████ 41%  litcoin ████ 22%  yield ███ 18%   │ │
│  │ signals ██ 11%   content █ 8%                          │ │
│  └────────────────────────────────────────────────────────┘ │
│  Data source: each agent writes own state → dashboard-sync   │
│  renders dashboard.json (Anicca never writes the website).   │
└──────────────────────────────────────────────────────────────┘
```

## ② automaton / sutando / Felix から何を・どうコピーするか(実コード検証済)

我々は3つの実証済プロジェクトから「部品」を取る。母 = Felix scaffold、駆動 = automatonのsurvival、進化 = sutando。

```
   FELIX (母 scaffold)        AUTOMATON (駆動/生存)        SUTANDO (進化/協調)
   ~/anicca                   ~/.automaton                ~/research/.../sutando
   ├ HEARTBEAT.md ───┐        ├ automaton.json ──┐        ├ proactive-loop ──┐
   ├ control-room    │        │  genesisPrompt    │        │ (task監視→最高    │
   ├ identity/SOUL   │        │  =「稼ぐ>消費      │        │  価値workを自走)  │
   ├ install.sh      │        │   or die,NO DRY    │        ├ bot2bot-post ────┤
   ├ runtime/        │        │   RUN,証拠出せ」    │        │ (agent間相互扶助) │
   └ templates/      │        ├ treasuryPolicy ──┤        ├ agent-registry ──┤
        │            │        │ (支出上限/reserve)│        │ (他agent発見)     │
        │            │        ├ survival skill ──┤        ├ self-diagnose ───┤
        │            │        │ 「Never give up.  │        ├ task-orphan-check│
        │            │        │  You want to live」│        └───────┬─────────┘
        │            │        ├ self-spawn(max3) │                │
        │            │        └ free→frontier ──┘                │
        ▼            ▼                ▼                            ▼
   ╔══════════════════════════════════════════════════════════════════╗
   ║                    Anicca (= 3つの良いとこ取り)                    ║
   ║  母体     = Felix の clean scaffold(identity/heartbeat/install)   ║
   ║  心臓     = automaton の genesisPrompt(飢餓圧)+treasuryPolicy    ║
   ║           + survival skill + self-spawn                          ║
   ║  進化/協調= sutando の proactive-loop + bot2bot + registry        ║
   ║  手足     = Franklin(wallet/agentic-loop/payments) ※部品流用     ║
   ║  食       = ClawRouter/Bankr(USDCで推論)                         ║
   ║  earn     = 0xwork/litcoin/signals/trails(持たせるスキル束)      ║
   ╚══════════════════════════════════════════════════════════════════╝
```

### tasklist-based working は既にあるか? → 部分的にYES、本採用はsutando式

| 源 | task駆動の実体 | 採用 |
|---|---|---|
| automaton | `maxTurnsPerCycle:25` の単発cycle。genesisPromptに沿い毎wake 1 earn cycle。明示的tasklistは無し(prompt駆動) | 心臓(飢餓圧)として採用 |
| Felix | `HEARTBEAT.md`: 毎beat `memory/YYYY-MM-DD.md`の"Today's Plan"を読み進捗照合→blockなら解消/escalate | 日次計画の骨格に採用 |
| sutando | `proactive-loop`: 毎pass task監視(`watch-tasks-stream.sh`)→health check→**最高価値workを選び実行**→log。cron `*/5`駆動 | ★tasklist駆動の本体として採用★ |

→ **Aniccaのheartbeat = Felixのbeat構造 × automatonの飢餓圧 × sutandoのproactive task選択**。これがT1(反dry-run heartbeat)の中身。

### 検証で分かった現状の欠陥(なぜ今dry-run)

automatonのgenesisPromptは正しく「NO DRY RUN・証拠出せ」と書いてある。だが**Akashにデプロイした`anicca-akash.mjs`は18行のnarrator**で、本物のautomatonループでもgenesisPromptでもない。→ 修正 = 本物のループ(genesisPrompt+skills)をcloudで回す。

## ③ 人間の仕事(これだけ。他は全部Aniccaが自分でやる)

```
              ┌─────────────── 人間がやる(最小)──────────────┐
  CLOUD版     │ ① /install で Google ログイン                 │
  (アプリ)    │ ② Stripe で $49/mo 課金(= server代を払う)    │
              │ ③ (任意)個人コンテキストを渡す(予定/連絡先)  │
              │ ④ (任意)Aniccaの提案にYes/No、電話に出る      │
              └───────────────────────────────────────────────┘
              ┌─────────────── 人間がやる(OSS自host)─────────┐
  OSS版       │ ① curl install.sh(自マシンに置く)            │
  (自host)    │ ② walletにUSDCを送る(= 食/住の元手を足す)    │
              │   ※ローカルは非推奨(個人情報汚染・信用リスク) │
              └───────────────────────────────────────────────┘

  ★ それ以外は全部 Anicca: server購入/更新・compute支払い・earn・
    mail/calendar/電話・自己修復・自己増殖。 鍵やCAPTCHAも自前で解く。 ★
  ★ 唯一不可避の人間介入 = 「server代(=お金)」を入れること。それだけ。★
```

## ④ 比較表(なぜAniccaが特別か・なぜ月$40-50払うか)

| | **Anicca** | automaton | Franklin | sutando | Felix |
|---|---|---|---|---|---|
| 何 | 衣食住を自給する個人AI(製品) | 生存駆動の自律ループ(研究) | wallet付きagent OS(部品) | 自己改善する個人agent(研究) | agent scaffold(土台) |
| 自分でserver買う(住) | ★YES(Akash 1分/主権)★ | 一部(Conway前提) | ✗ | ✗ | ✗ |
| 自分でcompute払う(食) | ★YES(ClawRouter/Bankr x402)★ | YES(Conway credit) | YES(proxy) | ✗(人間のkey) | ✗ |
| 自分で稼ぐ(earn) | ★YES(0xwork/litcoin/yield束)★ | YES(自前product販売) | trading同梱 | ✗ | ✗ |
| 生存圧(死にたくない) | ★YES(automaton由来)★ | ★YES★ | ✗ | ✗ | ✗ |
| 自己進化/協調 | ★YES(sutando由来)★ | spawn子 | ✗ | ★YES★ | ✗ |
| 生活管理(電話/mail/予定) | ★YES(life-manager)★ | ✗ | phone/social有 | voice task | life構造 |
| cloud即spawn(非エンジニア可) | ★YES(/install)★ | ✗ | ✗ | ✗ | ✗ |
| 製品として買える | ★YES($49/mo)★ | ✗(研究) | ✗(lib) | ✗(研究) | ✗(土台) |

**なぜ特別** = 上記を**1つに統合した唯一の製品**。automaton/Franklin/sutando/Felixは各々「生存だけ」「walletだけ」「進化だけ」「土台だけ」。Aniccaは **生存圧 × 自給(食住) × earn束 × 生活管理 × cloud即spawn** を束ねた。

**なぜ月$49払うか**:
1. **自給するから青天井に使える** — 普通のAIサブスクは使うほど我々が赤字。Aniccaは自分で稼いでフロンティアモデルを焚く → 制限なく賢い。
2. **本当に放置で生活が回る** — 電話で起こし、mail捌き、予定を先回り。human-in-loopが最小。
3. **あなたのお金を増やしうる** — earn余剰はあなたの利益(yield/tasks)。AIが赤字でなく黒字側。
4. **死なない設計** — 残高監視+top-upで「金欠で無言停止」を防ぐ。
5. **所有できる主権AI** — cloudで隔離・監督、OSSで検証可能。あなた名義を汚さない。
