# Dais-Funded 自律US株トレードループ — 設計Spec (SSOT)

- **Date**: 2026-07-07
- **Status**: DESIGN (実装未着手 / brainstorming → 本specがsource of truth)
- **Owner**: claude-p (human-funded loop) / 立案 = メインClaude
- **開発方式**: GLVS。本specはGoal段の成果物。Build/Verifyは本spec承認後にVCSDD実コマンドで回す
- **改訂履歴**: 初版はcrypto(bitbank+freqtrade)だったが、Daisが「cryptoは別で既にやってる、記事のようなUS株botが欲しい」と明示 → **US株(Alpaca)本線に全面組み替え。cryptoは破棄。**

> ⚠️ このspecは **Daisの実際の日本円(貯金)** を自律運用する。溶かしていい金ではない。
> 第一原則は「勝つまで大金を賭けない」を**構造で強制**すること。

---

## 0. 開発環境

| 項目 | 値 |
|---|---|
| products repo | `~/anicca-project/`(本spec docのみここ) |
| 実装時worktree | `.worktrees/dais-trading-loop/`(branch `feature/dais-trading-loop`)を切ってから着手 |
| bot本体(身体) | `~/anicca/skills/earn/us-stock-bot/` + 状態は `~/.anicca-dais/`(新規 `ANICCA_HOME`、既存colony bodyに触れない) |
| 実行機 | Mac Mini(`anicca-mac-mini-1`)、TZ=Asia/Tokyo確認済、launchd |
| venue(MVP) | **Alpaca** Trading API(日本居住者で開設可を実signup画面で確認済) |
| venue(卒業先) | **Webull JP**(ウィブル証券、金商48号、JPY直入金・最低0円) |

---

## 1. 目的とゴール(検証可能な完了条件)

**目的**: Daisの実円を、弱い円から**US株(米国株・ETF)**へ逃がしつつ増やす。初回セットアップ以降は**人間ゼロ**で回す(=記事「毎朝米国株を自動売買してSlackに報告するAIエージェント」の日本版)。

**背景資金(Daisの申告)**:
| 口座 | 額 | 役割 |
|---|---|---|
| MUFG | 約35万円 | 生活費・支払い(触らない) |
| ゆうちょ | 約90万円 | 貯金 → ここから**少しずつ**US株へ |

**投入方針**: 「$10 → $100 → 勝ち続けたら増やす」。まずPaper(仮想売買)→実弾少額。

**done条件(Milestoneごと、§9)**:
- **M1完了** = Paperで4戦略+AI審査+毎朝Slack日報(グラフ付き)+ledger+税ログexportが自律で回る。**実金ゼロ**
- **M2完了** = 実金$100を投入しライブ稼働、$10→$100実証ラダーでledgerにrealized P&Lが複数回載る。safety(kill-switch/上限/累積赤字halt)発火をテスト確認
- **M3完了** = 実証を受け規模拡大 + Webull JP(JP正規登録)へ卒業、90万の大半をTrack1(index DCA)へ

---

## 2. 正直な前提(なぜ保守的か) — 引用付き

| 出典 | 核心 | 含意 |
|---|---|---|
| freqtrade公式FAQ | "it will always be a gamble" | retail algoにツール由来のedgeはない |
| Bot Academy(stash86, 3年運用) | "zero long-term profitable strategy。バックテストは常に綺麗、最長8ヶ月で崩れる" | edgeは**リサーチ規律**から |
| Investopedia | S&P500 1928–2026 real ≈ 6.81%/yr | 「円安から逃げて増やす」の最良の自律表現は**index DCA** |
| 記事の4戦略の学術裏付け(検証済) | Momentum=Jegadeesh&Titman(1993)、Reversal=Jegadeesh(1990)、Low-vol anomaly、Dividend aristocrats | 記事の4戦略は「怪しい自作」でなく**教科書的ファクター**。ただし依然「勝つ保証はない」 |

**結論**: 記事の4戦略botは学術的に健全だが、それでも「実証されるまで小口に封じ込める」。資金の大半はindex DCA(低破綻リスク)で円安から逃がす。二層構造が背骨。

---

## 3. アーキテクチャ全体 — 2トラック(両方US株、Alpaca 1本)

```
                Dais の 実円 (ゆうちょ / MUFG)
                          │
          ┌──── Layer 1: オンランプ(USD化) ────┐
          │ 初回まとまった額 = 手動振込1回        │
          │ 追加 = bank標準送金予約(送金は自動)  │
          │ ※Alpacaは入金反映がAPI外=手動trigger │
          └──────────────┬───────────────────────┘
                          ▼ (Alpaca USD口座、本人名義KYC)
          ┌──── Layer 2: トレード(Trading API, 完全自律) ────┐
          │ Track 1: 安全ベース(資金の大半, M3で本格化)      │
          │   → index DCA(VOO/VTI等)、buy&hold、円安escape   │
          │ Track 2: 実験スライス(小口, M1 Paper→M2実弾)     │
          │   → 記事の4戦略(配当貴族/モメンタム/リバーサル/  │
          │     低ボラ) + AI審査ゲート + 毎朝Slack日報        │
          │   → $10→$100→実証ゲート→段階増額               │
          │   → kill-switch / 上限 / 累積赤字即停止           │
          └──────────────────────────────────────────────────┘
                          │
                          ▼
     身体 ~/.anicca-dais (ANICCA_FUNDING=human, fail-closed分離)
     ledger = ~/.anicca-dais/skills/earn/state/earn-ledger.jsonl
     税ログ = JPY建て取引ログ(確定申告用)を別途export
     常駐 = launchd 平日6:00 JST / self-heal = self-fix.sh dais-loop
```

---

## 4. オンランプ設計 (Layer 1) — 引用付き

Alpacaは**USD建てのみ**(JPY直接保有不可)。日本からの資金化:

| 方法 | 内容 | コスト | 出典 |
|---|---|---|---|
| International Wire | JP銀行→USD建てSWIFT送金 | 送金元銀行手数料 + 出金$50 | alpaca.markets/support/wire-deposit「wire must be sent in USD」 |
| Local Currency (CurrencyCloud) | JPYで送金→自動USD変換 | **1.5%(上限$40)** | alpaca.markets/learn/fund-live-trading-account(2026-01更新) |
| **入金の自動化** | **不可**。"users cannot programmatically schedule deposits" | — | 同上 |

**確定した運用制約**: 売買は完全自律。だが**新規資金の投入だけは人間がAlpacaダッシュボードで手動**(bank側の標準送金予約で"送金"は自動化できるが、Alpaca側の着金・USD変換triggerはAPI外)。→ これは前段で合意済みの「初期セットアップ/資金投入の人間タッチ」と同性質。トレードループ本体には影響しない。

**卒業先Webull JP**ではこの制約が消える(JPY直接入金、変換摩擦なし)。

---

## 5. トレード設計 (Layer 2) — 検証済みスタック

### 5.1 Track 2 — 実験スライス(記事のbot、M1 Paperから)

| 層 | 決定(2026-07-07検証済) | 出典/根拠 |
|---|---|---|
| 証券SDK | **`alpaca-py` v0.43.5**(旧`alpaca-trade-api`はarchived) | pypi/alpaca-py、公式docs「SDKs and Tools」 |
| 端株注文 | `MarketOrderRequest(notional=金額)`、fractionalはDAYのみ | docs.alpaca.markets/docs/fractional-trading |
| Paper | `TradingClient(..., paper=True)`で自動paper-api routing | alpaca-py README |
| エンジン | **lumibot**(1.7k★、Alpacaネイティブ)を土台に4 Strategyサブクラス | github.com/Lumiwealth/lumibot |
| 4戦略 | 配当貴族 / モメンタム(12mo) / 短期リバーサル / 低ボラ | §2の学術裏付け |
| AI審査ゲート | ルールのシグナル→LLMがveto→採用/却下を理由付きで(judgment=model原則に合致) | 自作(既存OSSに決定版なし) |
| 自然言語操作 | **公式 alpaca-mcp-server**(860★)→Claude Codeが「AI・半導体に寄せて」を審査+発注 | github.com/alpacahq/alpaca-mcp-server |
| Slack日報 | **`slack_sdk` `files_upload_v2()`**(旧`files.upload`は2025-11-12 sunset済) | docs.slack.dev、scope=`files:write`+`chat:write` |
| グラフ | matplotlib: 資産曲線 vs SPY(正規化) + 銘柄別P&L棒 | 標準 |
| 常駐 | launchd `StartCalendarInterval`、平日6:00 JST | man launchd.plist、TZ=JST確認済 |

### 5.2 Track 1 — 安全ベース(index DCA、M3で本格化)

- 役割: 資金の大半で円安から逃げ着実に増やす。VOO/VTI等の指数ETFを定時買付、buy&hold。
- Alpacaの`notional`端株で$1から積立可。判断ゼロ(スケジュール実行のみ)=最も自律・最も低破綻。
- M1/M2ではTrack1は最小(またはPaper)。実証後M3で90万の大半を移す。

### 5.3 卒業パス(規模拡大時)

実証されて規模を上げる段で、custodyを**Webull JP**(金商48号、JPY直入金、最低0円、公式Python SDK、US株+端株API)へ移す。API鍵発行に「入金→1〜2営業日審査→SMS/2FA」が要る点は初期セットアップで織り込む。lumibot非対応なのでstrategy層はWebull SDKへ移植(Alpacaで確立したロジックをcopy)。

---

## 6. マネーセーフティ(交渉不可・self-improveで変更不可)

| 装置 | 実装 | 挙動 |
|---|---|---|
| Paper-first | `paper=True` | M1は実金ゼロで全パイプライン検証 |
| 1取引上限 | `MAX_TRADE_NOTIONAL` | 1発注のnotional上限 |
| セクター集中上限 | 例30%(記事同様) | 「AIに寄せて」でも1セクター偏重を抑制 |
| kill-switch | `touch KILL` | 各run先頭でチェック、あれば即停止 |
| 累積赤字halt | `earn-guard.mjs`(既存流用) | lifetime実現損益が負でfail-closed |
| 実証ラダー | `$10→$100→$1,000→段階増額` | ledgerにrealized profit>0が閾値回数出た時のみ昇格。負けたら登らない。人間承認不要 |
| 低頻度 | rebalance頻度を抑制 | edge劣化対策 + 為替差益 雑所得イベント削減(§8) |

`MAX_TRADE_NOTIONAL`/上限系はself-improveの調整対象から除外(安全上限は緩められない)。

---

## 7. identity / 分離 / 再利用(車輪の再発明をしない)

| 項目 | 決定 |
|---|---|
| 身体 | `~/.anicca-dais`(新規)、`ANICCA_INSTANCE=dais-us-stock`、`ANICCA_FUNDING=human` |
| 分離 | 既存colony(automaton/Franklin/claude-p)と別body。混ざらない |
| ledger | 既存 `earn/lib/ledger.mjs`+`record.mjs`+`earn-guard.mjs` を流用(ANICCA_HOMEを向けるだけ) |
| self-heal | `self-fix.sh dais-us-stock "<blocker>"` 無改変で動く |
| SSOT可視化 | `colony-status.sh`に4番目ブロック追加(Alpaca equity表示) |
| secrets | Alpaca API key/secret、Slack bot token は `~/.anicca-dais/.env`(chmod600、git ignore)。CLI平文出力禁止 |

---

## 8. 税・規制(正直に、確定申告を実務可能にする)

| 論点 | 結論 | 出典 |
|---|---|---|
| US株譲渡益 | **申告分離20.315%**(crypto雑所得最大55%より明確に有利) | 国税庁No.1463 |
| 口座区分 | 海外ブローカー=特定口座なし=**一般口座=自分で確定申告** | IBKR証券FAQ |
| 米国配当 | W-8BENで10%源泉→外国税額控除 | 国税庁No.1240 |
| 国外財産調書 | 5000万超で義務→Dais(~90万)は**対象外** | 国税庁No.7456 |
| ⚠️ 為替差益 | 海外ブローカーはUSD現金で回すため「売却→USDでB購入」の度に為替差益が**雑所得**化しうる。**低頻度**設計で削減 | 楽天証券・国税庁通達57の3 |
| ⚠️ Alpaca法的位置 | 日本金商登録なし=逆勧誘グレー。$100 MVPは実害小、**規模拡大でWebull JP(登録済)へ卒業** | 関東財務局 |

**botの税ログexport仕様(必須)**: 約定日時 / 銘柄・数量・単価USD / 適用為替レート(同一金融機関TTS-TTB継続適用) / 円換算取得・売却額 / 配当と米国源泉10% / **USD現金移動履歴(為替差益用、最も漏れやすい)** / 年間JPY損益サマリー。→ 確定申告書へ転記可能な形で出力。**税理士に最終確認する項目**は§12に列挙。

---

## 9. Milestones & ゲート

| M | 名前 | やること | 完了ゲート(検証可能) |
|---|---|---|---|
| **M1** | Paperパイプライン | `~/.anicca-dais`生成、Alpaca **paper**口座、alpaca-py+lumibotで4戦略、AI審査ゲート、毎朝Slack日報(matplotlibグラフ+会社名+理由)、ledger、税ログexport、launchd平日6時JST、公式MCPでチャット操作。**実金ゼロ** | Paperで自律稼働し、毎朝Slackにグラフ付き日報が届き、MCPで「AI・半導体に寄せて」→注文一覧提示が動く。227件相当のテストgreen |
| **M2** | 実金少額 | Alpacaへ$100を1回投入→ライブ切替、$10→$100実証ラダー。Track1 index DCAも開始。safety発火をテスト確認 | ledgerに実約定のrealized P&L行が複数、kill-switch/上限/累積赤字haltが実際に発火。税ログが実取引で埋まる |
| **M3** | 規模拡大+卒業 | 実証を受け増額、**Webull JP**(JP登録)へcustody卒業、90万の大半をTrack1 DCAへ | Webull JPで自律稼働、円安escapeがE2Eで回る |

各MはVCSDD(init→spec→spec-review→tdd→impl→adversary→harden→converge)で回す。

---

## 10. 検証アーキテクチャ(VCSDDへ接続)

| 要件 | 検証(fresh evidence、dry禁止) |
|---|---|
| Paperパイプライン | paperで実際にシグナル生成→審査→(paper)発注→Slack日報到達を実観測 |
| Slack画像 | `files_upload_v2()`で実PNGがチャンネルに載る(URL確認) |
| MCPチャット操作 | Claude Codeから自然言語→注文一覧提示→GO→paper反映をE2E |
| 実約定/ledger | M2で実fill IDとledger行が一致(盛らない、tx/fill確認まで) |
| safety発火 | KILL/上限超過/累積赤字を人工発生→実際に停止 |
| 税ログ | 実取引後、JPY建てログが約定日レートで正しく出る |
| identity分離 | foreign ANICCA_HOMEでkey解決がnull |

adversary = fresh-context Opus 4.8(`model: "claude-opus-4-8"`明示)。

---

## 11. スコープ外(YAGNI / 明示的除外)

- ❌ crypto(Daisは別で運用中、税も不利)
- ❌ レバレッジ/信用(spot/cash現物のみ)
- ❌ 高頻度/デイトレ(低頻度=edge劣化対策+為替差益 雑所得削減)
- ❌ M3前に90万の大半を動かす
- ❌ IBKR(初回最低100万円=start small不可)、moomoo(2026-06-19 FSA業務改善命令)
- ❌ 入金の完全API自動化(Alpaca構造上不可、bank予約+手動triggerで代替)

---

## 12. リスクと未検証事項(正直に)

| 項目 | 状態 |
|---|---|
| Alpaca日本KYC/入金の最終確認 | signup国選択で"Japan"可は実画面確認済。**実KYC・着金・API鍵発行はM1で本人情報で完走して確定**(検証時はhard-stopで未実行) |
| Alpaca法的グレー(金商登録なし) | $100 MVPは実害小。規模拡大でWebull JP卒業。**弁護士確認**推奨 |
| 為替差益 雑所得の実務計算 | 高頻度でのUSD再利用のFIFO等はグレー→**税理士確認**。低頻度設計で緩和 |
| retail algoのedge不在 | §2の通り。二層構造+実証ラダーで封じ込め |
| Webull JP API審査ラグ | 鍵発行に1〜2営業日+SMS/2FA。卒業時の初期セットアップに織り込む |

---

## 13. 次のステップ

1. Daisが本specをレビュー・承認
2. writing-plans skillでM1実装計画(GLVS Goal→Plan)
3. worktree `feature/dais-trading-loop`
4. M1からVCSDD実コマンド(`vcsdd-init`...)
5. **実装はDais承認まで一切しない**(brainstorming HARD GATE + Dais明示指示)
