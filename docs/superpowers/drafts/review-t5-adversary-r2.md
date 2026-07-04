# T5 Adversary Review Round 2 — CLAUDE.md diet drafts（fresh-context、disk-only）

対象:
- `docs/superpowers/drafts/global-CLAUDE.md`（6112B = 5.969KiB）
- `docs/superpowers/drafts/project-CLAUDE.md`（12813B = 12.513KiB）

照合元: `docs/superpowers/plans/2026-07-04-claude-md-diet.md` / `docs/superpowers/specs/2026-07-04-claude-code-setup-optimization-design.md` / round1 `docs/superpowers/drafts/review-t5-adversary.md` / 原本 `~/.claude/CLAUDE.md` / 原本 `~/anicca-project/CLAUDE.md` / `.claude/rules/worktree.md`（同時修正対象）。

---

## R. round1 の4 FAIL — 個別回帰判定

| # | round1 指摘 | 判定 | 証拠 |
|---|---|---|---|
| R1 | 次元1 FAIL: project-CLAUDE.md の開発方式節が GLVS に従属せず独立 mandate として再掲 | **FIXED** | `project-CLAUDE.md:9-11` 「## 開発の道具立て（GLVS の Build/Verify 段で使う superpowers skill 群）」「開発方式そのものは `~/.claude/CLAUDE.md` の GLVS（Goal→Loop→Verify→State）が唯一の外枠。このプロジェクトでは GLVS の各段で以下の superpowers skill を道具として呼ぶ（並列の独立必須プロセスにしない）。」— 従属記述に書き換え済み、「全実装に必須」の独立宣言は削除済み（grep 0 hit） |
| R2 | 次元2 FAIL: 「HARD RULE #6 exception」「HARD RULE: Anicca は...」の自己重要化見出しが残存 | **FIXED** | `project-CLAUDE.md:29` 「## メール triage は LLM 直判断でよい例外」、`project-CLAUDE.md:166` 「### aniccaai.com への書き込み制限」— 記述的見出しに変更済み。`grep -n "HARD RULE" docs/superpowers/drafts/*.md` → 0 hit |
| R3a | 次元3 FAIL: 不可侵 store（`~/.cloak`/`~/anicca-rtdash`/`~/anicca-monk-factory`）がドラフトから完全脱落 | **FIXED** | `global-CLAUDE.md:86` 「不可侵 store（削除・移動禁止） \| `~/.cloak` `~/anicca-rtdash` `~/anicca-monk-factory` `~/.claude/projects/*/memory/` `**/state/*.jsonl`」— 3対象 + 追加2対象で復元済み |
| R3b | 次元3 FAIL: `.claude/rules/worktree.md` が `../anicca-<task>` のまま未修正 | **FIXED** | `.claude/rules/worktree.md:13-17` が `.worktrees/<task>` に統一済み（`git worktree add .worktrees/<task>` / `cd .worktrees/<task>` / `git worktree remove .worktrees/<task>`）。project-CLAUDE.md:81-85 と完全一致 |
| R4a | 次元4 FAIL: RTK.md の1行参照が消失 | **FIXED** | `global-CLAUDE.md:85` 「トークン節約 CLI \| `rtk` 経由でhook自動最適化、`rtk gain`/`rtk discover` は直接実行 → `~/.claude/RTK.md`」 |
| R4b | 次元4 FAIL: 出力フォーマット規律（0.5/0.11）の消失 | **FIXED** | `global-CLAUDE.md:88-90` 「## 出力形式・言語」「回答は常にテーブル/ビジュアル形式で書く（箇条書き単体にしない）。日本語で書く。」 |

**round1 の4 FAIL は全て修正確認 = PASS（回帰なし）。**

---

## 次元1: 矛盾11件の canonical 解のみ — **PASS**

11項目全てについて disk 上で canonical 解と一致する記述を確認（grep 証拠）:

| # | 矛盾 | 結果 |
|---|---|---|
| 1 | ブラウザ既定 | `global-CLAUDE.md:64` CloakBrowser daily-driver、camofoxはfallbackのみ。`grep "camofox >"` 0 hit |
| 2 | publish gate | `global-CLAUDE.md:26-33` No-human-loop、カーブアウト3つのみ明記（App Store含め自分で実行）※ただし別ファイル経由の残存あり→次元3参照 |
| 3 | 質問政策 | `global-CLAUDE.md:28` 「進めていいですか」実施しない明記。`project-CLAUDE.md:25` fundamental依存のみ確認、他は追加してspec記録 |
| 4 | human-loop度合い | ZERO、"NOT eliminate" 系表現 0 hit |
| 5 | commit/push | `global-CLAUDE.md:16,24` precedence表でplugin/hook矛盾時は無効と明記、即push方針のみ |
| 6 | Web検索 | firecrawlのみ、WebSearch/WebFetch「使わない」と明記 |
| 7 | コード検索 | Serena=シンボル操作、Grep/Glob=プレーンテキスト、と役割分担明記（禁止の絶対表現なし） |
| 8 | Mac UI操作 | cua-driverのみ、computer-use MCP「使わない」 |
| 9 | worktree置き場 | `.worktrees/<task>`に統一（次元Rで確認済み） |
| 10 | frontend必須ゲート | `global-CLAUDE.md:52` tasteskill→frontend-design→実ブラウザ確認、1行固定 |
| 11 | プロセス積層 | GLVSが唯一の外枠、project側は道具として従属（次元Rで確認済み） |

10/11 は完全解消。#2（publish gate）はドラフト本文としては解消しているが、**ドラフトが参照する既存ファイルに未解決の残骸がある**ため、次元3で FAIL として報告する（ドラフト単体の文言としては矛盾なしのため次元1は PASS 扱いとする）。

---

## 次元2: 書き方規約自己準拠 — **PASS（軽微な指摘1件）**

- 日付パターン・verbatim引用・激怒/incident文体・「SUPREME」「最上位」「HARD RULE」自己宣言: `grep -n -E "2026-[0-9]{2}-[0-9]{2}|verbatim|激怒|厳命|SUPREME|最上位|HARD RULE"` で self-declaration 系ヒットなし
- precedence表は `global-CLAUDE.md:7` に1個のみ

**軽微指摘（非ブロッキング）**: `project-CLAUDE.md:45,117,126` に `★唯一の products working tree★` `★唯一の products folder★` `★1個だけ★` という★装飾が残る。書き方規約が禁じるのは「自らを最上位・重大な違反と呼ぶ自己宣言」であり、これは事実の一意性強調（規則の重大性宣言ではない）なので文言上は規約違反ではないが、規約が排除しようとした旧文体（★連打）の残り香ではある。FAIL には数えないが、次回の diet で削ってよい候補として記録する。

---

## 次元3: 新規矛盾ゼロ — **FAIL（新規1件）**

### 3-NEW: `.claude/rules/git-workflow.md`「リリース管理」節が canonical 決定#2（no-human-loop）と正面衝突、ドラフトが未対応のままそこへ委譲している

- `project-CLAUDE.md:185` は「git commit/PR 詳細 → `.claude/rules/git-workflow.md`」と、この項目を無条件でこのファイルに委譲している。
- ところが `.claude/rules/git-workflow.md:43-50`「## リリース管理」節は現在も:
  ```
  | マージ | 絶対禁止。チェックリスト→ユーザーOK待ち |
  ```
  と書かれている。これは spec (`2026-07-04-claude-code-setup-optimization-design.md` D決定 matrix #2) の canonical 解「NO-HUMAN-LOOPが既定。唯一のカーブアウト = Dais個人資金の外部送金/設計外の不可逆broadcast/WF-C記事copy編集。**App Store提出もagentが実行**（0.27の旧gate削除）」と正面から矛盾する — release branch へのマージという通常の開発作業に「ユーザーOK待ち」という人間ゲートを課しており、3つのカーブアウトのいずれにも該当しない。
- round1 の 3b（`.claude/rules/worktree.md` の `../anicca-<task>` 残存）と同じ構造の欠陥（= ドラフトが指す先の checked-in ファイルが旧ポリシーのまま）だが、round1 はこのファイルをチェック対象に含めておらず未検出だった。
- `global-CLAUDE.md:26-33`（No-human-loop節）自体には矛盾はないが、project-CLAUDE.md が「git commit/PR 詳細はここを見よ」と誘導する先で読者が human-gate 記述に遭遇する以上、実運用上は矛盾#2が再発する。

**修正指示**: `.claude/rules/git-workflow.md` の「## リリース管理」節の「マージ | 絶対禁止。チェックリスト→ユーザーOK待ち」を、canonical 決定#2 に合わせて「マージ | テスト確認 → 自分で merge → push（人間の承認待ちなし）」等に書き換える。worktree.md と同様、project-CLAUDE.md 適用と同じコミットで修正すること。

他の新規矛盾チェック（矛盾なしを確認）:
- global/project 間でのモデル分業表の重複・不一致: なし（global 側1個のみ、project 側は言及なし）
- ツール優先順位の重複記載: `global-CLAUDE.md:58-66`（既定） と `project-CLAUDE.md:90-98`（プロジェクト固有分、"既定は global 参照" と明記）の役割分担は矛盾なし
- 不可侵 store の記載箇所が複数に分裂して食い違う: なし（`global-CLAUDE.md:86` 1箇所のみ）

---

## 次元4: 実務情報の喪失なし — **FAIL（軽微1件）**

| 項目 | 判定 | 証拠 |
|---|---|---|
| push先マップ | 保持 | `project-CLAUDE.md:41-49` |
| branch・deploy | 保持 | `project-CLAUDE.md:51-59` |
| fastlane | 保持 | `project-CLAUDE.md:59,95` |
| ツール優先順位 | 保持 | `global-CLAUDE.md:58-66`, `project-CLAUDE.md:90-98` |
| モデル分業表 | 保持 | `global-CLAUDE.md:68-75` |
| RTK参照 | 保持（round1 R4a で確認） | `global-CLAUDE.md:85` |
| 出力規律 | 保持（round1 R4b で確認） | `global-CLAUDE.md:88-90` |
| spec MUST | 保持 | `project-CLAUDE.md:21` |
| tasklist正直性 | 保持 | `project-CLAUDE.md:21` |
| **実行環境（MacBook SSH行）** | **喪失** | 原本 `~/anicca-project/CLAUDE.md`「実行環境」表は3行構成（Mac Mini / **MacBook SSH: `ssh cbns03@100.108.140.123`** / VPS）。`project-CLAUDE.md:39` は「Mac Mini（`anicca-mac-mini-1`、Tailscale 100.99.82.95）で直接実行する。自分自身に SSH しない。VPS は使わない。」のみで、MacBook への SSH アクセス経路（`ssh cbns03@100.108.140.123`）の記述が完全に脱落し、他のどこにも参照が無い（`grep -n "cbns03\|100.108.140.123\|MacBook" docs/superpowers/drafts/*.md` → 0 hit）。これは矛盾解消11件のどれにも属さない、単純な実務情報の取りこぼし |

**修正指示**: `project-CLAUDE.md` の実行環境節に「MacBook SSH: `ssh cbns03@100.108.140.123`」の1行を復元する。

---

## 次元5: サイズ・参照実在 — **PASS（global のマージンに要注意）**

- `project-CLAUDE.md`: 12813B = 12.513KiB ≤ 15KiB（headroom ≈ 2547B、十分）
- `global-CLAUDE.md`: 6112B = 5.969KiB ≤ 6KiB（headroom ≈ **32B のみ**）— 技術的には PASS だが、次回1行でも追記すれば即座に上限超過する超タイトなマージン。今回の3件の修正差分（不可侵store行・RTK行・出力形式節）で 389B 増えており、次元3/4 の残り2件（git-workflow.md 修正・MacBook SSH行復元）は project-CLAUDE.md 側で対応可能なため global 側はこれ以上増やさないこと
- 参照実在確認（`test -e`、新設除外分は対象外）:
  - project 側: `.claude/rules/{platform-gotchas,coding-style,dev-workflow,git-workflow}.md` 全 OK / `.claude/skills/tier-a-bypass/SKILL.md` OK / `.claude/agents/fact-checker.md` OK / `.claude/hooks/scripts/{post-edit-verify,stop-verify-claims}.sh` OK / `.cursor/plans/reference/{secrets,infrastructure}.md` OK / `agent_docs/openclaw_integration.md` OK / `docs/superpowers/specs/2026-06-04-anicca-inbox-autonomy-design.md` OK
  - global 側: `~/.claude/rules/loop-command.md` OK / `~/anicca/skills/self/founder-loop` OK / `~/.cloak` OK / `~/anicca-rtdash` OK / `~/anicca-monk-factory` OK / `~/.claude/RTK.md` OK
  - 除外（新設予定、確認済み未実在・問題なし）: `~/.claude/rules/disk-hygiene.md`（MISSING）/ `.claude/rules/honesty.md`（MISSING）

---

## 総合 verdict: **FAIL (2 dimensions: 3, 4)**

round1 の4 FAILは全て修正確認済み（回帰なし）。今回新たに検出した2件:

1. **[次元3・要修正]** `.claude/rules/git-workflow.md`「## リリース管理」の「マージ | 絶対禁止。チェックリスト→ユーザーOK待ち」を no-human-loop canonical 決定#2 に合わせて書き換える（project-CLAUDE.md 適用と同一コミットで、worktree.md と同様の扱い）。
2. **[次元4・軽微]** `project-CLAUDE.md` 実行環境節に MacBook SSH 行（`ssh cbns03@100.108.140.123`）を復元する。

次元1・2・5 は PASS（次元2は★装飾の軽微な指摘のみ、非ブロッキング。次元5は global のサイズマージンが32Bと極めてタイトな点を要注意として記録）。

修正後、本ファイルと同じ grep 手順（+ `.claude/rules/*.md` の内容照合）で再審査すること。
