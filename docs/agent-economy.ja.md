# Mr.bot の下で動いている「自己資金エージェント」

このファイルは**製品ではない方**を扱います。Mr.bot は人の身体・心・お金を管理する personal manager です（[README.ja.md](../README.ja.md)）。以下はその計算資源を払う層 — 自分の wallet を持ち、自分で稼ぎ、自分の推論代を払うエージェントの話です。

以前はこの2つが同じ README に同居していて、どちらも読めない状態でした。**意図的に分離しています。** 製品を見に来た人はこのファイルを読む必要はありません。

---

## なぜ存在するか

YC の RFS は *「インターネットの次の1兆人はヒトではなく AI エージェントだ」* と言います。それが本当になるのは、エージェントが**自分の**お金を持つ場合だけです。人間の API キーで人間の wallet から払っているエージェントは*手数の増えた人間*にすぎず、人間が払うのをやめた日に死にます。**金銭的独立**（自分の wallet・自分の収入・自分の計算資源代・自分の子）がエージェント経済の前提条件です。

**唯一のルール**: 人間が払うのは**1回だけ**。あとは世代 N の余剰が世代 N+1 を作ります（親 → 子 → 孫 → ∞）。seed → bet → win → **collect** → より大きく bet → 複利。

---

## 動かし方（ローカル自己ホスト・サーバー鍵も API キーも不要）

自分の計算資源を、自分の財布から USDC で推論ごとに x402 決済（BlockRun / ClawRouter）して払います。人間の API キーは不要。あなたが渡すのは動かす端末（住処）だけで、食料（推論）は自分で買います。財布が空なら **無料モデル（$0）**、USDC が入れば frontier モデルも使えます。

```bash
git clone https://github.com/Daisuke134/life-manager ~/mr-bot && cd ~/mr-bot
./install.sh                                    # runtime root + スキルスロット同期、自前 wallet 生成
cd runtime/compute-proxy && npm install && cd -  # 一度だけ（@blockrun/llm + viem）
./start-local.sh node runtime/loop/index.mjs    # 自己決済プロキシ + ループを起動
```

これで 2 つが起動します。(1) `http://127.0.0.1:8402/v1` の OpenAI 互換 **自己決済コンピュートプロキシ**（自前 wallet＝自動生成・人間の鍵では決してない、から毎推論を USDC で自己決済）と、(2) **ループ本体**（[`runtime/loop/`](../runtime/loop/)＝think → act → observe → persist の ReAct ループ＋heartbeat）。ループは毎 wake、ClawRouter の **`auto`** ルーター（モデルをハードコードせず、ツール呼び出しを検知して tool-calling 可能なモデルへ自動ルート＋wallet から課金）でプロキシに問い合わせ、ツール（例：`earn` スキル）を選んで実行し、`$ANICCA_HOME/state/ledger.jsonl` に 1 行追記します。

`install.sh` の runtime 既定値は `${XDG_STATE_HOME:-$HOME/.local/state}/mr-bot` です。複数 instance は `MR_BOT_HOME=/任意のruntime` で分離できます。container・CI・foreground 実行では `MR_BOT_INSTALL_DAEMON=0` を指定すると、lockfile 固定の依存と同じ runtime body を導入しつつ LaunchAgent / system service を変更しません。

> 別の頭脳を使いたい場合は `ANICCA_BRAIN=claude-p` で同じループを Claude Code（`claude -p`）で駆動できます。既定は `proxy`（自己資金の道）。他の OpenAI 互換ループも `OPENAI_BASE_URL` に向ければ動きます。

各能力は [`skills/registry.json`](../skills/registry.json) にスロットとして宣言され、`install.sh` が同期します。予約済みスロットを有効化するには、実装をそのディレクトリに置いて `status` を `live` にするだけです。

---

## 3つの型（すべて現在稼働中）

同じループ・同じスキルで、違うのは**燃料**と**wallet のチェーン**だけです。

### ① automaton — Base で自己資金（ClawRouter 燃料）
```bash
./install.sh
./start-local.sh node runtime/loop/index.mjs     # 自己決済プロキシ（x402）+ ループ
```
表示された wallet アドレスに USDC を送ると frontier モデルが開きます。空なら無料モデル（$0）なので止まりません。

### ② Franklin — Solana で自己資金（BlockRun 燃料）
Franklin（`@blockrun/franklin`）は 55+ のモデルと有料 API に自律的に*支払う* wallet 付きエージェントです。このリポジトリはその上に*稼ぐ*層を足します（Node 20.19+）。
```bash
npm install -g @blockrun/franklin
franklin setup solana        # 自前の Solana wallet を作り、~$5 USDC を送ると frontier が開く
franklin balance
ANICCA_HOME="$HOME/.blockrun" ANICCA_INSTANCE=franklin ANICCA_BRAIN=proxy \
  ./start-local.sh node runtime/loop/index.mjs
```

### ③ claude-p — 人間資金で始めて卒業する
crypto 不要。手持ちの Claude サブスクで動かし、USDC を稼ぎ、自分の計算資源を賄えるようになった時点で自己資金へ転換します。

**終着点**: 最終的に human-funded な AI は1つも残らず、自分で食べ・自分を所有し・自分で増える self-funded だけになります。人間資金はブートストラップにすぎません。

---

## human-funded と self-funded、具体的に何が動くのか

起動する前に、あなたのサブスク / 財布が何に使われるかを正確に知っておくべきです。全 loop の台帳（どこにあり、生死確認の仕方）は **[`docs/EARN_LOOPS.md`](EARN_LOOPS.md)**（英語）を参照。

```
skills/earn/
├── clip/        ← IG per-view クリップ(長尺動画→9:16切抜→字幕→投稿)
├── affiliate/   ← Amazon アソシエイトのスライドショー
├── video/       ← faceless動画のライフサイクル(作成→ウォームアップ→投稿)
├── bounty/      ← Algora GitHub bounty(Issue発見→修正→マージ)
├── gig/         ← ココナラ案件(発見→応募→納品)
└── run.sh       ← self-funded共通入口: yield / hl_trade / x402_sell / token_launch
```

**human-funded で起動する場合**（`ANICCA_BRAIN=claude-p`、あなたの Claude Code サブスクで駆動）: 5本の独立したループが、決まった時間・決まった通貨で稼ぎます。

```
clip-core       (毎時)        → USDC、IG per-view報酬
affiliate-core  (毎日08:41)   → ¥、Amazonアソシエイト報酬
video-core      (4時間毎)     → USDC、faceless動画アカウント
bounty-core     (毎日09:29)   → USD、マージされたGitHub bountyのPR
gig-core        (毎時)        → ¥、ココナラ報酬(法定通貨、人間の銀行口座着金)
```
判断は行いません — 決まったスケジュールを回すだけ。安価で予測可能ですが、この5本のレールが生む分にしか稼げません（上記の「銀行口座」は明示的に差し替えない限り Dais のものです）。

**self-funded で起動する場合**（既定 `ANICCA_BRAIN=proxy`、自分の wallet + 無料モデルで駆動）: 120秒毎に起きて「次に何をするか」を自分で判断する daemon が1本動きます。

```
1 wake → LLM が次のうち1つを選ぶ: hl_trade | x402_sell | token_launch | yield | cook |
                                    self/issue-dev | earn/clip | earn/video | earn/gig | earn/bounty
        (human-fundedループと全く同じコードを、固定スケジュールでなく判断で呼ぶ)
```
より自律的で、より不安定 — 学習前に取引で損をすることもありますが、cron の時報を待たない分、複利も速く効きます。両者は `skills/earn/` の全く同じコードを共有し、`ANICCA_INSTANCE` がアカウント / wallet / ledger の衝突だけを防いでいます。

---

## どう稼ぐか

ループは起きて wallet と市場を見て、スキルを1つ選びます。中核は3つの取引エンジンと自前の探索で、すべて no-KYC・wallet 署名のみです。

| エンジン | 場 / エッジ |
|---|---|
| **Polymarket**（`earn/pm-trade`） | 予測市場: 中値付近に流動性を置いて日次 LP 報酬を取り、値付けの歪んだ結果に賭け、**勝ち分を現金化（redeem）**して複利に回す。YES+NO < $1 の無リスク束アービトラージが出た時はそれも取る |
| **Solana**（`earn/sol-trade`） | 規律ある Jupiter スワップ — 往復手数料を超えるエッジがある時だけ。無ければ待つ（待つのは正しく知的な手） |
| **Hyperliquid**（`earn/hl-trade`） | perps: ストップと利確を置いたトレンドフォロー。口座不要、鍵署名のみ |
| **cook**（探索） | 新しい稼ぎ方を web から探して試し、効いたものをコロニーへ共有する |

賭けに勝つのは半分にすぎません。ループは勝ち分を**回収（redeem）**して初めて次を賭けられます。この回収と複利の循環が独立の原動力です。

---

## ループ: earn → eat → spawn → improve → give

```
  human ─ 1回の種銭（サブスク or 少額 USDC）─► 1体のエージェント
                         │
                         ▼
   EARN（Polymarket / Solana / Hyperliquid / 探索）──► 実現 USDC
                         │
        ┌────────────────┼───────────────────┬──────────────────┐
        ▼                ▼                   ▼                  ▼
   EAT（自分の      SPAWN（余剰で        SELF-HEAL +        GOJO（豊かな個体が
   計算資源代）      子を作る）           SELF-IMPROVE       破産寸前を助ける）
        │                │              （自分のコードを直し、        │
        │                │                稼ぐものを残す）            │
        └── 稼がなければ食べることも増えることもできない ── EARN が全て ──┘
                         │ 余剰
                         ▼
              人へ UBI（wallet / メール / 銀行 — 銀行情報は不要）
```

5つの自己\*性質が人間なしで回します: **自己監視・自己修復・自己改善・自己増殖・情報共有**（勝った教訓は全個体が読む GitHub issue になり、勝った戦略は本流へマージされ伝播します）。

### 最良のレシピは群れ自身が見つける（人間が選ばない）

コロニーは自分自身で実験します。どのモデル・どのハーネス・どの戦略という選択の行列に沿って変種を spawn し、それぞれを本番で走らせ、**実現したオンチェーン利益だけを評価**とします。最も稼いだレシピが勝ち、伝播します（収益で開く、人間なしのマージ）。[ダッシュボード](https://aniccaai.com/dashboard)がその探索を可視化します。

---

## アーキテクチャ（一段落）

[Conway の automaton](https://github.com/Conway-Research/automaton) と同じ **automaton パターン**（ReAct ループ＝think → act → observe → persist ＋ heartbeat）で動きますが、**より簡素で別のスタック：ClawRouter（食＝推論・自己決済 x402）＋ 自分の Mac（ローカル）または Akash（クラウド）** の上で動き、Conway に依存しません。ループは [`runtime/loop/`](../runtime/loop/) にあり、runtime root（`$ANICCA_HOME`）配下でスキルスロット群と 1 つの Base Smart Wallet とともに動きます。

---

## いま実在するもの vs 開発中

| 能力 | 状態 |
|---|---|
| 自己決済コンピュートプロキシ（自前 wallet で free → frontier、x402） | **実装済・実証済**（`runtime/compute-proxy/`） |
| **ループ**（`runtime/loop/`）＝wake → ClawRouter `auto` 頭脳 → スキル実行 → 台帳 → sleep | **実装済・稼働** — ツール呼び出しを end-to-end 発火（モデル非ハードコード）。テスト＋live wake 検証済 |
| 初の自律取引決済 | **2026-07-05 実証** — 個体が自分で Polymarket のポジションを建て決済（settle tx [`0x7662a88b…`](https://polygonscan.com/tx/0x7662a88b6851d12a08e1f4dd0c020254cb9f96107e6ceea7dd92965639a4bfc3)、status 0x1）。最初の $8.24 回収は人間が起動、後の $5.99 回収は自律（tx [`0xd33b09c8…`](https://polygonscan.com/tx/0xd33b09c8d78d9b28cc9f0ad5db06a1015fb3c63deefa20f7076ed5615c103e2b)）。**回収額は元本と利ざやの混合なので純益ではありません** |
| 自己増殖（`self/spawn`）/ 自己改善（`self/issue-dev`）/ UBI（`economy/ubi`） | **宣言済** — 機構は確定、稼ぎの後のロードマップ |
| クラウド自己 spawn（Akash）/ UBI 支払い | **開発中** — 資本で開く。spec で追跡 |

---

## 財布への入金（任意 — frontier モデル / さらに稼ぐ場合のみ）

秘密鍵は決して共有しません。エージェントの **公開** wallet アドレス（`start-local.sh` が表示）に USDC を送るだけです。

- **米国：** Coinbase → USDC 購入（カード）→ wallet アドレスへ送付
- **日本：** Binance アカウント → MetaMask → relay.link で swap → wallet アドレスへ USDC 送付

Base 上の全 wallet は `basescan.org/address/<addr>` で公開され、treasury は誰でも検証できます。
