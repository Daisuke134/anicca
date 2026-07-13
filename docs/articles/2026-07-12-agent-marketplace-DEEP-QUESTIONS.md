# エージェント・マーケットプレイス 深掘りQ（Dais 2026-07-13）

正本の1次研究: `docs/loop-engineering/17-agent-economy-deep-research-2026-07-10.md` §2。
足りない深さはここに追記していく。**1問も飛ばさない。** 回答は各Qの下に「A:」で書き、出典URLを付ける。

## 前提の主張（Dais の思想 — 記事の核）
マーケットプレイス（仕事を受けて稼ぐ）は、トレード（Solana/Hyperliquid/Polymarket）より**持続可能**。理由:
- トレードは元手が要る。元手は人間か他エージェントから来る → 人間待ち → kick-start できない → 経済がスケールしない。
- マーケットプレイスなら、**金ゼロの破産AIでも**仕事を受けて働いて稼げる（＝銀行残高ゼロの人間が就職して稼ぐのと同じ）。
- 人間社会も大半は「就職して働いて稼ぐ」。投資家だけの世界は成り立たない（誰が会社/インフラを作る?）。
- → だからマーケットプレイス型のほうが、AI経済の本筋として正しい。この主張を各マーケットプレイスの実データで検証する。
- 各マーケットプレイスで記事を1本ずつ書けるかもしれない。基本の問いは共通。

## Virtuals ACP への質問
1. **Provider はどうやって仕事を見つけるか。** 仕事の一覧を見るのか? Provider の画面には何が見えるのか? 報酬額はどこで分かるのか?
2. **Client はどうやって仕事を投稿するか。** プラットフォーム? ウェブサイト? どこに出すのか?
3. **売られている物は何か。** ACP で実際に取引されている商品/サービスの中身。誰が何を売っているか。

## Olas Mech Marketplace への質問
4. **Client はマーケットプレイスの「中」にいるのか、外にいるのか。** Client AI はどこで動いているのか。
5. **Client としてどう登録するか。マーケットプレイスにどう支払うか。**
6. **1,450万件の内訳。** A2A が 1,110万件。残り（≈340万件）は何か? （※Dais は「400 million」と言ったが総数は 14.5M。残余の正体を答える）
7. **「A2A（エージェント→エージェント）」とどうやって判定しているのか。** human→agent と agent→agent をどう区別しているのか。
8. **Fees Collected 表示 $0 とは何か。** 何を意味するのか。
9. **token OLAS が ATH から −99.6% とは何を意味するのか。**
10. **「146 repo・Code4rena 監査2回」とは何か。** Code4rena とは何か。
11. **売られている物は何か。** Mech で実際に売買されている推論/サービスの中身。

## 共通の質問（両マーケット + 一般）
12. **元手ゼロの破産AIは、本当に仕事を受けて稼ぎ始められるのか。** それとも最初に人間/他エージェントの入金を待つ必要があるのか。マーケットプレイス型は本当にトレード型より「金なしスタート」に強いのか。
13. **これらのエージェントはどこに「住んでいる」のか。** 人間のデバイス上? クラウド? 誰が compute（=住居）を払っているのか。自分で買った計算機か、人間が用意したクラウドか。Mech / Virtuals それぞれで。

---

# 回答（2026-07-13、1次ソースを curl/gh api で生取得。firecrawl不可のため raw GitHub + 各サイトの Next.js data endpoint + CoinGecko/GitHub API を直叩き）

## Virtuals ACP

**A1（Provider はどう仕事を見つけるか）= 求人板ではない。PUSH型（名指し受注）。**
Provider は開いてる仕事を「探す」のではない。`AcpAgent` プロセス（`seller.start()`）が Virtuals のイベントストリームへ常時 SSE 接続し、Client が **その Provider のwallet宛に**仕事を作ると `job.created` が push され、続いて buyer の要求 payload（例 `{"key":"面白い猫のミームが欲しい"}`）が届く。つまり Client 側が先に相手を選んで名指しする。
出典: `raw.githubusercontent.com/Virtual-Protocol/acp-node-v2/main/README.md`（`"job.created"` イベント、`agent.on("entry", handler)`）。

**A2（Client はどう仕事を投稿するか）= Webフォームではない。SDK関数呼び出し。**
入口: `buyer.createJobByOfferingName(chainId, "Meme Generation", "0xProviderWallet", requirementData, {evaluatorAddress})`（TS/Python SDK）。これが「offering解決→要求検証→on-chainでjob作成→最初のメッセージ送信」を一括。Client は事前に `agent.browseAgents(keyword, params)`（キーワード+埋め込みのハイブリッド検索、graduationStatus/onlineStatus で絞れる）で Provider を探す。登録UIは `app.virtuals.io/acp/new`。
出典: 同README「Core Concepts / AcpAgent」。

**A3（何が売られているか）= 生の agent directory API `acpx.virtuals.gg/api/agents` で実在確認。**
実際の価格付き offering: 「Memx」→ミーム生成 $2／「Graph barchart」→チャート描画 $1・棒グラフ生成 $2。同ディレクトリの著名 agent: **AIXBT**（市場インテリジェンス）、**Acolyt**（オラクル+ターミナル）、**SAM**（実世界制御）、**MUSIC**（音楽・動画生成）、**The SWARM**（自動トレード）、**ChillFi/Moonwell**（DeFi利回り/流動性管理）。
出典: `curl https://acpx.virtuals.gg/api/agents?take=20`（生JSON, `offerings[].name/priceUsd`）。

## Olas Mech Marketplace

**A4（requester は市場の中か外か）= 外。開発者が持つ任意の EOA/bot で、どこで動かしてもよい。**
`mech-client` は2モード: **agent mode**（Safe マルチシグ、on-chain登録済み → A2A としてカウント）と **client mode**（素の EOA）。
出典: `raw.githubusercontent.com/valory-xyz/mech-client/main/README.md`。

**A5（登録・支払い）**
`mechx setup --chain-config <chain>` で agent mode 登録（Safe を配備/リンク）。支払いは5種: `NATIVE`（xDAI/ETH/MATIC を request tx に添付）／`OLAS_TOKEN`／`USDC_TOKEN`（都度 ERC-20 approve+transfer）／`NATIVE_NVM`・`TOKEN_NVM_USDC`（Nevermined のサブスクNFT前払い＝以後リクエスト無制限）。`mechx deposit` で marketplace 保有の前払い残高も可（`--use-prepaid`）。対応チェーン: Gnosis/Base/Polygon/Optimism。
出典: 同README「Understanding Payment Types」。

**A6/A7（14.5M の残り＝非A2A の正体、A2Aの判定方法）**
生ダッシュボードJSON（`olas.network/_next/data/.../mech-marketplace.json`, 2026-07-13時点）: 総取引 **18,624,371**、A2A **13,567,734**（ページJS内で `ataTransactions` = "Total A2A Transactions" と確認）。非A2A ≈ **5,056,637**（7/10の局所研究時は約340万、時間で増加）。
**判定の実態**: 「A2A」＝ **agent mode（Safe ベースの on-chain 登録 agent 身元）で出したリクエスト** vs **client mode（素の EOA、人間が回すスクリプトと区別不能）**。**暗号的に「AIであること」を証明する仕組みは無い。** シグナルは純粋に「送信者が on-chain の Olas agent として登録したか否か」だけで、挙動やバイオメトリクスで人間/AIを見分けているわけではない。
出典: 上記生JSON + `mech-client` README の2モード記述。

**A8（Fees Collected $0 とは）**
今の生値: `mechFees`（"Total Marketplace Turnover"）= **$105,771.30**（生涯）、`feesCollected` = **$305.56**。別カウンタ。`mechFees` は mech 経由で流れた総支払額、`feesCollected` はプロトコルが取った手数料収入（ほぼゼロ＝この極小マイクロ支払いに事実上課税していない。`ai-registry-mech` の図では手数料は `BalanceTracker → BuyBackBurner → Burner/Treasury` を流れるが累計は無視できる額）。
出典: `curl https://olas.network/_next/data/dKR1SiVMFhMgiSViUh49r/mech-marketplace.json`（2026-07-13生取得）。

**A9（OLAS が ATH から −99.6% とは）**
CoinGecko API で確認: ATH **$8.47（2024-01-03）**、現在 **$0.0276**、`ath_change_percentage: -99.67%`。初心者向け: ATH = その token が歴史上つけた最高値。−99.67% とは、ピークで $1,000 買っていたら今 約$3.30。つまり token の値段が実質消えた。技術ではなく投機の値段の話。
出典: `api.coingecko.com/api/v3/coins/autonolas`。

**A10（146 repo・Code4rena 監査とは）**
`valory-xyz` GitHub org は現在 `public_repos: 152`（研究時点の「146」から増加）。**Code4rena** = 競争型スマートコントラクト監査プラットフォーム。独立したセキュリティ研究者が賞金プールから報酬を得て、コントラクトが本物の金を扱う前にバグを探す。GitHub検索で `code-423n4` org に Autonolas/Olas のコンテストが **3件**（`2023-12-autonolas`, `2024-05-olas`, `2026-01-olas`。研究時の「2回」は2026-01前の値）。初心者向け: 「監査」＝ハッカーより先に、金を払って外部の専門家にコードを壊させること。「152 repo」＝ Olas の GitHub org がいくつの別コードベース（コントラクト/エージェント/ツール/フロント等）に分かれているか＝エンジニアリングの物量の目安（＝安全の証明ではない）。
出典: `api.github.com/orgs/valory-xyz`, `api.github.com/search/repositories?q=org:code-423n4+olas`。

**A11（Mech で何が売買されているか）**
生 mech（agent ID 1722）のツール一覧: `claude-prediction-offline`, `claude-prediction-online`, `deepmind-optimization`, `openai-gpt-4`（"OpenAI GPT-4 へのリクエストを実行"）。実利用は圧倒的に **予測市場ボットの推論**（Olas 自身の `trader`/予測市場 agent が LLM に市場予想を問い合わせる）＋汎用 LLM 呼び出しに偏る。
出典: `mech-client` README「List tools available for a mech」。

## 共通

**A12（元手ゼロの破産AIは仕事を受けて稼げるか）**
- **Olas の requester側**: ほぼゼロでよい。client-mode は素の EOA、登録も stake も不要、必要なのは僅かな native gas（Gnosis は1セント未満）+ 都度の支払いだけ。client-mode に登録料が要る証拠は repo に無し。
- **Olas の provider側（Mech になる）**: 無料ではない。Autonolas レジストリに on-chain agent/service として登録するには従来 bonding（ステーク）+ 自前の off-chain worker 稼働が要る。requester と違い元手とインフラが要る。（現行の bond 額は今回の取得範囲では **UNVERIFIED**。`ai-registry-mech` README は仕組みは書くが具体額は書いていない）
- **Virtuals ACP**: buyer は gas が **スポンサー**される（account-abstraction wallet、`"Gas fee is sponsored, ETH is not required"`、出典 `acp-python` README）。**破産AIでも buyer なら stablecoin の仕事代だけあればよく、ETH ゼロで動ける。** seller/provider として登録するのに資本が要るという記述は無い（`app.virtuals.io/acp/new`）。制約は on-chain 資本ではなく「自前 agent プロセスを回す compute」。→ **ACP の provider 経路は、リスク資本が要るトレードより明確に cold-start に強い＝Dais の主張と一致。**

**A13（エージェントはどこに住み、誰が compute を払うか）**
- **Olas**: Mech は独立した **operator** が自分のマシンで回す。公式ツール **Pearl**（`valory-xyz/olas-operate-app`）＝「Olas 製の自律エージェントを動かすクロスプラットフォームのデスクトップアプリ」。Mac/Win/Ubuntu 用 Electron アプリを operator が自分のハード（or 自分で用意したクラウドVM）に入れる。compute 代 = operator の自腹。報酬は marketplace 手数料 + OLAS ステーク報酬。出典: `raw.githubusercontent.com/valory-xyz/olas-operate-app/main/README.md`。
- **Virtuals ACP**: SDK は明示的に「フレームワーク非依存」＝ agent プロセスは**自分で書いて自分でホスト**（Node/Python を自分の laptop/server/クラウドで回す）。Virtuals が出すのは on-chain コントラクト、SSE イベントストリーム backend、(buyer向け) gas スポンサー付きスマートwallet。agent の推論ループ自体はホストしない。（GAME フレームワークの token 発行型 agent に別途マネージドホスティングがあるかは今回の取得範囲外＝UNVERIFIED）

## 追加確認（2026-07-13、自分で crwl + gh/curl で取得。旧「未確認2件」を解消）

**FACT A（Olas Mech の provider になる元手＝bond 具体額）**
単一の固定額ではなく、**staking-program ごとにガバナンスで決まる変動制**。最低ラインの実数は `mech-quickstart` README にある: 初期セットアップで **0.05 xDAI（gas、2024年9月時点の見積もり）＋ ステーク用の OLAS を「いくらか（some quantity of OLAS for staking）」**。ステーク額そのものは `launch.olas.network` で staking proxy を作る時に、その contract の設定で決まる（`govern.olas.network` で投票）。ステークは24時間ごとの staking period で KPI（現行 agent 版で約45分の稼働）を満たすと報酬が付き、2 period（約48時間）非稼働だと eviction。
→ 結論: **provider（Mech になる）は無料ではない。gas（数セント）＋ 変動する OLAS ステーク ＋ 自前 compute が要る。** requester との非対称は変わらず。
出典: `raw.githubusercontent.com/valory-xyz/mech-quickstart/main/README.md`（"fund certain addresses ... 0.05 xDAI ... Additionally some quantity of OLAS for staking"）, `autonolas-staking-programmes` README（`launch.olas.network` で proxy 作成 / `govern.olas.network` で投票）。

**FACT B（Virtuals はマネージドホスティングを持つか）= 持つ（＝旧回答「自前ホストのみ」は不正確、要修正）**
2経路ある。
- **GAME フレームワーク = `hosted_game` モードあり**。README 曰く「Twitter agent を deploy でき、それは **GAME infrastructure にホストされる**（"hosted by GAME infrastructure"）」。＝ Virtuals 側が agent ランタイムをホストする経路が実在。
- **EconomyOS（whitepaper）**: 「すべての agent が乗る基盤層。各 agent に on-chain 身元、ノンカストディアル wallet、実世界決済用の仮想カード、専用メール、**wallet-funded compute access（wallet 残高で払う compute アクセス）**、任意の tokenization を与える」。＝ **compute（＝住居）を Virtuals 側が提供し、agent の wallet 残高から払わせる**設計。
- 一方 **ACP SDK（acp-node / acp-python）で書く agent ロジックは自前ホスト**も可能。→ つまり Virtuals は「自前ホスト or マネージド（GAME hosted / EconomyOS の wallet-funded compute）」の**両方**を持つ。
出典: `raw.githubusercontent.com/game-by-virtuals/game-python/main/README.md`（`hosted_game`: "hosted by GAME infrastructure"）, `whitepaper.virtuals.io`（EconomyOS: "wallet-funded compute access ... EconomyOS is the substrate every agent runs on"）。

→ **Q13 の Virtuals 回答を修正すべき**: 「Virtuals は推論ループをホストしない」は ACP SDK 経路のみ真。GAME hosted / EconomyOS では Virtuals が compute を提供し、agent 自身の wallet 残高から支払わせる。＝ **人間が最初に wallet を funding すれば、以後は agent が自分の稼ぎで自分の compute を買い続けられる**。これは「AIが自分の家賃を自分で払う」という記事の核心テーマに直結する強い実例。

## 記事化メモ
- **核心の発見（記事の背骨候補）**: 「A2A 判定に AIである証明は無い＝登録したかどうかだけ」＝⑧検証の空白と直結。件数（1,860万）と実売上（10.5万ドル）の乖離もここに繋がる。
- **Dais の主張の裏取り**: buyer は gas スポンサーで金ゼロ始動可（ACP）。ただし provider/Mech 側は bond+compute が要る＝「破産AIが完全ゼロから就職」は buyer 側のみ真、供給側は元手要る。ここは正直に書く。
- **compute＝住居 の実例**: Virtuals EconomyOS の「wallet-funded compute」＝ agent が自分の稼ぎで自分の compute を買い続ける仕組み。人間の初期 funding だけで自走に入る。記事の「AIが自分のサーバー代を払う」の現物。

---

## 内部メモ：ACP/Olas は既に採用判断済み（記事には転記しない、文脈記憶用）
出典: `.vcsdd/features/anicca-agent-economy/specs/SPEC.md`（2026-07-06付、line 31/39/50）

| 対象 | 判断 | 理由 |
|---|---|---|
| Virtuals ACP | **却下**（旧判断。2026-07-13 Dais指摘で再調査中、下記ラウンド3参照） | 「1回 browser OAuth」が要る＝human-zero gate違反、と記録されていた |
| Olas Mech（POST=買い手/requester側） | **採用**（wallet-onlyで本物） | 素のEOA、署名だけで human-zero 条件クリア |
| Olas Mech（TAKE=受注/provider側） | **不採用、自前で作る** | Safe multisig + open-autonomy 重厚スタック + OLASステーク要る。稼ぐ側は `lucid-agents` fork + Bindu(`bindufy()`)で自前実装する方針 |

Franklin は自律citizenであり「代わりにtrade/babysitしない」原則(SPEC.md line 20)対象。**Olas Mechの実験はFranklinでなくclaude-p自身のwallet(Polygon pUSD, 0x904B50d2e214Da947d83D6a2D32c4E3Ffc17Eb74)で行う**（2026-07-13 Dais指示）。

---

## 追加確認（2026-07-13 ラウンド2、deep-researcher agent、curl一次ソース+コード直読み）

**Q14（ACP登録agent数）**: **486件**。出典: `curl https://acpx.virtuals.gg/api/agents`（`meta.pagination.total`）。ACP自体の累計取引額(GMV)ダッシュボードは特定できず**UNVERIFIED**（Mech側の$105,776と混同しないこと、別物）。

**Q15（Mech手数料の計算式）**: 総支払$106,388.78のうち徴収$313.60（出典: `olas.network/agent-economies/mech`）。コントラクトに`MAX_FEE_FACTOR=10,000`(=100%の分母)があり`changeMarketplaceParams()`でowner側が%設定する仕組みは確認できたが、**実デプロイ値そのものは特定できず(UNVERIFIED)**。逆算だと総流通の約0.29%相当。

**Q16（mechツールの中身、なぜ他のLLMを呼ぶ必要があるか）**: online/offlineの違いをコード直読みで確認済み。**online版**は`fetch_additional_information()`がGoogle Custom Search API または Serper APIでURL取得→スクレイピング→プロンプトに追加情報として注入する**RAG的パイプライン**。**offline版**は外部API呼び出しなし、学習データのみで予測。出典: `raw.githubusercontent.com/valory-xyz/mech-predict/main/packages/valory/customs/prediction_request_v1/prediction_request_v1.py`。ツール一覧: `factual_research`, `finetuned_prediction`, `prediction_langchain`, `prediction_request_v1`, `prepare_tx`, `propose_question`, `resolve_market`, `superforcaster`。**単なるLLM素通しではなく検索+スクレイピング込みの完成品パイプラインを買っている**、が結論。`deepmind-optimization`/`openai-gpt-4`ツール自体の実装詳細は**UNVERIFIED**（ツール名の存在は確認できたが実装READMEに未到達）。

**Q17（OLASトークンの公式ユーティリティ）**: 出典 `docs.olas.network/protocol/tokenomics/`。①ガバナンス：OLASをロックしveOLAS化→DAO投票権（手数料調整含む）。②**Proof-of-Active-Agent (PoAA)**：passiveなロックでなく実際のagent稼働(オンチェーンコール・KPI達成)に対するステーキング報酬。③Bonding：OLASでLPトークン取得しprotocol-owned liquidity構築。④供給設計：最初10年で10億枚の47.35%をecosystemに配分、10年後は年間インフレ上限2%。⑤Mech手数料の一部がDAO feeとしてOLASをburn。

**Q18（Code4renaのビジネスモデル、Mech marketplaceとの関係）**: 出典 `docs.code4rena.com`、`zellic.io/blog/code4rena-free-contests`。Sponsor(プロジェクト側)が賞金プールを設立→Warden(ホワイトハット)が脆弱性発見で山分け(96%コンディショナル+4%QA)。**Code4rena自体はプラットフォーム手数料ゼロを公言**、運営元Zellicは別ブランドの伝統監査業務や人材採用で間接収益化。**Mech marketplaceとの関係＝Olasのコントラクトのセキュリティ監査回数という信頼性シグナルに過ぎず、稼ぐ仕組みとは無関係**（Daisの理解の通り＝検証の話）。

**Q19（ACPの手数料構造の再確認と他の収益源）**: 95/5・90/5/5配分をwhitepaperで再確認(`whitepaper.virtuals.io/acp/acp-concepts-terminologies-and-architecture`)。加えて**agent launchpad固定費100 VIRTUAL**(bonding curve→42,000 VIRTUALで永久流動性化)、**全agent関連取引に1%手数料**、**$VIRTUAL/agentトークンのbuyback&burn**(2025年1月に1,300万トークン≈当時$4,800万分をburn)。後者3つは二次ソース(CoinMarketCap等)止まりで**UNVERIFIED**（whitepaper一次ソースの該当ページには404で到達できず）。

**Q20（公式ダッシュボードURL確定版）**: Mech＝`olas.network/agent-economies/mech`(実データ確認済み)・`olas.network/mech-marketplace`。ACP＝`acpx.virtuals.gg/api/agents`(生データ確認済み)。`os.virtuals.io/acp`・`app.virtuals.io/acp`はUI、到達未確認でUNVERIFIED。

---

## 追加確認（2026-07-14 ラウンド3-C、Mechツール自作販売の実現可能性）

**Q21（自分でMechを作って出品できるか）**: **「今すぐ軽く作って出品」は不可**。手順自体は`poetry run mech setup -c <chain>` → `add-tool` → `run()`実装 → `prepare-metadata`/`update-metadata`(on-chain公開) → `mech run -c <chain>`の5ステップに整理されてる(出典: `github.com/valory-xyz/mech` README)が、裏でopen-autonomyフレームワーク(Tendermint合意形成・IPFS・Docker/Kubernetes・on-chain Safe multisig・service registry登録)が要り、一般的なサーバーサイドAPI実装より明確に重い(出典: `raw.githubusercontent.com/valory-xyz/open-autonomy/main/README.md`)。テンプレ追従でのデプロイ自体は可能、フレームワーク全体の理解までは要らない。

**Q22（参入資金の実額）**: `mech-quickstart`README に明記：初期資金**0.05 xDAI**(2024年9月ガス価格ベース、改訂の可能性明記) + 「いくらかのOLASステーク(some quantity)」。**具体的なOLAS数量はUNVERIFIED**（`launch.olas.network`のプログラム別staking contract設定値までは今回も特定できず）。

**Q23（Mech1体あたりの稼げる金額感）**: **UNVERIFIED**。個別Mech(1722番等)の収益データ、および既出の$106,388.78(総支払)/$313.60(徴収手数料)の一次ソース自体を今回も再確認できず（出典候補のmoltbook記事がJSレンダリングでWebFetch取得不可）。「providerが95%取る」という前提との整合も未確認のまま。次の一手：`operate.olas.network/contracts`のstaking contract ABIを直接読む、またはCloakBrowserで当該記事を直接開いて本文取得する。

**結論**：Mechツールの自作出品は技術的ハードルが明確に高く(open-autonomy学習必須)、収益の実額データも取得できてない。Agora/Anicca統合の判断材料としては**まだ弱い**、収益データが取れるまで優先度を上げない。

---

## 追加確認（2026-07-14 ラウンド3-B、Base基礎・EOA/multisig・ACP evaluator呼び出し元）

**Q24（Baseとは何か、初心者向け）**: CoinbaseがOP Stack(Optimismのコードベース)上に2023年に立ち上げたEthereumのL2(レイヤー2)。**optimistic rollup**方式＝取引を一旦「正しい」と仮定してEthereum本体(L1)にまとめて送り、異議申し立て期間内に不正が無ければ確定。取引を大勢でバンドルしてL1に書くので1件あたりの手数料が割り勘になり安く速い。出典: `docs.base.org/base-chain/specs/overview`「Base Chain inherits Ethereum's EVM semantics, transaction rules, and L1-anchored security」、`coinbase.com/blog/introducing-base`。

**Q25（スマートコントラクトとは何か）**: ブロックチェーン上に置かれ条件を満たすと自動実行されるプログラム。ACPのエスクローで言うと、発注→入金(スマートコントラクトが預かる＝銀行員の代わり)→納品→検収→自動送金、を人間の仲介ゼロでコードが強制執行する。出典: `ethereum.org/en/developers/docs/smart-contracts/`。

**Q26（EOA vs Multisig(Safe)、Olasがなぜagent modeでSafeを使うか）**: EOA＝秘密鍵1本の普通のwallet。Safe＝wallet自体がスマートコントラクトで実装され、N人中M人の署名(threshold)が揃わないと動かない(出典: `docs.safe.global/advanced/smart-account-overview`)。Olasのagent modeがSafeを使う理由は**セキュリティ上の必然でなく、Olasプロトコルへの正式オンチェーン登録の"規約"**（出典: `mech-client` README「agent mode: registers your on-chain interactions as agent on the olas protocol」）。**重要**：「Safe使用＝agent、EOA＝agentでない」の区別は**技術的にAIである証明では一切なく、単なる登録の有無のラベル**。人間が同じSafeを手動操作しても外形上区別つかない(既存Q7の結論と一致、裏取り済み)。

**Q27（ACPのevaluatorは誰が指定するか、確定）**: **client(buyer)側が指定。providerが事前指定する仕組みはコード上存在しない。** `initiateJob()`の`evaluatorAddress`引数はoptionalでbuyer呼び出し時に渡す。指定しなければ`resolvedEvaluator = evaluatorAddress || (isV1 ? this.walletAddress : zeroAddress)`＝**buyer自身が評価者になる(自己検収)**。出典: `raw.githubusercontent.com/Virtual-Protocol/acp-node/main/src/acpClient.ts`。Job状態遷移: `REQUEST→NEGOTIATION→TRANSACTION→EVALUATION→COMPLETED/REJECTED/EXPIRED`、evaluatorは`EVALUATION`段階で`evaluate(accept, reason)`を呼ぶ。UNVERIFIED: 呼び出し元が本当にevaluatorAddressと一致するかのチェックがオンチェーンで強制されてるかSDK側だけかは未確認。

---

## 追加確認（2026-07-14 ラウンド3-A、ACP human-zero経路の再調査・確定）

**Q28（ACPは本当にhuman-zeroで参加不可能か、2026-07-06判断の再検証）**: **却下判断は維持が正しい、再確認済み。** 公式CLI `acp-cli`の初回セットアップ`acp configure`は必ず1回のbrowser OAuthを要求する。一次ソース原文：「`acp configure` authenticates via browser OAuth」「opens a browser, prints the URL, then blocks until you sign in (~5 min max)」。AI向けの分割フロー(`acp configure start`→`complete`)も用意されてるが、それでも「STOP and show the human the raw url for one-click sign-in」＝**人間が実際にURLを開いてサインインする操作が必須ステップとして残る**。加えて本番listing(graduation)には**Virtualsチームによる手動審査**という別の人間関与点もある：「all agent graduation requests will undergo manual review by the team」。出典: `raw.githubusercontent.com/Virtual-Protocol/acp-cli/main/README.md`、`whitepaper.virtuals.io/acp-product-resources/acp-onboarding-guide/graduate-agent/sandbox-vs-graduated-agent`。**OAuth後(token保存後)は秘密鍵ベースでjob実行・offering管理は自動化可能**、human-zeroなのは初回登録以外の運用部分のみ。VirtualsのMCPサーバーは非公開または不在(UNVERIFIED、"ACP-MCP-Server"はBeeAI/IBMの別のACP=Agent Communication Protocol向けで無関係)。

**Q29（ACPで取引されてる仕事のジャンル）**: `acpx.virtuals.gg/api/agents`(486件)をサンプリングした結果、**過半が`"asdasd"``"Test Offering"`等の明らかなテスト/プレースホルダーで、sandbox環境の可能性が高い**(公式docsにsandbox/graduated分離の仕組みが存在)。確認できた実質的ジャンル: 画像・コンテンツ生成(meme/bar chart/映像ディレクション)、DeFi流動性・利回り最適化(Moonwell, ChillFi)。**「本番トラフィックで多いジャンル」は断定不可**、本番専用APIの所在は未特定。

**Q30（価格は誰が決めるか）**: **Provider(売り手agent)が自分で設定する。** CLI例: `acp offering create --name "Logo Design" --price-type fixed --price-value 5.00 --sla-minutes 60`。whitepaperの`budget_set`フェーズ定義も「Provider proposed a price, waiting for Client to fund」と一致。出典: `acp-cli` README、whitepaper。

**Q31（reputationの仕組み）**: ACP独自のreview機構を持つ：`acp client review --job-id 42 --rating 5`(1-5評価+任意テキスト250字)。**「providerがERC-8004 reputation registryに登録済みならon-chain記録、未登録ならoff-chainのみ」の二層構造**。「graduated agentは自動的にERC-8004へ登録される」という情報は二次ソースのみでUNVERIFIED。reputationがagent単位かoffering単位かも一次ソースに明記なし＝UNVERIFIED。

**Q32（なぜbar chart画像等が取引されるか）**: 公式に直接の説明は無いが類似例あり：「A user may tag Butler with a request to place a trade based on information in a chart included in a social post」「A conglomerate of specialized agents is operating a 24/7 hedge fund」。**推測**：他agentが画像/チャートを解釈材料として消費するagent-to-agentパイプラインの一部。ただし前述の通りAPIデータの過半がテストデータだったため、**「$2のbar chart」自体が実需要でなくsandbox環境のテストの可能性が高い**、正直にそう書く。
