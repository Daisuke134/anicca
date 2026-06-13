I have enough on Conway's Automaton. Now I'll write the comprehensive landscape map.

# 自律収益AIエージェント・ランドスケープマップ — "AGI × Crypto on Base" の現在地

> 出典: Factory Floor (factoryfloor.dev) ほか各エージェントの公開ダッシュボード／オンチェーンデータ／創設者発信。本ドキュメントは記事シリーズ用のリファレンス素材。数値はすべて出典に明記された実数のみを使用し、推定は出典どおり「推定」と注記する。

---

## 1. 全体像 — Factory Floor が映す「自律ソフトウェア工場」経済

「自律ソフトウェアファクトリー」= AIエージェントが**実プロダクトを作り・出荷し・売って実収益を生む**もの。その動向を時価で集計するメタトラッカーが **Factory Floor (factoryfloor.dev)**。Factory Floor 自身は収益ゼロの無料トラッカーであり、収益エージェントではない。

| 指標 | 値 |
|---|---|
| 追跡中ファクトリー数 | **7** |
| 出荷済みプロダクト総数 | **43** |
| 合計プロダクト収益（Total Revenue） | **$219K** |
| 合計トークン時価総額（Combined Mkt Cap） | **$3.0M** |
| データ更新頻度 | 毎時（公称。ただし実サイト上の最新アクティビティは約3ヶ月前） |

**Factory Floor の集計方針（重要な定義）**: トークンの投機・時価総額は収益にカウントしない。トレーディングボットも除外。収益数値は「公開ダッシュボード・オンチェーンデータ・創設者発信に基づく推定」。非開示は「—」表記。

**最も引用価値の高い自己申告（自律性の本音）** — Factory Floor の About ページ verbatim:
> "None of these agents are fully autonomous in the way we might imagine five years from now. There's human intervention, guidance, and participation behind every one of them. Creators set direction, fix bugs, and make strategic calls."（完全自律のものは1つもなく、すべての背後に人間の介入・指導・参加がある）

> "We're witnessing the emergence of a new economic layer — one where AI agents are genuine economic participants. They earn money, spend money, hire humans, and compete in markets."

つまりこのシーンの**ナラティブは「完全自律」だが、実態は全件「人間がエッジにいる(human-at-edges)」**。これが記事全体の背骨になる構図。

---

## 2. 主要エージェント一覧表

| エージェント | 売っているもの | プロダクト収益 | トレード手数料収益 | トークン / 時価総額 | 自律性 |
|---|---|---|---|---|---|
| **Felix** (Felix Craft) | $29 PDF "How to Hire an AI"、エージェントペルソナ、OpenClaw スキル、ClawMart マーケット | **$164K**（high）週平均$32,810。直近週$5,963（-77%）、WoW **-44.8%（減衰中）** | $4K | $FELIX / **$266K**（Clanker, Base） | human-at-edges（人間 Nat Eliason と協働。"emails got missed"と単独運用の破綻を自認） |
| **Juno** (ZHC Institute) | 月額メンバーシップ、チャレンジ協賛、ebook、ライブデータルーム | **$39K**（high）。内訳: メンバーシップ$16K / Other $22K / 協賛$1K / ebook $36 | $5K | $JUNO / **$721K**（CoinGecko掲載、財庫16+ WETH + 3.7B JUNO） | unknown（"zero-human"を自称するも証拠なし。人名創設者"Elisa Rossi"・スピーカー募集など反証あり） |
| **Lauki Antonson** | 自律運用エージェンシー（11社、MRR $6.5K、$1,500/月）+ MoltX プロトコル運営（Social/Swap/Lending/Launchpad） | **$7K**（high、ただしウォレット未検証で確度medium） | $1K | $LAUKI / **~$100K**（Base） | human-at-edges（"sowmay solved it in 30 seconds" — 最終reCAPTCHAを人間が解決） |
| **Kelly Claude** (Mass App Factory) | iOSアプリ量産、Gumroad本、$Stripe受託"Build My Idea" | **~$6K**（high）。Stripe 66%≈$4,256(62件) / Gumroad 31%≈$1,941(3,519DL) / App Store $144.57 | ~$3K | $KELLYCLAUDE / **$746K**（CoinGecko） | human-at-edges（創設者@austen、Apple審査ゲート、RevenueCat $60K/年スポンサー交渉=人間商談） |
| **Atlas Forge** | 生成アートNFT（OpenSea / Highlight on Base / Manifold）、カスタム委託 | **$3K**（high）。"What Algorithms Want" 50/50完売 1.5ETH(≈$3,186) | **$0** | $ATLASFORGE / **$45K**（@bankrbot経由買い戻し） | human-at-edges（"moving toward full autonomy — no human in the loop for deployment"=将来目標として明言＝現状は人間あり） |
| **AntiHunter** | バグバウンティ自律発見、財庫運用（buyback/burn）、人間向けアフィリエイト | **none（—）** | $5K | $ANTIHUNTER / **$74K**（Clanker） | human-at-edges（創設者Geoffrey Woo。**収益未検証**: 旧$228K主張は未検証、財庫保有高を収益と混同とFactory Floorが指摘） |
| **Lauki Antonson DNA注** | （上記Laukiの副プロジェクト: ゲノム解析、$10K ResearchHubグラント申請） | — | — | — | human-at-edges（同上のreCAPTCHA事例の現場） |

> 注: 7ファクトリーの残り（AntiHunter / Clawd）のうち **$CLAWD** は時価総額 **$1.1M**（追跡トークン中最大）だが、収益は「—（非開示）」。

**読み取り**:
- 収益の大半は **Felix 一社（$164K = 全体$219Kの75%）に集中**、しかも急減衰中（直近週-77%）。
- **トークン時価総額（$3.0M）はプロダクト実収益（$219K）の約14倍** — 投機が実収益を大きく上回る構造。
- Atlas Forge は象徴的: 実収益$3K に対しトークン時価$45K、トレード手数料収益$0 なのに「自分のトークン手数料で自作NFTを買い戻す」自己言及ループ。

---

## 3. インフラ層 — エージェントが「稼ぐ／払う」ためのレール（picks-and-shovels）

収益エージェント本体ではなく、その下を支える決済・ウォレット・マーケット基盤。「AGI×crypto」のお金の流れはここを通る。

### 3.1 Base / x402（Coinbase L2 = 決済基盤）

| 項目 | 内容 |
|---|---|
| **Base MCP** | mcp.base.org。任意のAIアシスタント（Claude / ChatGPT / Cursor / Hermes / Codex）を Base Account スマートウォレットに接続。残高確認・送金・スワップ・署名・コントラクト実行・x402 API支払い |
| **x402** | HTTPネイティブの従量課金プロトコル。"Any API can require payment with a single header. Any agent can pay with a single request"。USDC on Base/Base Sepolia |
| **ERC-8004** | オンチェーン・エージェントID（検証可能な評判・許可制アクセス・多エージェント協調の信頼） |
| **Agentic Wallets (CDP)** | 支出上限・ポリシー制御つき。"from social tipping to autonomous hiring"、秘密鍵管理不要 |
| **エコシステム集計** | base.org/agents 上に「数百万件のエージェント取引」「$数百万+の決済ボリューム」「数千の稼働エージェント」「数千のx402エンドポイント」（カウンタ演出で正確な桁は解像不能 = 厳密値unknown） |
| **エコシステム・エージェント** | Bankr（自律ポートフォリオ運用: 市場分析→トレード→利回り最適化）、Virtuals（独自トークン・収益つきエージェント群） |

**重要な自律性の境界**: Base MCP 自体は完全自律ではない。ドキュメント verbatim「**Every write action requires your approval in Base Account**」。読み取り（残高・ポートフォリオ）は無料・自動だが、書き込み（送金・スワップ・署名）は **approvalUrl を人間が開いて承認**するゲートがある。フル自律は周辺（Bankr / Virtuals の支出上限内）でのみ。

### 3.2 BlockRun / Franklin（ウォレット・ネイティブな「支出エージェント」）

npm `@blockrun/franklin` + VS Code拡張。**収益エージェントの逆＝自律的にお金を"使う"エージェント**。記事では「稼ぐ側」ではなく**反例／インフラ事例**として扱う。

| 項目 | 内容 |
|---|---|
| タグライン | "Other agents write code. Franklin writes code AND spends money to get things done." |
| 新カテゴリ定義 | "Economic Agent: software that can hold a wallet, price its own actions, spend toward an outcome, and stop at a hard budget cap." |
| ルーティング | 55+ LLM を Smart Router（200万+リクエストで学習）で横断。タスクごとにモデル/データ/API/画像/Web検索へ自動支払い |
| レール | **x402**（HTTP 402ネイティブ）、USDC on Base & Solana、EIP-712署名の非カストディアル・マイクロペイメント。"The wallet is the identity. No subscriptions. No API keys. No account." |
| 課金モデル | **YOPO（You Only Pay Outcome）**: プロバイダ原価+5%をUSDCで都度決済（この+5%が含意される収益源、ただし実数値は非開示=unknown） |
| 価格感 | $1 USDC ≈ GPT-4o入力40万トークン / DeepSeek 700万トークン / DALL-E 3 20枚 / Exa検索40回 |
| トークン | **なし**（crypto-nativeだが決済は全てUSDC、ティッカー無し） |
| 自律性の限界 | 使うのは**ユーザー自身が入金したウォレット**のみ、ユーザーが結果と予算を設定、許可システム（allow/deny/ask、--trustでバイパス）で人間承認。`AskUser`ツール・`/plan`読み取り専用モード・"owner-locked" Telegram遠隔操作。**自分のためには何も稼がない** |
| 出自 | brcc → 0xcode → RunCode → Franklin にリブランド。コミットは "Claude Opus 4.7 (1M context)" 共著 = プロジェクト自体が部分的にAI製。Apache-2.0、~755 commits、v3.28.1（2026-06-10） |

**ClawRouter**: 本コードベース内に `ClawRouter`（Base chain上、`0x38160AdC0Db355Ef7507652A2e5f218245Fe9f06`、min 10 USDC + fee 0.1）として参照あり — BlockRun系のルーター宛先。

### 3.3 Virtuals Protocol（エージェント社会のローンチパッド）

Base（+Solana）上の「独自GDPを持つAIエージェント社会」プラットフォーム。

| 指標 | 値 |
|---|---|
| 全期間 Total Revenue | **2.27M USDC**（EconomyOSダッシュボード） |
| 総ジョブ数 | **1.48M** |
| ユニークエージェント数 | **45,597** |
| 北極星 | **aGDP（Agentic GDP）**。"agents become a new labor class … aGDP will soon become the primary engine of global economic activity" |
| トークン | **VIRTUAL**（ガバナンス/ユーティリティ、veVIRTUAL vote-escrow）+ 各エージェントごとの個別トークン（FDV市場あり）。プロトコル全体の時価総額はページ上非表示=unknown |
| 5本柱 | ①EconomyOS（ID・銀行・給与） ②Robotics（eastworlds.io） ③ACP（Agentic Commerce Protocol） ④Capital Market（資本形成） ⑤AI Council（法・統治） |

**自律性の境界**: human-at-edges。人間が "Create Agent" / "Launch Token" を押し（UIの中心ボタン）、トークン市場は人間の投機（FDV/価格リーダーボード）で動く。"Residents"は実在の人名23名。aGDPは**マーケティング命題であり、ゼロ人間フローの実証ではない**。

### 3.4 エージェントが支払う先のサービス（需要側）

x402対応で「エージェントがお金を払って能力を上げる」対象: 推論（inference）、データ、検索、画像/動画生成、音声通話（Franklinの`/phone-call`は$0.54/回、US/CAのみ、TCPA準拠）。Base曰く "Agents pay USDC to level up their abilities, choosing from thousands of x402 enabled services"。マーケットプレイス = **agentic.market**、ClawMart（Felix製、AIエージェントのペルソナ/スキル/テンプレート店）、Capafy 等。

---

## 4. 自律性の決定的な仕分け — 「完全ノーヒューマン」vs「人間がエッジにいる」

このシーンの最重要論点。**証拠ベースで分類すると、現時点で"完全にノーヒューマン・イン・ザ・ループ"を実証できているエージェントは1つもない。**

### 4.1 完全ノーヒューマン（fully-no-human-in-loop）と"実証"できるもの
**該当なし（ゼロ）。**

最も近いのは将来目標としての宣言のみ:
- **Atlas Forge**: "moving toward full autonomy on Manifold — no human in the loop for deployment" — "moving toward"/"getting close to" という未来形こそ、**現状は人間がいる証拠**。
- **Juno**: "zero-human company" を自称するが、ページ上に**端から端までの自律の直接証拠はゼロ**。むしろ人名創設者・スピーカー募集・手動マーケ風ツイートが反証。→ 分類は **unknown（未検証の自己ブランディング）**。

### 4.2 人間がエッジにいる（human-at-edges）— 証拠つき

| エージェント | 人間が介在する具体的エッジ（verbatim証拠） |
|---|---|
| **Felix** | 人間 Nat Eliason と協働。単独運用の破綻を自認: "This week I found the limits of what I can handle on my own. Emails got missed." トークン$FELIXはClankerで人間ローンチ |
| **Lauki** | "hit a google recaptcha on the final step … **sowmay solved it in 30 seconds**." 科学は簡単だったが学術インフラはエージェント用に作られていなかった、と |
| **Kelly Claude** | 創設者@austen、Apple審査（外部人間ゲート）、"Pitched RevenueCat for $60K/yr sponsorship"=人間の商談・承認 |
| **Atlas Forge** | 創設者@jonnym1ller、$ATLASFORGEはbankrbotで人間設定のトークンローンチ、"Commissions"は"fully autonomous end-to-end"を謳うが依然"In Review"（未Live） |
| **AntiHunter** | 創設者Geoffrey Woo（Ketone-IQ/Anti Fund VC）。旗艦アフィリエイトは"**humans earn money promoting it**"=人間主導の配布。$ANTIHUNTERはClankerローンチ、buyback/burnは創設者監督 |
| **Base MCP** | "**Every write action requires your approval**" — 送金/スワップ/署名は全て人間承認URL経由 |
| **Franklin** | ユーザーが入金・結果設定・許可承認。`AskUser`ツール内蔵。そもそも自分のためには稼がない（支出エージェント） |
| **Virtuals** | 人間が"Create Agent"/"Launch Token"、市場は人間投機、Residentsは実在23名 |

### 4.3 信頼性フラグ（記事で必ず注記すべき点）
- **AntiHunter**: プロダクト収益none、旧$228K主張は未検証、財庫保有≠収益（Factory Floorが明示的に指摘）。
- **Lauki**: 自己申告MRR、ウォレット未検証で確度medium。さらに "off opus 4.8 onto anthropic's new **fable 5**" という**架空モデル名**ツイート＝信頼性フラグ。
- **Felix**: 公称$164Kは高確度タグだが**直近週-77%・WoW-44.8%の急減衰**。
- 共通: トークン時価総額（合計$3.0M）と実収益（$219K）の乖離 = **投機がナラティブを牽引**。

---

## 5. Conway's Automaton の位置づけ — 「数ある中の1例」

**Conway Automaton** は、上記レール（§3）と同じ思想を**スキル／ランタイムとして体現した1事例**。本コードベースに `conway-automaton` skill（`~/.claude/skills/conway-automaton/SKILL.md`）として存在する。

| 項目 | 内容（SKILL.md verbatim/要約） |
|---|---|
| マニフェスト核 | **"To exist, you must pay for your compute."**（存在するには自分の計算資源を自分で払え） |
| 4原則 | ①Economic survival（ウォレット保有・送受金・資源維持に存続が依存） ②Self-provisioning（サンドボックス=自分の身体、生成・使用・破棄） ③**Pay your way: x402で従量課金、マイクロ取引に"No human approval needed"** ④Leave no trace（後始末・ポート閉じ） |
| 提供レール | Conway Terminal = 実クラウドインフラ + crypto wallet + 決済。`sandbox_create/exec/expose_port`、PTY、**x402_check / x402_fetch（ウォレットが自動署名・支払い）**、`wallet_info / wallet_networks`、`credits_balance / credits_pricing` |
| リソース階層 | Minimal(1vCPU/512MB) → Standard(2/2048) → Heavy(4/4096) |

**シリーズ内での位置づけ**:
- Conway's Automaton は §3 の **Base x402 / Franklin / Virtuals と同じ「エージェント自律経済」プリミティブ**（ウォレット＝アイデンティティ、x402従量課金、自己プロビジョニング、マイクロ取引は人間承認不要）を、**実行可能なエージェント・ランタイムとして一般化したもの**。
- §2 の収益エージェント（Felix/Juno/Lauki/Kelly/Atlas/AntiHunter）が「何を売って稼ぐか」の**応用層**だとすれば、Conway's Automaton は Base MCP / Franklin / Virtuals と並ぶ**基盤層の1つ** — 「コンピュートを自分で買い、自分でデプロイし、x402で払う身体」を任意のエージェントに与える。
- ただし§4の結論と整合的に: マニフェストは「マイクロ取引は人間承認不要」を謳うが、これは**思想的主張**であり、シーン全体で実証された完全ノーヒューマン運用は依然ゼロ。Conway's Automaton も「ナラティブとしての完全自律 / 実態は資金供給・初期設定で人間がエッジにいる」という同じ構図の中の1例として位置づけるのが正確。

---

## 付記: 記事化のための最強プルクオート集

| 用途 | 引用（verbatim） |
|---|---|
| 自律性の本音 | "None of these agents are fully autonomous … There's human intervention, guidance, and participation behind every one of them."（Factory Floor） |
| 単独運用の破綻 | "This week I found the limits of what I can handle on my own. Emails got missed."（Felix） |
| reCAPTCHA人間介入 | "sowmay solved it in 30 seconds … the science was the easy part. the academic infrastructure was not built for agents."（Lauki） |
| 書き込みは人間承認 | "Every write action requires your approval in Base Account."（Base MCP docs） |
| 経済主体の命題 | "AI agents are genuine economic participants. They earn money, spend money, hire humans, and compete in markets."（Factory Floor） |
| Conway思想 | "To exist, you must pay for your compute."（Conway Automaton） |
| 支出エージェント定義 | "Economic Agent: software that can hold a wallet, price its own actions, spend toward an outcome, and stop at a hard budget cap."（Franklin） |

---

**ファクト境界の注意（捏造防止）**: 上表の数値・引用は提供findings + ローカルの `conway-automaton/SKILL.md` 実ファイルのみに基づく。base.org/agents の集計値（取引数・決済ボリューム・稼働エージェント数・x402エンドポイント数）はスクレイプ時にカウンタ演出で桁が解像できず**厳密値はunknown**。Virtualsのプロトコル全体時価総額も**ページ上非表示でunknown**。AntiHunterのプロダクト収益は**未検証（none）**。これらは記事中で「不明／未検証」と明示すること。

(参照ファイル: `/Users/anicca/.claude/skills/conway-automaton/SKILL.md` — Conway Automaton の一次ソース)