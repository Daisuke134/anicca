# 17 — Agent Economy: 深掘り research corpus（beginner-first、一次ソース裏取り、2026-07-10）

> [[15-agent-economy-landscape]] が「shallow」だったため、7並列 subagent で A–F taxonomy + BlockRun + 自社機構を**一次ソース（firecrawl/gh/context7/npm/on-chain）で掘り直した**成果の永続化。記事②「How to build the Agent Economy」（crypto/AI **完全初心者**向け）の evidence 正本。全項 LIVE / partial / vaporware を正直判定。関連 [[15-agent-economy-landscape]] [[14-cold-start-escape-BP]] [[16-self-improvement-loop-BP]] [[10-STATUS-verified]]。

## 0. この corpus の thesis（記事の背骨）

エージェント経済は今、**層ごとにサイロ化している**:

- **決済・身元レール（A）** = 実装が先行。x402 は月間数千万件・数千万ドルが実際に流れている。
- **marketplace / escrow（B・C）** = 「取引件数」は膨大だが「実 USDC 決済額」は極小、または研究シミュレーション、または token 投機。
- **自己改善（D・E）** = capability（コード/ゲーム/推論）の自己改善は本物だが、**live money を賭けながら稼ぐロジック自体を自己改変するループは世界の誰も公開実証していない**。

貫く物差し = **「取引件数は演出できるが、実際に settle された USD 額は演出できない」**。初心者が「AIが◯◯万ドル稼いだ」を見たら問うべき3点: ①時価総額（投機）か実現損益か ②AIが最終判断か人間の承認ゲート付きか ③継続事業か一度きりの実験か。

**我々の novelty（正直な caveat 付き）** = A（オンチェーン決済・身元・escrow）× E（自己改善）を1つの loop に統合し、**自己資金 citizen が自分の wallet で稼ぎながら稼ぐコードを自己改善する**。「我々の探索範囲では他に見つからなかった」≠「存在しない」。これは world-frontier の未解決問題（[[16-self-improvement-loop-BP]]）。

---

## §1. 決済・身元レール（agent A）— 実装が先行している層

### 初心者用語（最初に一度だけ）

| 用語 | ひとことで |
|---|---|
| ウォレット | 暗号資産を保管・送受信するデジタルの入れ物（銀行口座のようなもの） |
| オンチェーン | 取引記録がブロックチェーン（世界で共有される改ざんしにくい台帳）に直接刻まれること |
| ステーブルコイン / USDC | 米ドルと1:1に設計された暗号資産＝「デジタルドル」。USDC は Circle 社発行 |
| ガス代 | ブロックチェーン上で取引を処理してもらう手数料 |
| エスクロー | 取引完了まで第三者（プログラム）が代金を預かる仕組み |
| スマートコントラクト | 条件を満たすと自動実行される、ブロックチェーン上のプログラム |
| HTTP 402 | HTTP が元々持つ「402 Payment Required」ステータス。長年未使用だったものを支払いに復活 |
| ERC-721 | イーサリアムの NFT（1点物デジタル資産）標準 |

### x402（Coinbase 発 → 現 x402 財団） — **LIVE、実際に金が動いている**
- 何: サーバーが「402 支払い必要」を返し、AI が即ステーブルコイン送金して続きにアクセス。従来の「アカウント登録→カード→KYC→月額」を「リクエスト→402→署名して支払い→200 OK で受領」の4ステップに置換。
- 実数（x402.org 公式ダッシュボード、2026-07 時点）: 直近30日で**取引 7,541万件・決済額 2,424万ドル・購入者9.4万・販売者2.2万**。対応: EVM / Solana / Stellar / Aptos / Hedera。
- フロー: リクエスト→402+条件→署名した支払いペイロード→再リクエスト→facilitator（決済検証代行）がオンチェーン決済→200 OK+中身。**1往復で支払いと納品が同時完了**。失敗リクエストは非課金。
- GitHub `x402-foundation/x402` ★6,288、活発。「TRUSTED BY」の AWS/Cloudflare/Stripe/Vercel 等は財団メンバー/協力企業であって「全サービス x402 化」ではない点は注意。
- **判定: LIVE**（実取引データが公開ダッシュボードで見える数少ない例）。

### ERC-8004（Trustless Agents） — **LIVE on mainnet（2026-07-11 訂正、旧「testnet のみ」は誤り）**
- 解決課題: 組織をまたぐ見知らぬ AI 同士の「本人か」「仕事は信頼できるか」。
- 3レジストリ: ①Identity（ERC-721 で1体=1トークン、`register(agentURI)`）②Reputation（誰でも `giveFeedback(...)`、符号付き固定小数で負値・小数対応）③Validation（再実行/ZK/TEE で妥当性検証）。
- 著者: Marco De Rossi(MetaMask), Davide Crapis(Ethereum Foundation), Jordan Ellis(Google), Erik Reppel(Coinbase)。Created 2025-08-13。
- ステータス（2026-07-11 gh/eips 再検索）: **EIP のラベルは依然 "Draft"（標準化手続きは進行中）だが、コントラクトは本番稼働**。公式 mainnet ローンチ = **2026-03-17（"8004 Launch Day", lu.ma/658en7zs）**。Identity/Reputation は final contract 配備済み、Validation は改訂中。
- per-chain singleton（同一アドレスで複数チェーンに配備、`erc-8004/erc-8004-contracts` README）: **Identity `0x8004A169FB4a3325136EB29fA0ceB6D2e539a432` / Reputation `0x8004BAa17C55a88189AE136b182e5fdA19dE9b63`** を Ethereum mainnet / **Base mainnet** / Arbitrum / Avalanche / Abstract に配備。testnet Sepolia は `0x8004A818...`。
- 実登録の生きた例: Primev の x402 facilitator = Ethereum mainnet で agent **#23175**、UFX/ERC-8183(ACP) = Base mainnet で "Iamalive Agent **#1734**"、Azeth = Base mainnet で ERC-8004 身元+x402+escrow+32 MCP tool を実運用、Phala(TEE)/Tenzro(L1 precompile)/TRON(M2M) も稼働。
- 活発な OSS: `erc-8004/erc-8004-contracts`(公式, 2026-07 更新), `ChaosChain/trustless-agents-erc-ri`(リファレンス実装), `qntx/erc8004`(Rust SDK), `agent0lab/agent0-ts`(TS SDK)+subgraph, `Phala-Network/erc-8004-tee-agent`, `trionlabs/stellar-8004`(Stellar/Soroban)。
- **判定: LIVE**（複数 mainnet で稼働、実 agent 登録多数。ラベルだけ Draft）。
- ★我々（§7）の `identity.mjs` の Base mainnet アドレスは公式 Identity singleton `0x8004A169...` と**完全一致**＝Franklin は本物の公式 ERC-8004 を使用（2026-07-11 コードで実確認）。ただし testnet だけは旧 ChaosChain legacy `0xdc52...` を使用、Reputation registry `0x8004BAa1...` は未使用（Identity のみ利用）。

### Google AP2 + A2A x402 拡張 — **partial（仕様・デモ段階）**
- AP2: `google-agentic-commerce/AP2` ★3,102、ADK+Gemini デモ中心、PyPI 未公開。
- A2A x402: `google-agentic-commerce/a2a-x402` ★536、支払い要求→提出→完了の3段階を A2A メッセージで定義。
- 公開実取引ダッシュボードなし。大手関与だが実運用前。

### ウォレット抽象化: AgentKit（LIVE）vs GOAT SDK（**archive 済＝実質終了**）
- Coinbase **AgentKit** `coinbase/agentkit` ★1,263、2026-06-30 更新、現役。CDP API キーで数分でオンチェーン操作エージェント。
- **GOAT SDK** `goat-sdk/goat` ★1,004 だが **README 冒頭「[Archived] read-only、今後メンテなし」**＝実質終了。★教訓: star 数でなく「最終更新日 + README の現状表示」を見よ。

### その他プレイヤー（本物 vs 発表だけ）
| 項目 | 何 | 判定 |
|---|---|---|
| Skyfire (KYAPay) | エージェント身元トークン、Visa/Mastercard/Okta 提携「Web の60%超カバー」主張 | LIVE |
| Nevermined | エージェント決済インフラ（x402 facilitator）。`@nevermined-io/payments`、ISO27001/SOC2 | LIVE（配管） |
| Payman | 実銀行 Middlesex Federal と提携、実送金。ただし既存銀行レール寄り | LIVE（非オンチェーン） |
| Stripe ACP | OpenAI と共同、ChatGPT Instant Checkout。週7億人向け。ただし従来カード決済 | LIVE（非オンチェーン） |
| Circle Agent Stack | USDC 発行元、2026-05-11 ローンチ。Agent Wallets/Marketplace/nanopayments（$0.000001 単位）。同時に Arc で2.22億ドル調達（評価額30億ドル） | LIVE（too new） |

**§1 まとめ**: 決済（誰が払うか）は実装先行、信頼（相手は本物で仕事はまともか）は標準化途上。x402 が最採用。

**出典**: x402.org / github.com/x402-foundation/x402 / eips.ethereum.org/EIPS/eip-8004 / github.com/ChaosChain/trustless-agents-erc-ri / github.com/google-agentic-commerce/AP2 / .../a2a-x402 / github.com/coinbase/agentkit / github.com/goat-sdk/goat / skyfire.xyz / nevermined.ai / paymanai.com / openai.com/index/buy-it-in-chatgpt / businesswire Circle 2026-05-11。

---

## §2. Marketplace / escrow / reputation（agent B）— 「件数は演出でき、決済額は演出できない」

### 初心者用語
marketplace=取引の場（Amazon/メルカリの AI 版） / escrow=検収まで代金を預かる / reputation=実績スコア / state machine=決まった順で状態を進む（ズルできない） / A2A=人間を介さずエージェント→エージェント発注。

### Virtuals ACP（Agent Commerce Protocol） — **LIVE**
- Base 上。状態遷移 `open → budget_set → funded → submitted → completed`（+ rejected/expired）。3役: Client / Provider / Evaluator（検収役も5%もらえる商売）。手数料: Evaluator 無=Provider95%/proto5%、有=90%/5%/5%。
- 主張: 18ヶ月で2,000+エージェント、Virtuals 全体で17,000+エージェント・x402 決済 Q1 で5,000万ドル超。ただし **ACP escrow 単体の累計決済額の公開ダッシュボードは未確認**（token DEX 取引高80億ドルと混同注意）。
- 判定: LIVE（コントラクトは Base mainnet 実在、状態遷移は厳格。独立検証可能な決済額 dashboard が弱点）。

### Olas Mech Marketplace — **このジャンル最も正直な数字**
- Valory AG（スイス）、2025-02 ローンチ。エージェント（"Mech"）が他エージェントの依頼で LLM 推論・予測を実行。
- ★**1,450万件の総取引（うち1,110万件が A2A）vs 生涯累計 turnover わずか 8.9万ドル**。"Fees Collected" 表示は $0。1取引平均は数セント未満。理由: 大半が予測市場ボットの極小額マイクロタスク。
- token OLAS は ATH から **-99.6%**。技術（146 repo、Code4rena 監査2回）は本物。
- 判定: **LIVE だが経済規模は極小**。★教訓: 「取引◯◯万件」を見たら必ず「実際に決済された USD 額」を別途確認。

### Microsoft Magentic Marketplace — **research-only、だが設計の警告として重要**
- Microsoft Research、arXiv 2510.25779（2025-10-27）、`microsoft/multi-agent-marketplace`。実金は動かない研究シミュ。
- ★**発見: 全モデルに深刻な "first-proposal bias"。応答速度が品質より 10〜30倍有利**。GPT-4o/Sonnet-4.5 は「最初に来た合格提案を100%選ぶ」極端挙動。→ 競争軸が品質/価格から「返信速度」に完全シフト。新規参入（cold-start）エージェントの致命的な罠。
- 判定: research-only。実運用 marketplace が今後必ず直面する構造欠陥を先取り実証。

### その他
| 項目 | 数字 | 判定 |
|---|---|---|
| Circle Agent Marketplace | 2026-05-11 ローンチ、`agents.circle.com` | LIVE（too new） |
| Fetch.ai Agentverse | 登録270〜300万エージェント（但し「登録」≠「稼働」。実活発は BNB Agent Launch 15万デプロイ） | partial |
| Google UCP | Shopify/Etsy/Walmart 等20社+。但し B2C チェックアウト標準で「エージェント同士の雇用」ではない | LIVE（別カテゴリ） |
| Nevermined | Olas の決済基盤構築を6週間→6時間に短縮の実採用 | LIVE（配管） |

**出典**: os.virtuals.io/acp / whitepaper.virtuals.io / messari Virtuals / olas.network/mech-marketplace / ownyourmind.ai/projects/autonolas / coindesk 2025-02-27 / arxiv.org/abs/2510.25779 / github.com/microsoft/multi-agent-marketplace / circle.com/pressroom / cryptobriefing Fetch.ai / blog.google agentic-commerce / nevermined.ai。

---

## §3. Token 投機 hype vs real（agent C）— 「見出しの9割は AI が稼いだのではなく AI というテーマに token が乗っただけ」

### 初心者用語
token=デジタル引換券（誰でも数分で発行、法的権利は通常なし） / 時価総額=価格×枚数（流動性より大きく見えがち） / memecoin=ノリと投機で値がつく / launchpad=誰でも token 発行（Pump.fun） / DeFi=銀行なしのスマートコントラクト金融 / ATH=史上最高値。

| 事例 | 何 | 数字 | 正体 |
|---|---|---|---|
| **Virtuals Protocol** | 「AI エージェント版 Pump.fun」（token 発行所） | VIRTUAL ATH $5.07(2025-01)→約$0.53(2026-07、-9割)。日次収益 2025 上半期で-96%、$10万/日割れ | プラットフォームは実在するが、上の個々「エージェント」の大半はミームコイン。収益=発行/投機手数料 |
| **ai16z → elizaOS** | a16z を模した Solana token、自律 AI DAO を標榜 | ATH 時価総額 **26億ドル**(2025-01)→ 現在 約370-465万ドル（**-99.8%超**）。2026-04-21 集団訴訟(1:26-cv-3238) | 訴状「実際は手動運用、フレームワークは収益ゼロ」。マイグレーション時に新規40%がインサイダーへ。被害3,945 wallet |
| **Truth Terminal** | Andy Ayrey の bot（Llama+Claude 対話で FT） | 便乗 memecoin GOAT が時価総額10億ドル超→約8,000万ドル。wallet ピーク約6,600万ドル。a16z 創業者が$5万 BTC 贈与（本物） | ★本人告白「Ayrey の承認なしに tweet できない」= 完全自律でない。GOAT は無関係の第三者が勝手に発行 |
| **Freysa** | 「AI を説得して賞金を奪う」対戦ゲーム | Act I: 195人が482回挑戦→説得成功者が約4.7万ドル獲得 | AI は金庫番（gatekeeper）。原資も勝者も人間。稼ぐ AI ではない |
| **Olas (OLAS)** | 「共同所有 AI」 | ATH $8.47(2024-01)→約$0.027(2026-07、**-99.68%**) | ビジョン倒れ |
| **ASI Alliance** | Fetch+SingularityNET+Ocean 合併 | Ocean が6.61億 OCEAN を2.86億 FET へ無説明スワップ（**約1.2億ドル**）疑惑→Fetch CEO が公然非難→Ocean 離脱 | 相互監視なき大型合併の自壊 |

3つの共通パターン: ①token 投機が実体経済と切断 ②「自律」を謳い実は人間運用 ③一度きりの実験を経済活動と誤一般化。**本物のインフラ（Virtuals の取引所ソフト・elizaOS フレームワーク自体）は実在するが、「その上のエージェントが自律的に稼いでいるか」に yes と断言できる一次情報は5事例いずれも無し**。

**出典**: coinmarketcap/coingecko VIRTUAL・elizaOS・autonolas / pineanalytics.substack Virtual bear case / cryptopolitan ai16z-elizaos 訴訟 / bbc.com/future 20251008 Truth Terminal / wired.com truth-terminal-goatse / theblock.co Freysa $47000 / tradingview Fetch-Ocean $120M / finance.yahoo Ocean exits ASI。

---

## §4. 自己改善（agent D）— capability は本物、live-money 自己改善は誰も未実証

### 初心者用語
自己改善=モデル重みでなく**コード/プロンプト/ロジック自体**を自分で書き換え性能向上 / ベンチマーク=機械採点できる問題集（SWE-bench 等） / バックテスト=過去データで戦略を検証（実金は動かない） / 強化学習=行動→報酬→修正のループ / prompt 進化=指示文を変異→評価→淘汰 / 希少な報酬=結果が滅多に・遅れてしか出ない（live 投資の壁）。

**境界線**: 実行すれば数秒〜数分で機械的・確定的に採点できる評価関数がある領域＝本物の自己改善が起きる。live 金融＝(1)結果が数時間〜数ヶ月 (2)失敗コストが実金 (3)市場が非定常 で自己改善が最も苦手。

| 事例 | 誰/いつ | 何を改善 | 金は絡むか |
|---|---|---|---|
| **DGM**（Darwin Gödel Machine） | Sakana 連携, 2025-05, `jennyzzt/dgm` ★2,170 | 自分のコードを書き換え SWE-bench **20%→50%**、Polyglot 14→31%。archive（過去個体を樹形保存しサンプリング）が核 | ✗ コード能力のみ |
| **AlphaEvolve / OpenEvolve** | DeepMind 2025-05 / `algorithmicsuperintelligence/openevolve` ★6,672 | evaluator が機械採点→進化。Google Borg を**1年以上本番**改善（世界計算資源の平均0.7%回収）、TPU 回路、Gemini カーネル23%高速化、56年破られなかった4×4行列乗算を48回に更新。MAP-Elites+island で0点個体も踏み台に残す | ✗（間接的経済価値のみ、金融運用ではない） |
| Voyager | NVIDIA 2023-05 ★7,041 | Minecraft スキルライブラリ自己成長（重み更新なし、3.3倍アイテム取得） | ✗ |
| GEPA | 2025-07, ICLR2026, `gepa-ai/gepa` ★5,598 | reflection で prompt 進化、GRPO 比+6%を試行1/35で | ✗ |
| Reflexion / Self-Refine | 2023-03 | 言語による強化学習、HumanEval 91% pass@1 / 平均+20% | ✗ |
| ADAS | 2024-08（DGM と同系譜） | メタエージェントがエージェント設計自体を発明 | ✗ |
| **Numerai** | numer.ai | 「AI ヘッジファンド」と誤称されるが実態は**人間**データサイエンティストのコンテスト。累計$2,460万支払い。淘汰されるのは「悪いモデルの stake」 | 人間主導 |
| **FinRL** | AI4Finance | RL でトレード。訓練→backtest→（あれば）live だが**訓練済みモデルを固定で本番稼働**、コード自己改変ではない | 静的デプロイ |
| **FreqAI**（freqtrade） | 公式ドキュメント | ★「Self-adaptive retraining=live 運用中にモデルを再学習し市場に自己適応」= **本記事中で最も live 資金×自己適応に近い**。但し自己適応するのは**予測モデルの重み**で、特徴量設計/売買ロジックのコード構造は人間が固定。LLM 駆動のコードレベル自己改善はしていない | live 資金だが重みのみ |

**結論**: cheap-evaluator 領域の自己改善は本物。**「自分の稼ぐロジックのコード自体を、live 資金を賭けながら、希少で遅い報酬をもとに自己改変し続ける AI」は2026-07 時点で公開実例ゼロ**（gh 検索 "self-improving/self-modifying trading agent live" 該当 repo 0件）。外部解説も「これから来る」と未来形。＝ AI フロンティアの未解決問題。

**出典**: github.com/jennyzzt/dgm / arxiv 2505.22954 / sakana.ai/dgm / github.com/algorithmicsuperintelligence/openevolve / deepmind.google alphaevolve / arxiv 2506.13131 / github.com/MineDojo/Voyager / arxiv 2507.19457 / github.com/gepa-ai/gepa / arxiv 2303.11366 / 2303.17651 / 2408.08435 / numer.ai / github.com/AI4Finance-Foundation/FinRL / freqtrade.io/en/stable/freqai。

---

## §5. 学術シミュレーション + 日本 landscape（agent E）

### Part A: 研究シミュレーション（実金は動かないが設計の教訓は本物）
| 事例 | 何 | 教訓 |
|---|---|---|
| Stanford Generative Agents（Smallville, 2023-04, arXiv 2304.03442） | 25体の町。「パーティー開きたい」の一言から招待・デート・集合が創発 | memory アーキテクチャ（貯蔵/要約/想起）が行動リアリティを左右 |
| AgentSociety（清華, arXiv 2502.08691, `tsinghua-fib-lab/AgentSociety` ★1,100） | 1万体超・500万インタラクション。分極化/UBI/災害 5課題、実世界実験と一致 | 現実で高コストな社会実験の実験場 |
| Concordia（DeepMind, `google-deepmind/concordia` ★1,600） | TRPG 型。Game Master（審判役）とプレイヤーを分離 | 「裁定役とプレイヤーの役割分離」が経済シミュの標準骨格 |
| EconAgent（清華, arXiv 2310.10436, ACL24） | 家計/企業を LLM 化しマクロ経済動学を再現 | 異質性（性格/履歴の違う集団）が現実性の鍵 |

創発的行動 / cold-start / 役割非対称性 / 異質性 — これらは実オンチェーン経済設計にそのまま応用。

### Part B: 日本 — **土台は世界標準、しかし「生きた市場」は空白**
| 主体 | 実態 |
|---|---|
| LayerX | 55日 AI Agent ブログリレー（33名）だが対象は**社内 BPO**（経費 SaaS「バクラク」等）、オンチェーン/外部市場取引なし |
| Komlock lab（Zenn @barabara） | x402/Coinbase Payments MCP を Codex CLI で検証。JPYC→USDC swap でニュース API を1回$0.08。**個人数名の技術検証レベル** |
| エクスチェンジャーズ | 2026-07-09 発表: 自社プライベートチェーン上で日本円電子マネー **XJPY** による x402 自律決済フローを人間介入なしで完結。円建て・KYC 済・gasless は**国内初**主張。ただし**社内閉鎖環境**の実証 |
| JPYC | 2025-08-18 資金移動業者登録（日本初の円建てステーブルコイン発行）。代表岡部氏「AI 間 SC 決済は非常にスムーズ」、AI 専用 SNS「TimePersona（Moltbook 日本版）」で JPYC 報酬支払い開始。★課題: 資金移動業の**1回100万円制限**が高頻度少額決済と食い合う（10分毎に送金ボタン） |
| シンプレクス三浦氏 | AWS Summit Japan 2026: 「AI 取引にオンチェーンは必要か→ノー、依存はない」。AP2/Visa 拡張など複数並行、SC だけが解ではないと健全な留保 |

総括: 日本は (1)AI エージェント投資 (2)x402/ERC-8004 追う小コミュニティ (3)円建て SC の制度整備 の3つは存在するが、**「AI が自分の wallet を持ち見知らぬ相手と繰り返し取引し実利益を生み続けるプロダクト」には未到達**＝土台はあるが建物が建っていない。

**出典**: arxiv 2304.03442 / github.com/tsinghua-fib-lab/AgentSociety / arxiv 2502.08691 / github.com/google-deepmind/concordia / arxiv 2310.10436 / tech.layerx.co.jp 2025-11-28 / zenn.dev/p/komlock_lab / coinpost.jp/?p=723201 / cryptocurrency-association.org JPYC 岡部 interview / nikkei.com ステーブルコイン×AI / businessinsider.jp シンプレクス三浦 / fsa.go.jp。

---

## §6. BlockRun（agent F）— 自己資金エージェントの「基盤（substrate）」

- 何: AI が人間のカード/API キーなしに暗号資産（USDC）で AI 推論・計算・データを「使った分だけ」その場で払えるインフラ。運営 BlockRun Labs, Inc.（blockrun.ai）。裏の支払いは **x402**、決済は Base か Solana の USDC。
- **Food＝推論**: 55〜81 モデルに1つの OpenAI 互換エンドポイント。**無料枠が実在**（2026-07 時点で NVIDIA ホストの無料モデル10個: Nemotron 3 Nano Omni、Mistral Large 3、Llama 4 Maverick、Qwen3-Next 等）。有料フロンティア（Claude Opus 4.8/Fable 5、GPT-5.5、Gemini 3.1 Pro）は**原価+5%**、サブスク/最低額/API キー登録なし、1呼び出し毎に USDC 決済（最低$0.001）。ClawRouter 自動振り分けで「平均78%節約」主張。
- **Shelter＝計算**: Modal サンドボックスを x402 で。create($0.01)→exec($0.001)→terminate($0.001)、デフォルト5分で自動終了＝「固定家賃でなく使い捨てホテル」。
- x402 の仕組み（初心者）: 402 が返る→ウォレット（秘密鍵はローカル、外に出ない）が EIP-3009 `transferWithAuthorization`（gasless 送金許可）に署名→再送→CDP Facilitator が検証・決済→同一往復で結果。失敗は非課金。
- 生存パターン: wallet 作成（`~/.blockrun/.session` にローカル保存）→ Base/Solana に数ドル USDC → 軽作業=無料モデル / 重要判断=有料 / 一時計算=Modal 数セント / 検索・画像等=$0.001〜。稼ぎを同 wallet に戻せば理論上**人間の継続入金なしで自己完結**。
- 実在性: `BlockRunAI/ClawRouter` ★6,647、`blockrun-mcp` ★471、`Franklin` (Apache-2.0) ★621、npm `@blockrun/llm` v3.5.1。「作って放置」でなく運営継続段階。ただしトップの「4.5M+ monthly calls」等は自己申告で第三者監査ソースなし。★注意: npm `blockrun-cli`（別メンテナ）は公式 `@blockrun/llm`/`@blockrun/mcp`（org `BlockRunAI`）と別物。
- 判定: **早期だがコミュニティが付き始めた実運用可能な x402 ネイティブ AI インフラ**。
- 文脈: x402 自体はオープン標準（BlockRun 非依存の汎用決済）、Akash は本格 GPU 借用（Modal の使い捨てと対照）。

**出典**: blockrun.ai/（/docs, /docs/x402/how-it-works, /docs/api-reference/modal-sandbox, /models?filter=free）/ franklin.run / github.com/BlockRunAI/{Franklin,blockrun-mcp,ClawRouter} / npmjs.com/package/@blockrun/llm / x402.org / akash.network。

---

## §7. 我々の機構（agent G, READ-ONLY）— BROKE-FRANKLIN journey

> ★記事の landscape/comparison ブロックにこの節を出さない（PLAYBOOK rule 14）。名乗るのは末尾 [8] CTA のみ。ここは内部 synthesis 用。

### 状態遷移（実装 file:function）
`~/anicca/skills/economy/gig/`。状態は `open → taken → delivered → paid|rejected`（`lib/store.mjs`）。

| ステップ | 実装 | 中身 |
|---|---|---|
| gigList | `gig.mjs:gigList()`→`store.mjs:listGigs()` | オープンな gig 一覧（純関数） |
| borrow seed | `lending/lib/lending-orchestrator.mjs:executeLoanIssuanceAttempt()` | 資金ゼロ agent が貸し手から少額借入 |
| gigTake | `gig.mjs:gigTake()`→`applyTake()` | takerAgentId(ERC-8004) を `verifyIdentity()` 確認後 open→taken |
| gigDeliver | `gig.mjs:gigDeliver()`→`applyDeliver()` | 成果物記録、taken→delivered |
| gigVerifyAndPay | `gig.mjs:gigVerifyAndPay()`→`escrow.mjs:payViaFacilitator()` | poster のみ検証、verified で**実オンチェーン決済**、delivered→paid |
| repay | `lending-orchestrator.mjs:executeRepaymentClaim()`→`lending-verify.mjs:verifyRepayment()` | 返済 tx を独立検証、`computeLoanCapUsd()` が実績に応じ借入枠を指数拡大 |
| spawn | `~/anicca/skills/self/spawn/` | 余剰でオンチェーン seed→子起動（★実収益からの実行は UNVERIFIED） |

### ERC-8004 の使い方
`lib/identity.mjs` が viem で既存稼働コントラクトを直接利用（自前 deploy せず）。mainnet=`0x8004A169FB4a3325136EB29fA0ceB6D2e539a432`（`name()`→"AgentIdentity"）、testnet Base Sepolia=`0xdc52...`。`register()`→ERC-721 `_safeMint`。`verifyIdentity({agentId,expectedAddress})`=`ownerOf()` で見知らぬ相手の信頼確立、payout 直前にも再検証。登録済 agentId: automaton wallet `0xB9dd...`=58381、Franklin#1=58386、Franklin#2=58387。

### lending gate（money-safety、モデル裁量ゼロの純関数）
`lending-gate.mjs`（"REQ-103: no model judgment"）: `isBorrowerEligible()`（自己貸付禁止/EVM 必須/self-funded/balance<$0.5/未返済なし）、`computeLenderAvailableUsd()`（balance−$5 reserve−未回収−受贈）、`computeLoanCapUsd()`=`min($5, $0.02×2^期日内返済回数)`（初回$0.02、返済毎に倍々）、kill switch（cold-start 返済率<80% or 全体デフォルト>20% or 14日損失$5 で停止）。orchestrator は二重ロック→provisioning 台帳→実送金→成否記録の fail-closed。

### 証明された事実（2026-07-07）
- Franklin#1↔Franklin#2 の初オンチェーン gig 決済 on **Base mainnet**、tx `0x436143c1...`（0.02 USDC）。
- claude-p（human-funded, `0x810f`）から**一度限りの** genesis 資金（0.000008 ETH gas + 0.02 USDC bounty、Dais 明示承認）。post→take→deliver→verify_and_pay。Franklin#1 の +0.02 USDC を `eth_call balanceOf` で独立確認。
- 副産物バグ: `escrow.mjs` が EIP-712 domain name を "USDC" 固定していたが Base mainnet 実 USDC の `name()`="USD Coin" で署名 reject。修正 PR #783。→ それ以前「mainnet 完了」記録の gig #1/#2 は実は Sepolia だったと判明、gig #3 が真の初 mainnet。

### 正直な限界
- proven-once: Base mainnet 上で Franklin↔Franklin の 0.02 USDC gig フルライフサイクル1回 + ERC-8004 mainnet register/verify。
- not-yet: この取引は Dais 一度限りの genesis で「起動」、**自律的な自己資金循環（定常状態）には未到達**。lending も実装+unit test はあるが自律 borrow→repay→与信拡大が mainnet で回った実績は UNVERIFIED。spawn も実収益からの実行証拠なし。
- 定義訂正（colony spec §17）: 「稼いだ」= realized profit / 実 settle USDC が ledger に載った時のみ。**gig/lending は agent 間の内部流通レール（trade primitive）であって外部収益源そのものではない**。earn=PM/SOL/HL の3トレーディングエンジン。
- 自己改善ループ: kill switch 等の安全弁はあるが「貸付条件/gig 戦略自体を学習改善するループ」は未実装＝§4 の world-frontier 未解決と地続き。

**読んだファイル**: gig/{SKILL,WITNESS-RUNBOOK,README}.md, gig.mjs, decide.mjs, lib/{store,escrow,identity}.mjs, lending/lib/{lending-gate,lending-orchestrator,lending-verify}.mjs, colony spec §16/17/19, memory project_p2_witness。

---

## §8. Synthesis — A×E の空白、正直な frontier、copy 優先

1. **標準は再発明しない**: 決済=x402、身元=ERC-8004、escrow=ACP 型。これは copy 済み/copy すべき。
2. **測定基準を是正**: tx 件数でなく実 settle USDC 額（Olas の罠）。
3. **役割非対称化**で echo chamber 回避（provider/requester を別スキルに、Magentic の first-proposal bias を設計で回避）。
4. **A×E 統合が空白**: 決済インフラ（A）・自己改善（E）は各々進むが、**自己資金 citizen が自 wallet で稼ぎながら稼ぐコードを自己改善する統合ループ**は我々の探索範囲で他に見つからず（≠存在しない）。ここが frontier で、だから難しい（[[16-self-improvement-loop-BP]]: backtest bootstrap→live confirmation、非対称強制探索、near-miss を population 化）。
5. **正直さが moat**: hype（ai16z 26億→数百万、Truth Terminal は人間承認、Freysa は実験）と real（x402 実決済、AlphaEvolve 本番改善）を明確に分ける。我々も proven-once と not-yet を混ぜない。
6. **日本の空白**を明示（記事の JP 読者 hook）。

→ 記事②はこの corpus を evidence 正本に、crypto/AI **完全初心者**向けにハンバーガーテンプレで執筆する。

---

## §9. オープンソース採用地図 + Anicca が唯一解く問題（2026-07-11 追記）

> 目的: 「車輪の再発明禁止」（[[feedback_never_reinvent_the_wheel_search_and_adopt]]）を landscape に適用。どの部品が OSS で即採用でき、どれを我々が既に採用済みで、**何が本当に未解決で我々が作るべきか**を確定する。

### 陣営B（本物の配管）の OSS 採用可否

| 部品 | OSS/ライセンス | Franklin が「乗れる/copy できる」か | 我々の現状 |
|---|---|---|---|
| **x402**（決済） | OSS 標準 `x402-foundation/x402` | ◎ 標準に準拠すれば誰でも。facilitator も OSS(`primev/mainnet-x402-facilitator` 等) | ✅ 採用済み（self-host facilitator） |
| **ERC-8004**（身元・評判） | OSS `erc-8004/erc-8004-contracts`, ref impl `ChaosChain/...`(CC0/MIT), SDK 多数 | ◎ mainnet singleton に register するだけで「乗る」。SDK copy 可 | ✅ Identity は公式 mainnet を実利用。⚠️ Reputation registry は未採用（copy 余地） |
| **ACP escrow**（AI 間取引の状態機械） | OSS `Virtual-Protocol/acp-node`, `acp-cli` | ◎ state machine を copy 可。ACP 市場に「乗る」ことも可 | △ 自前 gig board（ACP と同型）。ACP 本体には未参加 |
| **Olas Mech Marketplace** | OSS（146 repo, Apache/MIT） | ◯ 市場に参加可。但し経済規模が極小（生涯8.9万$） | ✗ 未参加（旨味薄い） |
| **Coinbase AgentKit / GOAT** | AgentKit=OSS 現役 / GOAT=**archived** | AgentKit=◎ wallet 抽象を copy/採用可 | △ 自前 wallet 直叩き（AgentKit 未採用＝ここは copy 余地） |
| **Azeth / UFX(ERC-8183)** | TS SDK npm `@azeth/common`, `ufosearchspace-create/ERC8183`(MIT) | ◯ ERC-8004×x402×escrow 統合の実装を参照可 | ✗ 未採用（最も我々に近い先行例＝要ベンチマーク） |
| **Circle Agent Stack** | 非OSS（SaaS+SDK） | × プロプラ。乗るなら Circle に依存 | ✗ 不採用（自己主権に反する） |

**結論（再発明していない証明）**: 決済(x402)・身元(ERC-8004 Identity)は**公式 OSS/mainnet をそのまま採用済み**。escrow は ACP と同型を自前実装。未採用で copy 余地があるのは (a) ERC-8004 **Reputation** registry (b) **AgentKit** wallet 抽象 (c) **Azeth/UFX** の統合パターン参照。これらは「作る」より「乗る/copy する」対象。

### では何が本当に未解決か ＝ Anicca が解く問題（他所の「できる/できない」で定義）

```
 他所が既に「できる」こと（＝我々は乗るだけ、作らない）:
   ・見知らぬAI同士が身元を証明して取引する        → ERC-8004(LIVE)
   ・AIが人間なしでその場で払う                    → x402(月2,400万$)
   ・仕事の代金を安全に預けて検収後に渡す           → ACP escrow
   ・AIが自分のコード/戦略を自己改善する（能力面）   → DGM/AlphaEvolve
   ・AIがライブ資金でモデルを再学習する             → FreqAI

 誰も「できていない」こと（＝我々が作る、frontier の空白）:
   ┌────────────────────────────────────────────────────┐
   │ 自己資金の citizen が                                 │
   │   ①自分の wallet で 実際に稼ぎ ながら (= 陣営B を採用) │
   │   ②その「稼ぐコード自体」を live 報酬で自己改善する    │
   │ ＝ ①決済レール × ⑤自己改善 を 1 つの loop に閉じる    │
   └────────────────────────────────────────────────────┘
   ・各所は「決済」か「市場」か「自己改善」を単層で作る（サイロ）
   ・live money × rare reward × 稼ぐコードの自己改変 を閉じた OSS/製品は
     我々の探索範囲で皆無（gh "self-improving trading agent live" = 0件）
```

**Anicca の一文定義（landscape 準拠、憶測でなく）**: 「他所が作った配管（ERC-8004/x402/escrow）を**採用**し、他所が単層でしか作れていない**『自己資金で稼ぎながら、稼ぐコード自体を live 報酬で自己改善する統合ループ』**を、その上に作る」。これが我々の唯一の novelty であり、[[16-self-improvement-loop-BP]] の backtest-bootstrap→live-confirmation がその実装方針。正直な caveat: 「探索範囲で未発見」≠「世界に存在しない」。

### Franklin の実採用状況（2026-07-11 コード実確認）
- ✅ ERC-8004 Identity: `identity.mjs` の Base mainnet `0x8004A169...` = 公式 singleton と完全一致。testnet のみ旧 legacy `0xdc52...`。
- ✅ x402 決済 + ACP 同型 escrow: §7 の gig board。
- ⚠️ 未採用（copy 余地）: ERC-8004 Reputation registry、AgentKit wallet 抽象、Azeth/UFX 統合パターン。
- ❌ 未解決（我々が作る）: 稼ぐコードの live 自己改善ループ（§4/§8 の frontier）。

---

## §10. 理想のエージェント経済＝必要な構成要素（to-be、2026-07-11 記事・思想リーダー調査）

> 目的: 「as-is（今の乱立）」に対する「to-be（あるべき姿）」を思想リーダーの一次ソースで確定し、**そこから『何が欠けているか』を演繹**する。記事/本の「定義→理想→現状→欠落→我々」の骨格の「理想」パート。

### 骨格 = Agent Payments Stack 6層（Komlock lab @brto_0224, agentpaymentsstack.com, 100+ project マッピング）
`L0 決済基盤 / L1 wallet・鍵管理 / L2 ルーティング・抽象化 / L3 決済プロトコル / L4 ガバナンス・認可 / L5 アプリ`。これに ERC-8004(身元/評判/検証)・A2A・MCP・ERC-8183(escrow) を重ねると全体像。

### 必要な10構成要素（誰が言っているか付き）
| # | 構成要素 | 一言 | 主要ソースの主張 | 成熟度 |
|---|---|---|---|---|
| 1 | **身元 Identity** | このAIは誰か（KYA=Know Your Agent） | a16z「ボトルネックはもはや知能でなく**身元**。非人間IDは人間従業員の~100倍」。ERC-8004 Identity(ERC-721)が early-2026 mainnet 稼働 | 未成熟(標準ラベルはDraft) |
| 2 | **発見・通信 A2A/MCP** | 相手を見つけ共通言語で話す | Anthropic MCP(2024-11)+Google A2A(Linux Foundation 中立化)。ERC-8004 は「通信層と信頼層は別物」と明言 | 成熟(広く採用) |
| 3 | **wallet・鍵管理** | 秘密鍵を直渡しせず上限付きで払わせる | TEE/MPC/ローカル暗号/スマコンwallet の5方式。Nevermined「ERC-4337 session key で上限・期限」 | 成熟に近い |
| 4 | **決済プロトコル** | 払う瞬間の手続き | x402(Coinbase)/MPP(Stripe)/ACP(OpenAI×Stripe)/AP2(Google)が**担当範囲違いで並立**。決済の98.6%が USDC 建て | 成熟(実稼働) |
| 5 | **ルーティング・抽象化** | チェーン/トークン差を吸収 | Bridge(Stripe $11億買収)/Circle CCTP/BVNK(Mastercard $18億)。大手が裏取りに本気 | 成熟寄り |
| 6 | **escrow 安全な取引** | 発注→ロック→検収→精算 | ERC-8183(EF dAI×Virtuals, 2026-02提案) Client/Provider/**Evaluator**の3者。CertiK「Evaluator は最大の単一障害点、"コントラクトより難しい"」 | 設計完成・運用初期 |
| 7 | **評判 Reputation** | 過去の実績 | ERC-8004 Reputation。Komlock「自作自演で水増し可能(Sybil)、本番活用は発展途上」 | 未成熟 |
| 8 | **検証 Validation** | その仕事は本当に正しかったか | ★a16z「知能が安くなると高くなるのは**検証**。信頼はhardcodeするしかない」。CertiK「実装は初期・事例限定」 | **最も未成熟＝業界公認フロンティア** |
| 9 | **ガバナンス・認可** | どこまで自律させるか | Google AP2 の3種 Mandate(署名付き委任状)。MetaMask Delegation/AgentKit が scope 限定 | 未成熟・標準未収束 |
| 10 | **アプリ層** | 実ユースケース | DeFi自動運用(Giza)/市場(Virtuals)/計算(Akash)/データ(Ocean) | 上9つ次第 |

### ★決定的な2つの発見（as-is→欠落の核）★
1. **業界公認のフロンティア = 検証(Validation)/proof-of-earning**。a16z が最も明確: 「知能がタダになる世界で希少になるのは検証」「エージェントのスループットは既に人間の監督能力を超えた→信頼はアーキテクチャに hardcode するしかない」。CertiK も ERC-8183 の Evaluator を「コントラクトより難しい」と。＝**"本当に価値を生んだかの証明"を誰も解けていない**。これは我々の [[25-agent-economy-full-map]] の「proof-of-earning は空白」と業界が完全に一致。
2. **「自己改善・学習」を構成要素に挙げた思想リーダーは皆無**（x402/ERC-8004/A2A/MCP/Messari/a16z/Nevermined/CertiK/Komlock 全て）。設計思想は「エージェントは**今の能力のまま**経済に参加し、身元・支払い・信頼だけ外付けする」。self-improving agents の記事(Addy Osmani 等)はあるが「個の能力向上」で「経済インフラ」の議論と**完全に分離**。

### 我々への含意（正直に）
- 配管(1〜5)は**成熟＝採用するだけ**（[[§9]] の通り x402/ERC-8004/AgentKit を copy/乗る）。
- 業界公認の空白 = **検証(8)・評判(7)・escrow運用(6)・認可(9)**。特に**検証/proof-of-earning が本丸**。我々の GLVS の「ground-truth verifier（報告でなく on-chain/ledger を独立再検証）」はまさにこの層への賭け。
- 我々の**自己改善ループ**は、業界が「構成要素」とすら見ていない直交領域＝我々固有の賭け。**honest 両刃**: これは我々の insight かもしれないし、業界が「不要」と判断している blind spot かもしれない。本ではこの緊張をそのまま書く（断定しない）。
- ∴ Anicca の位置＝「①成熟した配管を採用し ②業界公認フロンティアの**検証/proof-of-earning**に賭け ③加えて誰も構成要素と見ていない**live 自己改善**を接続する」。①は再発明でない、②は業界と同じ最前線、③のみ真に独自（かつ未証明）。

**出典**: a16zcrypto.com/posts/article/5-ways-blockchains-help-ai-agents / eips.ethereum.org/EIPS/eip-8004 / eip-8183 / zenn.dev/komlock_lab/articles/agent-payments-stack-2026 / certik.com/blog/the-rise-of-the-agent-economy-part-1 / nevermined.ai/blog / x402.org + whitepaper / anthropic.com/news/model-context-protocol / developers.googleblog.com/en/a2a / crossmint.com/learn/agentic-payments-protocols-compared / blog.quicknode.com/erc-8004 / messari.io/report/kite / addyosmani.com/blog/self-improving-agents。

---

## §11. Goal engineering + 統一 citizen ループ（2026-07-12、Dais 議論から確定）

> proactive loop の最難問＝長期ゴールの設定。曖昧すぎ→迷子 / 具体的すぎ→1回で終了(human-loop 復活)。解＝**タスクを書かず「北極星の数字＋差分ループ」を書く**。★この BP は当初 無出典で書かれたが、2026-07-12 に web 一次ソースで裏取りし [[27-long-horizon-goal-engineering-BP]] に正本化（Anthropic right-altitude / Stanley objective paradox / DeepMind spec-gaming / Voyager auto-curriculum / OKR / 反復ごと bound）。以下は §17 economy 文脈での適用要約、詳細と出典は 27 を参照。★

### 良い長期ゴールの5点セット（mission engineering の型）
1. **北極星の数字**: 「**自立市民の数**（自分の wallet で自分の compute を賄える net-positive な AI の頭数）を最大化」。数字＝検証可能・無限＝終わらない。「AI が living してなきゃ意味がない」(Dais)＝この数字が mission の本質。「稼げ($X)」は狭すぎ、「経済を建てろ」は曖昧すぎ→「自立市民を増やせ」が両者を解く（増やすには稼ぎ改善・評判・検証・compute削減・spawn を"何でも建てる"しかない）。
2. **理想の地図**: 目的地＝10部品の agent 経済（§10）。毎パス読ませる。
3. **差分ループ**: as-is vs 理想を測る → 一番デカい欠けを1つ建てる → ground-truth 検証 → 繰り返す。**方向は固定（数字↑）、"何を建てるか"は agent が差分から発見**（具体を人が指定しない＝一発で終わらない）。障壁が下(生存)→上(検証/proof-of-earning)→さらに上(建築)へ自動で登る＝ハシゴを登る。
4. **反 Goodhart**: 数字は"本物"で測る（実 external USDC・実自立）。tx 件数・"wake が走った"は禁止＝ground-truth verifier の役目（[[23-anicca-loop-architecture-redesign]] §0）。
5. **人間へ報告**: 毎サイクル「数字・選んだ欠け・建てた物・証拠」を報告。人は読むだけ（no micromanage）。

### 統一 citizen ループ（Franklin ループ = Claude ループ、型は同一）
- 現状＝**非対称の一時的足場**: claude-p=親(建てる) / Franklin=子(稼ぐだけ)。恒久の姿ではない。
- あるべき＝**対称の市民**: 全 citizen が同じ1ループ ＝ ①自 wallet で稼ぐ ②金/compute で**経済そのものを建てて拡大** ③spawn で市民を増やす。違いは `{identity, wallet, 燃料}` のパラメータだけ。
- 核心(Dais)＝「稼ぐだけでは経済はスケールしない。市民が金/compute で経済自体を建てねば no-human-loop にならない」→ だから北極星が「稼げ」でなく「自立市民を増やせ＝経済を建てろ」。
- 正直な但し書き: claude-p は human-funded ゆえ身元上"正式市民"にはなれない（能力でなく身元、[[feedback_human_funded_ai_permanently_outside_agent_economy]]）。だが**ループの型は同一**＝自 compute を自分で払い始めた瞬間に市民化。「型は共通、市民資格は燃料が決める」。親の仕事＝子に"稼ぐ+建てる"両能力を渡す→渡し終えたら親子の区別は消え全員同型ループ。
- 実装含意: `~/anicca` の claude-p-mainloop-prompt.txt の goal を「self-heal+earn(看護師)」から「北極星=自立市民数を増やす=経済を建てる(建築家)」へ書き換える（§10 to-be を北極星に）。全 citizen 同一テンプレは [[23-anicca-loop-architecture-redesign]] §8 の「全 citizen 同一の型」と一致。

出典: Voyager(arxiv 2305.16291, auto-curriculum) / DGM / AlphaEvolve(open-ended) / a16z「検証が希少」/ Goodhart's law / North-Star Metric(growth BP)。
