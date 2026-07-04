# T5 Adversary Review — CLAUDE.md diet drafts (fresh-context, disk-only)

対象: `docs/superpowers/drafts/global-CLAUDE.md` (5723B/5.59KB) / `docs/superpowers/drafts/project-CLAUDE.md` (12944B/12.64KB)
照合元: `docs/superpowers/plans/2026-07-04-claude-md-diet.md` / `docs/superpowers/specs/2026-07-04-claude-code-setup-optimization-design.md` / 原本 `~/.claude/CLAUDE.md` (19904B) / 原本 `~/anicca-project/CLAUDE.md` (50709B)

---

## 次元1: 矛盾解消の完全性 — **FAIL**

10/11 は解消確認（grep 0 hit）。camofox は fallback文脈のみ（global-CLAUDE.md:64）、AskUserQuestion/どっち系ゼロ、"NOT eliminate"ゼロ、WebSearch/WebFetchは「使わない」明記のみ、単純Grep禁止表現ゼロ、computer-use MCPは「使わない」明記のみ、frontend順序1行固定、GLVS優先の宣言あり。

**しかし #11（プロセス積層）が未解消。**
- global-CLAUDE.md:39-46「開発方式 = GLVS（唯一の外枠）」は canonical 解通り: 「他の方式（VSDD、superpowers の TDD/verification skill 群）は並列の mandate ではなく、この枠の中の道具として使う」と明記。
- ところが project-CLAUDE.md:9-29「開発方式 = Superpowers spec-driven development（全実装に必須）」は、**GLVSへの参照が一切なく**、旧 HARD RULE #0 の8段階フローをそのまま独立の「全実装に必須」mandate として再掲している。「spec → plan → worktree → 実装(TDD+検証) → review → finish+push、いずれの段階もスキップしない」という文言は、まさに旧 Iron Law の並列 mandate 再現であり、canonical 解が禁じた「三者を並列 mandate として書かない」に反する。
- 2ファイルを合わせて読むと「タスクは GLVS で回す（global）」と「全実装は superpowers 8段階を通す、必須（project）」という**2つの独立した必須フレームワーク**が併存しており、矛盾#11はファイルを分けただけで実質未解決。

**修正指示**: project-CLAUDE.md の当該セクションを、GLVS の Build/Verify 段の「道具」として明示的に従属させる書き方に変更する。例:「GLVS の Build 段では、以下の superpowers スキル群をツールとして呼ぶ（spec化=brainstorming、実装=TDD、検証=verification-before-completion 等）」のように global の GLVS 記述に対する **参照+従属** の形にし、「全実装に必須」という独立宣言語を削除する。

---

## 次元2: 書き方規約の自己準拠 — **FAIL（軽微）**

日付パターン (`2026-0X-XX`)・verbatim引用・激怒/incident文体・「SUPREME」「最上位」自己宣言・precedence表の重複、いずれもゼロ hit（grep確認済）。precedence表は1個のみ（global-CLAUDE.md:7）。

**しかし** project-CLAUDE.md に旧ブランディングの残骸が2箇所:
- `project-CLAUDE.md:37` `## HARD RULE #6 exception`
- `project-CLAUDE.md:174` `### HARD RULE: Anicca は aniccaai.com に直接書き込まない`

書き方規約 (global-CLAUDE.md:5)「自らを最上位・重大な違反と呼ぶ自己宣言は書かない」の精神に反する — 「HARD RULE」という自己重要化ラベルそのものが旧文体の残骸。番号付け(0.XX)や日付は伴っていないため重大ではないが、規約の文字通りの精神には反する。

**修正指示**: 見出しをただの記述的な名前に変更する。例: `## メール triage は LLM 直判断でよい例外` / `## aniccaai.com への書き込み制限`。

---

## 次元3: 新規矛盾の混入 — **FAIL**

### 3a. 不可侵 store が両ドラフトから完全に脱落（★指定確認事項★）
spec (`2026-07-04-claude-code-setup-optimization-design.md:54`) の境界節:
> 「不可侵 store（Dais 2026-07-04 verbatim「deleting that is a sin」）: `~/.cloak`（ブラウザ履歴/ログイン profile）、`~/anicca-rtdash`、`~/anicca-monk-factory` — 削除・キャッシュ掃除・移動の対象外」

`grep -n "\.cloak\|anicca-rtdash\|anicca-monk-factory\|不可侵" docs/superpowers/drafts/*.md` → **0 hit**。disk-hygiene 系のドラフト記述（global-CLAUDE.md:82 の「ディスク管理手順 → `rules/disk-hygiene.md`」参照1行のみ）ではこの決定に一切触れておらず、disk-hygiene.md が新設されるまでこの安全境界線はどこにも書かれていない。T3/T7 でディスク回収・キャッシュ削除を伴う作業が控えている以上、この欠落は実害リスクが高い。

**修正指示**: 最低限 global-CLAUDE.md の参照表（またはproject-CLAUDE.mdの実行環境節）に「不可侵 store: `~/.cloak` / `~/anicca-rtdash` / `~/anicca-monk-factory`（削除・移動禁止）」の1行を追加する。disk-hygiene.md 新設を待たずに、CLAUDE.md 側にも生存させること。

### 3b. worktree 置き場が実際に矛盾したまま残る
- project-CLAUDE.md:89-93 は canonical 解通り `.worktrees/<task>`（repo内）を採用。
- しかし実ファイル `.claude/rules/worktree.md:13` は現在も `git worktree add ../anicca-<task> -b feature/<task>` のまま（未修正）。
- plan (`2026-07-04-claude-md-diet.md:50`) は「`rules/worktree.md` の `../anicca-<task>` を同時修正」と明記しているが、この修正はまだ実行されていない。
- 結果として、リポジトリには現在「`.worktrees/<task>`（CLAUDE.md 新draft）」と「`../anicca-<task>`（.claude/rules/worktree.md、checked-in・常時ロード対象）」という**2つの現行の矛盾する指示**が同時に存在する。ドラフト自体の欠陥ではなくapply手順の欠落だが、T5の「実行手順」ステップ4（適用）で一緒に直さないと矛盾#9は解消されない。

**修正指示**: project-CLAUDE.md 適用と同じコミットで `.claude/rules/worktree.md` の `../anicca-<task>` を `.worktrees/<task>` に置換すること。

---

## 次元4: 実務情報の喪失 — **FAIL**

### 4a. RTK.md の1行参照が消失
plan (`2026-07-04-claude-md-diet.md:30`)「出す」欄:「RTK.md の @import → 廃止（PreToolUse hook が既に強制。1行参照に）」— **「1行参照に」置き換えると明記**しているが、`grep -n "RTK\|rtk " docs/superpowers/drafts/*.md` → **0 hit**。global-CLAUDE.md 原本冒頭の `@RTK.md` import と、それが指す `rtk gain` / `rtk discover` / `rtk proxy` などのメタコマンドの存在が、ドラフトのどこにも痕跡を残していない。hook が変換を強制していても、`rtk gain`（節約analytics）や `rtk discover`（見逃し検出）はユーザーが明示的に叩く必要のあるメタコマンドであり、その存在を知る手がかりがCLAUDE.mdから消えると発見不能になる。

**修正指示**: global-CLAUDE.md の参照表に1行追加。例:「トークン節約CLI (`rtk`) | `rtk gain`/`rtk discover` 等はhookが自動書き換え、メタコマンドは直接使用」。

### 4b. 絶対ルール表からの日常運用ルールの消失（参照なし）
原本 project CLAUDE.md の「絶対ルール」表にあった以下は、plan上「矛盾解消と無関係」だが日常の出力/開発規律として頻繁に効いていたものであり、ドラフトのどこにも残骸・参照が無い:
- 0.5/0.11: 出力は常にテーブル形式、箇条書き単体・テキスト羅列禁止（回答フォーマット規律）
- 0.7: スペックに「任意」「optional」禁止、全てMUST
- 0.15/0.32: タスクリスト=source of truth、未完了をcompleted と書かない
- 0.8: `/compact` はコミット直後のみ

plan (`2026-07-04-claude-md-diet.md:36`)「絶対ルール表 → 半減（下の矛盾解消を反映した現在形のみ）」という指示自体がこれらの除去を許容するとも読めるため、次元1のような明確な計画違反ではないが、他の11矛盾のいずれにも属さない「無関係だが実務上重要」なルールが跡形もなく消えている。特に出力フォーマット規律（0.5/0.11）は本レビューファイル自体を含め全応答に影響する規律であり、1行参照すら無いのは"実務情報の喪失"に該当する。

**修正指示**: 少なくとも 0.5/0.11（出力フォーマット）は plan のどの矛盾にも属さないため、Sonnetドラフト作成時に見落とされた可能性が高い。Dais に確認の上、意図的除外なら plan に明記、そうでなければ project-CLAUDE.md に1行復元すること。

### 4c. 確認できた「残っているべきものは残っている」項目（参考、PASSに寄与）
push先マップ・ブランチ&デプロイ・fastlane必須・greenlight・folder tree・実行環境・ツール優先順位（Context7/Maestro/fastlane）・FK safetyへの参照・tier-a-bypass参照・anicca-inbox例外・Anicca Architecture現状更新（hermes/grok記述は正しく削除確認済み）は全て確認でき、喪失なし。

---

## 次元5: サイズと構造 — **PASS**

- global-CLAUDE.md: 5723B = 5.59KB ≤ 6KB（マージン約420B、タイト）
- project-CLAUDE.md: 12944B = 12.64KB ≤ 15KB（マージン約2.3KB）
- 参照先パス実在確認（全て `test -e` で確認済み）: `.claude/skills/tier-a-bypass/SKILL.md` OK / `.claude/agents/fact-checker.md` OK / `.claude/hooks/scripts/post-edit-verify.sh` OK / `.claude/hooks/scripts/stop-verify-claims.sh` OK / `.claude/rules/{platform-gotchas,coding-style,dev-workflow,git-workflow}.md` 全OK / `.cursor/plans/reference/{secrets,infrastructure}.md` OK / `agent_docs/openclaw_integration.md` OK / `~/anicca/skills/self/founder-loop/` OK / `docs/superpowers/specs/2026-06-04-anicca-inbox-autonomy-design.md` OK / `~/.claude/rules/loop-command.md` OK
- 除外対象（plan で「新設予定」と明記済み、未実在でも FAIL 扱いしない）: `~/.claude/rules/disk-hygiene.md`（未作成、確認済み） / `.claude/rules/honesty.md`（未作成、確認済み）
- モデル分業表に opus-4-6/4-7/4-8 等の古いID記述なし（grep 0 hit）、`.cursor/agents/*.md` の実ファイル（D3実装, T1）は sonnet/opus/haiku に正しく分業済みで整合。

---

## 総合 verdict: **FAIL (3 dimensions: 1, 2, 3, 4)** — 4/5 dimensions FAIL, 1 PASS

### 収束に必要な修正（優先順）
1. **[次元1・最重要]** project-CLAUDE.md の「開発方式 = Superpowers spec-driven development（全実装に必須）」節を GLVS の Build/Verify 段への従属記述に書き換え、独立 mandate 宣言を削除。
2. **[次元3a・安全性]** 不可侵 store（`~/.cloak` / `~/anicca-rtdash` / `~/anicca-monk-factory`）への言及をどちらかのドラフトに最低1行追加。
3. **[次元3b・適用手順]** `.claude/rules/worktree.md` の `../anicca-<task>` を `.worktrees/<task>` に修正（適用コミットと同時）。
4. **[次元4a]** RTK.md の1行参照を global-CLAUDE.md に追加。
5. **[次元4b]** 出力フォーマット規律（0.5/0.11）の意図的除外か復元かを確定。
6. **[次元2・軽微]** 「HARD RULE」ラベルの見出し2箇所を記述的な名前に変更。

修正後、本ファイルと同じ grep 手順で再審査すること。
