# 44 — 床を「効きを落とさず」削る best practice（公式+コミュニティ実測、2026-07-13）

doc 43 = 恒久ルール（予算・強制）。**本書 = そのルールの根拠と、削り方の型**。目的は「削る」ではなく「同じ効きを、より少ない床で出す」。重要な指示を消して性能が落ちたら失敗。

## 1. 公式が言っていること（引用付き）

### 1-1. CLAUDE.md サイズ
- **`docs.anthropic.com/en/docs/claude-code/memory`**: "Size: target under 200 lines per CLAUDE.md file. Longer files consume more context and reduce adherence." / "CLAUDE.md files are loaded in full regardless of length, though shorter files produce better adherence."
- 同ページ、MEMORY.md（auto memory）は別ルール: "the first 200 lines of MEMORY.md, or the first 25KB, whichever comes first, are loaded at the start of every conversation. Content beyond that threshold is not loaded."
- **`@import` は床を減らさない（公式で明言）**: "Splitting content into imports for organization... imported files still load and enter the context window at launch." / FAQ: "Splitting into @path imports helps organization but does not reduce context, since imported files load at launch."
- **削る基準（Anthropic engineering, `anthropic.com/engineering/claude-code-best-practices`）**: "Keep it concise. For each line, ask: 'Would removing this cause Claude to make mistakes?' If not, cut it. **Bloated CLAUDE.md files cause Claude to ignore your actual instructions!**"
  同記事の Include/Exclude 表:
  - ✅ 含める: Bash commands Claude can't guess / Code style rules that differ from defaults / Testing instructions and preferred test runners / Repository etiquette / Architectural decisions specific to your project / Developer environment quirks / Common gotchas or non-obvious behaviors
  - ❌ 除く: Anything Claude can figure out by reading code / Standard language conventions Claude already knows / Detailed API documentation (link instead) / Information that changes frequently / Long explanations or tutorials / File-by-file descriptions of the codebase / Self-evident practices like "write clean code"
  - 診断: "If Claude keeps doing something you don't want despite having a rule against it, **the file is probably too long and the rule is getting lost.**"

### 1-2. Skills の progressive disclosure（`docs.anthropic.com/en/docs/agents-and-tools/agent-skills/best-practices`）
- 3層構造: "At startup, only the **metadata (name and description)** from all Skills is pre-loaded. Claude reads SKILL.md only when the Skill becomes relevant, and reads additional files only as needed."
- description の書き方: "The description field enables Skill discovery and should include both what the Skill does and when to use it. **Always write in third person.**" 例: `description: Extract text and tables from PDF files, fill forms, ...` — 悪い例: `description: Helps with documents` / `description: Processes data`
- 本文の削り方: "**Default assumption: Claude is already very smart.** Only add context Claude doesn't already have. Challenge each piece of information: 'Does Claude really need this explanation?' 'Does this paragraph justify its token cost?'" — 良い例(~50 tok) vs 悪い例(~150 tok、同じ内容を冗長に説明)を並べて具体的に示している。
- サイズ上限: "Keep SKILL.md body under 500 lines for optimal performance. Split content into separate files when approaching this limit."
- **Examples はどこに置くか**: "Examples help Claude understand the desired style and level of detail **more clearly than descriptions alone**." → example/workflow は本文（on-demand）に置く。description には trigger 条件だけ。

### 1-3. Subagent description（`docs.anthropic.com/en/docs/claude-code/sub-agents`）
- frontmatter で必須なのは `name` と `description` のみ。"Claude uses each subagent's description to decide when to delegate tasks." "description: Yes — **When Claude should delegate to this subagent**"
- **example を description に書けという明文の推奨は見つからなかった**（証拠なし）。公式サンプルの description はいずれも1〜2文の trigger 条件のみ（例: `"Reviews code for quality and best practices"` / `"Debugging specialist for errors and test failures."`）。長い example やペルソナは system prompt（本文）側にある。
- コスト誘導: "Control costs by routing tasks to faster, cheaper models like Haiku."

### 1-4. MCP tool 数と deferred loading（`docs.anthropic.com/en/docs/claude-code/mcp`）
- **Tool search（既定 ON）**: "Tool search keeps MCP context usage low by **deferring tool definitions until Claude needs them**. Only tool names and server instructions load at session start, so adding more MCP servers has minimal impact on your context window."
- 挙動: "MCP tools are deferred rather than loaded into context upfront, and Claude uses a search tool to discover relevant ones when a task needs them."（＝我々の「deferred tool 名 559 tok」はこの仕組みそのもの。tool 名だけ載って schema は載らない）
- server instructions（＝我々の「MCP instructions 674+」）: "Add clear, descriptive server instructions... keep them **concise to avoid truncation, and put critical details near the start.**"
- 閾値モード: `ENABLE_TOOL_SEARCH=auto` で「10%窓に収まるなら前もってロード、溢れたら deferred」に変更可能。既定(unset)は全て deferred。

### 1-5. Effective context engineering for AI agents（`anthropic.com/engineering/effective-context-engineering-for-ai-agents`）
- 核心原則: "good context engineering means finding the **smallest possible set of high-signal tokens** that maximize the likelihood of some desired outcome."
- "right altitude"（ちょうど良い抽象度）: 両極端を避ける — ①複雑で脆いロジックをハードコードする失敗、②曖昧すぎて具体性のない指示しか与えない失敗。
- **minimal ≠ short**: "Note that minimal does not necessarily mean short; you still need to give the agent sufficient information up front to ensure it adheres to the desired behavior."（＝床を削る＝内容を薄めることではない。ノイズを削ること）
- Just-in-time retrieval: 事前に全データを詰め込むのではなく、file path / query / link のような軽量な識別子を持たせ、実行時に tool でロードさせる。Claude Code 自身がこの方式（Bash + grep/glob でファイルを都度参照）。
- Examples: "curate a set of **diverse, canonical examples** that effectively portray the expected behavior... examples are the 'pictures' worth a thousand words" — 大量の edge-case を列挙するのではなく、少数の代表例。

### 1-6. Writing effective tools for agents（`anthropic.com/engineering/writing-tools-for-agents`）
- ツール統合の効果: "consolidating scattered API calls into a single tool ... reduces an agent's overall risk of making mistakes" — 個別ツール description を積み上げるより、少数の高レベルツールに集約する方が床が減り精度も上がる。
- 実例: Claude web search で「クエリに2025を付け足す」誤挙動を **tool description の改善だけで**修正できた——description の文言が呼び出し精度に直結する実測例。
- 返り値も削る対象: "tool implementations should take care to **return only high signal information** back to agents."

## 2. コミュニティの型（repo名 + star + 核心）

| repo | star | 核心 |
|---|---|---|
| `hesreallyhim/awesome-claude-code` | 49,895 | キュレーション集。"Writing a Good CLAUDE.md" (HumanLayer) を "instruction-budget reasoning, progressive disclosure, and the test of whether Claude would err without a given line" と要約して掲載。 |
| `humanlayer.dev/blog/writing-a-good-claude-md`（HumanLayer） | — | "general consensus is that **< 300 lines is best, and shorter is even better**. At HumanLayer, our root CLAUDE.md file is **less than sixty lines**." / "CLAUDE.md is **the highest leverage point of the harness** — so avoid auto-generating it." / Progressive Disclosure = 詳細は別ファイルに逃し、self-descriptive な名前で参照だけ残す。 |
| `multica-ai/andrej-karpathy-skills` | 191,344 | 「1ファイル・4原則」型の極small CLAUDE.md（Think Before Coding / Simplicity First / Surgical Changes / Goal-Driven Execution）。**内容を削るのでなく高signal密度に絞る**実例として有効（星数はKarpathy起点でバイラルになったもの、確認済み）。 |
| `chroma-core/context-rot`（Chroma技術レポート） | 283 | "Context Rot: How Increasing Input Tokens Impacts LLM Performance" — **単純タスクでも入力トークンが増えるほど性能が劣化する**ことを実測。関係ない/冗長なトークンは中立ではなく実害という一次証拠。ベンチマークコードとデータセット付き。 |
| `ccusage/ccusage` | 17,105 | Claude Code のトークン使用量/コストを可視化する定番CLI（`npx ccusage`）。床の実測に使われる標準ツールの一つ（我々の `~/.claude/scripts/floor-guard.py` と同系統の思想）。 |
| `agent-sh/agnix` | 341 | CLAUDE.md/AGENTS.md/SKILL.md/hooks/MCP設定の**linter+LSP**。autofix付き。「太った instruction file」を機械的に検知する型（doc 43 の `floor-guard.py` と同じ発想を汎用ツール化したもの）。 |

補足: `Zandereins/schliff`（7 star）は instruction file の8軸品質スコアラーだが極小コミュニティのため参考程度。「instruction を減らしても性能が落ちない」ことを直接実証したベンチマーク記事は Chroma の context-rot 以外に確認できなかった（他は全て「経験則・consensus」の記述で、対照実験を伴う定量データではない）。

## 3. 我々への適用（実測 45,030 tok の内訳ごとに、書き換え方を具体的に）

| 内訳 | 現状 | 型 | 具体的な書き換え |
|---|---|---|---|
| 我々の markdown（CLAUDE.md+MEMORY.md+rules）10,278 tok | 3ファイルとも200行規律は守っている（global CLAUDE.md ~200行未満、project CLAUDE.md ~110行） | §1-1 Include/Exclude表 + "Would removing this cause mistakes?" | 各行を Include/Exclude 表に当てて再監査: 「〜すべき」的な一般論（Self-evident practices）が紛れていないか確認。特に project CLAUDE.md の「概要」節（Anicca説明）はClaude Codeがコード読めば分かる情報＝Exclude候補。`@import` で束ねている箇所があれば「整理にはなるが床は減らない」と自覚し、import ではなく rules(`paths:`) に格下げできないか毎回確認する。 |
| skill description ×76 = 5,433 tok | 全skillのdescriptionが常時ロード | §1-2「良い例50 tok / 悪い例150 tok」パターン + 3人称ルール | 各 description を「what + when」の1文に圧縮しているか棚卸し。頻度が低い/自分専用のskill（vcsdd系サブコマンド、caveman系等）は `disable-model-invocation: true` にして `/name` 起動専用にする（doc43 §3の表と同じ結論だが、根拠は公式の「metadataのみ常駐」原則）。description に長い実行例を書いている物があれば本文へ退避（Examples は本文で"more clearly than descriptions alone"効く、descriptionに置く意味がない）。 |
| agent 定義 ×35 = 4,919 tok | 全agentのdescriptionが常時ロード | §1-3 公式サンプルは1〜2文 | 各 `.claude/agents/*.md` の description を公式サンプル粒度（`"Reviews code for quality and best practices"`級）に揃え、長い `<example>` ブロック（現状 code-quality-reviewer 等が持つ）は本文の system prompt 側に移すか、そもそも公式に「description に example 推奨」の根拠が無いため、稀にしか呼ばれないagentは description を削るのでなく**統合**する（似た用途のagentをまとめて1つの高レベルagentにする＝§1-6の「ツール統合」原則をagentにも適用）。 |
| MCP instructions 674+ | server instructions が起動時ロード | §1-4「concise、critical detailsを先頭に」 | 使っている各MCP（serena, codegraph等）のserver instructionsが冒頭で要点を言っているか確認。自作/設定可能なMCPなら先頭1文を「いつ使うか」に絞り、詳細説明を後段に回す（先頭が切り詰められても意味が壊れないように）。 |
| deferred tool 名 559 tok | tool search が既定ONで既に最小化済み | §1-4 | これは既に「型通り」（tool search 有効＝schemaはdeferred、名前だけ）。追加でできるのは**未使用MCP serverを`/mcp`で切る**ことだけ（doc43 §3-6と同じ）。`ENABLE_TOOL_SEARCH=auto`系への変更は不要（既定のほうが厳格に deferred）。 |
| SessionStart hook 591 tok | floor-guard.py等の出力がhookとして毎回注入 | §1-5「smallest set of high-signal tokens」 | hookの出力メッセージ自体を「異常時のみ詳細、正常時は1行」に分岐させる（毎回フル内訳を出す必要はない。閾値超過時だけ詳細を出す設計に変更）。 |
| builtin tool description 6,033 tok | Claude Code本体、触れない | — | 対象外。ここを削る代わりに、上位項目を削って予算内に収める。 |
| 残り ~16,500 tok | Claude Code本体 | — | 対象外。 |

## 4. 効きを落とすリスクがある操作（やってはいけない削り方）

1. **`@import` で「整理した気になる」**: 公式明言 "imported files still load... does not reduce context"。ファイルを分割しても読み込む限り床は不変。削減目的でimportを使うのは無意味（整理目的なら可）。
2. **CLAUDE.mdの行数だけ削って、Bash commands Claude can't guess のような本当に必要な行まで消す**: 公式Include表にある項目（差分のあるcode styleルール、testランナー、repository etiquette）を消すと"Claude ignores your actual instructions"どころか、逆に毎回誤った推測をしてやり直しコストが増える。行数削減がKPIになってはいけない——"Would removing this cause mistakes?"がKPI。
3. **skill descriptionを「1行」にする際、trigger条件そのものを曖昧にする**: 公式は明確に悪い例として`"Helps with documents"``"Processes data"`を挙げている。短さのために具体語(key terms)を削ると、そのskillが呼ばれなくなる（=無言の機能喪失、気づきにくい）。
4. **agent definitionのdescriptionを一律1文に切り詰めて、複数agentの用途が重複・曖昧になる**: 公式subagentサンプルは短いが「1subagent=1明確な責務」を保っている。複数agentのdescriptionが似た文言になると、Claudeがどちらに委譲すべきか迷い、誤委譲や無委譲（メインスレッドで処理して床を余計に食う）が起きうる。この劣化は定量ベンチマークが見つからなかったため「証拠なし・リスクとして記載するに留める」。
5. **minimal を short と混同する**（§1-5で公式が明示的に警告）: 内容を薄めて短くすると、モデルは前提知識で埋めようとして誤った仮定をする（Karpathyの指摘そのもの）。正しい削減は「高signalなトークンだけ残す」であって「情報量を減らす」ではない。
6. **MCP server instructionsを削りすぎて、後半にあった重要事項が切り詰められて消える**: 公式は「concise, and put critical details near the start」——短くする代わりに**順序**を変えるのが正しい操作。単純truncateされる前提で書く。
7. **未使用MCPを切らずに、toolのdescriptionだけ削って誤魔化す**: tool search は既に効率化済みなので、真に効くのは「使わないserverを`/mcp`で切る」こと。個々のtool descriptionを削っても呼び出し判断精度が落ちるだけで、床の主要因（サーバー数）は減らない。

## 5. まとめ（15行要約は会話側に記載）

- 一次ソース: `docs.anthropic.com/en/docs/claude-code/memory`, `.../skills`, `.../sub-agents`, `.../mcp`, `docs.anthropic.com/en/docs/agents-and-tools/agent-skills/best-practices`, `anthropic.com/engineering/claude-code-best-practices`, `anthropic.com/engineering/effective-context-engineering-for-ai-agents`, `anthropic.com/engineering/writing-tools-for-agents`。
- コミュニティ: `github.com/hesreallyhim/awesome-claude-code`(49.9k★)、`humanlayer.dev/blog/writing-a-good-claude-md`、`github.com/multica-ai/andrej-karpathy-skills`(191k★)、`github.com/chroma-core/context-rot`(283★)、`github.com/ccusage/ccusage`(17.1k★)、`github.com/agent-sh/agnix`(341★)。
