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
