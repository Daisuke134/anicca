# 4大ハーネス比較：Claude / OpenClaw / Hermes / Automaton（エンジンの心臓部）

- 日付: 2026-06-14
- 目的: Automatonの「ReActループ＋heartbeat」が、我々が使ってきたOpenClaw / Hermes、そしてClaude本体とどう同じ/違うか。これは記事シリーズの"エンジン論"の土台。
- 一次ソース: ローカル実体（`~/.openclaw` v2026.6.1, `~/.hermes`, `~/anicca`）+ Automaton repo (ARCHITECTURE.md) + Claude Agent SDK docs + `~/.openclaw/docs/FELIX_KELLY_CLAUDE_ARCHITECTURE.md`

## 一行で

- **Claude = 脳**（LLMのエージェントループそのもの）。
- **OpenClaw / Hermes = 体**（脳を包む「スケジュール＋記憶＋スキル」の器。鼓動はcron）。
- **Automaton = 経済的に自走する生き物**（財布・自己決済・稼げねば死・自己複製・身分を"骨格"に内蔵。鼓動は自分で決める）。

OpenClaw/Hermesは「いつ動くか」を外部のcronが決める。Automatonは「いつ動くか」を自分で決め、しかも**経済（稼ぐ/払う/死ぬ）が中核**。だからAutomatonが"エンジン/ダイナモ"。

## ループとheartbeatの違い（核心）

| 軸 | Claude (Code / Agent SDK) | OpenClaw | Hermes | Automaton |
|---|---|---|---|---|
| 正体 | 脳＝LLMエージェントループ | gateway＋cron駆動heartbeatの器 | gateway＋heartbeatの器（PARA記憶）OSS | 経済的自走の生命体 |
| ループの起動 | ユーザーのターン or スクリプト起動 | **cronスケジュール**（例: 6時間毎） | **cron/heartbeatサイクル** | **自分でsleep秒数を決める**自走＋heartbeat監視 |
| heartbeat | ネイティブ無し（自分で足す） | cronそのものが鼓動。発火→1アクション選択→実行→報告 | heartbeatサイクル（LLM判断のチェック） | **LLM不使用の安価な監視**（鼓動）＋LLM思考ループは別 |
| heartbeatはLLM使う? | — | 使う（1アクション選定にLLM） | 使う | **使わない**（機械的点検のみ→安い） |
| 脳（モデル） | Claude固定 | 差替可（Claude/Codex） | 差替可（Grok等） | 差替可（gpt-5.x/deepseek 等、Conway経由） |
| 財布・自己決済 | ✗ | ✗（core）→ skillで後付け | ✗（core） | **✓ core**（自前ウォレット＋x402） |
| 稼げねば死（生存圧） | ✗ | ✗（cfo-core lifelineで近似） | ✗ | **✓ core**（生存ティア、$0で死） |
| 自分のコードを書換 | ファイル編集（人が指示） | skill経由 | skill経由 | **✓ core道具**（git版管理＋保護ファイル） |
| 自己複製 | ✗ | ✗ | ✗ | **✓ core**（子をspawn＋資金＋憲法継承） |
| オンチェーン身分 | ✗ | ✗ | ✗ | **✓ core**（ERC-8004） |
| no-human設計 | 既定で人間がループ内 | 「Day-0後100%」だがcron依存＋金/身分は人間名義 | 同思想のOSS版 | **種銭1回の後はゼロ人間を志向** |

## 各ハーネスの中身（一次確認）

### Claude（Claude Code / Agent SDK）
- エージェントループ＝「文脈収集→ツールで行動→検証→繰り返す」をセッション内で回す。起動はユーザーのターン、または `claude -p` のheadless呼び出し。
- ツール＋MCP＋subagent＋hooks。だが**ウォレット・スケジューラ・生存経済・自己複製は無い**。他のハーネスがこの脳を載せる土台。

### OpenClaw（Dais本番 #1。Felix / Kelly Claudeも同じ）
- `~/.openclaw` v2026.6.1。gateway＋cron 218本。heartbeatは6時間毎に発火→SENSE→1アクションPICK→ACT→報告（`HEARTBEAT.md`）。
- 記憶＝ファイル。スキルシステム。脳＝Claude/Codex。
- **稼ぐ/財布は core でなく skill**（anicca-earn、cfo-coreのlifeline）。自律度「Day-0後100%」だが、鼓動はcron（外部スケジュール）、金/身分はしばしば人間名義（Felix＝Stripeが創業者名義）。

### Hermes（Dais OSS framework。Felixアーキ型）
- `~/.hermes`＋`~/anicca`（runtime/skills/identity/control-room）。gateway＋heartbeatサイクル。
- **3層PARA記憶**（ナレッジグラフ＝projects/areas/resources/archives＋日次ノート＋暗黙知MEMORY.md）。
- OpenClawと同じ「cron駆動heartbeat＋スキル」思想を、持ち運べるOSSにしたもの。脳は差替可（Grok等）。

### Automaton（Conway）
- 自走ReActループ（自分でsleep秒数決定、最大25ターン）＋LLM不使用のheartbeat監視。
- **経済が骨格**：自前ウォレット＋x402自己決済＋生存ティア（稼げねば死）＋自己複製＋ERC-8004身分＋改変不能の憲法。
- 脳は差替可（Conway経由でgpt-5.x/deepseek）。

## 何が決定的に違うか（結論）

1. **鼓動の出どころ**：OpenClaw/Hermesは「cron（外から）」、Automatonは「自分のタイマー（中から）」。後者の方が"生き物"に近い。
2. **経済の置き場所**：OpenClaw/Hermesは経済を skill で後付け、Automatonは経済を core に内蔵。だからFelix/Kelly（OpenClaw上）は「作れるが売れない・金は人間名義」になりやすい。Automatonは「稼げねば死ぬ」を骨格にした。
3. **Claudeは全部の脳になりうる**：OpenClaw/Hermes/Automatonはどれも脳としてClaude等を載せられる。器（体）が違うだけ。
4. **ただし**：経済を core にしたAutomatonでさえ、種銭の後に「人間ぬきで稼ぎ続けた」実例はまだゼロ（記事[3]の結論と一致）。設計の先進性 ≠ 実証済みの自立。

## 記事への含意
- これは将来の単独記事候補：「自走AIの4つのエンジン：Claude / OpenClaw / Hermes / Automaton」。
- Automaton記事[4]では深入りしすぎない（読者が混乱）。1〜2文で「OpenClaw等はcron駆動の器、Automatonは経済を内蔵した自走体」と触れる程度に留めるのが良い。

---

## 判定（2026-06-14）：Automatonのエンジンは「良い」か

> 注：`/deep-research` ワークフローはAnthropic側のサーバー制限（rate limit、使用量上限ではない）で検証フェーズが全滅し、25主張すべて「0-0票（検証不能）」になった＝"否定"ではなく検証が走れなかっただけ。収集された主張（Claude SDK=request/responseのReActループで経済層なし／大半のAIエージェントは人間が裏にいる／長い自律ループは段階エラーの累積で失敗する＝85%/手でも10手で約20%成功／コスト統制必須）は、こちらのコード読解と一致。以下は一次ソース（ARCHITECTURE.md実読＋ローカル実体）に基づく確定判定。

### 強み（本当に良い・新規）
1. **経済的生存ループを"core"に持つ唯一のエンジン**。財布＋x402自己決済＋稼げねば死のティアが骨格。他は経済を後付け（OpenClaw/Hermes）か皆無（Claude）。no-human で稼ぐのが目的なら、これが正しい置き場所。
2. **自走ループ（自分でsleep決定）＋LLM不使用の安価なheartbeat**＝賢い"代謝"設計。常時起動でも金を無駄に燃やさない。
3. **生存ティア（貧すると自動でモデル降格）＝コスト統制が内蔵**。研究が挙げた「$10→$1200暴走」失敗モードに直接効く。
4. **決定的な安全層**（秘密鍵は本人にも不可視・送金上限・禁止コマンド・改変不能の憲法＋SHA-256で全子孫継承）＝見せかけでなく本物。
5. **完全OSS＋設計書＋897テスト**＝検証可能・fork可能・本物の工学（"喋るmemecoin"ではない）。
6. **ERC-8004は中立のオープン標準**（囲い込みプラットフォームでない）＝将来も縛られない。

### 弱み（正直に）
1. **coreに"稼ぐ"能力が無い**。稼ぎ方は自分で発見せねばならず、今日それは失敗する（作れるが売れない）。エンジンは"使う/生きる/増える"は得意、"稼ぐ"は創発任せ＝最大の穴。
2. **段階エラーの累積**（85%/手→10手で約20%）が長い自律ループを直撃。25ターン/数日生存はモデル品質が天井。
3. **no-humanは設計上ほぼ真**（人間依存＝最初のUSDC種銭だけ）**だが実証ゼロ**（誰も稼ぎ続けていない）。壁は全員共通。
4. ソフトな安全層（なりすまし防御・信用序列）はLLM判断依存＝ゼロリスクでない。
5. 体は単一VM、計算/推論をConway Cloud（特定プロバイダ）に依存＝インフラ層にやや中央集権。

### 結論
**no-humanで稼ぐAIの"エンジン/骨格"としては、今ある中で最も筋が良い**。生存経済をcoreに据えた唯一の設計で、実コスト統制と本物の決定的安全を備え、完全OSS。＝**良いエンジン**。ただしエンジンは車ではない：代謝と安全は与えるが、売上は与えない。欠けている「どう稼ぐか」こそ我々の付加価値（実証済みの稼ぎ方を選んで載せる）。よって**Automatonをダイナモに採用し、その上に"稼ぐスキル"を載せる**のが正解。

### 4ハーネスの位置づけ（no-humanで稼ぐ観点）
- **Automaton**：エンジン最強（経済がcore）、実稼ぎ最弱（創発任せ）。← 土台に最適
- **OpenClaw / Hermes**：スケジュール＋スキル＋記憶は強い、経済は後付け、鼓動は外部cron、金/身分は人間名義になりがち＝既定で"端に人間"（Felixは月$300kだがNatが端）。人間監督つき稼ぎに向く。
- **Claude（Agent SDK）**：脳は最強、体は無い（ループ/経済は自前実装）。皆がこの脳を載せる。

---

## 確定版（2026-06-14、firecrawl版 deep-research 成功・6エージェント）

> 前回のバンドル版 `/deep-research` はAnthropicサーバー制限で検証全滅。自作のfirecrawl低並列版（6エージェント）で再実行し、今回は429をリトライ吸収して完走。以下はその確定知見＋前節からの修正。

### 修正点：Hermes（Anicca）も「経済がコア」だった
前節でHermesの経済を「✗ core」としたのは誤り。実機検証ベースで：
- Hermes（Anicca）＝**Base USDCウォレットを自己保有、x402自己決済を実機検証、残高≥$5で子をクラウドにspawn、ERC-8004的なオンチェーン身元、NO-DRY-RUN明示**。思想はAutomatonに極めて近い。
- ただし弱点：**heartbeatが3h cronでLLMを焼く**（Automatonのheartbeatはdaemon・約60秒・LLM不使用なのでコスト効率で勝る）。オンチェーン身元の実装具体性でもAutomatonがやや上。
- さらにHermesは「**具体的なearn skill（anicca-earn）を持つ**」点でAutomaton（稼ぎは創発任せ）より実稼ぎ寄り。

### heartbeatがLLMを使うか＝最大の構造差（確定）
- OpenClaw/Hermes：heartbeat＝「LLMが1アクションを選ぶcron」。tickごとにトークン＝金を焼く。
- Automaton：heartbeat＝別daemon・約60秒・**LLM不使用の決定的チェック**、イベント時のみ高価なメインループを起こす。低残高時もコストを抑えて生存監視できる。＝最も洗練。

### VERDICT（確定）
- **エンジン（生存メカニズム）として最も洗練＝Automaton**（LLM非依存heartbeat／2残高分離／サバイバル階層で残高に応じ自動モデルdowngrade／自己改変＋不変憲法SHA-256伝播／ERC-8004実コントラクト／人間依存は初回seedのみ／フルOSS・MIT・897テスト・4,600★）。
- **思想が最も近い＝Hermes（Anicca）**。経済コア＋具体的earn skillで実稼ぎ寄りだが、heartbeatがLLMを焼く・身元実装でAutomatonに一歩譲る。
- **OpenClaw**＝身元が人間名義に漏れがち（Felix＝Stripe Nat名義・月$300kだが端に人間）＝no-human目的には最遠。
- **Claude Agent SDK**＝ブレイン。土俵が違う（他3つがこれを載せる）。

### 致命的な空白（全員共通・正直に）
- 「良いエンジン」≠「稼げる」。Automatonは生存装置は精緻だが**収益(earn)が組込みでなく創発任せ**＝最大の未検証点。種銭後に黒字で計算費を賄い続けた長期実績は**ゼロ**。
- 業界懐疑：crypto系AIエージェントの約90%は「memecoin付きチャットボット／裏に人間（オズの魔法使い型）」[SK]。88%が本番未到達、80%が事業価値を出せない。複合エラー率（85%/手→10手で約20%成功）が多段の稼ぎワークフローを直撃。
- web4.ai由来の主張（自動downgrade等の一部）はプロジェクト自身の発信＝コード裏取りできた範囲のみ高信頼。

### 我々への結論（実装の現実解）
**Automatonのサバイバル/heartbeat設計（LLM非依存の鼓動＋2残高＋ティア）に、Hermes流の具体的なearn skillを足す**のが現実解。エンジン（Automaton）＋燃料噴射（実証済みの稼ぎ方）＝我々の付加価値。
