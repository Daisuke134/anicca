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
