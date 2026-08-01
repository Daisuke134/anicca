# Dais Life Manager 5段階実行仕様 — 専用正本

status: ACTIVE
owner: Dais / Life Manager
created: 2026-08-01 JST
updated: 2026-08-02 JST
scope: 応募基盤、イベント、資金調達、求人、個人CFO、暗号資産、法定通貨投資・NISA

## 0. この文書の権限

この文書は、上記scopeだけの実行順序、残作業、完了条件、採用する外部部品の
**専用正本**である。

他の仕様書に記事、動画、マーケティング、クラウド移行、自己複製、別agentの作業が
書かれていても、このtrackの次作業へ混ぜない。

矛盾時の優先順位:

1. Daisの最新の明示指示
2. この専用仕様書
3. `2026-07-30-outbound-apply-engine-design.md`の各pack内部順序
4. その他の全体・履歴仕様

### 0.1 Life Managerの成果義務

Life Managerは「検索した」「分析した」「失敗した」と報告するsystemではない。userが理想の自分へ
近づく**次の現実行動を成立させるsystem**である。

| organ / loop | 内部作業ではなく要求する現実成果 |
|---|---|
| Connector | rolling 21日を見て、空いている各日に東京の対面eventを入れ、二重予約せず人と会う |
| LT | 登壇応募、登壇、Life Manager demo、参加者との接点 |
| Fundraising | 実提出、返信、面談、採択、資金とpeer group |
| Job Hunter | 実応募、返信、面接、offer、給与改善 |
| Financial Organ | 口座把握、支出改善、収入増加、risk管理、長期資産形成 |

「no action」が安全上正しい場面はある。たとえばrisk条件を満たさないcrypto取引は実行しない。
その場合も、何もせず閉じるのではなく、停止理由、次の観測、改善案、次回判断時刻という現実の
次行動を残す。Connectorではno-eventを正常終了にせず、実参加予約までloopを継続する。

### 0.2 現在地と残りの一本道（2026-08-02 JST）

正本実装は`/Users/operator/Projects/life-manager-main`の`main`である。`O1A-01〜06`と
`O1B-01〜19`は実装・実測・証拠化・push済み。21日coverageの器に加え、実Luma Tokyoを終端まで読み、
全candidateを21日へ投影し、好みで候補を捨てず、本文・主催者・参加者・場所・時間からgoalと
serendipityを根拠付き評価するところまで完成した。実Calendarを読んだ
2026-08-02〜2026-08-22の初回coverage snapshotは、後続のCalendar/event照合前なので21日すべて
`open`である。これは「イベントがない」という意味ではない。

現在の唯一の実行対象は`O1B-24`である。残作業は、途中へ別trackを混ぜず次の順序で進める。

```text
完了: O1B-20〜23 source handoff、候補継続、全Calendar・移動時間gate
いま: O1B-24 無料優先・有料event自動支出policy
  → O1B-25 21日coverageのTelegram報告
  → O1C-01〜27 Fundraising / acceleratorの探索・提出・返信・面談追跡
  → O2-01〜12 Job Hunterの統合・実応募・返信・面接追跡
  → O3A-01〜07 壊れたCFO runtime loopを復旧
  → O3B-01〜24 Moneytree / Binance / walletを統一財務台帳へ接続しCFOを完成
  → O4-01〜16 Cryptoをpaper→小額canary→risk制御付き運用へ進める
  → O5-01〜14 Fiat / NISAを生活防衛資金・制度・risk制約付きで接続
  → OW-01〜12 同じcoreをWebへtenant化し、Dais以外のpilotで実証
```

各checkboxの完了条件は「codeを書いた」ではない。fresh test、実serviceでのreadbackまたは
許可された実action、receipt/ledger、Telegramで人間が理解できる報告、commit、pushが揃った時だけ
`[x]`にする。

## 1. 固定実行順序

```text
1A 共通応募基盤 + Guardian
  → 1B イベント応募（Luma優先）
  → 1C 資金調達・アクセラレーター応募 + 追跡
  → 2  求人応募
  → 3A CFO実行基盤の復旧
  → 3B Dais実口座を読む個人財務管理
  → 4  暗号資産運用（Anicca + Daisを分離）
  → 5  法定通貨投資・NISA
  → W  同じcoreをLife Manager Webアプリへtenant化
```

前段階の完了条件を満たすまで、次段階へ着手しない。

## 2. scope外

以下は、この5段階の途中へ割り込ませない。

- 記事執筆
- 動画制作
- 一般SNSマーケティング
- 別productの開発
- 全体クラウド移行
- 自己複製・takeoff
- 他agentが所有する並行track

共通基盤の障害がこのtrackを直接止める場合だけ、最小限の修復をこのtrackへ含める。

## 3. 現状の事実

- 稼働実装は`/Users/operator/Projects/life-manager-main`。
- 旧spec checkoutではなく、remote `Daisuke134/life-manager`の`main`を正本とする。
- outbound specはevents → funders → jobsの内部順序を定義済み。
- CloakBrowser daily-driverは既に`http://127.0.0.1:9222`で稼働し、求人loopは
  `chromium.connect_over_cdp()`で既存default contextへ接続する。新しいChromiumや
  browser ownerを起動しない設計が実装済み。
- daily-driverにはLumaの過去登録実績があるが、現在のlogin状態は未確認であり、過去証拠には
  「ログイン」表示もある。agentが既存Google認証でloginを復旧し、events、funders、jobsは
  この同じdaily-driverをbrowser transportとして共有する。
- CFOのジョブ登録側はruntime database URLが無く停止している。
- CFOジョブを消費するexecutorもlaunchdに存在しない。
- 現行financial reportはDaisの銀行・カード・Binance・NISAを完全には読んでいない。
- 現行の暗号資産台帳はAniccaのagent economyとDais個人資産を完全な個人CFOとして統合していない。
- `ai.anicca.connector-fill-gaps`と`ai.anicca.connector-daily-report`は既にlaunchd登録済み。
  ただし前者は大半のday taskが180秒timeoutで失敗し、後者はTelegram応答のJSON parseで
  `SEND-ERR`になる。新規Connectorを作るのではなく、この既存loopを修復する。
- `apply-to-yc`はdeprecatedで、後継は`apply-to-funder`。しかし実stateは
  `yc-2026-summer.json = ready_to_submit`、`yc-w26-latest.json = dry_run_planned`であり、
  YC本体の提出receiptはまだ無い。
- `anicca-meetup-talk-applier`にはAI Tinkerers Tokyo/SFの過去提出stateがある。
  一方、connpassは偽陽性防止のため最終click直前で意図的に停止し、accept watcherも
  Gmailを読まず手順を表示するだけである。
- `mufg-epoc-watcher`はMUIT/EPOC向け外部情報briefであり、DaisのMUFG銀行口座や
  個人取引明細を読むconnectorではない。

### 3.1 2026-08-01に再確認したConnectorの既存資産

| 項目 | 実測 | Daisが今渡すもの |
|---|---|---|
| Google Calendar / Gmail | `gog` OAuthで`redacted@example.invalid`のcalendar、gmail scopeが有効 | 追加credentialなし |
| CloakBrowser daily-driver | `:9222`が応答中。Lumaの現在loginは未確認 | 追加browserなし。agentが同profileと既存Google認証でloginを復旧 |
| Telegram | Life Manager / OpenClawのtoken設定あり | 追加tokenなし |
| 応募identity | 氏名、かな、romaji、電話、Google loginの環境設定あり | 秘密値をchatへ再送しない |
| 決済 | 保存済みcardを今回のread-only点検では確認していない | 無料eventから開始。paidも完全自動にする場合は一度だけ自動支出policyを仕様化 |

現在の`anicca-meetup-talk-applier`は再利用できる完成品ではない。実測では`14日`、先頭`1〜2件`、
AI登壇枠だけを対象にし、候補0件をexit 0で終了する。Luma discoverはdisabled、別Chrome`:9223`を
起動する。この制約を延命せず、既存の応募・Calendar・receipt部品をrolling coverage loopへ移す。

## 4. 外部調査からの結論

「類似物が存在しない」ことを前提にしない。既存部品を調査し、使える部分を再利用する。

### 4.1 共通応募・ブラウザ

| 候補 | 確認した事実 | 方針 |
|---|---|---|
| **既存CloakBrowser daily-driver** | CDP `http://127.0.0.1:9222`。job loopのowner probe、Playwright接続、共有context運用が実装済み | **唯一のbrowser transportとして採用済み。events / funders / jobsで共有。新browserを導入しない** |
| [browser-use](https://github.com/browser-use/browser-use) | agent向けブラウザ操作基盤。2026-08-01実測で約10.7万stars、MIT | 調査比較だけ。現在のtrackへ導入しない |
| [Steel Browser](https://github.com/steel-dev/steel-browser) | self-host可能なagent browser API。約7.4千stars、Apache-2.0 | 調査比較だけ。daily-driverの代替として導入しない |
| [Luma API](https://docs.luma.com/reference/getting-started-with-your-api) | 公式APIは主催者自身のevent/guest管理用で、calendar単位keyとLuma Plusが必要 | 参加者RSVPは既存daily-driverを使う |
| [connpass API v2](https://connpass.com/about/api/v2/) | API key必須、1秒1request。公式API外の自動アクセスは禁止 | API key取得までconnpass自動操作を止め、Lumaを先に完成させる |
| [YC創業者動画](https://www.ycombinator.com/video/) | 1分、創業者だけ、全創業者、原稿朗読ではなく要点で話す | 58秒の既存候補を実画面で検証して使用する |

### 4.2 求人応募

| 候補 | 確認した事実 | 方針 |
|---|---|---|
| [AIHawk](https://github.com/feder-cr/Jobs_Applier_AI_Agent_AIHawk) | 求人発見、個別化、自動応募の既存OSS。約3万stars、AGPL-3.0 | form adapter、profile、回答生成、状態管理を研究する。コード流用はlicense確認後 |
| [LinkedIn利用規約](https://www.linkedin.com/legal/user-agreement) | 無許可bot、scraping、message自動化を禁止 | LinkedInへの無許可自動操作を中核railにしない |
| Ashby / Workday | 現行Life Managerにadapterと検証計画が存在 | 実応募receiptを基準に既存実装を完成させる |

### 4.3 個人CFO

| 候補 | 確認した事実 | 方針 |
|---|---|---|
| [Actual Budget](https://github.com/actualbudget/actual) | local-first家計管理、約2.8万stars、MIT | 予算・カテゴリ・月次比較のUXとdata modelを参考にする |
| [Firefly III](https://github.com/firefly-iii/firefly-iii) | 個人財務管理、約2.4万stars、AGPL-3.0 | 口座、取引、予算、rule設計を研究する |
| [Ghostfolio](https://github.com/ghostfolio/ghostfolio) | OSS資産管理、約9千stars、AGPL-3.0 | 純資産、配分、performance画面を研究する |
| [rotki](https://github.com/rotki/rotki) | privacy重視のcrypto portfolio・accounting、約4千stars、AGPL-3.0 | crypto取引、原価、fee、chain receiptのmodelを研究する |
| [Moneytree LINK](https://getmoneytree.com/jp/link/link-api) | 日本の銀行、card、電子money、証券を共通形式で取得。OAuth同意が必要 | Daisの銀行・card・証券を読む第一候補 |
| [Moneytree scopes](https://docs.link.getmoneytree.com/docs/api-scopes) | `accounts_read`、`transactions_read`、投資口座・投資明細scopeが存在 | 最小read scopeから開始する |
| [Binance Spot API](https://developers.binance.com/en/docs/products/spot/rest-api) | `USER_DATA`と`TRADE`を分離可能 | CFOはread-only key。取引・出金権限を与えない |

### 4.4 agent wallet・暗号資産

| 候補 | 確認した事実 | 方針 |
|---|---|---|
| [Franklin](https://github.com/BlockRunAI/Franklin) | USDC wallet、budget、x402を持つ経済agentの既存実装 | wallet-bound agentのUXと会計を参考にする |
| [Coinbase AgentKit](https://github.com/coinbase/agentkit) | agentへwalletとon-chain actionを与える公式toolkit | agent wallet provider候補 |
| [Coinbase Agentic Wallet](https://docs.cdp.coinbase.com/agentic-wallet/welcome) | hold・spend・trade・earnとsecurity guardrailを提供 | 小額agent wallet候補として実測する |
| [Circle Agent Wallet](https://developers.circle.com/agent-stack/agent-wallets) | 支出policy付きagent wallet | CDPとの比較候補 |
| [Safe Smart Account](https://github.com/safe-fndn/safe-smart-account) | smart account、複数署名・module基盤 | personal vaultまたはtreasury候補 |
| [Safe Guards](https://docs.safe.global/advanced/smart-account-guards) | transaction前後の制約をprogramで検査可能。ただし壊れたGuardは停止原因になる | recoveryを含む危険制限にだけ使う |
| [CCXT](https://github.com/ccxt/ccxt) | 100以上の取引所・予測市場を共通化、約4.3万stars、MIT | 読取・試作の共通adapter。資金移動は公式SDKを優先 |
| [Binance公式connector](https://github.com/binance/binance-connector-python) | Binance Public APIの公式connector | Binance固有処理はこちらを優先 |

### 4.5 日本株・NISA

| 候補 | 確認した事実 | 方針 |
|---|---|---|
| [J-Quants](https://jpx-jquants.com/) | JPX公式の日本株data API。V2はAPI key方式 | 銘柄・価格・財務data候補 |
| [kabuステーションAPI](https://kabu.com/item/kabustation_api/default.html) | 個人向けの自動取引APIを公式提供。事前設定と対応環境が必要 | Daisの証券会社・口座区分・NISA対応を実画面とAPIで検証してから採用 |
| [金融庁NISA](https://www.fsa.go.jp/policy/nisa2/know/index.html) | 年間360万円、総枠1,800万円、つみたて枠と成長枠を併用可能 | 枠計算と口座区分の制度正本 |

### 4.6 既存OpenClaw資産 — 作り直さず移植する

| 既存資産 | 実測状態 | Life Managerでの扱い |
|---|---|---|
| `ai.anicca.connector-fill-gaps` | 毎朝07:50。CloakBrowser `:9222`と`gog`を使うが、多数のbounded agentがtimeout | schedulerは残し、1日1巨大fan-outをdurable queueへ分解 |
| `connector_daily_report.sh` | Telegram日報を持つが、送信responseのparseが壊れる | Telegram adapterの戻り値contractを直し、delivery receiptをledger化 |
| `anicca-meetup-talk-applier` | discover、AI Tinkerers応募、Calendar登録、state JSONが存在 | pitchとplatform知識をevents packへ移植。別loopとしては退役 |
| `connpass-lt-discover.py` | LT枠を分類できるが、証跡不足のためsubmit直前で停止 | API keyまたは確認mailを含むE1/E2/E3経路ができるまで送信禁止 |
| `apply-to-yc` | 20 text fields、動画、validationまで到達。deprecated | 画面知識だけ`apply-to-funder`へ移植。二重submitしない |
| `apply-to-funder` | JSON form specとguardrailがある。YC/JSTはdry-run止まり | funders packの入力adapterとして残し、stateは共通ledgerへ移す |
| `apply-anywhere` | YC、ANRI、Coral、Solo Founders等の過去receiptを記録 | ATS/form routing知識を共通ACTへ移植。未実装shell骨格を正本にしない |
| `gog` 0.17.0 | Gmail/Calendarのlocal OAuth CLIが導入済み | localのread/write transportに採用。MCPを定期workerの必須dependencyにしない |
| Job Hunter confirmation ledger | message/thread ID、時刻、evidence hash、fence、dedupが実装済み | events/funders/jobsの共通result trackerへ一般化 |
| `mail-gog.js` / `calendar-gog.js` | Life Manager内にadapterとtestが存在 | local共通transport。Web版は同interfaceのtenant別Google OAuthへ差し替え |
| `cfo-core` | AniccaのBase USDC、x402、LLM cost中心 | agent economy subledgerとして残す。Dais個人CFOとはownerで分離 |
| `mufg-epoc-watcher` | 外部AI情報のSlack brief | 個人口座connectorに流用しない。この5段階の金融data sourceではない |

移植はcopy-and-forgetにしない。旧loopと新loopをshadowで動かし、同じ入力に対する
候補・実行・receiptを比較する。新loopが予定runを7回連続で完了してから、旧cronまたは
launchdを一つずつ退役する。

### 4.7 外部の金融multi-agent実装 — 2026-08-01 GitHub実測

| repository | 実測した構造 | license / 成熟度 | Life Managerへ持ち込むもの |
|---|---|---|---|
| [FinRobot](https://github.com/AI4Finance-Foundation/FinRobot) | Lead Agent、data/analysis/modeling/synthesis/reportの5 specialist、bull/bear/judgeの3 debate agent。数値はpure Python、説明はLLM、出典追跡 | 約7.7k stars、Apache-2.0 | **Financial Organの主な構造正本**。CFO→specialist、決定的計算、provenanceを移植 |
| [TradingAgents](https://github.com/TauricResearch/TradingAgents) | fundamentals/sentiment/news/technical analyst、bull/bear、trader、risk team、portfolio manager。checkpoint、decision log、結果reflection | 約95.2k stars、Apache-2.0。研究用途で投資助言ではない | Order 4/5の分析・反対意見・risk review・paper trade・reflection構造を移植 |
| [ai-hedge-fund](https://github.com/virattt/ai-hedge-fund) | 17 analyst、Risk Manager、Portfolio Manager。backtesterあり | 約62.5k stars、MIT。proof of conceptで実取引しない | riskと最終portfolio承認の分離、backtest harnessを参考。著名投資家personaの大量複製はしない |
| [OpenBB](https://github.com/OpenBB-finance/OpenBB) | proprietary/public dataを一度接続し、Python、REST、MCP、UIへ共通提供 | 約71.2k stars、独自license | 市場data providerの共通interfaceを参考。個人口座・予算・執行systemとしては使わない |
| [Actual Budget](https://github.com/actualbudget/actual) | local-first、account、transaction、envelope budget、device sync | 約27.9k stars、MIT | 口座・取引・予算・rule・local-first UX/data modelを移植候補 |
| [Ghostfolio](https://github.com/ghostfolio/ghostfolio) | multi-account、株/ETF/crypto、期間別performance、portfolio risk | 約9.0k stars、AGPL-3.0 | 純資産・配分・performance UXを研究。license判断なしにコードcopyしない |
| [rotki](https://github.com/rotki/rotki) | local encrypted data、exchange/chain balance、transaction decoding、PnL/accounting | 約4.0k stars、AGPL-3.0 | Crypto subledger、原価、fee、chain/exchange照合を研究。license判断なしにコードcopyしない |

結論:

- 完成品を一つ丸ごとcopyできるrepositoryは確認できなかった。
- **FinRobotのorgan構造 + Actual Budgetの家計model + Ghostfolioの資産UX +
  rotkiのcrypto会計 + 既存Life Manager/OpenClawの実行・Telegram・応募loop**を合成する。
- generic multi-agent frameworkのCrewAI/AutoGenを新たなruntime正本にしない。既存OpenClawと
  Life Manager durable runtimeの上で、必要なspecialistだけをtaskとして呼ぶ。
- 外部repositoryのagent出力を、そのまま金銭executionへ接続しない。研究・提案・paperの
  inputとして使い、最終的な金額計算・上限・署名・照合はLife Manager自身が所有する。

### 4.8 YC応募の既存skillと現在地

| 項目 | 実測 |
|---|---|
| 旧skill | `~/.openclaw/skills/apply-to-yc/` |
| 実行script | `~/.openclaw/skills/apply-to-yc/scripts/apply.sh` |
| 後継skill | `~/.openclaw/skills/apply-to-funder/` |
| 既存application ID | `99b966b0-7e90-4856-ab0d-93651488a4ea` |
| 既存state | Summer 2026 late、20 text fields入力、動画upload記録、validation errorなし、`ready_to_submit` |
| 実際の提出状態 | submit receiptなし。**未提出として扱う** |
| 後継state | `yc-w26-latest.json = dry_run_planned`。古いW26 specを現在batchへそのまま使わない |
| 公式current batch | [YC Fall 2026](https://www.ycombinator.com/apply)。on-time deadlineは7月27日だがlate application受付中 |
| batch | 2026年10〜12月、San Francisco |

旧`apply-to-yc`はdeprecatedだが、20項目、動画、progress page、React formの実画面知識を持つ。
この知識を捨てず、後継`apply-to-funder`のYC providerへ移す。ただし旧skillが使う別Chrome
`9223`は起動せず、現行の唯一のCloakBrowser daily-driver `:9222`へ接続する。

YC提出手順:

```text
YC公式pageでlate application受付を当日再確認
  → CloakBrowser daily-driverでapply.ycombinator.com/homeを開く
  → 既存application IDがFall 2026へ継続可能か実画面で確認
  → application-kit、production、dashboardから会社factsを再生成
  → 20項目、founder profile、動画、demo、progressを現在値で更新
  → 全回答と添付をpreviewで保存
  → 一度だけSubmit
  → 完了画面とconfirmation mailを取得
  → Gmail thread、application URL、提出内容を同じdecisionへ保存
  → Telegramへ応募内容、動画、deck、確認mailの直接linkを送る
  → reply/interviewを毎日追跡
```

## 5. 残作業 — 必ず番号順

完了: `O1B-01`。追加実測で、E1/E2/E3 verifierは存在するが、runtime workerは
`outbound.event.apply` handlerが返した任意の`receipt`をそのままcompletedへ保存できると判明した。
bare `{status:"success"}`、DOM自己申告、verifier結果のJSON copyを成功にしない。現在のprocessで実際に
E1/E2/E3 verifierが生成したverified objectから作られ、同じtenant/job/attemptへboundされたreceiptだけを
完了可能にする。証拠不成立は外部効果の有無が不明なため`unknownEffect=true`でreconciliationへ渡す。
fresh verificationはoutbound 31件、runtime worker回帰31件が成功した。実装commit: `4ea9e931a`。
実装plan: `docs/superpowers/plans/2026-08-01-connector-o1b01-remove-fake-success.md`。evidence:
`docs/evidence/outbound/2026-08-01-o1b01-fake-success-gate.json`。後続の`O1B-02`も完了した。

完了: `O1B-02`。URL不具合は2件ある。Calendarへ一回性`/join/complete/`を保存する不具合は
旧Connectorの`gcal_write.py`と現在のOpenClaw配備版ではすでに拒否・canonical URL分離が入っている。
connpass subdomainについても`~/.openclaw`配備版は検索結果のURLを保持するが、
`profitable-claude`内の古いvendor copyはevent IDだけを残し、`https://connpass.com/event/<id>/`へ
再構築する退行状態だった。配備版だけを暗黙の正本にせず、provider非依存のcanonical URL契約を
`life-manager`へTDDで置き、E3 verifierと旧配備監査を同じ契約へ揃える。実装plan:
`docs/superpowers/plans/2026-08-01-connector-o1b02-canonical-event-url.md`。

O1B-02進捗1: `life-manager`正本にprovider非依存のcanonical event URL境界をTDDで追加した。
REDはmodule不存在で失敗した。GREENではHTTPS・credentialなし・一回性URL拒否を共通化し、connpassは
検索結果のgroup subdomainとevent IDを保持したまま末尾slashへ正規化し、tracking queryとfragmentを
除去する。E3 verifierもこの境界へ接続し、正規化後のgroup URLへredirectなしHEADを行う。freshの
canonical/E3 9件とoutbound全体36件を通してから実装commitを作る。次は配備版と古いvendor copyの
回帰監査。

O1B-02進捗2: 再配備元の`profitable-claude/main`にも2件を反映した。Calendarはcanonical event URLを
独立引数で受け、一回性URLを拒否し、description先頭をタップ可能なcanonical URLにするcommit
`d75c19f`。connpassは検索snapshotからevent IDとgroup hostを一緒に保持し、root domainへ再構築しない
commit `c901bab`。新規Python回帰4件と既存Calendar回帰7件が成功した。`life-manager`側には配備版と
再配備元を5条件でfail closed監査するscriptを追加し、監査2件とoutbound全体38件が成功した。
実配備版にだけ存在する「証拠経路のない旧connpass submit停止」は保持し、古い応募処理で上書きして
いない。次は現行canonical URL 10件の実HEAD 200証拠化。

O1B-02完了実測: Web検索と公式connpass group inventoryから得たgroup subdomain付きcanonical URL
10件を、実runtimeと同じNode HEAD・redirect manualで再確認し、10/10が200、redirect 0、
`/join/complete/` 0だった。fresh verificationは`life-manager` outbound 38件、runtime 31件、
`profitable-claude`新規URL回帰4件、既存Calendar回帰7件、旧配備監査5/5が成功した。
証拠: `docs/evidence/outbound/2026-08-01-o1b02-canonical-event-urls.json`。次は`O1B-03`。

実行中: `O1B-03`。2026-08-01の着手実測で、既存CloakBrowser daily-driver
`http://127.0.0.1:9222`はChrome 145 / CDP 1.3として応答した。一方、production
`config/loop-adapters.json`は5 adapterだけで`outbound.event.apply`が存在せず、workerはcapabilityを
広告しても実handlerを持たない。既存Luma auth bootstrapはSteel transport向けであり、今回の唯一の
daily-driver transportではない。第二browserや第二runtimeを作らず、CDP read-only契約、Luma discovery、
effect-fenced RSVP、E1/E2/E3 completionを順番に既存registryへ接続する。実イベントsubmitは次の
`O1B-04`まで行わない。実装plan:
`docs/superpowers/plans/2026-08-01-connector-o1b03-luma-daily-driver-adapter.md`。

O1B-03進捗1: `:9222`はChrome 145 / CDP 1.3、共有context 1つとして稼働中。既存pageは
閉じず、自分で作ったread-only pageだけをcloseした後もCDP生存を確認した。Luma cookieは10件あり、
過去登録marker 5件も残るが、`https://luma.com/home`は描画後`/signin`へ遷移し、email login formと
sign-in表示を返したため、**現在のLuma loginはexpired**と確定した。cookieの値は読出し・保存・出力して
いない。adapterはこの状態を成功にせず`login_required`として分類し、既存daily-driver上のGoogle/Luma
認証を復旧してから実submitへ進む。

O1B-03進捗2: CloakBrowser daily-driver transportをTDDで正本へ追加した。REDはmodule不存在、GREENは
新規4件とoutbound全体42件成功。CDP endpointを`127.0.0.1:9222`だけに固定し、Luma HTTPS origin、
credentialなし、共有context 1つを必須にした。既存pageをtaskへ渡さず、自分で作ったpageだけを例外時も
closeし、browser自体はcloseしない。実moduleを`:9222`へ接続したread-only確認でも
`existing_page_count=1`、`login_required`、path `/signin`を返し、その後もdaily-driver生存を確認した。
次は東京対面Luma inventoryのdiscovery契約。

O1B-03進捗3: Luma Tokyo discoverは仮想scrollで、実DOM候補数が`15→23→16`と減るため、最終DOMだけを
読むと候補を落とすことを確認した。各scroll snapshotのevent cardをcanonical URLで累積し、終端で
scroll heightと新規候補0件が3回連続安定した場合だけ`complete=true`にするcollectorをTDDで追加。
実ページは7 roundsで終端、27候補を取得し、AI以外の候補も保持した。event detailは公式JSON-LDから
開始・終了・attendance mode・会場・開催statusを取得し、実buttonの完全一致からauthとRSVPを分離する。
実候補`https://luma.com/h8157e6c`は対面、2026-08-02 09:30 JST開始、会場取得済み、
`login_required`かつ`rsvp_status=available`だった。数値定員が非公開なので推測せず
`capacity_status=availability_control_only`とした。新規discovery 5件、detail 5件、outbound全体52件が
成功。次は同日次候補へ進む失敗分類。

O1B-03進捗4: 同日candidate sequenceをTDDで追加した。満席、waitlist、承認制、不適格、競合、cancelは
同日の次candidateへ進み、実verifier receiptを伴う`verified_registered`だけでbookedになる。
login切れ・transport停止・inventory未完了は全candidateを無駄に消費せず復旧へ移し、submit後の
`unknown_effect`や未検証successは二重応募せずreconciliationへ止める。Luma候補を最後まで使い切った
場合だけ`next_provider_required`として同日をconnpassへ渡す。新規sequence 4件、outbound全体56件が
成功。Task 2完了。次はproduction RSVP adapterとeffect fence。

O1B-03進捗5: Luma RSVP adapterを既存`outbound.event.apply`へ接続した。submit直前の登録状態を
effect fenceとして再読出しし、`registered`は再送せず証拠検証、`login_required`と明確な
`unavailable`は外部効果なし、submit後の不明状態だけを`unknownEffect=true`としてreconciliationへ
送る。Luma provider receiptとPNGはtenant配下の不変objectとして保存し、同一attemptのE1 provider
response、E2 PNG、E3 canonical URLが全て実verifierを通った時だけruntime completion receiptを返す。
production manifestはportableな`outbound-luma-rsvp`を登録し、workerは同じruntime data rootと
CloakBrowser daily-driverを使う。Docker内では`host.docker.internal`をprivate IPv4へ解決するが、
owner portは`:9222`から変更できず、public IP・別port・第二browserを拒否する。fresh verificationは
outbound 68件、runtime-up 32件、runtime-adapters 121件が成功した。実Luma登録はO1B-04まで行わない。

完了: `O1B-03`。正本Dockerfileからimageをbuildし、base compose + Connector overlayだけでworker一台を
recreateした。runtime volume、PostgreSQL、object storeは削除せず、Honneの
`marketing.video.generate`を含む既存3能力を保持した。production worker内でadapter file、manifest
route、fresh healthを確認し、同じCloakBrowserへCDP接続した実Luma read-only handlerは
`login_required / unknown_effect=false`を返した。submitと成功報告は0。live evidence:
`docs/evidence/outbound/2026-08-01-o1b03-luma-daily-driver-adapter.json`。次はO1B-04で同じprofileの
Luma認証を復旧し、実イベント一件の登録をverified receiptまで成立させる。

O1B-04開始: 専用plan
`docs/superpowers/plans/2026-08-01-connector-o1b04-live-luma-registration.md`を追加した。既存
`redacted@example.invalid`の`gog` OAuthはGmail/Calendarともread可能で、過去Luma sign-in code mailも
実在する。新しいcodeは同じ`:9222` pageから要求し、request後に届いた新着mailだけを自動照合する。
code値、mail本文、cookie、tokenは正本やlogへ残さない。

O1B-04進捗1: 既存CloakBrowser daily-driverの共有context 1つだけを使い、
`redacted@example.invalid`へ新しいLuma sign-in codeを要求した。最初のpollは英語件名に限定したため、
実際に届いた日本語件名を見落とした。検索を`support@luma.com`送信元と今回要求の直近時刻へ修正し、
直近15分の今回要求分だけを同じOTP pageへ入力した。code値は保存・spec記載・最終出力していない。
認証後readbackは`https://luma.com/home`、auth inputなし、共有context 1、既存browser維持。
実event `https://luma.com/h8157e6c`のread-only再確認は`login_required`ではなく、
`scheduled / in_person / rsvp_status=available`を返した。次はCalendar全pageとLuma inventoryを照合する。

O1B-04進捗2: Google Calendarを2026-08-01〜08-21、全calendar、全pageで取得し、127件を読んだ。
認証後のLuma Tokyo inventoryは終端7 rounds、27/27 detail取得、detail failure 0。表面上の対面受付中は
3件だったが、8/2 09:30–12:00は10:33以降の既存予定と競合、8/19 10:00–13:00は
8:40–17:10の既存予定と競合した。8/4 19:00–22:00はpage本文で会場券売切・online券だけ受付中と判明。
この実測により、hybrid eventのgeneric「参加登録」を対面空席と誤認する不具合をREDで再現し、
会場参加ticketが全て売切なら`rsvp_status=full`を優先するよう修正した。focused 6/6、outbound 69/69。
まだ実登録は0。Luma内の追加検索とweb indexへ探索範囲を広げ、Calendar非競合の対面eventまで継続する。

O1B-04進捗3: Lumaの正しいTokyo place pageは`https://luma.com/tokyo?k=p`であり、終端7 rounds、
35件だった。旧`/discover/tokyo`の27件より8件多いため、正本discovery URLも後続で置換する。
追加候補のSupabase Meetup Tokyo #1（8/5 19:00–22:00）は既存予定が17:10までで競合しないが、
実pageはすでに`参加確定 / Ticket: Standard / マイチケット`を表示した。現adapterが日本語の
`マイチケット`を登録済みmarkerとして認識しない二重登録riskをREDで再現し、detailとsubmit後readbackの
両方へmarkerを追加した。focused 10/10、outbound 70/70。既存登録はverified receiptへ回収し、
O1B-04の実submit用には別の未登録・非競合候補を探索する。

O1B-04進捗4: 正しいTokyo place inventoryとweb index候補を本文まで再読出しし、未登録・即時確定・
Calendar非競合の`Engineer BAR`（`https://luma.com/a879ax7k`、8/15 18:00–23:00、
新宿、途中入退場可）を実submit候補に選んだ。当日の既存予定は15:00までで3時間の余白がある。
Luma上の登録費・前払いは0だが、現地でチャージ1,000円 + 1ドリンク700円が必要。
pageの実buttonは`ワンクリックで参加登録`であり、旧adapterはunknownにしたためREDを追加。
detail availabilityとbrowser submit selectorを日本語実DOMへ対応し、focused 12/12、outbound 72/72。
次は新imageをworkerへ配備し、durable runtime jobを一度だけ実行する。

O1B-04進捗5: 新imageをworkerへ配備し、対象jobがDBに未存在であることを確認して初回enqueueを試したが、
外部操作前に`runtime effect class invalid`で停止した。真因は`enqueueEventApplication`が
`buildRuntimeJob`のcanonical snake_case出力を、そのままcamelCase入力専用だった`enqueueJob`へ再投入する
shape mismatch。DB行0、Luma click 0を確認した。canonical jobを実`enqueueJob`へ渡すREDを追加し、
runtime storeが曖昧なmixed shapeを拒否しつつ自身のcanonical出力を受理するよう修正した。
runtime-job 14/14、outbound 72/72。次のenqueueが引き続き同jobの実初回となる。

完了: `O1B-04`。最新imageをworkerへ配備し、`Engineer BAR`の新規durable jobをenqueueした。
`created=true`、attempt 1、provider submit 1、8秒以内に`completed`。receiptはE1 Luma provider response、
E2 497,151-byte PNG、E3 canonical URLを同一attemptで検証した`status=verified`で、live pageも
`rsvp_status=registered`を返した。既存Calendar policyで直前競合を再確認し、本体8/15 18:00–23:00、
往路17:15–17:45、復路23:05–23:30をGoogle Calendarへ作成し、3 IDを再読出しした。実装/証拠:
`docs/evidence/outbound/2026-08-01-o1b04-live-luma-registration.json`。次は固定順序どおりO1B-05で、
この同じeventの確認mailをGmailから照合する。

完了: `O1B-05`。専用plan
`docs/superpowers/plans/2026-08-01-connector-o1b05-confirmation-mail.md`に従い、既存`gog` Gmail
OAuthだけを使い、O1B-04と同一registration attemptのLuma mailからmessage ID、受信時刻、送信元、
event title、canonical event URLを照合した。Gmail `internalDate`は14:38:38Z、runtime attemptは
14:38:32.325780Z〜14:38:40.076343Zだった。Lumaはsubmit受理後、workerの完了画面検証より先に
mailを送るため、同一attempt開始後〜完了30分後を因果windowとする。別event、attempt開始前、
完了30分超、曖昧件名、非Luma送信元はtestで拒否する。mail本文とaddressは保存せず、tenant/job/eventへ
boundしたimmutable `gmail-message://` receiptだけをruntime volumeへ保存し、別processで再読出しした。
focused 5件、outbound 77件が成功した。実測証拠:
`docs/evidence/outbound/2026-08-01-o1b05-live-luma-confirmation-mail.json`。次はO1B-06で、
同じeventの照合済みGmail messageからguest keyを同一processのmemoryにだけ読み、実QRを取得する。

O1B-06開始: 専用plan
`docs/superpowers/plans/2026-08-01-connector-o1b06-luma-ticket-qr.md`を追加した。O1B-05で照合した
同一Gmail messageだけからguest-specific ticketを同一processのmemoryへ読み、guest key、ticket URL、
mail本文を永続化しない。まず既存CloakBrowser `:9222`の`マイチケット`を実測し、Luma公式QRがあるなら
payloadを推測した自作QRへ置き換えない。完成物はtenant/job/eventへboundしたhash検証済みPNGだけである。

完了: `O1B-06`。既存CloakBrowser `:9222`の同一sessionで`Engineer BAR`の`マイチケット`を開いた。
Lumaは200×200 SVGの公式QRを表示し、そのdecode payloadは旧specが想定したevent URLではなく、
Luma公式`check-in/<opaque>` URLだった。QR内guest keyとO1B-05の確認mail内guest keyを平文を残さず
SHA-256で照合し一致した。公式SVGを10,140-byte PNGへcaptureし、tenant/job/event boundのticket receiptと
objectへruntime volume内で保存した。別processからreceiptとPNGを再読出しし、PNG hash、公式check-in path、
guest-key hashを再検証した。guest key、ticket URL、mail本文は永続化していない。focused 4件、outbound
81件が成功した。実測証拠:
`docs/evidence/outbound/2026-08-01-o1b06-live-luma-ticket-qr.json`。次はO1B-07でこのartifact refだけを読み、
人間向けevent名・日時・会場・event link・Calendar linkと一緒にTelegramへ実送信し、positive message IDを得る。

O1B-07開始: 専用plan
`docs/superpowers/plans/2026-08-01-connector-o1b07-telegram-ticket-delivery.md`を追加した。O1B-06の
verified artifact refだけを読み、技術語やhashではなくevent名・日時・会場・選定理由を日本語で説明する。
eventとCalendarはplaceholder buttonではなく実URLをcaptionへ入れ、Telegramから直接tapできる形にする。
既存OpenClaw Telegram transportで一度だけ送信し、positive message ID以外を成功にしない。

完了: `O1B-07`。O1B-06のtenant-bound QR PNGをruntime volumeから読み、非技術者向け日本語captionを
組み立てた。captionは`Engineer BAR`、8月15日18:00〜23:00、新宿の会場、Dais名義、選定理由、
Luma確認mail済み、Google Calendar済みを説明し、eventとCalendarの実URLを直接tapできる形で含む。
既存OpenClaw Telegram accountからQR photoを一度だけ実送信し、positive message ID `5103`を得た。
最初の2回は許可外temporary pathをOpenClawがdelivery前に拒否したためTelegram side effectは0であり、
OpenClaw自身のowner-only `/tmp/openclaw` media rootへ修正後の一回だけが配信された。temporary PNGは送信後に
削除し、chat IDはhashだけ、bot tokenとguest keyは保存しない。focused 5件、outbound 86件が成功した。
実測証拠: `docs/evidence/outbound/2026-08-01-o1b07-live-telegram-ticket-delivery.json`。
次は固定順序どおりO1B-08で、agentがevent本文から一般参加とLT/CFP/demo枠を判断するevalを通す。

O1B-08開始: 専用plan
`docs/superpowers/plans/2026-08-01-connector-o1b08-talk-slot-agent-eval.md`を追加した。固定keywordで
`LT`を探すclassifierには戻さない。event本文全体をGemini structured outputで読み、公開応募中、締切済み、
招待制、単なるspeaker紹介、一般参加のみを区別する。agentの根拠は本文中の連続substringであることを
deterministicに検証し、公開応募URLとopen statusが揃う場合だけtalk application entityを作る。

完了: `O1B-08`。Gemini 2.5 Flashのstructured output classifier、厳格schema、cross-field invariant、
本文中の連続substring根拠、HTTPS application URL検証を追加した。keyword fallbackはなく、model/schema失敗を
登壇枠ありへ変換しない。held-out 8件は公開LT、公開CFP、締切済みCFP、招待制demo、speaker紹介だけ、
一般参加workshop、event本文内prompt injection、公開demoである。初回は招待制demoのtaxonomy曖昧さにより
7/8だった。`participation_kind`はevent内の枠の存在、`application_status`と
`should_create_talk_application`は今の応募可否と明確化し、caseや期待値を削らず再実行して8/8になった。
focused 5件、outbound 91件が成功した。実測証拠:
`docs/evidence/outbound/2026-08-01-o1b08-live-talk-agent-eval.json`。次はO1B-09で旧Connector loginと
既存events packの実装を棚卸しし、正本runtimeへ必要知識だけを統合する。

O1B-09開始: 専用plan
`docs/superpowers/plans/2026-08-01-connector-o1b09-events-pack-integration.md`を追加した。O1B-04で
一度だけ実証したDaisのLuma email-code認証復旧を、既存CloakBrowser daily-driver、Luma discover、
`outbound.event.apply`から再利用できる正規events packへ統合する。旧Connectorと`anicca-booking`は
棚卸し元だけにし、`PROPOSED`先行、Slack、CamoFox、AI/crypto hard filter、別schedulerは移植しない。
同じ`:9222` context、Calendar全page、既存`gog` Gmail OAuth、登録後証拠だけを正本へ残す。
認証復旧は応募effect開始前に一回だけ許可し、code、cookie、mail本文、tokenを保存・出力しない。
O1B-09の範囲はlogin/events pack統合までで、21日coverageは固定順序どおりO1B-16以降で行う。

O1B-09進捗1（RED）: 認証済みsession再利用、login切れからのGmail code復旧、code不正、復旧後の
authenticated readback不成立、認証前のevent task禁止、同時実行時の復旧一本化を固定するtestを追加した。
さらにdiscoverとRSVPが必ず同じauth-aware daily-driverを受け取るevents pack composition testを追加した。
production moduleはまだ存在しないため、この時点のREDはmodule不存在で失敗することを期待値とする。

O1B-09進捗2: auth-aware daily-driverとevents pack compositionを実装し、既存Luma transport/provider/
discovery/detailを含むfocused 30件が成功した。認証済みならmailを要求せず、login切れだけを一回復旧し、
同時callerは同じ復旧promiseを共有する。次のREDとして、request時刻より古いmail、偽Luma sender、別宛先、
不正codeを拒否し、選択した`gog` accountの新着Luma mailだけを読むreader contractを追加した。

O1B-09進捗3: host read-only events packの初回live runは安全に失敗し、応募副作用は0だった。identity、
CDP、browserは正常で、root causeはLuma Homeの認証済みnavigationが旧`Create Event / My Events`文言から
日本語の`/create`と`/home/calendars`へ変わり、sessionを`unknown`と誤分類したstale markerだった。
同一origin、`/home`、2本のprotected navigation、active auth controlなしの組合せへ更新し、UI表示言語に
依存せず、公開login copyだけでは認証済みにしない境界へ修正した。次はfocused回帰とlive再実測を行う。

O1B-09進捗4: marker修正後のfocused 24件が成功した。実`:9222`でhost events packを再実行し、
`authenticated=true`、`recovered=false`、inventory終端6 rounds、reference-only候補33件を取得した。
既存Dais sessionを再利用したため認証mail送信、code取得、応募submit、Calendar writeはすべて0だった。
このread-only entrypointを正本`test:outbound`へ追加し、以後の全Connector回帰でpack境界を検証する。

O1B-09進捗5: workerの`outbound.event.apply`も直接Luma providerを組み立てず、同じcanonical events packから
providerを取得する構成へ変更した。host coordinatorはGmail付き復旧を担当し、workerは応募effect直前に
同じ`:9222` sessionをread-only再確認する。session切れならsubmit前に停止し、次のhost passが一回だけ復旧する。
outbound 106件、runtime 33件が成功した。最終live read-onlyは`authenticated=true`、`recovered=false`、
inventory終端7 rounds、候補35件で、mail・応募・Calendar副作用は0だった。次は実装commit後、そのcommitを
指すsecretなしevidence JSONを保存してO1B-09を完了する。

完了: `O1B-09`。Daisの既存Luma sessionを再利用し、期限切れ時だけrequest後の新着Luma mailから
6桁codeを取得するhost recovery、discover/detail/RSVPが共有するcanonical events pack、workerの
submit前read-only auth gateを正本へ統合した。初回liveでLuma日本語UI変更によるstale markerを発見し、
同一originのprotected navigationで修正した。最終liveは認証済み、復旧不要、inventory終端7 rounds、
候補35件、認証mail・応募・Calendar・Telegram副作用0だった。outbound 106件、runtime 33件が成功した。
実測証拠: `docs/evidence/outbound/2026-08-01-o1b09-live-events-pack-integration.json`。
次は固定順序どおりO1B-10で、旧Connector launchdと旧報告経路を停止し、正本runtimeだけを残す。

O1B-10開始: 専用plan
`docs/superpowers/plans/2026-08-01-connector-o1b10-retire-legacy-runtime.md`を追加した。対象は
`ai.anicca.connector-fill-gaps`と`ai.anicca.connector-daily-report`の固定2 labelだけである。
bootout + disable後、plistは削除せずowner-only state archiveへchecksum付きで移す。正規Guardian、
Docker worker、PostgreSQL、runtime volume、他launchdには触れない。旧repositoryのdirty worktreeも
編集しない。再登録経路を塞ぎ、正規events packとworkerのlive healthを確認してから完了にする。

O1B-10進捗1（RED）: temp LaunchAgentsと偽launchctlを使い、固定2 labelだけのbootout・disable・
recoverable archive、SHA-256 manifest、rollback説明、Guardian非変更、二回目idempotency、危険なroot/relative
path拒否を固定するtestを追加した。production retirement scriptはまだ存在しないためmodule path不在でREDになる。

O1B-10進捗2: 固定2 labelだけをbootout + disableし、owner-only archiveへplistを移し、SHA-256と
rollback手順をmanifestへ残すidempotent scriptを実装した。archive済みplistと同一内容が再出現した場合も
削除せず`reappeared` artifactとして退避する。temp実機相当test 3件とshell syntaxが成功し、正規Guardian
plistがbyte単位で変わらないことを確認した。次は旧launchd registryをisolated clean worktreeでdisabledへ
移し、現在のdirty worktreeには触れず再登録・誤警告を防ぐ。

O1B-10進捗3: 旧registryはplistを生成するinstallerではなくread-only inventoryだった。ただしfill-gapsを
`enabled`と誤表示していたため、旧repoの現行branchで未変更だったregistry 2ファイルだけを個別stageした。
fill-gapsをrevenue/enabledから除き、fill-gapsとdaily-reportをretired/disabled、owner=`life-manager`へ移した。
他のwriter作業中変更には触れていない。launchd inventory test 22件が成功し、実inventoryで固定2 labelが
desired=`disabled`、owner=`life-manager`となった。旧repo commit `a5eab2e`を同branchへpush済み。
次は正本commit後、実2 labelをrecoverable archiveへ移してlive verificationする。

O1B-10進捗4: 初回live retirementは成功扱いせずexit 3で停止した。fill-gapsをbootout + disableした直後、
直前preflightで存在を確認した旧plist実体がなく、archiveも未作成だったためである。正規Guardianとworkerには
影響しない。root causeはscriptがarchive確保よりlaunchd変更を先に行った順序欠陥だった。2 plistを先に
archive確保してからlaunchdを変更する順へ修正し、今回すでに消えた実体にはpreflightで読んだLabel、command、
log path、scheduleをXML plistとして正本に固定したverified fallbackを使う。次は追加回帰後に再実行する。

完了: `O1B-10`。旧fill-gapsと旧daily-reportは両方ともlaunchctlから不在、persistent disabled、元plist不在、
owner-only archiveとSHA-256 manifestありになった。初回のarchive順序欠陥を直し、消失後のplistは直前の
`plutil`実測内容からverified fallbackを正本化した。旧registryも両方retired/disabledへ移した。正規Guardianは
run 26、last exit 0、workerはrunning/healthyで`outbound.event.apply`を保持する。events pack live read-onlyも
認証済み、inventory終端7 rounds、35候補で成功した。outbound 110件、runtime 33件、旧inventory 22件が成功。
実測証拠: `docs/evidence/outbound/2026-08-01-o1b10-live-legacy-retirement.json`。
次は固定順序どおりO1B-11で、connpassの現行公式API提供・申請経路を確認し、key取得まで自動アクセスを禁止する。

O1B-11開始: 専用plan
`docs/superpowers/plans/2026-08-01-connector-o1b11-connpass-api-application.md`を追加した。2026-08-01の
connpass公式help、v2 reference、利用規約を再調査した。v2は全endpointでAPI key必須。referenceは1秒1requestだが、
2026-08-01に実画面で確認した個人申請formはさらに厳しく5秒1request以下を要求するため、実装は5秒間隔に固定する。
個人・コミュニティは無料審査制でkey 1本、審査約5営業日、個人申請は非商用同意必須である。企業利用は
月額297,000円または年額3,564,000円。v2には参加申込みendpointがなく、events/groups/users等のGETだけである。
さらに公式API以外の自動crawler/scraper等は規約で禁止される。よって個人keyはDais本人のローカル・非商用・
read-only event discoveryだけに使い、Life Manager Webへ転用しない。connpass browser自動申込みは行わず、
Lumaを実予約sourceとしてcoverageを埋める。key受領まではconnpassへの全自動network accessをcodeで0にする。

O1B-11進捗1（RED）: key欠落時network 0、公式`/api/v2/events/` GETと`X-API-Key`だけ、任意URL・POST・
不正query拒否、公式申請formの厳しい方へ合わせた5秒間隔の直列化、HTTP/schema failure時のsecret非反射を固定するtestを追加した。
production clientはまだ存在しないためmodule不存在でREDになる。実runtime auditでは旧launchd 2本は退役済みだが、
stale OpenClaw jobs fileに`connpass-lt-apply-daily`と`anicca-booking-daily`がenabledで残り、正本
`anicca-booking`にもFirecrawl/ブラウザconnpass経路が残ることを確認した。これらもkey申請前に無効化する。

O1B-11進捗2: 公式v2 GETだけを許すfail-closed clientを実装した。key欠落時network 0、固定endpoint、
`X-API-Key`、query schema、5秒間隔、secret非反射をtestで固定した。stale OpenClaw jobsは
`anicca-meetup-discover-daily`、`anicca-meetup-apply-tokyo-weekly`、`connpass-lt-apply-daily`、
`anicca-booking-daily`の固定4本だけをdisabledへ変更し、自己防衛用`anicca-cron-auto-disable`はenabledのまま
保持した。旧`anicca-booking`はretired tombstoneへ置換し、runnerはcredential読取・network接続より前にexit 78、
旧proposerからconnpass URLを削除した。focused 7件とoutbound 117件が成功した。key審査中もConnectorは止めず、
認証済みLumaだけで21日coverageを埋める。

完了: `O1B-11`。既存の本人設定から申請者名、connpass username、Gmail accountを取得し、raw値を
specや証拠へ保存せず、公式個人・コミュニティ向けAPI利用申請formへ送信した。用途はDais本人の
ローカルPCだけ、個人・非商用、1日1回のbatch、東京で今後21日以内のevent、最大30日非公開保存、
第三者利用なし、リアルタイム呼出しなし、connpass参加申込みなしと明記した。送信後に公式Google Formの
`formResponse`遷移を確認した。審査目安は約5営業日。key受領まではclientがnetwork 0でfail closedし、
ConnectorはLumaで継続する。実測証拠:
`docs/evidence/outbound/2026-08-01-o1b11-connpass-api-application.json`。次は固定順序どおりO1B-12で、
一般参加eventとLT/CFP/demo登壇応募を別entity・別状態機械として実装する。

O1B-12開始: 専用plan
`docs/superpowers/plans/2026-08-01-connector-o1b12-separate-participation-entities.md`を追加した。
event本体だけを共有し、一般参加は`audience_registration`、登壇応募は`talk_application`として別ID・
別action URL・別state・別証拠で保存する。一般参加は`discovered / registration_queued / registered /
waitlist / cancelled`、登壇応募は`discovered / submission_queued / submitted / accepted / rejected /
withdrawn / presented`とする。登壇応募がclosed/invite-onlyでも候補entityとして追跡するが送信可能にはしない。
O1B-14のtimelineとO1B-15のimmutable transition ledgerを先取りせず、まず混同不能なdurable current-stateを作る。

O1B-12進捗1（RED）: `both` eventから別ID・別action URLの2 entity、audience-only/talk-only、
closed talkの追跡、classifier provenance必須、reference-only input、atomic insert、失敗時rollbackを固定する
test 5件を追加した。production `event-participation-entities.js`はまだ存在しないためmodule path不在でREDになる。

O1B-12進捗2: classifierが検証済みdecisionへin-process provenanceを付け、plain objectの偽判定を拒否する。
`event-participation-entities.js`はtenant、canonical Luma event、開始時刻、evidence refだけからkind別の
stable IDを生成する。`both`なら一般参加と登壇応募をexactly 2行にし、一般参加actionはevent URL、登壇actionは
本文中に実在する公開応募URLだけに固定する。PostgreSQL migrationはkind別state CHECK、unique key、RLSを持つ。
実DB前の監査で`Pool.query`のtransactionが同じconnectionに固定されない欠陥を発見し、`pool.connect()`で
一つのclientをBEGINからCOMMITまでleaseし、失敗時ROLLBACK、finally releaseする形へ修正した。

完了: `O1B-12`。実CloakBrowserの`Codex Meetup Tokyo #2`ページを再読し、ログイン欄の本人情報を除いた
公開本文だけを実Geminiへ渡した。実判定は`participation_kind=both`、`application_status=open`、
`talk_format=lightning_talk`。production migrationを実runtime PostgreSQLへ適用し、同じeventについて
`audience_registration`と`talk_application`を別ID・別action refの2 rowとしてatomic保存した。DB readbackは
rows=2、distinct IDs=2、distinct kinds=2、distinct actions=2、raw identity=false。まだ参加申込、LT応募、
Telegram送信の外部effectは起こしていない。outbound全回帰125件が成功した。実測証拠:
`docs/evidence/outbound/2026-08-01-o1b12-live-separated-participation-entities.json`。次はO1B-13で、
Life Managerの実測に基づくtalk title、5分outline、応募理由をagent生成し、このtalk entityへreferenceで接続する。

O1B-13開始: 専用plan
`docs/superpowers/plans/2026-08-02-connector-o1b13-grounded-talk-pack.md`を追加した。応募先eventの
公開本文とO1B04〜O1B12の実証済みfact/evidence refだけをGeminiへ渡す。出力はtitle、abstract、
application reason、product demo summary、0〜300秒をgap/overlapなしで覆う4〜7 segmentとする。
各segmentは許可済みevidence refへ必ず遡る。未実装の実口座CFO、crypto、NISAを完成済みとせず、
収益保証やbillionaire promise、placeholder、raw identity/secretをvalidatorで拒否する。

O1B-13進捗1（RED）: 300秒exact timeline、4〜7 segment、segment単位のevidence subset、gap/overlap、
未知reference、placeholder、email/secret、wealth promise拒否、untrusted event本文、model failure時fallback禁止を
固定するtest 4件を追加した。production `grounded-talk-pack.js`はまだ存在しないためmodule path不在でREDになる。

O1B-13進捗2: Gemini structured output generatorとvalidatorを実装した。初回実生成は300秒とevidence
参照には合格したが、product名がなく、Codex利用について根拠のない否定文が入ったためartifact化せず不合格にした。
Life Managerの明記を必須化し、根拠のない`not directly/わけではありません`、wealth promise、secret、
placeholderを拒否する境界へ強化した。再生成では実装がCodex TDD、commit、pushで行われたfactも追加した。

完了: `O1B-13`。実`Codex Meetup Tokyo #2`の公開本文とO1B04〜12 evidenceだけから、
「Life Manager Connector: Codexで開発したイベント参加自動化フローの実践」を生成した。outlineは5 segment、
0〜300秒exact、gap/overlapなしで、全segmentが許可済みevidence refを持つ。artifact SHA-256を
`artifact://connector-talk-pack/sha256/...`として実runtime DBの`talk_application` row 1件へ接続し、
hash一致をreadbackした。audience rowには接続できないDB/code制約を持つ。LT応募とTelegram送信はまだ行っていない。
outbound全回帰130件が成功した。実talk pack:
`docs/evidence/outbound/2026-08-02-o1b13-live-grounded-talk-pack.json`。attachment証拠:
`docs/evidence/outbound/2026-08-02-o1b13-live-talk-pack-attachment.json`。次はO1B-14で、accepted後の
slide締切、登壇日、会場、QR、follow-upを一つのtimelineへ接続する。

O1B-14開始: design
`docs/superpowers/specs/2026-08-02-connector-o1b14-accepted-talk-timeline-design.md`と実装plan
`docs/superpowers/plans/2026-08-02-connector-o1b14-accepted-talk-timeline.md`を追加した。可変JSON直書き、
Google Calendar単独正本、immutable snapshotの3案を比較し、source-bound immutable snapshot + current viewを採用する。
follow-upは主催者へのslide締切・会場・QR・資料提出確認だけとし、参加者への連絡や次回面談はscope外のままにする。
現在の実talkは未採択なのでtimelineを捏造せず、production DB schema適用後にaccepted fixtureをtransaction rollbackで実証する。

O1B-14進捗1（RED）: accepted sourceからslide/appearance/venue/QR/follow-upを一つにすること、
不足情報を`pending`で保持すること、timestamp矛盾、source外ref、不整合field、raw secretを拒否すること、
Geminiへuntrusted dataとして渡してmodel failure時にfallbackしないことをtest 4件で固定した。
production `accepted-talk-timeline.js`はまだ存在しないためmodule path不在でREDになる。

O1B-14進捗2（GREEN）: Gemini structured outputとdeterministic validatorを実装し、accepted時刻、登壇時刻、
slide締切、会場、QR artifact、主催者確認予定を一つの検証済みtimelineへ合成した。不足情報は成功へ補完せず
`pending`のまま保持し、model/API失敗時もkeyword fallbackを行わない。自己レビューで、原文にない会場住所を
modelが補っても通る抜けをREDで再現し、会場名・住所が空白差を除いてsource本文に実在する場合だけ`known`を
許可した。focused test 4/4成功。次はimmutable PostgreSQL snapshot storeをTDDで実装する。

O1B-14進捗3（DB RED）: 検証済みtimelineだけからstable・reference-only snapshotを作ること、同じtenantの
`accepted / talk_application`だけへ保存すること、idempotent retry、衝突時rollback、UPDATE/DELETE禁止、
current viewをtest 5件で固定した。production `accepted-talk-timeline-store.js`が未実装のためmodule path不在で
期待どおりRED。次はこのcontractを満たすmigrationとsingle-client transaction storeを実装する。

O1B-14進捗4（DB GREEN）: content hashでstableなsnapshot ID、in-process検証provenance、同一tenantの
`accepted / talk_application`を`FOR SHARE`で固定するsingle-client transaction、idempotent retry時の
完全一致照合を実装した。DBにもcomposite foreign key、accepted talk insert gate、UPDATE/DELETE拒否trigger、
tenant別current viewを追加した。正規表現test自身の括弧escape漏れを根因確認して1箇所だけ修正し、focused 5/5、
新規testを含むoutbound全回帰140/140成功。次は実runtime PostgreSQLへmigrationを適用し、rollback fixtureで
insert/current view/immutable triggerを実測する。実talkは未採択のまま変更しない。

完了: `O1B-14`。migrationを実runtime PostgreSQLへ適用した。transaction内のaccepted talk fixtureで
snapshot 1件、current view 1件、UPDATE拒否、拒否後の値不変1件を確認し、ROLLBACK後にfixture 0件を
再読出しした。実`Codex Meetup Tokyo #2`は未採択talk entity 1件、timeline 0件のままで、採択や締切を
捏造していない。focused 5/5、新規保存層を含むoutbound全回帰140/140成功。証拠:
`docs/evidence/outbound/2026-08-02-o1b14-live-talk-timeline.json`。次は固定順序どおり`O1B-15`で、
登壇応募の`submitted / accepted / rejected / presented` transitionをimmutable ledgerへ保存する。

O1B-15開始: design
`docs/superpowers/specs/2026-08-02-connector-o1b15-talk-transition-ledger-design.md`と実装plan
`docs/superpowers/plans/2026-08-02-connector-o1b15-talk-transition-ledger.md`を追加した。parent state直UPDATE、
immutable ledger + atomic projection、ledger-only event sourcingの3案を比較し、既存query互換を保ちながら履歴を
失わないimmutable ledger + atomic projectionを採用する。意味判断はagent、state graph、tenant、時刻、参照、
原子性、不変性はdeterministic code/DBが担当する。実talkは変更せずrollback fixtureで実証する。

O1B-15進捗1（RED）: `submitted / accepted / rejected / presented`のsource-bound観測、queue/withdrawalを含む
forward graph、state rollback拒否、未来時刻、invented ref、本文外excerpt、raw secret拒否、Gemini failure時の
no-fallbackをtest 4件で固定した。production `talk-application-transition.js`は未実装のためmodule path不存在で
期待どおりRED。次はmodel judgmentとdeterministic validationの境界を実装する。

O1B-15進捗2（GREEN）: Gemini structured outputでsourceからnext state、exact excerpt、reason、source refsを
判断し、deterministic validatorがtrusted current stateとのforward graph、観測時刻、excerpt binding、ref subset、
secret境界を検証するmoduleを実装した。plain object copyはprovenanceを失い、model/API/JSON failure時はtransitionを
作らない。focused 4/4、新規testを含むoutbound全回帰144/144成功。次はimmutable DB ledgerとatomic projectionを
TDDで実装する。

O1B-15進捗3（DB RED）: verified transitionからstable reference-only recordを作ること、parent talk rowの
`FOR UPDATE`、append後のcurrent projection、後続stateへ進んだ後のexact retry、cross-tenant/stale/audience/
collision rollback、DB graph/trigger/immutabilityをtest 6件で固定した。production
`talk-application-transition-store.js`は未実装のためmodule path不存在で期待どおりRED。次はstoreとmigrationを
実装する。

O1B-15進捗4（DB GREEN）: verified transitionだけからcontent-addressed recordを作り、single-client
transactionでparentを`FOR UPDATE`、exact retryを照合、新規transitionをappendし、DB AFTER triggerによる
current state projectionを再読出しするstoreを実装した。migrationはcomposite FK、forward pair CHECK、
DB自身のcurrent-state gate、atomic projection、UPDATE/DELETE拒否、RLSを持つ。focused 6/6、新規store testを
含むoutbound全回帰150/150成功。次は実runtime DBへmigrationを適用し、全forward pathとrollbackを実測する。

完了: `O1B-15`。migrationを実runtime PostgreSQLへ適用した。最初に4 transitionを一つのmulti-row INSERTへ
まとめたfixtureは、同一statementのBEFORE triggerがAFTER projectionより先に走るため2行目をfail closedし、
接続終了時に全rollbackされた。production storeと同じ1 append = 1 statementへ直し、transaction内で
`discovered → submission_queued → submitted → accepted → presented`の4 transition、ledger 4件、parent
`presented` 1件を確認した。terminalからの逆行とledger UPDATEは拒否され、ROLLBACK後はfixture entity/transition
とも0件。実talkは`discovered` 1件、transition 0件のままで変更していない。focused 4/4 + 6/6、outbound
全回帰150/150成功。証拠: `docs/evidence/outbound/2026-08-02-o1b15-live-talk-transition-ledger.json`。
次は固定順序どおり`O1B-16`で、今日を含む21日間のrolling coverage goalを実装する。

O1B-16開始: design
`docs/superpowers/specs/2026-08-02-connector-o1b16-rolling-coverage-goal-design.md`と実装plan
`docs/superpowers/plans/2026-08-02-connector-o1b16-rolling-coverage-goal.md`を追加した。固定24時間加算、
timezone-local暦日加算、Calendar query window直結の3案を比較し、DSTでもexactly 21 unique local datesになる
timezone-local暦日加算を採用する。毎run全snapshotを再構築し、後続stageのtrusted resolved evidenceがない日は
必ず`open`。Calendarに予定があるだけでcoverage済みとは判断しない。

O1B-16進捗1（RED）: JSTでtoday〜+20、New YorkのDST境界でも21 unique date、翌local dayのwindow slide、
trusted resolved evidenceだけのstate/count、invalid timezone、duplicate、out-of-window、open自己申告、根拠なし、
secret ref拒否をtest 5件で固定した。production `rolling-event-coverage.js`は未実装のためmodule path不存在で
期待どおりRED。次はtimezone-local暦日builderとcontent hashを実装する。

O1B-16進捗2（GREEN）: IANA timezoneからlocal todayを取得し、固定24時間ではなく`YYYY-MM-DD`の暦演算で
exactly 21日を生成するpure builderを実装した。resolved evidenceのない日は`open`、trusted ref付き3状態だけを
反映し、重複日や範囲外を拒否する。snapshotは全内容のSHA-256 IDとin-process provenanceを持つ。focused 5/5、
新規testを含むoutbound全回帰155/155成功。次はimmutable PostgreSQL snapshot storeをTDDで実装する。

O1B-16進捗3（DB RED）: in-process verified snapshot以外をDBへ到達させないこと、single-client insert、
exact retry、collision rollback、21日/date/count DB constraints、UPDATE/DELETE拒否、tenant latest viewをtest 4件で
固定した。production `rolling-event-coverage-store.js`は未実装のためmodule path不存在で期待どおりRED。
次はstoreとmigrationを実装する。

O1B-16進捗4（DB GREEN）: in-process provenanceを持つsnapshotだけをsingle-client transactionでappendし、
retry時はDB rowを正規化して完全一致を要求するstoreを実装した。migrationは21日、start+20日、4 count合計21、
days JSON length 21を制約し、tenant latest viewとUPDATE/DELETE拒否triggerを持つ。migration文字列testの`+`未escape
2箇所を同じ根因として修正した。focused 4/4、新規store testを含むoutbound全回帰159/159成功。次は実DB適用、
実Calendar read-only count、21-open snapshot保存を行う。

完了: `O1B-16`。migrationを実runtime PostgreSQLへ適用した。既存`gog` OAuthで2026-08-02〜08-22を
`--all --all-pages` read-only取得し、Calendar event 124件（timed 123 / all-day 1）を確認した。title、location、
attendee等のraw fieldは出力・保存していない。O1B-23前なので124件をcoverageへ推測せず、実DBへexactly 21日の
初回snapshotを`open=21 / covered_existing=0 / covered_new=0 / unavailable=0`として保存した。current view 1件、
days 21、UPDATE拒否をreadbackした。focused 5/5 + 4/4、outbound全回帰159/159成功。証拠:
`docs/evidence/outbound/2026-08-02-o1b16-live-rolling-coverage.json`。次は固定順序どおり`O1B-17`で、
21 open datesそれぞれについてLuma mainの東京対面inventoryを終端まで読む。

O1B-01進捗1: verifier provenanceとruntime completion gateをTDDで追加した。最初のREDは
`outbound-success.js`不存在、runtime REDはbare `{status:"success"}`が実際に`completeJob`へ入ることを
再現した。GREENでは、同一processの実verifier由来E1/E2/E3 objectだけがsuccess receiptを作れる。
missing tier、plain object copy、JSON roundtrip receipt、別attempt、bare successを拒否する。
証拠不成立は`CAPABILITY_EXECUTION_FAILED`かつ`unknownEffect=true`となり、retryによる二重応募を防いで
既存reconciliationへ渡す。fresh verificationはoutbound 31件、runtime worker回帰31件が成功した。
次は実装commitと非secret evidence JSON。

完了: `O1A-06`。実機workerを意図的に停止し、Guardianの異常判定、DaisへのTelegram
停止警告のpositive message ID、Docker workerの決定論的再起動、boundedな`/health`再確認、復旧通知の
positive message ID、incident state clearまでを一続きで実証した。再起動で戻らない場合だけ既存
`self-fix.sh`へ昇格する。現在のHonne JA shadow設定とvolumeを保持し、健康な実行では通知しない。
passing retestの警告message IDは`5016`、復旧message IDは`5017`、Guardian exit 0、launchd last exit 0。
fresh verificationはoutbound 28件、runtime worker回帰30件、evidence JSON、live health、plist、launchd、
incident clear、self-fix未起動がすべて成功した。実装commit: `a7c01157e`、`df1ac3495`、`43d9134fc`。
実装plan: `docs/superpowers/plans/2026-08-01-connector-o1a06-live-recovery.md`。live evidence:
`docs/evidence/outbound/2026-08-01-o1a06-live-recovery.json`。次は`O1B-01`。

O1A-06進捗1: Telegram incident契約をTDDで追加した。REDは13件中4件がmessage ID検証、停止警告、
重複防止、復旧通知の未実装理由で失敗した。GREENはGuardian 13件を含むoutbound 24件とruntime
worker回帰30件が成功した。警告文は非技術的な停止状態、自動復旧開始、未確認応募を応募済みと
報告しないことを明示する。positive message ID取得後だけincidentを保存し、同じincidentを再通知せず、
復旧通知のpositive message ID取得後だけincidentをclearする。次はlaunchdとcomposeの実機配線。

O1A-06進捗2: launchd installer、local Docker recovery、Connector compose overlayをTDDで追加した。
REDはinstallerが宛先なしを拒否しない、overlay不存在、Docker recovery不存在の3理由で失敗した。
GREENはGuardian 16件を含むoutbound 27件、runtime worker回帰30件、render済みplist、shell syntax、
base compose + Connector overlay configが成功した。Telegram targetはrepositoryへ保存せずinstaller引数から
local plistだけへ入る。Docker recoveryは指定された一つのcontainerだけをrestartし、最大30回・1秒間隔で
同じ`/health`契約を再確認する。次は既存Honne shadow設定を保持した実機deploy。

O1A-06進捗3: base compose + 既存Honne JA shadow override + Connector overlayでworker一つだけを
recreateした。PostgreSQL、object store、runtime volumeは削除していない。`/health`は200、
`role=worker`、`runtime.noop,marketing.video.generate,outbound.event.apply`、fresh pollを返した。
Guardian launchdを5分cadenceで登録し、健康なkickはexit 0、incidentなし、Telegram誤送信なしだった。
一回目の実停止では警告message ID `5014`、復旧message ID `5015`、worker復旧、incident clearまで
成功したが、元の異常verdictを保持した結果へ`verdict.ok`だけを見たmainがexit 1を返す欠陥を発見した。
root causeをpure exit判定testでREDにし、`ok=true OR recovered=true`だけexit 0へ修正した。再実証では
2026-08-01T08:47:05Zにworkerが`exited`、警告message ID `5016`、自動restart後に復旧message ID
`5017`、2026-08-01T08:47:18ZにGuardian exit 0、worker `running/healthy`、fresh poll、incident clearを
確認した。その後のlaunchd kickもrun count 2、last exit code 0、healthy出力だった。次は証拠JSONと
最終fresh verification。

O1A-06着手時の追加実測: 現workerの`LM_WORKER_CAPABILITIES`は
`runtime.noop,marketing.video.generate`で、host health portは未公開。さらに
`outbound.event.apply`はjob/lease test用handler注入では動くが、production adapter manifestにはまだ無い。
O1A-06ではGuardianのprocess/capability claimと復旧を実証し、実応募adapterそのものは番号どおり
`O1B-03`で完成させる。Guardian healthyを「実イベント応募成功」と読み替えることは禁止する。

完了: `O1A-05`。Connector専用の第二監視系やheartbeat fileは作らず、既存runtime workerの
`/health`を既存Guardianと`self-fix.sh`へ接続した。HTTP 200に加え、`role=worker`、
`outbound.event.apply` capability、freshな`last_poll_at`を必須条件とし、到達不能、不正JSON、
HTTP異常、role違い、capability不足、未来・stale pollをfail closedにした。local worker health port、
5分cadenceのlaunchd plist、副作用なしで検証できるinstallerを追加した。fresh verificationは
Guardian 9件を含むoutbound 20件、runtime worker回帰30件、compose config、plist template、
render済みplist、shell syntaxがすべて成功した。実装commit: `fff711b20`。実装plan:
`docs/superpowers/plans/2026-08-01-connector-o1a05-guardian-wiring.md`。実機は別worktree由来の古い
composeでworker health portが未公開のため、launchd登録を先行すると偽の到達不能self-fixになる。
現在のcomposeへの更新、launchd登録、強制停止、Telegram警告、実復旧は次の`O1A-06`で一続きに実証する。

完了: `O1A-04`。`apps/life-manager`の完全な`npm test`を現在のlockfileとinstallで実行し、
2026-08-01にexit 0を確認した。不足moduleはなく、新しいoutbound 11件、runtime worker 30件、
runtime adapter 120件、browser auth 75件、legacy path Node 18件 + Python 8件を含む全commandが
最後まで成功した。dependency追加やproduction変更は不要だった。次は`O1A-05`。

完了: `O1A-03`。events・funders・jobs共通の成功条件を`E1 AND E2 AND E3`としてmodule化した。
callerの成功booleanやDOM本文は信用せず、外部receipt reader、immutable artifact reader、実HEADを
gate自身が呼ぶ。E1はreference schemeと結果kindを一致させ、E2は実bytesのPNG signature、5000 bytes、
SHA-256 object reference一致を検証し、E3はHTTPS canonical URLへredirectなしのHEAD 200を要求する。
一回性`/join/complete/`、raw email、filesystem path、302、cross-tenant attemptはすべてfailedとなる。
fresh verificationはoutbound 11件とworker回帰30件が成功した。実装commit: `fce82564c`。実装plan:
`docs/superpowers/plans/2026-08-01-connector-o1a03-evidence-contract.md`。次は`O1A-04`。

完了: `O1A-02`。新runtimeや第二queueを作らず、既存workerへtenant・job・attempt・workerで
scopedされた定期lease heartbeatを接続した。pulseを直列化し、停止時にin-flight更新を待つ。
heartbeat喪失とadapter失敗が重なった外部効果jobもretry可能にせず、`unknownEffect=true`で
既存reconciliationへ渡す。`outbound.event.apply`固有の実PostgreSQL testで二重enqueueが一行、
claim、heartbeat、既知の送信前失敗による一回のretry、上限到達後のdead-letter、immutable failed
receipt二行を確認した。fresh verificationはoutbound 7件、worker回帰30件、PostgreSQL lifecycleが
すべて成功した。実装commit: `9d6a6d51f`。実装plan:
`docs/superpowers/plans/2026-08-01-connector-o1a02-runtime-execution.md`。次は`O1A-03`。

完了済み: `O1A-01`。既存`lm_runtime_jobs`がenqueue、claim、lease、heartbeat、retry、dead-letter、
idempotency、immutable receiptを既に持つことを2026-08-01に再確認した。別worktreeの独立outbound
engineは第二runtimeになるため取り込まず、Connector event applicationをreference-only job contractで
既存runtimeへ接続した。`outbound.event.apply`、安定job/effect key、tenant境界、Luma URL・時刻・
identity/browser/calendar reference検証を追加し、新規4件と既存runtime 8件の計12件が成功した。
実装commit: `7aeed4098`。実装plan:
`docs/superpowers/plans/2026-08-01-connector-o1a01-durable-runtime.md`。

最後までのmaster checklist:

| order | 残っている成果 | 次へ進める条件 |
|---|---|---|
| 1A | 共通応募runtime、Guardian、証拠、再試行、Telegram | 強制停止から自動検知・復旧し、偽の成功を作らない |
| 1B | 東京対面eventの21日coverage、一般参加、LT応募、確認mail、QR、Calendar | 未処理の空き枠がなく、実申込と確認証拠がCalendarまでつながる |
| 1C | accelerator/VC/grantの継続探索・応募・返信・面談 | 実提出、確認mail、追跡、Calendar、面談資料が一つにつながる |
| 2 | 高年収job探索・応募・返信・面接 | Ashby/Workday実応募と面接mail→Calendarが成立 |
| 3A | CFO runtime database、executor、launchd、失敗復旧 | enqueue→実行→財務報告が止まらず動く |
| 3B | Moneytree、銀行/card、Binance、wallet、JPY、予算、CFO organ | 総資産と1/3/12か月収支が原本まで遡れ、CFO specialist loopが動く |
| 4 | Anicca/Dais分離crypto、paper、canary、risk、停止 | fee後実現P&Lと全cap・緊急停止を実資金の小額で実証 |
| 5 | Fiat/NISA data、余剰資金、提案、注文、税/fee | NISA/課税/現金/cryptoを分け、約定からCFOまで照合 |
| Web | 同じcoreのtenant化、認証、secret、panel、課金 | ローカルで実証した同じjob/ledger/reportを別userが安全に使える |

### 5.1 Order 1A — 共通応募基盤

- [x] O1A-01 既存`lm_runtime_jobs`を唯一のdurable runtimeとしてConnector event application job contractへ接続
- [x] O1A-02 enqueue、claim、heartbeat、retry、dead-letter、idempotencyを接続
- [x] O1A-03 Evidence E1/E2/E3を共通module化
- [x] O1A-04 不足dependencyを解消し全testを実行
- [x] O1A-05 Guardianを接続
- [x] O1A-06 強制停止→検知→Telegram警告→復旧を実証

### 5.2 Order 1B — イベント

- [x] O1B-01 偽物の成功判定を削除
- [x] O1B-02 event URLの2不具合を修正
- [x] O1B-03 既存CloakBrowser daily-driverを使うLuma discover + RSVP adapterを完成
- [x] O1B-04 実イベント一件へ登録
- [x] O1B-05 確認mailをGmailで読み、同一attemptへ照合
- [x] O1B-06 同一eventのLuma公式QRをguest key hashで照合して保存
- [x] O1B-07 人間向け説明と直接link付きでTelegramへ実QRを送る
- [x] O1B-08 agentが本文からLT/CFP/demoを判断する実Gemini evalを8/8で通す
- [x] O1B-09 旧Connector loginを復旧しevents packへ統合
- [x] O1B-10 重複旧実装を退役
- [x] O1B-11 connpass API keyを申請。取得まで自動アクセス禁止
- [x] O1B-12 一般参加とLT/CFP/demo登壇応募を別entityとしてdiscover・追跡
- [x] O1B-13 Life Managerの実測demoに合うtalk title、5分outline、応募理由をagent生成
- [x] O1B-14 accepted後にslide締切、登壇日、会場、QR、follow-upを一つのtimelineで追跡
- [x] O1B-15 登壇応募ごとの`submitted / accepted / rejected / presented`を応募ledgerへ記録
- [x] O1B-16 今日を含む21日間（今日〜20日後）を毎日再計算するrolling coverage goalを実装
- [x] O1B-17 Luma mainの東京・対面inventoryを日付ごとに最後まで読み、表示上位数件だけで探索を終えない
- [x] O1B-18 AI/crypto/英語等は優先順位にだけ使い、eventを捨てるhard category filterにはしない
- [x] O1B-19 agentがevent本文・参加者・主催者・場所・時間を読み、Daisの目標とserendipityを自然言語で評価
- [x] O1B-20 Lumaで実参加を確保できない場合、許諾済みsourceを探索する。connpassはkey取得後の公式API read-only discoveryだけとし、自動申込み・coverage達成には使わない
- [x] O1B-21 一つの候補で申込失敗・満席・不適格になっても同じ日の次候補へ進み、予約確認までloopを継続
- [x] O1B-22 「検索一巡」「一件の操作失敗」「一sourceの失敗」を終了条件にしない
- [x] O1B-23 Google Calendarの全calendarからbusy intervalを読み、前後移動時間を含むfree intervalだけへ予約
- [ ] O1B-24 無料を優先し、有料eventは一度設定した自動支出policy内で保存済み決済手段を使い、都度承認を要求しない
- [ ] O1B-25 21日coverage、既存予定、新規予約、残り空き、申込証拠、選定理由をTelegramへ一通で報告

O1B-17開始（2026-08-02）: discovery cardの日本語日付labelは証拠に使わない。仮想scroll終端を
証明したTokyo inventoryの全canonical URLについて公式JSON-LD detailを読み、ISO開始時刻を
Asia/Tokyoの日付へ変換して、O1B-16のverified 21日snapshotへ完全投影する。一件でもdetail不能、
URL集合不一致、重複、終端未証明ならfail closedする。0候補の日はinventory読取済みでもcoverageは
`open`のままであり、`unavailable`へ変換しない。設計:
`docs/superpowers/specs/2026-08-02-connector-o1b17-luma-date-inventory-design.md`。実装plan:
`docs/superpowers/plans/2026-08-02-connector-o1b17-luma-date-inventory.md`。

O1B-17進捗1（RED）: provenanceのないcloneを拒否し、discovery URLとdetail URLの完全一致を要求し、
一件欠落・重複・別URLをfail closedにし、JSTで21日すべてへ投影し、0候補日をcoverage完了へ
変換しないtestを追加した。production moduleと2つのprovenance verifierが未実装のため3件が期待どおり
失敗し、既存10件は成功した。

O1B-17進捗2（pack RED）: 認証済みevents packへ全detail読取を一つの操作として公開し、host側
read-only entrypointが21日coverageを作ってその操作だけを呼ぶ契約を追加した。未実装のため新規2件が
期待どおり失敗し、既存の構成拒否2件は成功した。

O1B-17進捗3（GREEN）: discovery inventory、provider detail、日付別snapshotにin-process provenanceを
追加した。verified coverage、終端証明済みinventory、全candidateと完全一致するverified detailだけから、
JSTの21日を全件持つimmutable content-addressed snapshotを作る。events packとhost read-only entrypointを
この操作へ接続し、公開event名・URLを標準出力せず集計だけを返す。focused 20/20成功。次は実Luma
Tokyoの全detail readbackとoutbound全回帰である。

O1B-17完了: 実CloakBrowser daily-driverと既存認証をread-onlyで使い、Luma Tokyo inventoryを
7 roundsで終端まで読んだ。35 candidateを発見し、公式detailを35/35照合、欠落0。rolling
2026-08-02〜2026-08-22へ投影するとscheduled in-personは29件、候補あり12日、候補なし9日だった。
0候補日をcoverage完了へ変換せず、21日coverageは変更していない。CLIが結果出力後もCDP client handleを
保持する問題も、共有browserをcloseせずstdout/stderr flush後に自processだけexitするよう修正した。
focused 20/20、CLI境界9/9、outbound全回帰164/164成功。証拠:
`docs/evidence/outbound/2026-08-02-o1b17-live-luma-date-inventory.json`。次は固定順序どおり`O1B-18`。

O1B-18開始（2026-08-02）: verifiedな日付inventoryの全event refをexactly onceで返すGemini rankingを
実装する。AI、crypto、英語、founder等は自然言語のpreferenceとしてarray順とfitへだけ反映し、
`weak / unknown`も捨てない。schemaにexclude判定を持たせず、欠落・重複・未知ref・model failureは
fail closedし、keyword fallbackを作らない。本文・主催者・参加者・serendipityの深い評価はO1B-19。
設計: `docs/superpowers/specs/2026-08-02-connector-o1b18-preference-ranking-design.md`。実装plan:
`docs/superpowers/plans/2026-08-02-connector-o1b18-preference-ranking.md`。

O1B-18進捗1（RED）: 全candidate保持、`weak / unknown`保持、exact permutation、immutable provenance、
exclude-shaped output拒否、model failure時のfallback禁止、0候補日のmodel非呼出しを5 testで定義した。
production module不存在のため期待どおり失敗した。

O1B-18進捗2（GREEN）: verified O1B-17 snapshotと対象日だけを入力にし、Geminiのstrict JSONを
全event refのexact permutationとして検証するmoduleを追加した。schemaにexclude/eligibleを持たず、
`strong / moderate / weak / unknown`と理由だけを返す。好み本文はhashだけをsnapshotへ残し、model failure、
invalid JSON、欠落、重複、未知refにfallbackしない。focused 5/5成功。次は実Gemini 8-case eval。

O1B-18進捗3（live eval + pack RED）: 実Gemini 8ケースで全候補保持8/8、期待上位8/8を確認した。
初回は期待ref自体が存在しないeval fixture bugで7/8となり、caseごとの期待indexと期待ref存在gateを
追加して修正した。events packからrankingを呼ぶ契約testは`rankDatePreferences`未実装のため期待どおり
1件失敗し、既存の構成拒否1件は成功した。

O1B-18完了: events packへ`rankDatePreferences`を接続し、O1B-17のverified snapshotから同日全候補を
欠落・重複なく並べる経路を完成した。実Gemini 8ケースは全候補保持8/8、期待上位8/8。schemaに
exclude/eligible fieldはなく、`weak / unknown`も残る。focused 7/7、outbound全回帰169/169成功。
証拠: `docs/evidence/outbound/2026-08-02-o1b18-live-preference-ranking.json`。次は固定順序どおり
`O1B-19`で、本文・主催者・参加者・場所・時間・Daisの目標・serendipityを自然言語で評価する。

O1B-19開始（2026-08-02）: 実Luma Tokyoは終端6round、32候補。確認した公式JSON-LDは
description 913文字、organizer 2件、会場住所・緯度経度・開始終了を持つ一方、attendee/performerは
0件だった。公開profile link 2件はorganizer数と一致するため参加者とは扱わない。providerが明示する
description、organizer、attendee、place、timeだけをverified sourceとして、全候補を保持したまま
Daisのgoal alignmentとserendipity potentialをGeminiが評価する。5 factorをexactly once返し、
参加者非公開は`unavailable`、sourceにないexcerpt・欠落・重複・model failureはfail closedする。
設計: `docs/superpowers/specs/2026-08-02-connector-o1b19-grounded-serendipity-design.md`。実装plan:
`docs/superpowers/plans/2026-08-02-connector-o1b19-grounded-serendipity.md`。

O1B-19進捗1（source RED）: 公式description、organizer、attendee、住所の正規化、attendee欠落時の
`unavailable`、日付snapshotへのsource伝播をtestで固定した。未実装の3件が期待どおり失敗し、既存9件は
成功した。

O1B-19進捗2（source GREEN）: Luma公式JSON-LDからdescription、organizer name、attendee descriptor、
住所をboundedに正規化し、verified detailから21日snapshotへ伝播した。attendeeが無い場合は空配列と
`participant_visibility=unavailable`を保持し、推測しない。O1B-18回帰を含むfocused 17/17成功。

O1B-19進捗3（decision RED）: verified O1B-17/O1B-18 provenance、全candidate保持、5 factor exactness、
source完全一致excerpt、非公開participantの捏造拒否、goal/serendipity理由、model failure時fallback禁止を
4 testで定義した。production module不存在のため期待どおり失敗した。

O1B-19進捗4（decision GREEN）: verified O1B-17/O1B-18だけを受け、同日全候補についてgoal alignment、
serendipity potential、自然言語理由、5 factor assessmentをcontent-addressed decisionにするmoduleを
追加した。source有りは完全一致excerpt、source無しは`unavailable + null`を強制し、架空participant、
候補/factor欠落、model failureを成功にしない。focused 4/4成功。

O1B-19進捗5（pack RED）: events packがverified date inventory、preference ranking、Dais goalsを
一つのO1B-19操作へ渡す契約を追加した。`evaluateDateGoals`未実装の1件が期待どおり失敗し、既存の
構成拒否1件は成功した。

O1B-19完了: events packへ`evaluateDateGoals`を接続した。実Gemini 6ケースは全候補保持6/6、期待上位
6/6、5 factor完全6/6、participant honesty 6/6。実Luma production parserは終端6round・21候補の
runで、description、organizer、住所を正規化し、attendee 0を`participant_visibility=unavailable`として
保持した。provider/model failureはstageだけを示し本文を漏らさない。focused 6/6、outbound全回帰
174/174成功。証拠: `docs/evidence/outbound/2026-08-02-o1b19-live-grounded-serendipity.json`。
次は固定順序どおり`O1B-20`で、Lumaで実参加を確保できない日だけ許諾済みsourceへ継続する。

O1B-20開始（2026-08-02）: connpass keyは未配備で、提出日以後の公式API返信mail 0件、credential-like
value 0件。公式v2はkey必須のGET discoveryだけに使い、API外access、browser申込み、coverage creditを
禁止する。MeetupはPro OAuth審査、Eventbriteは第三者eventのparticipant registration endpointを確認
できないためactive sourceへ追加しない。verified Luma exhaustion後、keyありならconnpass公式GET、keyなし
ならnetwork 0のままkey watcherとLuma retryへ進み、dateを`open`に保つ。設計:
`docs/superpowers/specs/2026-08-02-connector-o1b20-source-handoff-design.md`。実装plan:
`docs/superpowers/plans/2026-08-02-connector-o1b20-source-handoff.md`。

O1B-20進捗1（RED）: Luma exhaustionとsource capabilityへin-process provenanceを要求し、key未配備時は
network 0、key配備時もconnpass公式v2の全page GET discoveryだけ、候補はadvisory-only、registrationと
coverage creditは常に禁止、source error・empty inventoryでもdateは`open`のままLuma再探索へ戻す契約を
5 testで定義した。production handoff moduleとLuma provenance verifierが未実装のため2件が期待どおり
失敗し、既存3件は成功した。

O1B-20進捗2（core GREEN / pack RED）: verified source handoff coreを実装しfocused 8/8成功。次に既存の
認証済みevents packがcapability作成、handoff plan、必要時だけconnpass client作成、handoff実行を一つの
操作として公開する契約を追加した。pack method未実装のため新規2件が期待どおり失敗する段階である。

O1B-20進捗3（pack GREEN）: events packへ`handoffEventSource`を追加した。key未配備ならconnpass clientを
作らず、key配備時だけ既存の5秒間隔公式v2 clientを生成する。source handoff、Luma sequence、packの
focused 11/11成功。新規handoff suiteをoutbound全回帰へ追加した。次は実環境のnetwork 0証拠と全回帰である。

O1B-20完了: 実構成監査ではconnpass key未配備、公式返信0、credential-like返信0。missing-key executionは
connpass clientを作らず独立counterでもnetwork 0、registration 0、coverage credit 0、dateは`open`のまま
key watcherとLuma再探索へ戻った。key配備後の経路も公式v2 GET全page discoveryだけで、候補を予約済みへ
昇格できない。focused 11/11、outbound全回帰179/179成功。証拠:
`docs/evidence/outbound/2026-08-02-o1b20-authorized-source-handoff.json`。次は固定順序どおり`O1B-21`で、
同日の一候補が満席・不適格・申込不能でも次候補へ進み、verified registrationまでloopを継続する。

O1B-21開始（2026-08-02）: O1B-03で実装済みのverified candidate sequenceを唯一のstate machineとして
再利用し、認証済みevents packから公開する。一件失敗を日次終了へ変換する別loopは作らない。設計:
`docs/superpowers/specs/2026-08-02-connector-o1b21-ranked-candidate-loop-design.md`。実装plan:
`docs/superpowers/plans/2026-08-02-connector-o1b21-ranked-candidate-loop.md`。

O1B-21進捗1（pack RED）: events packが順序付き同日候補とattempt関数を既存verified sequenceへそのまま
渡す契約を追加した。`runSameDayCandidates`未実装のため新規1件が期待どおり失敗する段階である。

O1B-21完了: O1B-03のverified candidate sequenceをevents packの`runSameDayCandidates`へ接続した。
満席、waitlist、承認制、不適格、競合、cancelは同日次候補へ進み、login・transport・inventory異常は
候補を消費せず復旧、unknown effectは二重申込せずreconciliation、全候補exhaustionだけが次sourceへ
handoffする。focused 12/12、outbound全回帰180/180成功。証拠:
`docs/evidence/outbound/2026-08-02-o1b21-same-day-candidate-loop.json`。次は`O1B-22`で、検索一巡、
一件の操作失敗、一sourceの失敗をrolling coverage loop全体の終了条件から除外する。

O1B-22開始（2026-08-02）: `open=0`だけを完了条件とするcoverage continuation state machineを追加する。
検索一巡、一件の操作失敗、一source失敗、結果なしはinventory refresh、復旧要求はsource recovery、
unknown effectはeffect reconciliationを次actionとしてdurableな次回時刻を持たせる。設計:
`docs/superpowers/specs/2026-08-02-connector-o1b22-coverage-continuation-design.md`。実装plan:
`docs/superpowers/plans/2026-08-02-connector-o1b22-coverage-continuation.md`。

O1B-22進捗1（RED）: search exhaustion、一操作失敗、一source失敗でも5分後のinventory refreshを予定し、
reconciliation/recoveryを優先し、open 0だけがcomplete、plain coverage・未知status・window外dateを拒否する
4 testを追加した。production module不存在のため期待どおり失敗する段階である。

O1B-22完了: verified rolling coverageだけを受けるcontent-addressed continuation state machineを実装し、
events packへ接続した。`open>0`なら結果なしを含め必ず5分後の次actionを作る。unknown effectは
`reconcile_effect`、auth/transport/inventory異常は`recover_source`、検索一巡・一操作・一source失敗は
`refresh_inventory`であり、`open=0`だけがcompleteである。focused 9/9、outbound全回帰181/181成功。
証拠: `docs/evidence/outbound/2026-08-02-o1b22-coverage-continuation.json`。次は`O1B-23`で、Google
Calendarの全calendarと移動時間を申込前gateにして、衝突しないfree intervalだけへ予約する。

O1B-23開始（2026-08-02）: 既存`gog` account/keyringは利用可能で追加credential不要。実Google Calendarは
5個、2026-08-02〜2026-08-22には全calendar合計124 event、eventを持つcalendarは3個だった。本文・identityは
出力していない。全calendar/全pageをverified busy inventoryへ正規化し、候補の前後移動時間まで含むintervalを
申込前gateにする。設計:
`docs/superpowers/specs/2026-08-02-connector-o1b23-calendar-free-interval-gate-design.md`。実装plan:
`docs/superpowers/plans/2026-08-02-connector-o1b23-calendar-free-interval-gate.md`。

O1B-23進捗1（transport RED）: 既存`listEventsRaw`は`--all-pages`でもcalendar指定省略によりprimaryだけを
読む経路だった。calendar listを`--all`で終端まで読み、eventsを明示的`--all --all-pages`で読む2操作と、
provider failureを空予定へ変換しない契約testを追加した。新method未実装のため2件が期待どおり失敗する段階。

O1B-23進捗2（transport GREEN / inventory RED）: `listCalendarsRaw`を`--all`、`listAllEventsRaw`を明示的
`--all --all-pages`で実装し14/14成功。次に全calendarのtimed/all-day busyをopaque calendar/event refだけへ
正規化し、transparent/cancelledを除外、provider failure・未知calendar・重複・壊れた時刻をfail closedにする
3 testを追加した。production inventory module不存在のため期待どおり失敗する段階である。

O1B-23進捗3（inventory GREEN）: 全calendarを一度列挙し、全page eventsのCalendarIDが列挙集合に属する
ことを検証するcontent-addressed busy inventoryを実装した。timedとall-dayを保持し、transparent/cancelledを
busyから除外する。calendar ID、event ID、予定名、場所はsnapshotへ出さずopaque hash refだけを保持する。
provider failureは空予定へ変換しない。transport + inventory focused 17/17成功。次は移動込みcandidate gate。

O1B-23進捗4（gate RED）: verified date inventoryとbusy inventoryだけを受け、直接衝突、all-day衝突、
前後5分bufferを足した実route時間による衝突を候補ごとに判定する3 testを追加した。短い既存予定が一件
あっても後続のfree候補を残し、route不能は`unavailable`でなくrecovery、結果はopaque refだけを保持する。
production gate module不存在のため期待どおり失敗する段階である。

O1B-23進捗5（gate GREEN / pack RED）: direct/all-day/travel-expanded conflictを全candidateへ投影し、
route不能をrecoveryにするcontent-addressed gateを実装した。focused 20/20成功。次にgateでeligibleなcandidate
だけをcanonical URL付きで既存same-day sequenceへ渡すpack契約を追加した。helper/method未実装のためRED段階。

O1B-23進捗6（candidate pack GREEN / calendar pack RED）: verified gateと同じinventory snapshotの全候補を
照合し、eligibleだけを既存same-day sequenceへ渡す`runCalendarGatedSameDay`を実装、focused 13/13成功。
次にbusy readとtravel gate自体もevents packの一操作として所有する契約を追加した。2 method未実装でRED段階。

O1B-23進捗7（calendar pack GREEN / write transport RED）: events packへbusy read、travel gate、eligible-only
same-day sequenceを接続しfocused 27/27成功。既存Calendar writeはsuccess booleanだけでevent IDと冪等keyを
残さないため、固定private propertyで既存eventを先に検索し、未作成時だけprovider ID/link付きで作成する
transport契約2 testを追加した。新method未実装でRED段階。

O1B-23進捗8（write transport GREEN / sync RED）: private property検索とprovider ID/link付き作成をgog transportへ
実装し20/20成功。次にin-process verifier provenanceのあるLuma registration receiptとcalendar-eligible gateだけを
受け、同一eventを一度だけ作成しexact retryは既存eventを返すsync契約2 testを追加した。module未実装でRED段階。

O1B-23進捗9（sync GREEN / final pack RED）: verified outbound receipt、同一canonical Luma URL、eligible gateを
全て照合してからだけCalendarを検索・作成するsyncを実装した。exact retryは既存eventを返し、provider IDは
opaque ref化する。sync + transport 18/18成功。events packへsync境界を公開する契約を追加した。

O1B-23完了: events packへ全calendar busy read、移動込みgate、eligible-only same-day sequence、verified
registration後の冪等Calendar syncを接続した。実production read-onlyは5 calendar、124 source event、
123 busy、transparent 1除外で、raw予定名・場所fieldはsnapshotに0。短い予定の前後へ候補を残し、
direct/all-day/travel-expanded conflictだけをopaque event ref付きで落とす。focused 32/32、追加境界12/12、
outbound全回帰184/184成功。証拠:
`docs/evidence/outbound/2026-08-02-o1b23-live-all-calendar-travel-gate.json`。次は`O1B-24`で、無料候補を
優先し、有料候補は一度設定した自動支出policy内だけ保存済み決済手段を使い、都度承認なしで進める。

完了条件: 実Luma登録、確認mail、QR、Telegram報告が同一eventとして照合され、
今日を含む21日間（今日〜20日後）に未処理の空き日がない。各日は次のどれか一つである。

- `covered_existing`: 既に参加確定した東京の対面eventがあるため、重複予約しない。
- `covered_new`: Connectorが新たに東京の対面eventを予約し、receiptを取得した。
- `unavailable`: 固定予定と前後移動時間で実行可能なevent枠が残っていないため、重複予約しない。

単にCalendarへ何か一件あるだけでは`covered_existing`にしない。既存予定が短時間なら、その前後の
free intervalへ参加できるeventを探す。`unavailable`は、候補eventの開催時間と前後移動時間が
固定予定に衝突することをCalendar event IDと時刻で証明できた場合だけ使う。「候補を見つけられない」
ことを`unavailable`へ変換してはならない。終了条件は21日分の`open`が0件になったことだけである。
既存eventのcancelや予定変更で枠が空けば、その日は次回runで自動的に`open`へ戻る。

検索の停止条件は「候補が見つからなかった」ではなく、rolling 21日coverageが埋まったことである。

```text
今日〜20日後についてGoogle Calendarの全calendarを読む
  → 既存event、勤務、学校、移動時間からbusy/free intervalを計算
  → 既存の東京対面eventがある日はcovered_existing
  → 固定予定で参加可能な時間が残らない日はunavailable
  → それ以外をopenとして、日付の早い順に処理
  → Luma mainのTokyo / In Person inventoryを最後まで取得
  → agentが全候補を読み、好み・目標・人との出会い・serendipityでranking
  → free intervalと前後移動時間に収まる最上位候補へ申込
  → 満席・失敗・確認なしなら同じ日の次候補へ即時進む
  → Lumaを十分に探索しても確保できない時は別の許諾済み予約sourceへ進む
  → connpass key受領後は公式APIを候補発見にだけ使い、予約はしない
  → 東京・対面・時間非衝突・自動支出policy内を確認
  → 完了画面または確認mailを取得
  → Calendar、QR、Telegramを作成
  → その日をcovered_newにする
  → 21日分のopenが0になるまで続ける
```

好みは自然言語promptと実際の参加結果から学習する。AI、crypto、英語、founder等は「高く評価する
例」であり、それ以外を除外するkeyword listではない。最も重要な目的は、Daisが家に留まらず、
毎日東京で人と会い、経験と接点を増やすことである。

同じ壊れた申込画面を無限に繰り返さない。失敗した候補は記録し、同じ日の別候補へ進む。
「0件」「検索した」「時間切れ」を正常終了にせず、`open=0`になるまで継続状態を次のjobへ渡す。
認証challenge等で一候補を完了できなくても人間の操作待ちでloop全体を止めず、別候補へ進む。

Connector内部構成:

```text
Connector Lead（21日coverageと応募完了を所有）
  ├─ Calendar Tool       gogで予定を取得・作成、重複と時刻を計算
  ├─ Event Scout         Luma本文を読み、候補とserendipityをagent判断
  ├─ Registration Tool   CloakBrowser :9222で申込、完了画面・mail・QRを取得
  ├─ Confirmation Tool   gog Gmailで確認mail、承認、cancelを照合
  ├─ Routes Tool         前後予定と移動時間を使い、申込可能か計算
  └─ Application Ledger  discovered→attempted→confirmed→calendar_addedを記録
```

Calendar/Routesの時刻計算、dedup、状態遷移、証拠照合はdeterministicに行う。どのeventへ応募するかは
agentが本文と履歴を読んで判断し、keyword/regexの固定分類へ戻さない。現地参加、参加者への連絡、
返信、follow-up、次回面談はこのConnectorのscopeへ含めない。

### 5.3 Order 1C — 資金調達・アクセラレーター

- [ ] O1C-01 `application-kit`をcompany factsの正本として接続
- [ ] O1C-02 funder/accelerator registryを再構築
- [ ] O1C-03 MUFG運営/CVC deny gateとpartner確認を実装
- [ ] O1C-04 YC descriptionを制約内へ修正
- [ ] O1C-05 58秒founder videoを検証してupload
- [ ] O1C-06 founder profileを完了
- [ ] O1C-07 YC Fall 2026へ実提出
- [ ] O1C-08 完了画面、確認mail、ledger、Telegramを照合
- [ ] O1C-09 cold outreachを1日3〜5通で再開
- [ ] O1C-10 follow-up最大2回を自動実行
- [ ] O1C-11 Gmail reply/rejection/meetingを型付きstatusへ反映
- [ ] O1C-12 meetingをCalendarへ登録し面談資料を生成
- [ ] O1C-13 全form送信を既存CloakBrowser daily-driverで行い、新browserを起動しない
- [ ] O1C-14 公式program pageを毎日探索し、固定list外の新規募集をregistryへ追加
- [ ] O1C-15 deadline、location、solo可否、terms、eligibilityを提出当日に再検証
- [ ] O1C-16 会社facts、traction、MRR、deck、videoのfreshness gateを実装
- [ ] O1C-17 `gog`でconfirmation/replyをthread ID単位に取得し、Job Hunter ledgerへ統合
- [ ] O1C-18 application→confirmation→interview→offer/reject→fundedのfunnelをWebへ投影
- [ ] O1C-19 accelerator以外のVC/angelはthesis一致時だけ1日3〜5件へpersonalized outreach
- [ ] O1C-20 採択・面談の結果を次のpitchとtarget rankingへ反映する週次reflection
- [ ] O1C-21 旧`apply-to-yc`のfield/video/progress知識を後継YC providerへ移植
- [ ] O1C-22 古いSummer application IDがFall 2026へ継続可能かYC home実画面で確認
- [ ] O1C-23 `yc-w26.json`のbatch、deadline、amount、URLをcurrent official factsへ更新
- [ ] O1C-24 YC操作を別Chrome `9223`から既存CloakBrowser daily-driver `:9222`へ移行
- [ ] O1C-25 current company facts、founder profile、58秒動画、demo、progressをpreviewで全確認
- [ ] O1C-26 Submitを一度だけ実行し、完了画面とconfirmation mailを取得
- [ ] O1C-27 YC reply/interviewを毎日追跡し、Calendarと面談準備へ接続

完了条件: 実accelerator提出と確認receipt、reply追跡、面談calendar経路が動く。

### 5.4 Order 2 — 求人応募

- [ ] O2-01 job worktreeの未commit変更を整理
- [ ] O2-02 canonical mainへrebase
- [ ] O2-03 206 testを再実行し緑化
- [ ] O2-04 PR、review、merge
- [ ] O2-05 canonical runtimeで実cycle
- [ ] O2-06 700万円未満reject・1,000万円targetを実logで検証
- [ ] O2-07 Guardian、Lifecycle、summary.v2を完成
- [ ] O2-08 Ashbyへ実応募しreceipt取得
- [ ] O2-09 Workdayへ実応募しreceipt取得
- [ ] O2-10 面接mail→Calendarを実証
- [ ] O2-11 trace、週次reflection、segment Pareto、20% holdoutを実装
- [ ] O2-12 既存daily-driver owner `ai.anicca.job-search-daily`を維持し、共有browserや他tabを閉じない

完了条件: AshbyとWorkdayの実receipt、canonical実cycle、面接mail→Calendarが揃う。

### 5.5 Order 3A — CFO実行基盤復旧

- [ ] O3A-01 runtime database URLをsecret providerから注入
- [ ] O3A-02 bootが正しいenv/secretを読む
- [ ] O3A-03 financial executorをlaunchdへ登録
- [ ] O3A-04 enqueue→claim→execute→receipt→Telegramを実証
- [ ] O3A-05 restart、retry、dead-letter、dedupを実証
- [ ] O3A-06 死んだ`ai.anicca.cfo-daily`残骸を退役
- [ ] O3A-07 data freshnessと失敗をTelegramへ警告

### 5.6 Order 3B — Dais個人CFO

- [ ] O3B-01 account、transaction、position、liability schema
- [ ] O3B-02 JPY、original currency、FX provenance
- [ ] O3B-03 Moneytree OAuth read connection
- [ ] O3B-04 銀行・card・証券の残高と明細をimport
- [ ] O3B-05 Binance read-only接続
- [ ] O3B-06 Daisのon-chain walletをread-only取得
- [ ] O3B-07 内部振替の二重計上防止
- [ ] O3B-08 merchant正規化と支出category
- [ ] O3B-09 subscription検出と利用状況
- [ ] O3B-10 1か月・3か月・12か月集計
- [ ] O3B-11 net worth、cash flow、burn、runway、budget、baseline、anomaly
- [ ] O3B-12 daily/weekly/monthly Telegram report
- [ ] O3B-13 reportの全数値からsource receiptへ遡れることを実証
- [ ] O3B-14 CFO Lead Agentのgoal、input、tool、output、停止条件を定義
- [ ] O3B-15 Bookkeeper、Cashflow、Income、Capital、Fiat/NISA、Crypto、Tax、Reporter specialistのcontractを定義
- [ ] O3B-16 specialistが同じ統一財務台帳だけを読み書きし、agent間chatを正本にしない
- [ ] O3B-17 FinRobot型の「数値はコード、解釈はagent、全数値は出典付き」をcontract test化
- [ ] O3B-18 Actual Budgetのaccount/transaction/budget modelをLife Manager schemaと比較し、移植範囲を決定
- [ ] O3B-19 Ghostfolio/rotkiのUX・会計modelについてlicense reviewとcopy禁止境界を記録
- [ ] O3B-20 Financial Organの日次close loopと週次reflection loopを実装
- [ ] O3B-21 specialistごとの予測、提案、実行、結果を同一decision IDで追跡
- [ ] O3B-22 self-improvement変更をhistorical replay→shadow→canary→promotionで検証
- [ ] O3B-23 agentが権限、損失上限、署名policyを自己変更できないことをtest
- [ ] O3B-24 CFOが全specialist結果を一つの人間向けTelegram briefingへ統合

完了条件: Daisの総資産、収入、支出、負債、投資、cryptoがJPYで照合され、1か月・3か月報告が正しい。

### 5.7 Order 4 — 暗号資産運用

- [ ] O4-01 Anicca-ownedとDais-ownedをwallet・ledger・reportで分離
- [ ] O4-02 Dais main Binanceはread-onlyを維持
- [ ] O4-03 CFOから失ってよいcanary上限を算出
- [ ] O4-04 strategy data、backtest、paper trade
- [ ] O4-05 fee、slippage、drawdown、benchmark比較
- [ ] O4-06 paper gate通過strategyだけ小額canary
- [ ] O4-07 1取引・1日・1か月loss cap
- [ ] O4-08 asset/destination allowlist
- [ ] O4-09 LLMから独立したpolicy signer
- [ ] O4-10 emergency stopとrecovery
- [ ] O4-11 fill、fee、transfer、P&LをCFOへ照合
- [ ] O4-12 負けるstrategyを縮小・停止し、勝つstrategyだけ段階増額
- [ ] O4-13 TradingAgents型のanalyst→bull/bear→trader→risk→portfolio reviewをpaper環境へ接続
- [ ] O4-14 ai-hedge-fundのbacktesterとLife Managerのfee/slippage/benchmark要件を比較
- [ ] O4-15 debate agentの多数決ではなく、独立Risk Governorのpolicy gateを最終権限にする
- [ ] O4-16 reflectionが未来dataを参照しないlook-ahead防止evalを通す

完了条件: 所有者別会計、全cap、緊急停止、after-fee P&L、CFO照合が実canaryで成立する。

### 5.8 Order 5 — 法定通貨投資・NISA

- [ ] O5-01 emergency cash reserveと投資可能余剰をCFOから算出
- [ ] O5-02 NISA保有、年間残枠、生涯残枠、課税口座を分離
- [ ] O5-03 J-Quants等から市場dataを取得
- [ ] O5-04 Daisの証券会社と正式execution APIを実測
- [ ] O5-05 NISA口座でAPI注文可能かを口座・商品別に検証
- [ ] O5-06 allocation、積立、rebalance proposal
- [ ] O5-07 approval/signing policy
- [ ] O5-08 order→fill→receipt→CFOを実証
- [ ] O5-09 fee、配当、税、FX込みperformance
- [ ] O5-10 monthly Telegram report
- [ ] O5-11 FinRobotのvaluation operatorとOpenBBのdata interfaceをJ-Quants/NISA向けに評価
- [ ] O5-12 Fiat/NISA Agentの提案をRisk GovernorとCFO Leadが別々にreview
- [ ] O5-13 benchmark、tax、fee後performanceを週次reflectionへ戻す
- [ ] O5-14 NISA制度・年間枠・生活防衛資金をagentが自己変更できないpolicyとして固定

完了条件: cash reserve、NISA、課税口座、cryptoを混ぜず、提案から約定・CFO反映まで照合される。

### 5.9 Order W — Life Manager Webアプリ化

- [ ] OW-01 localのjob、specialist contract、ledger、report templateをshared coreとして切り出す
- [ ] OW-02 全financial row、decision、secret、artifactへtenant境界を追加
- [ ] OW-03 tenant別Google OAuth、Moneytree OAuth、exchange/broker credential vault
- [ ] OW-04 tenant別browser profile、scheduler、worker、rate limit、cost budget
- [ ] OW-05 Telegram account connectionと同じ直接link/添付UXを再現
- [ ] OW-06 Web panelへnet worth、cash flow、1/3/12か月、応募funnel、agent別成果を表示
- [ ] OW-07 user自身がpermission、budget、risk cap、停止を確認・変更できる設定画面
- [ ] OW-08 data export、account disconnect、token revoke、全data削除を実装
- [ ] OW-09 security review、tenant isolation test、secret leak test、financial action audit
- [ ] OW-10 Stripe subscriptionとtrue MRR、churn、active paidを計測
- [ ] OW-11 Dais以外のpilot user一人でbank接続からTelegram月次報告まで実証
- [ ] OW-12 pilotの誤分類・誤通知・離脱理由をevalへ戻し、10人→100人へ段階拡大

完了条件: Daisローカル版を書き直さず、同じcoreを別userが自分の口座・Telegram・risk policyで
安全に使い、最初の有料継続利用と月次reportまで成立する。

## 6. agent判断とdeterministic処理の境界

agentが判断する:

- event、accelerator、jobの意味・適合性・優先度
- 相手ごとの応募文面・返信
- 市場状況からの候補戦略と説明
- transactionのmerchant/category候補とconfidence
- 支出の意味、通常状態からの逸脱理由、利用者へ伝える優先度
- 複数の投資仮説、反対意見、riskの説明、実行候補のranking
- specialistを呼ぶ必要があるか、追加dataを調べるべきか、いつ判断を保留するか

deterministic codeが担当する:

- API/browser tool
- 金額計算
- 権限と上限
- ledger
- deduplication
- receipt検証
- retry、heartbeat、emergency stop
- 口座残高、複式/振替照合、JPY換算、tax lot、fee、PnL、NISA枠
- permission、allowlist、loss cap、生活防衛資金、署名、注文の最終gate
- source timestamp、freshness、decision ID、監査履歴、Telegram delivery

意味判断をregexやkeywordだけで実装しない。固定形式のparseだけにregexを許可する。
specialist agentの合議、多数決、CFO Leadの指示のいずれも、deterministic policy gateを
上書きできない。

## 7. ローカルからLife Manager Webアプリへの進化

新しい二つ目のLife Managerを作らない。同じruntime、ledger、receipt、Telegram文面を
ローカルとWebで共有する。

```text
段階L: DaisのMacで実証
  CloakBrowser daily-driver :9222
  + local scheduler / executor
  + PostgreSQL ledger
  + Telegram
          ↓ 同じjob・同じreceipt・同じsnapshot hash
段階W: 既存Life Manager panelへ投影
  Telegram = 毎日の操作面
  Web panel = 詳細、履歴、グラフ、証拠
          ↓ Order 1〜5のlocal実証完了後
段階C: Life Manager Webアプリとして提供
  tenant別connector
  + tenant別secret / browser profile
  + managed scheduler / worker
  + subscription
```

ローカル版で得た実装を捨ててWeb版を書き直さない。Webアプリは同じcoreの別表示・別配置である。

### 7.1 画面の役割

- Telegram: 朝の要約、完了報告、例外警告、承認、停止
- Web panel: 全資産、1か月・3か月推移、応募funnel、receipt、agent別P&L、設定
- CloakBrowser daily-driver: ローカルの外部Web操作。ユーザー画面ではない
- ledger: TelegramとWeb panelの唯一の数値正本

## 8. 月間1,000万円への経済モデル

月間1,000万円を一つの曖昧な数字にしない。dashboardでは次を分ける。

```text
月間総経済効果
  = 給与手取り増分
  + Life Managerその他事業の継続売上
  + agentの外部純収益
  + 暗号資産・法定通貨投資の実現純利益
  + 削減した固定費

事業MRR
  = 毎月継続して支払う顧客からの売上だけ
```

給与、資金調達額、含み益、元本入金をMRRとして数えない。

各agentの寄与:

| agent | 月間1,000万円へどう寄与するか | 正しい計測 |
|---|---|---|
| Events | 登壇、顧客、投資家、採用機会を増やす | 登録→参加→商談→成約 |
| Fundraising | 資金とnetworkを獲得し、runwayと事業成長速度を上げる | 調達額はMRRでなくcapital |
| Job Hunter | より高い安定収入を獲得する | 旧職との差額、手取り、継続月数 |
| CFO | 無駄な固定費を止め、投資可能余剰を増やす | 解約・削減済み金額、cash flow |
| Crypto Manager | 分離された小額capitalをrisk-adjustedに運用する | fee後実現P&L、drawdown |
| Fiat/NISA | 長期資本を税制込みで複利運用する | 税・fee後performance |
| Life Manager Webアプリ | Daisで実証したsystemを他userへ月額提供する | active paid、churn、真のMRR |

真のMRRを月間1,000万円にする算式例:

| 月額単価 | 必要な継続有料user |
|---:|---:|
| ¥10,000 | 1,000人 |
| ¥20,000 | 500人 |
| ¥50,000 | 200人 |

最初はDais一人のローカル運用で、支出削減、応募、収入、投資、Telegram UXを実証する。
その後、同じcoreをLife Manager Webアプリへ統合し、有料userの継続売上をMRRとして積み上げる。

## 9. 完成時の全体図

```text
                              Dais
                               │
                    1つのTelegramチャット
                               │
       ┌───────────────────────┼────────────────────────┐
       │                       │                        │
イベント・資金調達          求人応募                   CFO
応募・追跡・面談          応募・返信・面接       総資産・支出・収支
       │                       │                        │
       └───────────────────────┼────────────────────────┘
                               │
                        資金配分・危険管理
                               │
                    ┌──────────┴──────────┐
                    │                     │
              暗号資産運用          法定通貨・NISA
             AniccaとDais分離          長期資産形成
                    │                     │
                    └──────────┬──────────┘
                               │
                          統一財務台帳
                               │
                      計測 → 学習 → 改善
                               │
                         Telegramへ報告
```

### 9.1 Life ManagerのOrgan構造

Life Manager全体は四つのorganを持つ。同じuser、Calendar、Telegram、memoryを共有するが、
organごとに目的、data、権限を分離する。

```text
Life Manager
│
├─ Daily Organ
│   └─ 今日の予定、応募、連絡、優先順位、実行状況
│
├─ Physical Organ
│   └─ 睡眠、運動、食事、通院、身体data
│
├─ Mental Organ
│   └─ 気分、注意、習慣、瞑想、介入、振り返り
│
└─ Financial Organ
    └─ 残高、支出、収入、資金調達、投資、risk、純資産
```

Daily Organは一日の入口であり、他organの正本dataを所有しない。たとえば「今夜のイベント」と
「今月使えるevent予算」はDailyとFinancialの両方に関係するが、予定の正本はCalendar、
予算の正本はFinancial ledgerとする。

### 9.2 Financial Organ — CFO Leadとspecialist

```text
                              Dais
                               │
                        Telegram / Web
                               │
                         CFO Lead Agent
               目標、優先順位、task分解、最終説明
                               │
       ┌───────────┬───────────┼───────────┬───────────┐
       │           │           │           │           │
  Bookkeeper   Cashflow     Income      Capital     Reporter
  Agent        Agent        Agent       Agent       Agent
  明細整理     予算・burn   給与・事業   資金調達     人間向け報告
  振替照合     subscription 求人成果     runway       link/添付
       │           │           │           │           │
       └───────────┴──────┬────┴───────────┴───────────┘
                          │
                  Portfolio Strategy Team
                 ┌────────┴─────────┐
                 │                  │
          Fiat / NISA Agent    Crypto Agent
          日本株・ETF・現金      Binance・wallet
                 │                  │
                 └────────┬─────────┘
                          │
                  Independent Review
             ┌────────────┴────────────┐
             │                         │
        Tax/Audit Agent          Risk Governor
        税・出典・照合            上限・権限・停止
             │                         │
             └────────────┬────────────┘
                          │
             Deterministic Policy + Signer
          金額計算・NISA枠・loss cap・allowlist
                          │
                 Bank / Broker / Exchange
```

役割:

| role | 自分で考えること | 自分では変更・実行できないこと |
|---|---|---|
| CFO Lead | 今日の財務課題、必要なspecialist、優先順位、Daisへの説明 | ledger数値の創作、risk gateの上書き、秘密鍵操作 |
| Bookkeeper | merchant/category候補、明細の意味、確認が必要な取引 | 残高計算、振替の二重計上、原本削除 |
| Cashflow | 支出の異常、予算改善、subscription、runway改善案 | 予算値の無断変更、契約の即時解約 |
| Income | Job Hunter、事業収入、agent収益の改善仮説 | 給与やMRRへの資金調達額・含み益の混入 |
| Capital | accelerator、VC、grant、runwayの資金調達戦略 | 調達を売上として計上、契約への無断署名 |
| Fiat/NISA | allocation、積立、rebalance、投資仮説 | NISA枠・生活防衛資金・注文上限の変更 |
| Crypto | strategy、market調査、paper結果、canary提案 | Dais main口座の出金、loss cap変更、無許可asset |
| Tax/Audit | source不足、税区分、照合差、監査質問 | 不明差額を推測で埋める |
| Reporter | 全agentの結果を人間が理解できる一通へ編集 | 未確認の成功、数字、linkの創作 |
| Risk Governor | 反対意見、集中risk、流動性、停止提案 | policy signerを迂回した執行 |

CFO Leadだけを常時「親」とするが、すべてのspecialistを毎回起動しない。残高同期ならBookkeeper、
支出異常ならCashflow、投資日ならFiat/NISAとRiskだけを呼ぶ。これはagent数を増やすこと自体を
目的にせず、必要な専門判断だけを呼ぶためである。

### 9.3 一日のFinancial Organ loop

```text
OBSERVE
  Moneytree / bank / card / Binance / wallet / broker / incomeを同期
     ↓
RECONCILE
  残高、明細、振替、為替、freshnessを決定的コードで照合
     ↓
CFO PLAN
  CFO Leadが今日解くべき問題と必要なspecialistを選ぶ
     ↓
SPECIALIST ANALYSIS
  支出、収入、資金調達、Fiat、Crypto、Taxを必要な分だけ分析
     ↓
CHALLENGE
  bull/bearではなく、提案に応じた反対仮説とRisk reviewを行う
     ↓
POLICY GATE
  金額、権限、生活防衛資金、NISA枠、loss cap、allowlistをcodeで検査
     ↓
EXECUTE
  読取、応募、通知、承認済み注文など許可されたtoolだけを実行
     ↓
VERIFY
  providerの完了結果、mail、fill、残高変化を元のdecisionへ結合
     ↓
REPORT
  「何をした・なぜ・いくら・結果・次」をTelegramへ直接link付きで送る
```

### 9.4 self-improvement loop

各specialistはloopを持つが、勝手にpromptや権限を書き換えて即本番化しない。

```text
予測・提案をdecision ID付きで保存
       ↓
後日の実結果と比較
       ↓
失敗理由・成功理由を週次reflection
       ↓
prompt / tool / data sourceの改善案を生成
       ↓
過去期間を使ったhistorical replay
       ↓
現行版とのshadow比較
       ↓
小範囲canary
       ↓
accuracy、after-fee効果、false positive、costが改善した時だけpromotion
       ↓
悪化時は自動rollback
```

self-improvementの対象:

- 調べるsourceと追加query
- 説明の分かりやすさ
- category提案
- anomalyの優先順位
- investment researchと反対仮説
- Telegram reportの有用性

self-improvementの対象外:

- bank/exchange permission
- withdrawal権限
- loss cap
- NISA制度値
- 生活防衛資金
- owner境界
- secret、signer、allowlist

これらのhard safetyはDaisの明示変更とtestなしに変えない。

## 10. Telegram逐語文面の正本

以下はこのtrackでDaisへ届く**正確なtemplate**である。`{{...}}`だけをledgerの実値で置換する。
実装はi18n/templateから生成し、agentが数値や成功を創作しない。

### 10.0 人間向け報告の絶対規則

Telegramは開発者用logではない。利用者が知りたいのは「自分の代わりに何をしたか」である。

通常メッセージに次の内部語を出さない:

- launchd、cron、runner、worker、queue、bounded、timeout、parse
- receipt、ledger、E1/E2/E3、JSON、HTTP status、stack trace
- adapter、provider、runtime、process、exit code

必ず利用者の言葉へ変換する:

| 内部状態 | 利用者へ伝える言葉 |
|---|---|
| job succeeded + evidence verified | 「応募が完了しました。確認メールも届いています」 |
| process succeeded but evidence missing | 「操作は行いましたが、応募完了を確認できていません」 |
| timeout | 「応募画面の途中で止まりました。応募済みにはしていません」 |
| delivery parse error | 「Telegramへの報告送信に失敗しました」 |
| dead-letter / retry scheduled | 「明日もう一度試します」 |
| Gmail reconciliation | 「応募先からのメールを確認しました」 |

すべての行動報告は、次の7問へ上から順に答える。

1. 何をしたか
2. どこへ応募したか
3. 何の役割・登壇内容・programか
4. どの履歴書、deck、動画、応募文を使ったか
5. なぜDaisに合うと判断したか
6. 本当に完了したか、相手から確認が来たか
7. 次に何が起き、Daisに何が必要か

内部診断は通常非表示とし、本文中の`[技術詳細を見る]({{technical_detail_url}})`を
タップした時だけ表示する。

実装時はTelegram templateへcopy lintを置き、上記内部語が通常本文に入ったらtestを失敗させる。
また、履歴書、職務経歴書、cover letter、deck、動画、LT概要はファイル名だけで終わらせず、
Telegram添付または認証済みpanel linkから実物を開けることを完了条件にする。

リンクのUX規則:

- `［履歴書を見る］`のようなURLを持たない疑似buttonは禁止
- 外部のevent・求人・programは、本文中のMarkdown linkから公式pageへ直接開く
- 履歴書、職務経歴書、cover letter、deckはTelegramへ実ファイルを添付する
- 添付に加えて、認証済みLife Managerの恒久URLも本文へ置く
- private artifactへ公開URLを発行しない。user認証または短寿命signed URLを要求する
- 状態変更操作はlink先に確認画面を出し、誤tapだけで取消・送信・売買しない
- Telegram inline keyboardを使う場合も、tap後に目的画面が直接開くことをE2E testする

### 10.1 毎朝の統合briefing

```text
☀️ おはようございます。今日のLife Manager報告です。

純資産: ¥{{net_worth}}（前日比 {{net_worth_delta}}）
現金: ¥{{cash}}
投資: ¥{{investments}}
暗号資産: ¥{{crypto}}
負債: ¥{{liabilities}}

今月の収入: ¥{{income_mtd}}
今月の支出: ¥{{spend_mtd}}
今月の純増減: ¥{{net_change_mtd}}
生活可能期間: {{runway_months}}か月

応募状況:
・イベント: {{event_count}}件
・資金調達: {{funder_count}}件
・求人: {{job_count}}件
・面談予定: {{meeting_count}}件

今日の実行:
{{today_actions}}

[今日の詳細を開く]({{daily_detail_url}})
[今日の実行を止める]({{pause_confirmation_url}})
```

### 10.1A Connectorの24時間UX

Connectorは一日一回の検索cronではなく、21日間の空きを継続的に埋めるevent application loopである。
責務はdiscover、申込、確認mail、QR、Calendar登録までで終わる。現地参加後の連絡や関係管理はしない。

| 時刻 / trigger | 裏側で行うこと | Daisへ届くもの |
|---|---|---|
| 00:05 | 日付を一日進め、今日〜20日後の全Calendar、cancel、変更を再照合 | 通常は無通知 |
| 00:15〜06:00 | `open`日を日付順にLuma中心で探索・申込・mail/QR/Calendar照合。失敗候補は捨てて次へ進む | 通常は無通知 |
| 06:30 | 21日coverage、既存予約、今回の新規予約、未処理の空きを集計 | 朝のConnector briefingを一通 |
| 新規予約成立時 | そのrunで成立した複数eventをまとめて保存 | 3週間の空きを何件埋めたかを一通。eventとCalendarの直接link付き |
| 09:00 | 夜間に届いたLumaの確認、承認、cancel mailを再照合 | 状態が変わったeventだけ通知 |
| 12:00 | 残っている`open`日と、朝以降に公開されたeventを再探索 | 新規予約成立時だけ通知 |
| 18:00 | cancelや予定変更で再び空いた日を検知し、同日の別候補へ申込 | 置換予約が成立した時だけ通知 |
| 23:45 | 未確認申込と未処理の空きを次runへ再投入 | 正常時は無通知。翌日も同じ状態から継続 |

固定時刻はschedulerの起動契機であり、event選択をhardcodeするものではない。新規予約が06:30以降に
成立すれば、翌日まで隠さず成立時に送る。候補単位の失敗は通知せず、別候補へ進む。

現在の次の文面は禁止する。

```text
🔌 Connector 日報 {{date}}
本日の新規登録なし（none: 対面AI/crypto候補が見つからなかった or horizon埋済）
```

禁止理由:

- 「候補がない」と「すでに埋まっている」という別状態を`none`へ潰している
- AI/cryptoをhard filterにし、startup、founder、VC、product、finance、serendipityを捨てている
- 21日間のどの日に空きがあるか分からない
- どのeventへ申し込み、確認mailとCalendar登録が完了したか分からない
- event名、日時、場所、申込link、QRへ直接移動できない

朝のConnector briefing:

```text
🔌 Connector 3週間計画 {{date}}

確認期間: {{window_start}}〜{{window_end}}
既存の対面予定: {{covered_existing_count}}日
新しく予約済み: {{covered_new_count}}日
固定予定で追加不可: {{unavailable_count}}日
未処理の空き: 0日

今日の予定:
{{event_time}} {{event_name}}
場所: {{event_location}}
申込状態: {{registration_status}}

[今日のイベント]({{canonical_event_url}})
[QRを開く]({{ticket_url}})
[3週間のCalendar]({{calendar_coverage_url}})
```

新規予約成立時:

```text
🎟️ 3週間の空きを{{covered_new_count}}件埋めました。

確認期間: {{window_start}}〜{{window_end}}
未処理の空き: {{open_count}}日

今回予約したevent:
{{confirmed_event_rows}}

各eventについて申込完了画面または確認mailを取得し、Calendarへ登録しました。

[予約したeventを開く]({{confirmed_event_list_url}})
[3週間のCalendarを開く]({{calendar_coverage_url}})
```

新規予約0件が許される文面:

```text
✅ 今後3週間のevent予定はすでに埋まっています。

確認期間: {{window_start}}〜{{window_end}}
既存予約でcovered: {{covered_existing_count}}日
固定予定により追加不可: {{unavailable_count}}日
未処理の空き: 0日
今回の新規予約: 0件

理由: 21日間に申込可能な空きが残っていないため、二重予約しませんでした。

[3週間のCalendarを開く]({{calendar_coverage_url}})
[予約済みeventを開く]({{confirmed_event_list_url}})
```

「見つからなかった」だけを理由に新規予約0件を送ってはならない。`open`が残る限り探索と申込を
継続する。Connectorの報告対象はevent applicationだけであり、現地参加、相手への連絡、返信、
次回面談を実行・報告しない。

### 10.2 イベント登録

```text
🎟️ イベント参加の申込みが完了しました。
イベント: {{event_name}}
日時: {{event_datetime}}
場所: {{event_location}}
申込者: {{registration_identity}}

このイベントを選んだ理由:
{{selection_reason}}

当日のQRをこのメッセージに添付しました。
カレンダーにも登録済みです。

イベントページ: {{canonical_event_url}}

[イベントページを開く]({{canonical_event_url}})
[カレンダーを開く]({{calendar_event_url}})
[申込内容を見る]({{application_detail_url}})
```

一候補の証拠が不足した場合は、通常Telegramへ失敗報告を送らない。未確認候補をCalendarへ
登録せず、同じ日の次候補へ進む。account lock、予期しない課金、identity不一致のようにDaisの
資産・accountへ影響する例外だけを即時警告し、Connector本体は安全な別候補で継続する。

LT・登壇応募:

```text
🎤 {{event_name}}へLT登壇を申し込みました。

発表タイトル: {{talk_title}}
発表時間: {{talk_duration}}
話す内容:
{{talk_summary}}

Life Managerを紹介する部分:
{{product_demo_summary}}

提出したもの:
・登壇者プロフィール: {{speaker_profile_name}}
・発表概要: {{abstract_name}}
・デモURL: {{demo_url}}
・スライド: {{slide_status}}

現在の状態: 主催者の確認待ち
回答予定: {{expected_reply_date}}

[提出した登壇内容を見る]({{talk_application_url}})
[イベントページを開く]({{canonical_event_url}})
[カレンダーを開く]({{calendar_event_url}})
```

### 10.3 アクセラレーター提出

```text
🚀 {{program_name}}へ応募しました。

会社: {{company_name}}
応募したprogram: {{program_name}}
応募日時: {{submitted_at}}

このprogramを選んだ理由:
{{fit_reason}}

提出したもの:
・応募回答: {{application_answer_version}}
・pitch deck: {{deck_name}}
・創業者動画: {{founder_video_name}}
・product demo: {{demo_name}}
・使用した実績値: {{traction_as_of}}時点

相手からの確認メール: 受信済み
現在の状態: 書類選考待ち
次に確認する日: {{followup_at}}

[応募回答を見る]({{application_detail_url}})
[pitch deckを開く]({{deck_url}})
[確認メールを見る]({{confirmation_mail_url}})
```

### 10.4 投資家・アクセラレーターからの返信

```text
📨 {{sender_name}}から返信が届きました。
判定: {{reply_status}}
要点: {{reply_summary}}
必要な次の行動: {{next_action}}

{{meeting_datetime_line}}

[返信案を見る]({{reply_draft_url}})
[カレンダーを開く]({{calendar_event_url}})
```

### 10.5 求人応募

```text
💼 求人への応募が完了しました。

会社: {{company}}
職種: {{role}}
勤務地: {{location}}
提示年収: {{salary_range}}

この求人を選んだ理由:
{{fit_reason}}

提出したもの:
・履歴書: {{resume_name}}
・職務経歴書: {{career_history_name}}
・cover letter: {{cover_letter_name}}
・追加回答: {{additional_answers_summary}}

相手からの応募確認メール: {{confirmation_mail_status}}
現在の状態: {{human_status}}
次に確認する日: {{followup_at}}

[求人ページを開く]({{job_url}})
[提出した履歴書を開く]({{submitted_resume_url}})
[応募内容を見る]({{application_detail_url}})
```

### 10.6 面接確定

```text
📅 面接が決まりました。
会社: {{company}}
職種: {{role}}
日時: {{interview_datetime}}
形式: {{interview_format}}

カレンダーへ登録済みです。
会社調査、想定質問、回答材料も準備しました。

[面接準備を見る]({{interview_prep_url}})
[カレンダーを開く]({{calendar_event_url}})
```

### 10.7 支出異常

```text
⚠️ 支出に異常を検知しました。
項目: {{merchant_or_category}}
今月: ¥{{current_amount}}
通常: ¥{{baseline_amount}}
差: {{difference_percent}}%

主な明細:
{{transaction_lines}}

[明細を見る]({{transaction_detail_url}})
[予算を変更する]({{budget_edit_url}})
[今月だけ除外する]({{ignore_confirmation_url}})
```

### 10.8 未使用subscription

```text
💡 未使用の可能性が高いsubscriptionがあります。
サービス: {{service_name}}
料金: ¥{{monthly_fee}}／月
最終利用確認: {{last_used_at}}
年間削減額: ¥{{annual_saving}}

[解約手順を見る]({{cancellation_guide_url}})
[維持すると記録する]({{keep_confirmation_url}})
[判断を保留する]({{snooze_confirmation_url}})
```

### 10.9 暗号資産の実行報告

```text
₿ 暗号資産の取引を実行しました。
所有者: {{owner}}
戦略: {{strategy}}
取引: {{side}} {{asset}}
約定額: ¥{{notional}}
手数料: ¥{{fee}}
現在の実現損益: ¥{{realized_pnl}}
本日の損失上限残り: ¥{{loss_budget_remaining}}

取引証拠: {{receipt_url}}
```

損失停止時:

```text
🛑 暗号資産運用を自動停止しました。
所有者: {{owner}}
理由: {{stop_reason}}
本日の実現損益: ¥{{realized_pnl}}

新規注文を停止し、未約定注文を取り消しました。
資金は元の隔離口座またはwalletに残っています。

[停止理由を見る]({{stop_detail_url}})
[停止を維持する]({{keep_stopped_url}})
```

### 10.10 NISA・法定通貨投資

```text
📈 今月の投資案です。
投資可能余剰: ¥{{investable_surplus}}
生活防衛資金: ¥{{emergency_reserve}}（保護）
NISA年間残枠: ¥{{nisa_remaining}}

提案:
{{allocation_lines}}

この提案後の資産配分:
{{post_allocation_lines}}

[投資案の詳細を見る]({{proposal_detail_url}})
[今回は見送る]({{skip_confirmation_url}})
```

約定後:

```text
✅ 投資注文が約定しました。
口座: {{account_type}}
商品: {{instrument}}
約定額: ¥{{filled_amount}}
手数料: ¥{{fee}}
NISA年間残枠: ¥{{nisa_remaining}}

注文証拠: {{receipt_id}}
CFOの総資産へ反映済みです。
```

### 10.11 月次締め

```text
💰 {{year_month}}の月次報告です。

純資産: ¥{{net_worth}}
前月比: {{net_worth_change}}

給与・事業収入: ¥{{earned_income}}
事業MRR: ¥{{business_mrr}}
agent外部純収益: ¥{{agent_net_income}}
投資実現損益: ¥{{investment_realized_pnl}}
削減できた固定費: ¥{{cost_savings}}
月間総経済効果: ¥{{total_economic_effect}}

支出: ¥{{spend}}
暗号資産最大下落: {{crypto_drawdown}}%
NISA利用額: ¥{{nisa_used}}

応募成果:
・イベント参加: {{events_attended}}件
・資金調達面談: {{fundraising_meetings}}件
・求人面接: {{job_interviews}}件

月間1,000万円目標まで: ¥{{target_gap}}
来月の重点: {{next_month_focus}}

[月次報告の詳細を見る]({{monthly_report_url}})
[元データを見る]({{source_detail_url}})
```

## 11. 最終利用体験

### 11.0 全実装後の一枚図

```text
                         Life Manager
                              │
                  goal・権限・risk policy・予算
                              │
       ┌──────────────┬───────┴────────┬──────────────┐
       ▼              ▼                ▼              ▼
  Connector       Fundraising      Job Hunter    Financial Organ
  21日を埋める     応募→返信→面談    応募→面接→offer  CFO Lead
  Calendar/QR      accelerator/VC    給与改善          │
       │              │                │        ┌─────┼────────┐
       │              │                │        ▼     ▼        ▼
       │              │                │      支出   Crypto   Fiat/NISA
       │              │                │      改善   運用      長期運用
       └──────────────┴────────┬───────┴──────────────┘
                               ▼
                共通runtime + decision/receipt ledger
                               │
                    ┌──────────┴──────────┐
                    ▼                     ▼
             Telegram（毎日の行動面）   Web（資産・履歴・証拠）
```

このsystemが増やす対象は一つではない。Connectorは出会いと機会、Fundraisingは提出・面談・資金、
Job Hunterはofferと給与、CFOは可視性・費用削減・資金配分、CryptoとFiat/NISAはrisk調整後の資産形成を
担当する。すべてを同じdecision IDとreceiptで測り、給与、調達額、含み益、元本をMRRへ混ぜない。
利益、採択、offer、10M MRR、billionaire到達は保証値にしない。毎日の実行と結果を測り、失敗した仮説を
縮小し、証拠上よい経路へ時間とrisk budgetを段階配分する。

毎朝:

- 総資産と前日比
- 1か月・3か月の収入と支出
- 異常支出と不要subscription
- event登録と当日QR
- accelerator応募・reply・meeting
- job応募・reply・interview
- cryptoとNISAの成績
- 今日agentが実行する行動

日中:

- event QRが届く
- accelerator提出確認が届く
- investor/recruiter replyを追跡する
- meeting/interviewをCalendarへ登録する
- financial cap違反時は自動停止する

月末:

- source receipt付き財務報告
- agent別の収入・費用・利益・損失
- 応募→返信→面談→採択のfunnel
- crypto/NISAのafter-fee成績
- 翌月の予算、資金配分、改善対象

## 12. 2026-08-01時点の資金調達queue

固定listを永続的な正本にはしない。以下は**今日のbootstrap queue**であり、毎日公式pageから
再取得する。締切、terms、eligibilityが変わったprogramを古いJSONのまま提出しない。

| 優先 | program | 2026-08-01の公式事実 | 今日の判断 |
|---:|---|---|---|
| 1 | [SPC Founder Fellowship F26](https://www.southparkcommons.com/founder-fellowship) | 8月2日締切、solo founder可、SF/NYC/Bangalore、$400Kで7% + 次round $600K | **最優先でprepare**。NYC peer groupへの直接経路にもなる |
| 2 | [YC Fall 2026](https://www.ycombinator.com/apply) | 7月27日の定時締切後もlate application受付、10〜12月SF | 既存draftを現在batchへ移し、事実と動画を再検証して提出 |
| 3 | [a16z SPEEDRUN](https://speedrun.a16z.com/faq) | SR007締切後もoff-cycle受付。次回SR008は2027年1〜4月SF。solo可、最大$1M | 古い`a16z START` specを使わず、SPEEDRUN最新form specを新設 |
| 4 | [Entrepreneurs First](https://apply.joinef.com/) | London Fallは8月4日、SF Bridgeは8月30日。full-time/in-person | 居住・visa・full-time条件を確認してqualify |
| 5 | [Techstars](https://www.techstars.com/for/founders) | 複数programへ随時応募、標準投資$220K | fintech/AI/NYCなど個別program単位でdeadlineをdiscover |
| 6 | [Antler Japan](https://www.antler.co/location/japan) | 6週間Tokyo、$150K初期投資。掲載cohort日付は既に経過 | 次cohort公開をdaily watcherで検知。古い日付では提出しない |

YCの標準dealは$500Kで、$125Kが7%、残り$375Kがuncapped MFN SAFEである。
a16z SPEEDRUNは最大$1Mで、$500Kが10%、残り$500Kが次roundである。SPCは$400Kで7%と
次round $600Kである。したがって「数億ドルを1%で調達」は初期roundの現実的な前提ではない。
$100Mを1%で調達するにはpost-money $10Bが必要であり、まずproduct tractionと段階的な
valuation上昇が必要である。

## 13. Fundraising agentの連続loop

```text
毎日06:30 DISCOVER
  公式accelerator/VC/grant page・newsletter・既知registryを取得
        │
        ▼
QUALIFY（agent判断）
  Life Managerとの適合、solo可否、地域、締切、terms、競合、MUIT conflict
        │
        ├─不適合 → 理由付きskip + 次回再確認日
        ▼
PREPARE
  application-kitの事実 + 最新traction + deck + 58秒video + program別回答
        │
        ▼
VERIFY（deterministic gate）
  全必須field / facts freshness / URL / terms / CAPTCHA / 重複 / denylist
        │
        ▼
ACT
  既存CloakBrowser daily-driver :9222で一度だけsubmit
        │
        ▼
RECEIPT
  完了画面 + canonical URL + Gmail message/thread IDを同じattemptへ結合
        │
        ▼
TRACK（gog Gmail + Calendar）
  submitted → confirmed → interview → offer/rejected → funded
        │
        ▼
LEARN（週次）
  program別の返信率・面談率・採択率からtargetとpitchを更新
```

探索は「登録された5件を順番に回す」だけではない。registry entryに
`source_url`、`last_verified_at`、`next_deadline`、`terms_hash`、`solo_allowed`、
`location`、`status`を持たせる。毎日、新規programを発見し、既存programの変更も検知する。

localでは`gog`を使う。すでにOAuthとCLIがあり、launchdからJSONで安定して読めるためである。
Gmail MCPは対話調査には使えても、停止中のaccept watcherのように定期workerが「MCPで読め」と
表示するだけでは実行にならない。Web版では同じmail interfaceをtenant別Google OAuth/Gmail APIへ
差し替え、localの個人tokenを他userへ流用しない。

## 14. Telegramに今日届くべき実例

過去状態を説明する文面は2026-08-01の実ファイルとlaunchdに基づく。完成時templateの
`{{...}}`は、送信時にCalendar、応募結果、確認mail、統一ledgerの実値だけで置換する。

```text
🎟️ 今後3週間の空き予定を埋めました。

確認期間: {{window_start}}〜{{window_end}}
対象日: 21日
既存の対面予定で埋まっていた日: {{covered_existing_count}}日
今回新しく予約した日: {{covered_new_count}}日
固定予定で追加できない日: {{unavailable_count}}日
未処理の空き日: 0日

今回追加した予定:
1. {{event_date_1}} {{event_name_1}}
   {{event_time_1}} / {{event_location_1}}
   理由: {{selection_reason_1}}
   [イベントページ]({{canonical_event_url_1}})・[Calendar]({{calendar_event_url_1}})

2. {{event_date_2}} {{event_name_2}}
   {{event_time_2}} / {{event_location_2}}
   理由: {{selection_reason_2}}
   [イベントページ]({{canonical_event_url_2}})・[Calendar]({{calendar_event_url_2}})

すべて参加申込み、確認メール、Calendar登録を照合済みです。
既存予定と移動時間が重なる予約はありません。

[3週間のCalendarを開く]({{calendar_coverage_url}})
[参加予定とQRの一覧を開く]({{confirmed_event_list_url}})
```

新しく予約しなかった場合に許される唯一の通常報告:

```text
✅ 今後3週間はすでに埋まっています。

確認期間: {{window_start}}〜{{window_end}}
対象日: 21日
既存の対面予定でcovered: {{covered_existing_count}}日
固定予定で追加可能な時間なし: {{unavailable_count}}日
未処理の空き日: 0日
今回の新規予約: 0件

理由: 予約できる空き枠が残っていないため、二重予約を作りませんでした。
「イベントを見つけられなかった」ことを理由にはしていません。

[3週間の予定をカレンダーで見る]({{calendar_coverage_url}})
[参加予定の一覧を見る]({{confirmed_event_list_url}})
```

```text
🎤 LT応募状況 2026-08-01

AI Tinkerers Tokyo:
・登壇申込みを送信済み
・主催者からの最終回答はまだ確認できていません

AI Tinkerers San Francisco:
・登壇申込みを送信済み
・現在は主催者の確認待ちです

connpass:
・募集中のLT枠を見つけられます
・申込み完了を確認する方法がまだないため、勝手に送信していません

今日の新規LT応募: 0件
次の行動: 主催者からの確認メールまで追跡できる状態にしてから、実際のLTへ1件申し込みます

[過去の登壇応募を見る]({{talk_application_history_url}})
[候補イベントを見る]({{talk_candidate_list_url}})
```

```text
🚀 資金調達queue 2026-08-01

1. SPC Founder Fellowship F26 — 締切 8/2、NYC選択可、未提出
2. YC Fall 2026 — late application受付中、既存draftは未提出
3. a16z SPEEDRUN SR008 — off-cycle受付、最新form spec未作成
4. Entrepreneurs First London — 締切 8/4、適格性確認待ち

YC既存draft:
・応募回答20項目: 入力済み
・創業者紹介動画: upload済み
・入力漏れ: なし
・現在の状態: 最終送信前
・相手からの応募確認メール: なし

まだ送信していないため、「YCへ応募済み」とは表示しません。

[YC応募内容を見る]({{yc_application_url}})
[使用する動画を見る]({{founder_video_url}})
[応募先一覧を見る]({{funder_pipeline_url}})
```

過去の実応募を新しいUXで表す場合:

```text
💼 Anthropicの求人への応募が完了しました。

会社: Anthropic
職種: Financial Services Industries Enterprise Account Executive
応募日: 2026-05-30

この求人を選んだ理由:
金融業界でのCRM導入経験と、AI agentを実際に構築・運用している経験の両方を活かせるためです。

提出したもの:
・履歴書: Daisuke_Narita_Resume.pdf
・cover letter: Anthropic FSI向けに作成したPDF
・応募者情報: Daisの共通プロフィール

応募完了画面: 確認済み
現在の状態: 返信待ち

履歴書とcover letterをこの報告から開けます。

[提出した履歴書を開く]({{submitted_resume_url}})
[cover letterを開く]({{cover_letter_url}})
[求人ページを開く]({{job_url}})
```

```text
🎤 AI Tinkerers Tokyoへ登壇を申し込みました。

イベント: AI Tinkerers Tokyo - Shinagawa: May 26th Meetup
応募日: 2026-05-06
応募内容: Aniccaの自律運用とLife Managerへつながる実装demo

提出したもの:
・登壇者プロフィール
・demo proposal
・product URL
・GitHub URL

イベント主催者の画面では申込み受付を確認しました。
カレンダーにも予定を追加済みです。
現在の状態: 主催者からの最終回答待ち

[提出した登壇内容を見る]({{talk_application_url}})
[イベントページを開く]({{canonical_event_url}})
[カレンダーを開く]({{calendar_event_url}})
```

採択後の実際のUX:

```text
🔥 SPC Founder Fellowshipから面談招待です。
状態: interview_requested
拠点候補: New York City
メールthread: 証拠保存済み
締切: 2026-08-06 17:00 JST

候補日時をCalendarの空き時間と照合しました。
面談資料:
・Life Manager 90秒説明
・Daisのfounder-market fit
・Daisローカル実証の応募/CFO metrics
・なぜ今、なぜ1人で開始できるか

[返信案を確認する]({{reply_draft_url}})
[面談資料を見る]({{meeting_prep_url}})
[辞退の確認画面を開く]({{decline_confirmation_url}})
```

## 15. 生活と会社がどう変わるか

```text
現在
  Daisがevent、求人、accelerator、メール、口座を別々に見る
  → 応募漏れ、返信漏れ、数字の分断、壊れたcronに気づけない

local完成後
  Life Managerが候補を探す
  → 応募・確認証拠を取る
  → Gmail返信とCalendarを追う
  → 銀行・card・Binanceをread-onlyで集計
  → 毎朝Telegramで「資産・支出・応募・面談・今日の行動」を一通にする

成長後
  LTでLife Managerの実証を話す
  → user / founder / investorとの接点
  → acceleratorで密度の高いpeer group、partner支援、資金
  → product改善と有料user獲得
  → 同じcoreをLife Manager Webへ提供
  → 真のMRRを積み上げる
```

各agentは単独で「儲けを保証」しない。Eventsは機会、Fundraisingはcapitalとnetwork、Job Hunterは
給与、CFOは漏出削減、Crypto/NISAはrisk-adjusted return、Web appは継続売上を担当する。
これらの寄与を同じledgerで計測し、月間1,000万円へのgapを毎月更新する。accelerator採択、
投資利益、unicorn、billionaireは目標であって保証値ではない。

## 16. 実装前に残る不確実性

| # | 不確実性 | 解消方法 / gate |
|---:|---|---|
| U01 | CloakBrowser `:9222`のlogin sessionがLuma/YC/SPCでfreshか | 各siteをread-onlyで開き、login identityとcookie expiryを記録 |
| U02 | 直近Connector runner成功が実登録を意味するか | result JSON、完了画面、mail、ledgerを照合。runner successだけでは登録扱い禁止 |
| U03 | connpassで規約準拠のdiscover/submitと証跡取得が可能か | API key取得、利用規約、確認mailを実測。不可ならorganizer CFPだけを対象 |
| U04 | LT応募と一般参加登録をどう区別するか | `attendance_application`と`talk_proposal`を別entity・別receiptにする |
| U05 | YC既存draftがFall 2026へ安全に移行できるか | current home画面、batch、application ID、submit前previewを実測 |
| U06 | YC動画・demo・tractionが現在の真実か | application-kit、dashboard、動画実体、production URLを提出当日に照合 |
| U07 | SPC 8/2までに必要field/動画を揃えられるか | formをread-only captureし、missing field listと所要時間を出す |
| U08 | a16zの旧`START` specと現SPEEDRUNの差 | 旧specを無効化し、公式current formから新specを生成 |
| U09 | 各programがagentによるform入力を許容するか | terms/robots/form表示を提出直前に確認。CAPTCHA/明示禁止はhuman handoff |
| U10 | Gmail検索がconfirmationと営業mailを誤結合しないか | nonce/domain/thread/time fenceと送信attempt IDで結合、spoof testを追加 |
| U11 | 返信分類の型とCalendar timezone | confirmation/interview/offer/reject/request_infoをschema化し、JST/現地TZを保持 |
| U12 | MUITとの利益相反 | MUFG/MUIT運営・CVCをdeny。LPだけの関与と業務外応募の線引きを確認 |
| U13 | Moneytree LINKの契約、client ID、本番利用審査、料金 | Moneytreeへ正式確認。OAuth client取得前は「接続可能」とdoneにしない |
| U14 | MoneytreeがDaisの全銀行/card/証券と必要履歴を返すか | sandbox→本人同意→1口座で残高・1/3/12か月明細・categoryを実測 |
| U15 | Binance Japan口座で使えるendpointと履歴範囲 | read-only `USER_DATA` keyをIP制限し、balance/trades/deposit/withdraw履歴を実測 |
| U16 | Binance Earnやwallet外資産を総資産へ含められるか | product別endpointを列挙し、unsupportedは手動snapshotとして明示 |
| U17 | JPY換算の価格sourceと時刻 | original currencyを保存し、FX/crypto quote sourceとtimestampを全行へ付与 |
| U18 | subscriptionの「未使用」を何で判断するか | 支払明細だけで断定せず、login/app usage/mail receiptの有無とconfidenceを表示 |
| U19 | crypto/fiatのexecution権限 | Order 3Bはread-only。Order 4/5で隔離口座、上限、signer、emergency stopを実証 |
| U20 | local profileをWeb multi-tenantへどう移すか | tenant別OAuth、secret、browser profile、worker isolationのcontract test |
| U21 | 「NYC」がNew York CityかYCの音声認識か | queueでは両方を扱う。SPC NYCとYC SFを混同しない |
| U22 | 調達額と希薄化の許容範囲 | cap table scenarioを提示し、法務・税務確認後だけsign。資金調達額をMRRに入れない |
| U23 | specialistを増やすほど品質が本当に上がるか | single CFO baselineとspecialist構成を同じeval setで比較し、改善しないroleは統合 |
| U24 | specialist間で数字や結論が食い違う場合の正本 | 数字は統一ledger、解釈は出典付き意見として保存し、Risk/CFO reviewで解消 |
| U25 | FinRobot/TradingAgentsをどこまで直接移植できるか | dependency、data provider、test、Apache-2.0 noticeをcode-level spikeで確認 |
| U26 | Ghostfolio/rotki/Firefly IIIのAGPLコードをproductへ使えるか | 法務/license review完了までUX・schema研究だけとし、source codeをcopyしない |
| U27 | self-improvementが過学習やrisk増加を起こさないか | time-split replay、shadow、canary、rollbackを必須にし、permission/capを対象外にする |
| U28 | 多数agentのcostとlatencyが日次利用に耐えるか | 必要なspecialistだけ起動し、single-agent baseline比の有用性/cost/時間を計測 |
| U29 | Luma mainの各日inventoryを「最後まで読んだ」とどう証明するか | pagination、infinite scroll、日付・東京・対面条件、取得件数と最終cursorを探索証跡へ保存 |
| U30 | 都度承認なしで自動予約してよい有料eventの支出policy | 日次・月次上限と対象を一度だけ設定し、範囲内は自動決済、範囲外は無料の別候補へ進む |
| U31 | rolling 21日のeventが勤務・学校・既存予定・移動時間と両立するか | 全Calendarと経路時間を申込前gateにし、重複時は同日の別時間・別候補へ進む |
| U32 | Summer 2026のYC applicationをFall 2026へ継続できるか | 現行YC homeをread-only確認し、継続不可なら既存回答を新applicationへ安全に移す |
| U33 | 既存YC回答・動画・tractionが現在も正確か | production、dashboard、application-kit、動画実体を照合し、古い主張を修正してからsubmit |

## 17. 変更規則

1. 順序変更はDaisの明示指示だけで行う。
2. 状態変更時は、この文書のcheckboxと証拠pathを同じcommitで更新する。
3. 推測でdoneにしない。外部receiptまたは再現可能な実測を要求する。
4. 他trackの作業をこの文書へ追加しない。
5. 新しい候補部品を発見したら、URL、license、実測日、採用判断を§4へ記録する。
