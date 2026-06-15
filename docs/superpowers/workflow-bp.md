# Workflow BP — Dynamic Workflows in Claude Code(6 patterns / 14 steps)

出典: movez.substack.com「How to master Dynamic Workflows in Claude Code」(Anthropic engineers が実際に使う 6 patterns + 14 steps)。Dynamic Workflows = 2026-05-28 Claude Code に出荷。
★ 用途: Anicca の全実装をこの BP に沿って Workflow で回し、タスクを取りこぼさない。本ファイルは future reference の正典。★

## Part 1 — Mental Model

### 01. Workflow = Claude が書く harness
デフォルト harness は「plan と execute を同一 context」。long-running / parallel / adversarial では破綻。Dynamic Workflow = Claude が**そのタスク専用の harness を JS で自動生成** = subagent を spawn/協調する特殊関数 + 標準 JS(Math/JSON/Array)。デフォルトに無い3つ:
- **Per-agent isolation**: 各 subagent が独立 context、1ゴールに集中、相互汚染なし。
- **Per-agent model choice**: 各 subagent のモデルを選べる(Opus=難推論 / Haiku=安い探索 / Sonnet=中間)。
- **Per-agent isolation level**: worktree(隔離 git checkout)or remote(checkout 無)。
起動 = 「make a workflow that…」or trigger word **ultracode**。中断しても resume で再開。

### 02. Workflow が構造的に潰す3つの失敗モード
- **Agentic laziness**: 複雑な多部分タスクを途中で「done」宣言(50項目中20で「あとは handled」)。
- **Self-preferential bias**: 自分の出力を自分で検証/採点すると贔屓する。利害ある検証者は公正になれない。
- **Goal drift**: 多ターン+compaction で元目標から徐々にズレる。「Don't do X」が turn 47 で消える。
→ Workflow は「別 Claude・独立 context・集中ゴール・隔離 state」で3つを構造的に解決。

### 03. Static vs Dynamic
- Static(Agent SDK / `claude -p`): 汎用・全 edge case 用に1回書く・保守的。
- Dynamic: **このタスク専用**に Claude が書く。あなたの code を読み、各機能を実 docs に照合し、あなたの取引量で price し、自分の答えに「なぜ移行すべきでないか」adversarial pass をかける。static には不可。

### 04. Core API: `agent()` / `parallel()` / `pipeline()`
- `agent(prompt, {model, schema, isolation})` → subagent を1体。schema 指定で構造化出力。
- `parallel(thunks[])` = **barrier**: 全部 fan-out → 全完了を待って返す。「全結果が揃わないと次に進めない」時。
- `pipeline(items, stage1, stage2…)` = **streaming**: 各 item が全 stage を独立に流れる(barrier なし)。「次に全結果が要らない」時(安い・速い)。
- ★ 選択基準: 次の一手に全結果が要る? → Yes=parallel / No=pipeline ★

## Part 2 — 6 Patterns

### 05. Classify-and-act(やる前にルーティング)
classifier agent がタスク種別を判定 → 種別ごとに別 agent/挙動へ routing。安いモデルで分類 → 複雑な所だけ Opus。例: 「auth module を説明」→ classifier が codebase 読んで複雑度推定 → 10ファイル=Sonnet / 100ファイル=Opus。

### 06. Fan-out-and-synthesize(多数の小ステップ→1つに統合)
タスクを多数の小 step に分割 → 各 step を parallel agent → synthesize(barrier、全 fan-out を待って merge)。「一度に多すぎ」失敗を解決。各 subagent は自分の piece だけ見る。列挙可能な work item(50ファイル/200 endpoint)・各 item 独立・最後に1つの統合答え、が条件。
```js
const reviews = await parallel(files.map(f => () =>
  agent(`Review ${f} for security`, {model:"haiku", schema:IssueList})))
const report = await agent(`Merge into one prioritized report:\n${JSON.stringify(reviews)}`, {model:"opus"})
```

### 07. Adversarial verification(self-preferential bias の構造的修正)
各 spawned agent の出力を、**別の** spawned agent が rubric に対し敵対的に検証。検証者は元 work を見ていない=贔屓不能。claim-checking / code review(author≠reviewer)/ quality gate。★pairing rule: 検証者は rubric と artifact だけ知る、誰が作ったかは知らせない★。

### 08. Generate-and-filter(遅くコミット)
N 個アイデア生成 → rubric/検証で filter + dedupe → 最高品質だけ返す。命名30個→陳腐/商標衝突を殺して3個。「best answer を聞く」=早期コミット。generate-and-filter=全選択肢を challenge した後に late commit。

### 09. Tournament(絶対採点より pairwise 比較)
N agent が同タスクを別アプローチで → pairwise 比較で勝者決定。1000件を1 prompt で sort は品質劣化+context 溢れ。bracket を fresh agent に分割、各比較は2つだけ。bracket は決定的ループ code に置く(context でない)。taste 系(デザイン/候補選別/優先順位)に最適。

### 10. Loop until done(未知量の仕事)
停止条件(新発見なし/log にエラーなし/理論検証済)まで agent を spawn し続ける。固定回数でない。flaky test debug / bug hunt(0件になるまで)/ pattern mining。`/goal`(hard 完了条件「1理論が通るまで止まるな」)+ `/loop`(workflow 自体を定期実行)と組む。

### 11. Compose(実用途は 2-4 patterns の合成)
| 用途 | 合成 |
|---|---|
| Migration/refactor | fan-out(callsite毎 worktree)→ adversarial verify(別 agent review)→ loop until done(Bun の Zig→Rust 移植がこれ) |
| Deep research | fan-out(並列 web 検索)→ adversarial verify(各 claim 独立検証)→ synthesize(引用付き report) |
| Draft 検証 | claim 抽出(1 agent)→ fan-out(claim 毎 verifier、source 照合)→ meta-verifier(source 品質確認) |
| 1000+件 sort | tournament(pairwise、絶対採点禁止) |
| rule 遵守 | rule 毎 verifier(fan-out)→ skeptic が rule 自体を review(false positive 回避) |
| Root-cause | 分離 evidence から理論生成(別 agent が log/file/data)→ 理論毎に verifier+refuter panel → loop until 1つ survive |
| Triage at scale | classify-and-act → 既存 ticket と dedupe → fix or escalate(`/loop` で継続) |
| Exploration/taste | generate-and-filter(5-20)→ tournament(rubric)→ rank/pick |
★ 失敗モードで pattern を選ぶ: Drift→fan-out / self-preference→adversarial verify / open-ended→loop until done / hard-to-score→tournament ★

### 12. `/goal` `/loop` token budget で制御
- `/goal` = hard 完了条件(loop pattern と組む)。無いと soft 完了で早期停止。
- `/loop` = workflow 自体を定期実行(triage/週次 research)。
- ★ token budget: prompt に「use 10k tokens」。無いと 5-10× に膨張 ★。
例: `> ultracode quick adversarial review of "moving to Postgres eliminates shard rebalancing". Use 5k tokens. /goal don't stop until a counterexample or three independent confirmations.`
★ 「regular session が5分で終わるなら workflow 不要」★。

### 13. Quarantine(untrusted input)
公開/ユーザー投稿/scrape/第三者 API 出力を読む agent は prompt injection を想定。**読む agent に high-privilege action を禁止**、別の(raw を見ない)agent が act。30行の read-only reader で injection の1クラスを除去。

### 14. Save & ship as Skill
動いたら `s` で保存 → `~/.claude/workflows`。local 再利用 or Skill 化(JS を Skill フォルダに同梱、SKILL.md で参照)。★ Skill 化時は「verbatim 実行でなく template として扱え」と prompt → タスクに合わせ shape を flex(deep-verification/triage 向き)★。

## トークンを無駄にする間違い(チェックリスト)
- regular session で済むのに workflow を使う / token budget 無し / 同一 agent が work と verify 両方 / parallel と pipeline を混同 / loop に `/goal` 無し / untrusted を actor に通す / 絶対採点で sort / 動いた workflow を保存しない。

## Anicca への適用方針
- 全実装(earn skill / shelter / spawn / dashboard / life-manager)を ultracode workflow で。
- 失敗モード対応: 取りこぼし(laziness)→ fan-out + loop-until-done / 検証 → adversarial verify(author≠reviewer)/ 設計選択 → generate-and-filter + tournament。
- untrusted(0xwork タスク本文 / mail / web)→ quarantine reader。
- 動いた workflow は `s` 保存 → Anicca skill 化。
