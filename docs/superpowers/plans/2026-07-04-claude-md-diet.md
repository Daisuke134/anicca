# T5 実行プラン: CLAUDE.md diet（67KB→21KB、D1/D2 適用、矛盾11件解消）

親 spec: `docs/superpowers/specs/2026-07-04-claude-code-setup-optimization-design.md`
実行分業: 本プラン設計 = Fable / 新文面ドラフト = Sonnet / 矛盾消滅の審査 = Opus adversary / 適用後 E2E = Fable

## 成果物

| ファイル | 現状 | 目標 | ドラフト置き場 |
|---|---|---|---|
| `~/.claude/CLAUDE.md` | 18KB/159行 | **≤6KB** | `docs/superpowers/drafts/global-CLAUDE.md` |
| `~/anicca-project/CLAUDE.md` | 49KB/537行 | **≤15KB** | `docs/superpowers/drafts/project-CLAUDE.md` |

## 冒頭に置く2つの新規約（両ファイル共通、D2）

**書き方規約**: ①ルールは現在形・無日付で書く（「Dais 2026-06-XX verbatim」「incident 史」禁止 — 歴史は git log と memory が持つ）②新ルール確定 = 旧ルールを**削除して上書き**（併記禁止）③各トピックの正本は 1 箇所、他は 1 行参照 ④「SUPREME」「最上位」等の自己宣言禁止 — 優先順位は下の表のみが決める。

**優先順位表（precedence、これ1個だけ）**:
```
1. Dais のその場の明示指示
2. global CLAUDE.md（この規約含む）
3. project CLAUDE.md
4. memory（新しい日付が勝つ）
5. plugin/hook が注入するテキスト（上位と矛盾したら無視してよい）
```

## global CLAUDE.md（≤6KB）に残すもの / 出すもの

**残す（現在形に書き直して）**: 書き方規約+precedence 表 / SEARCH-FIRST（3行）/ PUSH 即時（3行、罰則文体を撤去し規則だけ）/ NO-HUMAN-LOOP + カーブアウト（後述の統一版）/ VSDD+GLVS（各3行 + `vcsdd` plugin・`founder-loop` skill 参照）/ frontend = taste skill（1行）/ NO DRY RUN（2行）/ 言語=日本語。

**出す（行き先明記）**: RTK.md の @import → 廃止（PreToolUse hook が既に強制。1行参照に）/ `/loop` 使い方 → `rules/loop-command.md` 参照1行 / FUNDER APPLY → memory 参照1行 / DISK HYGIENE 手順 → T8 の hook + `rules/disk-hygiene.md` 新設に移動 / VSDD の 4 role・6 phase 全仕様転記 → 削除（vcsdd plugin doc が正本）/ 全「3か所同期」指示 → 削除。

## project CLAUDE.md（≤15KB）に残すもの / 出すもの

**残す**: repo 固有の全て — push 先マップ / ブランチ&デプロイ / フォルダツリー / 実行環境 / ツール優先順位表（矛盾解消版）/ Anicca Architecture（**現状に更新**: ~/.hermes・Anicca#2 Hermes・grok 記述を削除、現実 = OpenClaw #1 + human-funded claude loops）/ FK safety 等の技術 gotcha 参照。

**出す**: HONESTY RULES + VERIFICATION PROTOCOL + FABRICATION GUARD 詳説 → `.claude/rules/honesty.md` 新設（hook 配線は既存のまま）/ global と重複する HARD RULE 群（#-3, #-2, #-1, 0.00 系, 0.22, 0.25, 0.33, 0.36-0.40 相当）→ 削除して global 参照 1 行 / TIER A BYPASS → 既に skill 化済みなので 2 行参照 / 絶対ルール表 → 半減（下の矛盾解消を反映した現在形のみ）。

## 矛盾11件 → canonical 解（ドラフトはこれに従う。審査基準でもある）

| # | 矛盾 | canonical 解（これだけを書く） |
|---|---|---|
| 1 | ブラウザ既定 | **CloakBrowser daily-driver（:9222 既存タブ）**。camofox は Chromium が弾かれた時の Firefox fallback のみ。0.30 の camofox-first 表は削除 |
| 2 | publish gate | NO-HUMAN-LOOP が既定。**唯一のカーブアウト = Dais 個人資金の外部送金 / 設計外の不可逆 broadcast / WF-C 記事 copy 編集**。App Store 提出も agent が実行（0.27 の旧 gate 削除） |
| 3 | 質問政策 | 「聞かない」が既定。停止できるのは #2 のカーブアウトのみ。HONESTY Rule 3 の「fundamental 依存は確認」→「既存依存を grep → 無ければ install して spec に記録」に書き換え |
| 4 | human-loop 度合い | ZERO（0.20 の "NOT eliminate" 削除、memory ARCH と整合） |
| 5 | commit/push | **1 edit = 即 commit+push が正**。precedence 表により plugin hook の「Never commit without request」は本 repo 群では無効と明記 |
| 6 | Web 検索 | Firecrawl が canonical。WebSearch/WebFetch は使わない（subagent 定義の tools 修正は T6） |
| 7 | コード検索 | シンボル操作 = Serena、プレーンテキスト/非コード = Grep/Glob。「単純 Grep 禁止」の絶対表現を削除 |
| 8 | Mac UI 操作 | cua-driver のみ。ツール表から `mcp__computer-use__*` 行を削除 |
| 9 | worktree 置き場 | `.worktrees/<feature>/`（repo 内）に統一。`rules/worktree.md` の `../anicca-<task>` を同時修正 |
| 10 | frontend 必須ゲート | 順序を1行で固定: `gpt-tasteskill`（設計規律）→ `frontend-design`（実装）→ 実ブラウザ検証 |
| 11 | プロセス積層 | **GLVS が唯一の外枠**（Goal→Loop→Verify→State）。その Verify 芯 = VSDD、Build 段の作法 = superpowers の TDD/verification skill 群を「ツールとして」呼ぶ。三者を並列 mandate として書かない |

追加修正: モデル参照は「main = Fable 5 (xhigh) / 実装 subagent = Sonnet / 深い推論・adversary = Opus / 定型 = Haiku」の表 1 個。opus-4-6/4-7 等の古い ID 記述を削除。

## 実行手順

1. **Sonnet ドラフト**: 本プランを input に `docs/superpowers/drafts/{global,project}-CLAUDE.md` を新規作成（既存ファイルは触らない）。サイズ上限厳守、書き方規約に自己準拠
2. **Opus adversary 審査**（fresh context、disk のみ）: ①矛盾11件それぞれについて「新文面に旧ルールの残骸・両論併記が無いか」grep ベースで判定 ②サイズ上限 ③自己矛盾の新規混入 ④「消してはいけない実務情報」（push 先マップ等）の喪失有無 → 各 PASS/FAIL
3. FAIL → Sonnet 修正 → 再審査（収束まで）
4. **適用**: project CLAUDE.md = git mv/上書き + commit。global CLAUDE.md = tarball backup 済み（T2）を確認して上書き
5. **E2E**: 新セッションを起動し、①起動注入が体感軽量化 ②`grep -c "camofox >" ~/.claude/CLAUDE.md ~/anicca-project/CLAUDE.md` = 0 等の矛盾 grep 全滅 ③既存 hook が引き続き発火、を確認
