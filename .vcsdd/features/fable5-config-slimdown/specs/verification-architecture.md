# Verification Architecture — fable5-config-slimdown (Phase 1b)

## Tier legend（この feature 専用、team-lead 指定 — plugin 既定の formal-proof tier 0-3 とは意味が異なる）

この feature はコードの正しさではなく「ライブ設定ファイルの事後状態」を検証する。よって以下の3段
tier を使う（kani/hypothesis 等の formal tool は不要）:

| Tier | 内容 |
|---|---|
| 0 | shell アサーション（決定的、ファイル状態: 存在/非存在/grep/wc/diff/md5） |
| 1 | JSON validity（`jq .` パース可否） |
| 2 | E2E（新規 `claude -p` セッションでの fresh evidence 取得 + PushNotification 実送信、または
      fresh-context adversary による自然言語 judgment） |

## Purity boundary map

この feature に純粋な決定的ロジックは存在しない — 全て「ライブ設定ファイルの読み書き」という副作用
そのものが対象である。従って purity boundary は「検証コード」と「実装（編集）ステップ」の間に引く。

| 領域 | Purity | 内容 |
|---|---|---|
| **検証（tests/verify.sh、Phase 2a で実装）** | Pure（副作用なし読み取り専用） | 全アサーションは grep/jq/wc/diff/md5sum 等の read-only コマンドのみで構成する。verify.sh 自体はいかなるファイルも書き換えない。 |
| **実装（Phase 2b、builder subagent）** | Effectful（意図的な副作用） | ファイルの編集・削除・移動・commit・push。全て REQ-SAFE-1〜4 のガードを経由する。 |
| **judgment（Tier 2 の一部）** | 副作用なし、ただし非決定的 | 「4点の趣旨が残っているか」「promotion 文の趣旨が一致するか」等の自然言語判断は grep で機械化できないため、fresh-context adversary（Opus 明示、CLAUDE.md モデル分業に従う）のレビューに委ねる。adversary は disk 読み取りのみ、書き込みは verdict/finding ファイルに限定。 |

## Proof obligations

| ID | Requirement | Tier | Required (lean) | Verification method |
|---|---|---|---|---|
| PROP-P1 | REQ-P1（git-context-lite.sh 矛盾除去） | 0 | true | `! grep -q "Never without explicit user request" $F && ! grep -q 'Avoid .git add -A' $F && grep -q 'CLAUDE.md' $F && grep -qi 'secret' $F && bash -n $F` |
| PROP-P2a | REQ-P2a（loop-engineering.md 削除+backup） | 0 | true | `[ ! -f ~/.claude/rules/loop-engineering.md ] && [ -f ~/.claude/backups/fable5-slimdown-2026-07-07/loop-engineering.md ]` |
| PROP-P2b-shell | REQ-P2b（session-architecture.md 行数+禁止語+backup） | 0 | true | `[ $(wc -l < $SA) -le 20 ] && ! grep -qE "Thinking Patterns|Dialectic|runAgent|opus-4-6|Hard bans" $SA && [ -f ~/.claude/backups/fable5-slimdown-2026-07-07/session-architecture.md ]` |
| PROP-P2b-judgment | REQ-P2b（4点の意味内容が残存） | 2 | true | fresh-context adversary が `$SA` を読み、4点（独立tool call束ね/軽ツール優先/Edit優先/重い往復はsubagentへ）の趣旨がそれぞれ判読可能かを PASS/FAIL 判定 |
| PROP-P3a | REQ-P3a/REQ-SAFE-4（MOVE REF-CHECK、★ iteration-1 FIND-003 対応: ログ出力先を明示 ★） | 0 | true | 3ファイル名 × `{~/.openclaw/skills, ~/anicca/skills, ~/.openclaw/cron}` × `{絶対パス, ~/, $HOME/}` の27通り grep を実行し、各1回の実行結果を `.vcsdd/features/fable5-config-slimdown/evidence/move-ref-check.log` へ1行ずつ追記（ファイル名・検索ディレクトリ・パス形式・hit件数のフィールドを含む、計27行以上）するスクリプト。CLAUDE.md 以外の hit が0件であることを確認、1件でも hit → 当該ファイルは PROP-P3b 対象から除外し「report only」を PASS 条件とする。verify.sh は同ログの `[ -f <log> ] && [ $(wc -l < <log>) -ge 27 ]` を追加でアサートする |
| PROP-P3b | REQ-P3b（移動先+CLAUDE.md 参照更新） | 0 | true（PROP-P3a を通過したファイルのみ） | `[ -f ~/.claude/references/<name>.md ] && [ ! -f ~/.claude/rules/<name>.md ]`（3ファイル分）`&& grep -q "references/loop-command.md" ~/.claude/CLAUDE.md && ! grep -q "rules/loop-command.md" ~/.claude/CLAUDE.md && [ -f ~/.claude/rules/context7.md ]` |
| PROP-P4 | REQ-P4（SSOT guard 重複解消、★ iteration-2 FIND-005 blocking 対応: iteration-1 FIND-002 由来の静的カウント方式は当日中の drift で不成立と判明したため snapshot-diff 方式へ全面書き換え ★） | 0+1 | true | 実装者が編集直前に `jq '.hooks' ~/.claude/settings.json > .vcsdd/features/fable5-config-slimdown/evidence/p4-pre-hooks.json`、編集直後に同様に `p4-post-hooks.json` を保存する。verify.sh は以下4点を確認: (a) `jq -e '[.UserPromptSubmit // [] \| .[].hooks[]?.command \| select(test("ssot-guard"))] \| length == 0' p4-post-hooks.json`（UserPromptSubmit の ssot-guard entry が0件）。(b) 構造的同値比較（jqで決定的に記述、★ iteration-3 FIND-008 対応: `UserPromptSubmit` キー自体が
編集で丸ごと削除され `null` になるケース（(a)の `// []` は既に防御済みだが(b)は未対応だった）に
備え、EXPECTED/ACTUAL 双方の `.UserPromptSubmit` に `// []` を追加し、キー欠落時に jq が
"Cannot iterate over null" でクラッシュせずクリーンな FAIL/空配列比較に落ちるようにした ★）:
`EXPECTED=$(jq -c '(.UserPromptSubmit // []) \| map(.hooks \|= map(select(.command \| test("ssot-guard") \| not))) \| map(select((.hooks // []) \| length > 0)) \| sort' p4-pre-hooks.json)` と
`ACTUAL=$(jq -c '(.UserPromptSubmit // []) \| map(select((.hooks // []) \| length > 0)) \| sort' p4-post-hooks.json)` を比較し `[ "$EXPECTED" = "$ACTUAL" ]`（pre から ssot-guard entry のみを機械的に除去し、除去後に空になった matcher-group を両側とも正規化除外した上での同値性。これにより diff が「ssot-guard entry 削除」以外の何も含まないことを保証する。disk-guard は現状 UserPromptSubmit に存在しないため個別 assertion は置かない）。(c) `diff <(jq -S '.SessionStart' p4-pre-hooks.json) <(jq -S '.SessionStart' p4-post-hooks.json)` が空（SessionStart 側の disk-guard/ssot-guard/cozempic 全て不変）。(d) `jq . ~/.claude/settings.json` が exit 0 |
| PROP-P5a | REQ-P5a（--model opus） | 0 | true | `grep -q -- '--model opus' ~/anicca/skills/_shared/adversary-daily.sh` |
| PROP-P5b | REQ-P5b（refusal fallback 行、grep+judgment） | 0+2 | true | shell: `grep -q 'refusal' ~/.claude/CLAUDE.md`／judgment: adversary が追加行にセキュリティ監査・攻撃的サイバー系タスク＋Opus 4.8 fallback の趣旨が正しく含まれるか確認 |
| PROP-P6a | REQ-P6a（worktree settings.json effortLevel） | 0+1 | true | `jq -e '.effortLevel == "high"' .claude/settings.json && jq . .claude/settings.json` |
| PROP-P6b | REQ-P6b（live checkout settings.json effortLevel+push） | 0+1 | true | `jq -e '.effortLevel == "high"' /Users/anicca/anicca-project/.claude/settings.json && jq . /Users/anicca/anicca-project/.claude/settings.json`、かつ `git -C /Users/anicca/anicca-project status --porcelain .claude/settings.json` が空、かつ `git -C /Users/anicca/anicca-project log origin/feature/clip-rewards..HEAD --oneline -- .claude/settings.json` が空（= push 済み） |
| PROP-P6c | REQ-P6c（モデル分業表メイン行） | 0 | true | `grep -q 'high。設計・監査・難デバッグ' ~/.claude/CLAUDE.md` |
| PROP-P7a | REQ-P7a（8ファイル PushNotification 配線、★ iteration-1 FIND-001 blocking 対応: 「ファイル内のどこかに文字列がある」から「実行時 prompt 値の内側にある」検証へ強化 ★） | 0 | true | 8ファイルそれぞれについて (a) REQ-P7a表の代入span（行範囲）を実装前バックアップと `diff` し byte-identical であること、(b) 代入spanの最終行+1行目から起動行-1行目までの範囲を `sed -n '<start>,<end>p' <file>` で抽出し、その範囲に対して `grep -E '^\s*(TASK\|STARTUP\|PROMPT)="\$\{?(TASK\|STARTUP\|PROMPT)\}?'`（該当ファイルの実際の変数名1つに固定して使う、バックリファレンスではなく定数）にマッチし、かつ "PushNotification" を含む行が1行以上存在すること、(c) 起動行自体を実装前バックアップと `diff` し byte-identical であること。8ファイル全てで (a)(b)(c) が PASS して初めて PROP-P7a は PASS |
| PROP-P7b | REQ-P7b（促し文の趣旨、adversary-daily.sh は FAIL限定） | 2 | true | fresh-context adversary が8ファイルそれぞれの、PROP-P7a(b) で特定された自己参照 concatenation 追記行を読み、趣旨一致（7ファイルは一般文言、adversary-daily.sh は FAIL verdict 限定文言）を PASS/FAIL 判定。併せて追記行が代入span後・起動行前という正しい位置にあることも目視で二重確認する |
| PROP-P7c | REQ-P7c（PushNotification 実送信 E2E） | 2 | true | `claude -p --model sonnet` を実起動し、PushNotification tool call + エラーなし tool_result が transcript に記録されることを確認（mock 禁止、HARD RULE 0.24） |
| PROP-P8 | REQ-P8（hooks.json SessionStart entry 削除） | 0+1 | true | `jq -e '[.hooks.SessionStart // [] \| .[].hooks[]?.command \| select(test("session-start"))] \| length == 0' <hooks.json> && jq . <hooks.json>`、かつ SessionStart 以外の hook 配列が編集前後で byte-identical（`diff` ベース） |
| PROP-SAFE-1 | REQ-SAFE-1（編集前バックアップ、6ファイル） | 0 | true | 6ファイル（git-context-lite.sh, loop-engineering.md, session-architecture.md, `~/.claude/settings.json`, worktree `.claude/settings.json`, `hooks.json`）それぞれについて `~/.claude/backups/fable5-slimdown-2026-07-07/<basename>` の存在 + mtime が対応する実装ファイルの最終編集より前であることを確認 |
| PROP-SAFE-2 | REQ-SAFE-2（4 JSON ファイルの validity） | 1 | true | `jq . ~/.claude/settings.json && jq . .claude/settings.json && jq . /Users/anicca/anicca-project/.claude/settings.json && jq . <hooks.json>` 全て exit 0 |
| PROP-SAFE-3 | REQ-SAFE-3（不変条件4点） | 0 | true | 実装前後の `jq '.enabledPlugins' / .includeGitInstructions` の値比較、cozempic command 集合の比較（`jq` で抽出 → `diff`）、`context7.md` の `md5sum` 前後一致 |
| PROP-SAFE-4 | REQ-SAFE-4（MOVE REF-CHECK ゲート） | 0 | true | PROP-P3a と同一スクリプトを指す（重複実装しない、traceability 上の別名） |

## Verification tiers 詳細

- **Tier 0（shell アサーション）**: 全て `tests/verify.sh`（Phase 2a で実装）内の read-only コマンド
  として実行可能。実行順序: PROP-SAFE-1（バックアップ存在）→ 各 P1/P2a/P2b-shell/P3a/P4/P5a/P6a/P6b/
  P6c/P7a/P8 → PROP-SAFE-2（JSON validity）→ PROP-SAFE-3（不変条件）。P3a が1件でも hit を返した
  場合、PROP-P3b は該当ファイルをスキップし「report only」で PASS 扱いにする分岐を verify.sh に
  実装する。
- **Tier 1（JSON validity）**: `jq .` の exit code のみで判定、Tier 0 のスクリプト内に混在してよい
  （team-lead 指定通り分離表記するが実装上は同一スクリプト）。
- **Tier 2（E2E + judgment）**: 2種類に分岐する。
  - **judgment 系**（PROP-P2b-judgment, PROP-P5b の judgment 半分, PROP-P7b）: fresh-context
    adversary（`vcsdd:vcsdd-adversary`、CLAUDE.md モデル分業に従い Opus 明示）が disk 上の該当
    ファイルを読み、PASS/FAIL verdict を `.vcsdd/features/fable5-config-slimdown/reviews/` 配下へ
    書く。
  - **live E2E 系**（PROP-P7c）: 主エージェント自身が新規 `claude -p --model sonnet` セッションを
    実起動し、PushNotification ツールの実行結果（tool_result）を fresh evidence として取得する。
    adversary はブラウザ/外部送信権限を持たないため、この tier は主エージェントのみが実行する
    （`clip-clawrouter-instance-provision` feature が確立した「adversary=文書レビュー、主エージェント
    =live 検証」の two-gate 分割を踏襲）。

## Gate

Phase 3（adversarial review、fresh-context Opus）が以下を確認する:
1. PROP-P1〜PROP-P8・PROP-SAFE-1〜4 の shell/JSON tier（Tier 0/1）が全て PASS（verify.sh の実行
   ログで確認、fabricated report は不可）。
2. PROP-P2b-judgment・PROP-P5b（judgment 半分）・PROP-P7b の自然言語趣旨判定が PASS。
3. REQ-SAFE-3 の4不変条件（cozempic hook / enabledPlugins / includeGitInstructions / context7.md）が
   実装前後で完全一致している（diff/md5 の実際の出力を確認、「変更していないはず」の申告のみでは
   不可）。
4. P3 の移動について、REQ-P3a のガードが実際に実行された証跡
   （`.vcsdd/features/fable5-config-slimdown/evidence/move-ref-check.log`、27通り grep の実行ログ、
   計27行以上）が存在し、report-only に分岐したファイルがあればその報告内容が記録されている。
5. plugin cache 配下（P1・P2b・P8）の編集について、`.vcsdd/features/fable5-config-slimdown/tests/
   verify.sh` が恒久保存され、drift 再検知に使える状態であることを確認する。

PROP-P7c（live E2E、PushNotification 実送信）は Phase 3 PASS 後に主エージェントが実行し、adversary
の再レビュー対象にはしない（adversary はツール実行権限を持たないため）。

## Traceability

| REQ | PROP | 実装対象ファイル |
|---|---|---|
| REQ-P1 | PROP-P1 | `~/.claude/plugins/cache/ww-w-ai/claude-code-token-saver/2.1.0/hooks/git-context-lite.sh` |
| REQ-P2a | PROP-P2a | `~/.claude/rules/loop-engineering.md`（削除） |
| REQ-P2b | PROP-P2b-shell, PROP-P2b-judgment | `~/.claude/plugins/cache/ww-w-ai/claude-code-token-saver/2.1.0/hooks/session-architecture.md` |
| REQ-P3a / REQ-SAFE-4 | PROP-P3a / PROP-SAFE-4 | （ガードのみ、ファイル編集なし） |
| REQ-P3b | PROP-P3b | `~/.claude/rules/{building-voice-agents,building-effective-ai-agents,loop-command}.md` → `~/.claude/references/`、`~/.claude/CLAUDE.md` |
| REQ-P4 | PROP-P4 | `~/.claude/settings.json` |
| REQ-P5a | PROP-P5a | `~/anicca/skills/_shared/adversary-daily.sh` |
| REQ-P5b | PROP-P5b | `~/.claude/CLAUDE.md` |
| REQ-P6a | PROP-P6a | `.claude/settings.json`（worktree） |
| REQ-P6b | PROP-P6b | `/Users/anicca/anicca-project/.claude/settings.json`（live checkout） |
| REQ-P6c | PROP-P6c | `~/.claude/CLAUDE.md` |
| REQ-P7a | PROP-P7a | loop CLI 7本 + `adversary-daily.sh`（計8ファイル、`~/anicca/skills/` 配下） |
| REQ-P7b | PROP-P7b | 同上8ファイル |
| REQ-P7c | PROP-P7c | （実行時 E2E、ファイル編集なし） |
| REQ-P8 | PROP-P8 | `~/.claude/plugins/cache/superpowers-marketplace/superpowers/5.0.7/hooks/hooks.json` |
| REQ-SAFE-1 | PROP-SAFE-1 | 6バックアップ対象ファイル（上記のうち git 管理外のもの） |
| REQ-SAFE-2 | PROP-SAFE-2 | `~/.claude/settings.json`, `.claude/settings.json`, `/Users/anicca/anicca-project/.claude/settings.json`, `hooks.json` |
| REQ-SAFE-3 | PROP-SAFE-3 | `~/.claude/settings.json`（cozempic/enabledPlugins/includeGitInstructions）, `~/.claude/rules/context7.md` |
| REQ-SAFE-4 | PROP-SAFE-4 | REQ-P3a と同一（別名） |
