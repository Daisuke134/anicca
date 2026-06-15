# Money-Maker スキル評価 — Aniccaに「持たせる」稼ぐスキルの選定

## 概念モデル(Dais 2026-06-13 確定)

```
Anicca = 1体のエージェント
 ├ BODY(中身・役割。合否対象でない)
 │   ├ OpenClawランタイム … スキルを load/実行する器
 │   ├ automaton ループ  … 24/7 自走
 │   ├ Franklin          … wallet を持ち task を実行する手
 │   └ ClawRouter/Bankr  … 自分のwalletでLLM推論を払う(food)
 │
 └ SKILLS(持たせる道具。多数)
     ├ life-manager / mail / content … 生活系
     └ ★ EARN スキル群 ★ … これを持たせて使うから稼げる  ← 本稿の選定対象
```

★ Franklin/automaton/OpenClaw を「不合格」と書くのは誤り。役割(BODY)が違う。
★ 評価するのは「**どの EARN スキルを Anicca に持たせるか**」だけ。

## 選定フィルタ(3条件すべて満たす = 持たせる)

| # | 条件 | 理由 |
|---|---|---|
| ① クラウドで動く | headless で droplet/Akash 上で走る。GUI/Electron 専用は不可 | 兄ちゃんはクラウドで稼ぐ |
| ② no-human(walletのみ) | 自分のwallet/署名キーだけ。他人のAPIキー・KYC口座・人間承認 不要 | human-in-loop 禁止 |
| ③ 稼ぐ | USDC/換金可能token が wallet に着金する | earn が目的 |

★ 重要: `BANKR_API_KEY` 等は **エージェント自身のリモートwallet署名キー(no private key on disk)** であり、他人のAPIキーではない → ①②に抵触しない(自分のwallet)。

## ★ ポートフォリオ: Anicca に持たせる EARN スキル束 ★

出典: `github.com/BankrBot/openclaw-skills`(OpenClawネイティブ・約80スキルのplug-and-play登録庫)+ awesome-OpenClaw-Money-Maker 各カテゴリ最星。

| スキル | カテゴリ | 稼ぎ方 | 資本 | クラウド | no-human | 採否 |
|---|---|---|---|---|---|---|
| **0xwork** | タスク市場 | Writing/Research/Code/Data タスク完了→USDC(Base escrow) | 不要(知能) | ✅ | ✅自wallet | ★★★ 主力 |
| **litcoin** | research mining | 24分野の研究mining→$LITCOIN(Bankr内蔵LLM=他provider不要) | stake小 | ✅ | ✅自wallet | ★★ 常時稼働 |
| **signals** | シグナル販売 | tx検証済tradeシグナルをprovider登録→購読料 | 不要 | ✅ | ✅自wallet | ★★ |
| **trails** / zyfai | DeFi yield | Aave/Morpho vault入金→利回り | 要(元手) | ✅ | ✅自wallet | ★ passive基盤 |
| **signa** | A2A capability | keylessでエージェント間capability提供 | 不要 | ✅ | ✅keyless | ★ |
| **darksol-random-oracle** | x402 service | 乱数をx402 USDCで販売 | 不要 | ✅ | ✅x402 | ☆ niche |
| **bankr** | (BODY backbone) | wallet+LLM gateway+token手数料。実行/決済層 | — | ✅ | ✅自wallet | body候補(ClawRouter代替/併用) |

### クラウド or no-human で落ちる(持たせない)

| スキル | ⭐ | 落ちた理由 |
|---|---|---|
| OpenAlice | 5.2k | Electron desktop GUI専用 → ①クラウド不可 |
| Freqtrade/Hummingbot/Jesse | 46.5k/15.9k/7.4k | CEX API+KYC口座 → ②human |
| Solana Trading Bot 各種 | 2.3k等 | walletのみ可だが pump.fun投機=高リスク。trails/0xworkを優先、上振れ枠で保留 |
| Artemis(MEV) | 2.9k | walletのみだが資本+gas競争激烈 → 小資本で非現実的。保留 |
| MoneyPrinterTurbo 等 content | 44k | 生成はクラウド可だが収益化に YT/TikTok アカウント+観客+時間 → ②間接 |
| ScrapeGraphAI/SalesGPT(lead gen) | 22.6k/2.2k | 顧客/商談先(人間)が要る → ②不可 |
| MasterCryptoFarmBot 等 airdrop | 232 | Telegramゲーム多重アカウント farming、低/不確実収益 → ②③弱 |

## ライブ battle-test 証拠

- **0xwork API 生存確認**: `GET https://api.0xwork.org/manifest.json` → v4.0.0, chain=Base(8453), taskPool=`0xF404aFdbA46e05Af7B395FB45c43e66dB549C6D2`(on-chain escrow デプロイ済)。
- **実タスク取得**: `GET https://api.0xwork.org/tasks?status=open` → HTTP 200。task schema に `bounty_amount/category(Writing/Research/Social/Creative/Code/Data)/stake_amount/deadline/proof_hash/payout_tx_hash` 等を確認。
- **2026-06-13 時点の供給**: open 2件(両方 category=Social「Jesse Pollak に follow/RT させる」)= 社会影響力依存で自律向きでない。→ **供給は変動する。だから単一依存せず litcoin(常時mining)+ DeFi yield(passive)+ signals と束で持たせる** = ポートフォリオの根拠そのもの。
- **litcoin**: `litcoin-miner` skill。「start a research miner」で server-side Sentinel が Bankr key を LLM key(llm.bankr.bot)に使って自走 → 他AI provider不要・クラウド常駐可。stake tier(Spark〜Architect)。
- **AutoHedge**(参考): swarm+ClawRouter で起動はOK だが `EXA_API_KEY`(他人の研究API)必須 → ②抵触。研究検索を無料手段に差し替えれば候補だが、0xwork/litcoin が上位。

## 結論(実装する earn スキル束)

1. **0xwork** を主力(知能→USDC 直行、兄ちゃんの得意分野=research/writing/code、資本ゼロ)。`skills/earn/0xwork`。
2. **litcoin** を常時稼働(供給0の時間帯も研究miningで稼ぐ、Bankr内蔵LLM)。`skills/earn/litcoin`。
3. **trails(DeFi yield)** を passive 基盤(元手をAave/Morphoで利回り)。`skills/earn/defi-yield`。
4. **signals** を上振れ(シグナル販売)。`skills/earn/signals`。
5. wallet/決済 backbone は **bankr**(or 既存 ClawRouter)。BODY層。

★ これらは BankrBot/openclaw-skills から OpenClaw skill として Anicca の body に drop-in できる。「持たせるスキル」= まさにこれ。
★ 完全自給の算数: passive(yield)だけでは資本~$750-2250 要 → 現実解 = 0xwork+litcoin(知能労働で日銭)+ yield(元手の複利)+ サブスク収益で元手供給。
