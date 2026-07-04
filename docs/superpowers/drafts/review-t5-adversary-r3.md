# T5 Adversary Review Round 3 — CLAUDE.md diet drafts（fresh-context、disk-only、最終確認）

対象:
- `docs/superpowers/drafts/global-CLAUDE.md`（6112B）
- `docs/superpowers/drafts/project-CLAUDE.md`（12878B）
- `.claude/rules/git-workflow.md`
- `.claude/rules/worktree.md`

照合元: round2 `docs/superpowers/drafts/review-t5-adversary-r2.md`／`docs/superpowers/plans/2026-07-04-claude-md-diet.md`／`docs/superpowers/specs/2026-07-04-claude-code-setup-optimization-design.md`。

スコープ: round2 の FAIL 2件の完治確認 + 最終スイープのみ（全面再審査はしない）。

---

## 1. R2-FAIL-1 完治確認 — `.claude/rules/git-workflow.md` の human-gate 残存

**判定: PASS**

- 該当行（旧「マージ | 絶対禁止。チェックリスト→ユーザーOK待ち」）は書き換え済み:
  `.claude/rules/git-workflow.md:49` 「マージ | 検証（adversary PASS + E2E green）後に agent が実行。`gh pr merge --merge --delete-branch` で branch 同時削除。人間の承認待ちなし」
- ファイル全体（51行、全セクション: Commit Format / PR Workflow / Feature Flow / Semver / Hotfix / 壊れた Submodule / Prisma Migration / リリース管理）を通読し、他の human-gate 表現（「待ち」「承認」「禁止」「OK」等）を grep — 該当箇所は上記1行の書き換え後の文（矛盾ではなく解消済みの記述）のみ。他のセクションに承認待ち系の残骸なし。
- round1で指摘された worktree.md 側（`.worktrees/<task>` 統一）も再確認 — 継続して修正済み（`.claude/rules/worktree.md:13-17`）。

## 2. R2-FAIL-2 完治確認 — project ドラフトの MacBook SSH 情報欠落

**判定: PASS**

- `docs/superpowers/drafts/project-CLAUDE.md:39` 「Mac Mini（`anicca-mac-mini-1`、Tailscale 100.99.82.95）で直接実行する。自分自身に SSH しない。**MacBook へは `ssh cbns03@100.108.140.123` で接続できる。**VPS は使わない。」— 原本の3行構成（Mac Mini / MacBook SSH / VPS）情報が1文に統合される形で完全復元されている。
- `grep -n "cbns03\|100.108.140.123\|MacBook"` → 該当1行のみヒット、欠落なし。

---

## 3. 最終スイープ

### 3-a. サイズ制約

| ファイル | 実サイズ | 上限 | 判定 |
|---|---|---|---|
| `global-CLAUDE.md` | 6112B | ≤6144B | PASS（余白32Bのみ、依然タイト） |
| `project-CLAUDE.md` | 12878B | ≤15360B | PASS（余白 ≈2482B） |

### 3-b. global/project 間の食い違い

- precedence 表・書き方規約・No-human-loop・GLVS・ツール既定・モデル分業 いずれも global に1箇所のみ、project 側は重複せず「→ global 参照」の1行に収まっている（例: `project-CLAUDE.md:98`「Web検索/コード内シンボル操作/ブラウザ/Mac操作の既定は `~/.claude/CLAUDE.md` 参照。」）。
- `GitHub Actions` 禁止の記述は project 側1箇所のみ（`project-CLAUDE.md:49`）、global には重複なし — repo固有ルールとして適切な配置。
- 自己宣言語・日付付きverbatim・「SUPREME」「最上位」「HARD RULE」の再スキャン → 新規ヒットなし（global 5行目の「書き方規約」自己記述のみで、これは規約の説明文であり自己宣言の禁止対象ではない）。

### 3-c. 参照先パス・skill名の実在確認

以下すべて実在確認（`test -e`）:
`.claude/rules/{platform-gotchas,coding-style,dev-workflow,git-workflow}.md` / `.claude/skills/tier-a-bypass/SKILL.md` / `.claude/agents/fact-checker.md` / `.claude/hooks/scripts/{post-edit-verify,stop-verify-claims}.sh` / `.cursor/plans/reference/{secrets,infrastructure}.md` / `agent_docs/openclaw_integration.md` / `docs/superpowers/specs/2026-06-04-anicca-inbox-autonomy-design.md` / `~/.claude/rules/loop-command.md` / `~/anicca/skills/self/founder-loop` / `~/.cloak` / `~/anicca-rtdash` / `~/anicca-monk-factory` / `~/.claude/RTK.md`。

`~/.claude/rules/disk-hygiene.md` と `.claude/rules/honesty.md` は未実在だが、plan (`2026-07-04-claude-md-diet.md:30,36`) で「新設予定」と明記された対象であり、round2 でも除外扱い済み — 回帰ではなく想定通り。

軽微指摘（非ブロッキング）: `project-CLAUDE.md:31` の anicca-inbox spec 参照は「`docs/superpowers/specs/` 内の anicca-inbox-autonomy-design spec §12」とファイル名を曖昧化しており、原本の完全パス（`docs/superpowers/specs/2026-06-04-anicca-inbox-autonomy-design.md §12`）より探索コストが上がる。実在はするので参照切れではない。

### 3-d. 新規発見 — `.claude/rules/dev-workflow.md` GATE 3 の human-gate 残存（round1/round2 未検出の第3ファイル）

**判定: FAIL（新規1件）**

- `project-CLAUDE.md:185` は「3ゲート開発ワークフロー（Spec→TDD→codex-review）→ `.claude/rules/dev-workflow.md`」と、この内容を無条件でこのファイルに委譲している。
- ところが `.claude/rules/dev-workflow.md:9`:
  ```
  | GATE 3: REVIEW | 品質・セキュリティ | codex-review → ok: true + ユーザー実機確認 |
  ```
  と、GATE 3 の**通過条件そのものに「ユーザー実機確認」を必須要件として組み込んでいる**。これは canonical 決定#2（no-human-loop が既定、唯一のカーブアウトは Dais 個人資金の外部送金／設計外の不可逆broadcast／WF-C記事copy編集の3つのみ、App Store提出も含め agent が最後まで実行）と正面から矛盾する。「品質・セキュリティ」ゲートの通過に「ユーザーの実機での確認」を要求する記述は、上記3カーブアウトのいずれにも該当しない汎用の human-gate であり、round1の3b（worktree.md の `../anicca-<task>` 残存）・round2の3-NEW（git-workflow.md のマージ承認待ち残存）と全く同じ構造の欠陥 —— **ドラフトが指す先の checked-in ファイルが旧ポリシーのまま**なパターンが、今回チェック対象に含めた3番目のファイル（dev-workflow.md）でも再現している。
- round1・round2 はこのファイルをチェック対象に含めておらず未検出だった（round2 は git-workflow.md のみ新規追加、dev-workflow.md は参照実在確認のみで内容点検されていない）。

**修正指示**: `.claude/rules/dev-workflow.md:9` の GATE 3 通過条件から「ユーザー実機確認」を、canonical 決定#2 に合わせて「agent が実機/シミュレータ相当の手段（例: computer-use MCP 経由のシミュレータ操作、または実機相当の自動化）で自己検証」等、agent 自身が完結できる検証条件に書き換える。worktree.md・git-workflow.md と同様、project-CLAUDE.md 適用と同一コミットで修正すること。

---

## 総合 verdict: **FAIL（新規1件: dev-workflow.md GATE 3 の human-gate）**

| 項目 | 判定 |
|---|---|
| R2-FAIL-1（git-workflow.md マージ承認待ち） | 完治 PASS |
| R2-FAIL-2（MacBook SSH 情報欠落） | 完治 PASS |
| 最終スイープ: サイズ | PASS |
| 最終スイープ: global/project 食い違い | PASS |
| 最終スイープ: 参照先実在 | PASS（軽微指摘1件、非ブロッキング） |
| 最終スイープ: 新規矛盾 | **FAIL** — `.claude/rules/dev-workflow.md:9` GATE 3 の「ユーザー実機確認」がno-human-loop canonical決定と衝突 |

round2 の2 FAILは両方修正確認済み（回帰なし）。適用前に `.claude/rules/dev-workflow.md:9` の修正が必須。修正後、本ファイルと同じ grep 手順（+ 未点検の残り `.claude/rules/*.md` 全ファイルの内容照合）で再審査すること。
