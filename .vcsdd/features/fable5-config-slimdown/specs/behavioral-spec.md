# Behavioral Spec — fable5-config-slimdown (Phase 1a)

設計元: `docs/superpowers/specs/2026-07-07-fable5-config-slimdown-design.md`（P1〜P8、全て確認済み recon ベース）

## スコープの性質

この feature に「振る舞い」はない（UI もアルゴリズムもない）。振る舞いの単位は **実行後のファイルシステム状態**
（設定ファイルの内容・存在・非存在・JSON validity）である。各 REQ は「WHEN 実装が完了した時点で THE SYSTEM
SHALL 〜」という事後状態アサーションとして記述する。トリガーは常に「fable5-config-slimdown の実装完了」。

対象ファイル一覧（設計 spec のスコープ境界表と同一、これ以外は触らない）:

| # | ファイル |
|---|---|
| P1 | `~/.claude/plugins/cache/ww-w-ai/claude-code-token-saver/2.1.0/hooks/git-context-lite.sh` |
| P2a | `~/.claude/rules/loop-engineering.md`（削除） |
| P2b | `~/.claude/plugins/cache/ww-w-ai/claude-code-token-saver/2.1.0/hooks/session-architecture.md`（置換） |
| P3 | `~/.claude/rules/{building-voice-agents,building-effective-ai-agents,loop-command}.md` → `~/.claude/references/` |
| P3/P5/P6 | `~/.claude/CLAUDE.md` |
| P4 | `~/.claude/settings.json` |
| P5 | `~/anicca/skills/_shared/adversary-daily.sh` |
| P6 | `.claude/settings.json`（worktree 版）+ `/Users/anicca/anicca-project/.claude/settings.json`（live checkout、branch `feature/clip-rewards`） |
| P7 | loop CLI 7本 + `adversary-daily.sh` の spawn プロンプト定義箇所 |
| P8 | `~/.claude/plugins/cache/superpowers-marketplace/superpowers/5.0.7/hooks/hooks.json` |

## 既知の drift（recon で新規確認、実装時に注意）

worktree 内 `.claude/settings.json` は dev の最新版から drift しており、現時点で `effortLevel` キー自体が
**存在しない**（`"model": "claude-opus-4-7"` のみ、`post-edit-verify.sh`/`stop-verify-claims.sh` hook・
`autoCompactEnabled` も欠落）。設計 spec の「現状 = `xhigh`」という記述は live checkout 側の状態であり、
worktree 側はそれとは異なる古い snapshot である。REQ-P6a はこの drift を織り込み、「事後状態として
`effortLevel == "high"` が存在すること」のみを要求する（既存キーの値変更か新規キー追加かは実装の自由、
本 feature のスコープ外の他キー欄の同期は行わない）。

## Requirements (EARS)

### REQ-P1: git-context-lite hook の矛盾除去
**EARS**: WHEN fable5-config-slimdown の実装が完了した時点で、THE SYSTEM SHALL
`~/.claude/plugins/cache/ww-w-ai/claude-code-token-saver/2.1.0/hooks/git-context-lite.sh` のheredoc から
「Never without explicit user request」の文言と「Avoid `git add -A`」の文言を除去し、代わりに
`~/.claude/CLAUDE.md` の Push 節を参照する1行を含める。
**Edge Cases**:
- secrets 保護（.env/credentials/*.pem 等）への言及は残存していなければならない（`grep -qi secret`）。
- 破壊的操作（`reset --hard` 等）への注意、main への force push 禁止、HEREDOC コミットメッセージ、
  interactive flag 禁止、empty commit 禁止の記述は残存していなければならない（削除対象は「commit/push
  に user request が要る」「`git add -A` を避ける」の2ブロックのみ、周辺の他の安全記述を巻き込んで消しては
  ならない）。
- ファイルは bash heredoc を含むシェルスクリプトであり、編集後も `bash -n` で構文エラーを起こしてはならない。
**Acceptance Criteria**:
- `grep -q "Never without explicit user request"` が false
- `grep -q 'Avoid .git add -A'` が false
- `grep -q 'CLAUDE.md'` が true
- `grep -qi 'secret'` が true
- `bash -n <file>` が exit 0

### REQ-P2a: loop-engineering.md の削除
**EARS**: WHEN fable5-config-slimdown の実装が完了した時点で、THE SYSTEM SHALL
`~/.claude/rules/loop-engineering.md` を削除済み状態にする。
**Edge Cases**:
- 削除前に元ファイルが `~/.claude/backups/fable5-slimdown-2026-07-07/loop-engineering.md` へ
  コピーされていなければならない（REQ-SAFE-1 準拠）。
- 同ファイルを参照する他ファイル（CLAUDE.md 含む）が無いこと（この feature の対象ファイル一覧に
  含まれていないため、参照があれば別問題として報告する）。
**Acceptance Criteria**:
- `[ ! -f ~/.claude/rules/loop-engineering.md ]`
- `[ -f ~/.claude/backups/fable5-slimdown-2026-07-07/loop-engineering.md ]`

### REQ-P2b: session-architecture.md の最小版置換
**EARS**: WHEN fable5-config-slimdown の実装が完了した時点で、THE SYSTEM SHALL
`~/.claude/plugins/cache/ww-w-ai/claude-code-token-saver/2.1.0/hooks/session-architecture.md` を
20行以下に置換し、次の4点のみを残す: (1) 独立 tool call は1メッセージに束ねる (2) 軽いツール優先
（Grep/Glob/LSP → 部分 Read → 全文 Read） (3) 既存ファイルは Edit（Write しない） (4) ブラウザ MCP・
WebFetch 等の重い往復は subagent に吸収させる。
**Edge Cases**:
- Thinking Patterns（Dialectic/Metacognition 等）、Response style 詳細、具体行番号
  （`runAgent.ts:682-684` 等）、旧モデル名（`opus-4-6` 等）、"Hard bans" セクションへの言及は
  一切残ってはならない。
- 4点の意味内容が実際に含まれているかどうかは自動 grep では判定不能な自然言語判断であり、
  fresh-context adversary のレビュー対象とする（Tier judgment、shell アサーション対象外）。
- 削除前に元ファイルが `~/.claude/backups/fable5-slimdown-2026-07-07/session-architecture.md` へ
  コピーされていなければならない。
**Acceptance Criteria**:
- `wc -l < <file>` が 20 以下
- `grep -qE "Thinking Patterns|Dialectic|runAgent|opus-4-6|Hard bans" <file>` が false
- `[ -f ~/.claude/backups/fable5-slimdown-2026-07-07/session-architecture.md ]`
- adversary が4点の意味内容の残存を PASS 判定

### REQ-P3a: MOVE REF-CHECK（P3 の前提ガード）
**EARS**: WHEN `~/.claude/rules/{building-voice-agents,building-effective-ai-agents,loop-command}.md`
の移動を実行する直前に、THE SYSTEM SHALL 各ファイル名について `~/.openclaw/skills`・`~/anicca/skills`・
`~/.openclaw/cron` を3形式（絶対パス `/Users/anicca/...`・チルダ `~/...`・`$HOME/...`）で grep する。
**Edge Cases**:
- `~/.claude/CLAUDE.md`（および本 worktree 内 `CLAUDE.md`）からの参照は許容対象外（この移動自体が
  CLAUDE.md 内の参照パスを更新するため）。
- CLAUDE.md 以外から1件でも参照が見つかった場合、THE SYSTEM SHALL その特定ファイルの移動を中止し、
  発見箇所（ファイルパス+行）を報告する。この場合 REQ-P3b の当該ファイル分の目標状態は適用されない
  （移動しない旨の報告が正とみなされる）。
**Acceptance Criteria**:
- 3ファイル × 3ディレクトリ × 3パス形式 = 27通りの grep 結果が
  `.vcsdd/features/fable5-config-slimdown/evidence/move-ref-check.log` に記録されている
  （★ iteration-1 FIND-003 対応: 1 grep 実行 = 1行、計27行以上。各行はファイル名・検索ディレクトリ・
  パス形式・hit件数のフィールドを含む形式でなければならず、verify.sh がログの存在 + 行数 ≥27 を
  機械的にアサートできる ★）
- 参照ゼロ件のファイルのみ REQ-P3b へ進む

### REQ-P3b: 知識ファイルのオンデマンド化（REQ-P3a が全ファイルで zero-hit の場合の目標状態）
**EARS**: WHEN REQ-P3a のガードが対象ファイルについて参照ゼロを確認した時点で、THE SYSTEM SHALL
そのファイルを `~/.claude/rules/` から `~/.claude/references/` へ移動し、`~/.claude/CLAUDE.md`
の「その他の参照」表（GLVS 節内の参照を含む）のパスを `rules/loop-command.md` から
`references/loop-command.md` へ更新し、`references/building-voice-agents.md`
（voice agent 実装時に読む）と `references/building-effective-ai-agents.md`（agent 設計時に読む）
の2行を追記する。
**Edge Cases**:
- `~/.claude/rules/context7.md` は移動対象外、`~/.claude/rules/` に残存しなければならない。
- CLAUDE.md 内に `rules/loop-command.md` という文字列が1箇所でも残ってはならない（GLVS 節内の
  参照も含め全箇所更新）。
**Acceptance Criteria**（3ファイル分、REQ-P3a 通過分のみ）:
- `[ -f ~/.claude/references/<name>.md ] && [ ! -f ~/.claude/rules/<name>.md ]`
- `grep -q "references/loop-command.md" ~/.claude/CLAUDE.md`
- `! grep -q "rules/loop-command.md" ~/.claude/CLAUDE.md`
- `[ -f ~/.claude/rules/context7.md ]`（不変条件、移動されていないこと）

### REQ-P4: SSOT guard の二重注入解消（★ iteration-2 FIND-005 blocking 対応: 静的カウント前提を
実行時 snapshot-diff 方式へ全面書き換え ★）
**EARS**: WHEN fable5-config-slimdown の実装が完了した時点で、THE SYSTEM SHALL 編集直前の
`~/.claude/settings.json` の `.hooks` オブジェクト全体を
`.vcsdd/features/fable5-config-slimdown/evidence/p4-pre-hooks.json` へ jq でスナップショット保存し、
`hooks.UserPromptSubmit` から `ssot-guard` に一致する command entry のみを外科的に削除し（削除の結果
entry を含んでいた matcher-group の `hooks` 配列が空になった場合はその matcher-group ごと削除しても
よい）、編集直後の `.hooks` オブジェクト全体を
`.vcsdd/features/fable5-config-slimdown/evidence/p4-post-hooks.json` へ同様にスナップショット保存する。
**Edge Cases**:
- ★ `~/.claude/settings.json` は当日中にも並行して drift する実運用ファイルであり、iteration-1
  時点の「ssot-guard と disk-guard が UserPromptSubmit 内の同一 matcher-group に同居している」という
  記述は本改訂時点（2026-07-07）で既に不正確と判明した（実装時点の実ファイルを再確認した結果:
  `hooks.UserPromptSubmit` は `ssot-guard.sh` 単独の1エントリのみを含む1個の matcher-group。
  `disk-guard.sh` は `hooks.SessionStart` 側の matcher:"*" グループで `ssot-guard.sh` と同居している）。
  よって本要件は特定時点の固定構造（entry数・同居関係）を前提にせず、実装直前の実ファイルを
  snapshot して diff する方式に一本化する。実装者は実装開始時点で改めて `jq '.hooks'` を実行して
  現況を確認すること（この Edge Case に書かれた具体的な現況もその時点で drift している可能性がある）。
- `hooks.SessionStart` の内容（disk-guard・ssot-guard・cozempic 全て）は本要件の編集対象外であり、
  pre-hooks.json と post-hooks.json で完全に不変（canonical JSON 比較で byte-identical）でなければ
  ならない。
- `hooks.UserPromptSubmit` 内の ssot-guard 以外のいかなる entry（他 matcher-group、実装時点で
  cozempic 由来 entry が存在する場合はそれも含む）も変更してはならない。
- 編集後、ファイル全体が `jq .` でパース可能でなければならない（REQ-SAFE-2）。
**Acceptance Criteria**:
- post-hooks.json の `.UserPromptSubmit` に `ssot-guard` に一致する command entry が0件
- pre-hooks.json の `.UserPromptSubmit` から `ssot-guard` の command entry のみを jq で機械的に
  取り除いた構造（除去後に空になった matcher-group をそのまま残すか削除するかは両方とも許容し、
  比較時は両側とも「`hooks` 配列が空の matcher-group」を正規化して除外してから比較する）が、
  post-hooks.json の `.UserPromptSubmit` と構造的に一致する（jq による同値比較、diff は
  ssot-guard entry 除去 1点のみであることを機械的に保証する）
- pre-hooks.json の `.SessionStart` と post-hooks.json の `.SessionStart` が canonical JSON で
  byte-identical
- `jq . ~/.claude/settings.json` が exit 0

### REQ-P5a: adversary の refusal fallback（--model opus 明示）
**EARS**: WHEN fable5-config-slimdown の実装が完了した時点で、THE SYSTEM SHALL
`~/anicca/skills/_shared/adversary-daily.sh` の claude 起動コマンドに `--model opus` を含める。
**Acceptance Criteria**:
- `grep -q -- '--model opus' ~/anicca/skills/_shared/adversary-daily.sh`

### REQ-P5b: グローバル CLAUDE.md への refusal fallback 行追加
**EARS**: WHEN fable5-config-slimdown の実装が完了した時点で、THE SYSTEM SHALL
`~/.claude/CLAUDE.md` のモデル分業表に、セキュリティ監査・攻撃寄りタスクは Opus 4.8 を使う旨、
かつ Fable 5 が safety classifier で refusal を返した場合も Opus 4.8 へ fallback する旨の行を追加する。
**Acceptance Criteria**:
- `grep -q 'refusal' ~/.claude/CLAUDE.md`
- 追加行にセキュリティ監査/攻撃的サイバー系タスクと Opus 4.8 への言及があることを adversary が
  意味内容として確認する（grep は語の存在のみ保証、文脈の正しさは judgment tier）

### REQ-P6a: worktree 内 settings.json の effortLevel
**EARS**: WHEN fable5-config-slimdown の実装が完了した時点で、THE SYSTEM SHALL 本 worktree の
`.claude/settings.json` に `effortLevel: "high"` を存在させる。
**Edge Cases**:
- 「既知の drift」節の通り、実装前の時点でこのファイルに `effortLevel` キー自体が存在しない場合が
  ある。この場合は新規キー追加で目標状態を満たしてよい（既存値の書き換えである必要はない）。
- 本 feature のスコープはこの1キーのみであり、`model` キーの値や欠落している hook 配線
  （`post-edit-verify.sh` 等）を同期する義務はない（別 drift、対象外）。
**Acceptance Criteria**:
- `jq -e '.effortLevel == "high"' .claude/settings.json`
- `jq . .claude/settings.json` が exit 0

### REQ-P6b: live checkout 側 settings.json の effortLevel
**EARS**: WHEN fable5-config-slimdown の実装が完了した時点で、THE SYSTEM SHALL
`/Users/anicca/anicca-project/.claude/settings.json`（live checkout、branch `feature/clip-rewards`）
にも `effortLevel: "high"` を存在させ、commit + push 済みにする。
**Acceptance Criteria**:
- `jq -e '.effortLevel == "high"' /Users/anicca/anicca-project/.claude/settings.json`
- `git -C /Users/anicca/anicca-project log --oneline -1 -- .claude/settings.json` が本変更の
  commit を指す
- `git -C /Users/anicca/anicca-project status --porcelain .claude/settings.json` が空
  （commit 済み、未 push 分は fetch 比較で確認）

### REQ-P6c: モデル分業表のメイン行更新
**EARS**: WHEN fable5-config-slimdown の実装が完了した時点で、THE SYSTEM SHALL
`~/.claude/CLAUDE.md` のモデル分業表メイン行を「Fable 5（high。設計・監査・難デバッグ等の最重要作業のみ
xhigh に一時上げ）」へ更新する。
**Acceptance Criteria**:
- `grep -q 'high。設計・監査・難デバッグ' ~/.claude/CLAUDE.md`

### REQ-P7a: loop CLI 群への PushNotification 促し文の配線（★ iteration-1 FIND-001 blocking 対応:
追記位置を実行時 prompt 値の内側に構造的に固定する ★）
**EARS**: WHEN fable5-config-slimdown の実装が完了した時点で、THE SYSTEM SHALL 次の8ファイルそれぞれに
ついて、既存の TASK/STARTUP/PROMPT 変数の代入（1行または複数行にまたがる、下表「代入span」）の内容を
一切改変せず、その代入が完了した直後の行から、その変数を実際に `claude`/`tmux` 起動へ渡す行
（下表「起動行」）より前までの間に、変数への自己参照 concatenation で追記する新規1行
`VAR="${VAR} <促し文>"`（または `VAR="$VAR <促し文>"`）を追加し、その追記行自体の中に
PushNotification という文字列を含める。

これにより追加文が「ファイル内のどこかに存在する」だけでなく「実際に spawn される claude セッションへ
渡される prompt 値の一部として実行時に評価される」ことを構造的に保証する（既存の巨大な引用符付き文字列
を直接編集して壊すリスクも同時に排除する）。全て `~/anicca/skills/` 配下。

| ファイル | 変数名 | 代入span（行、実ファイル確認済み） | 起動行 |
|---|---|---|---|
| `self/self-fix.sh` | `TASK` | 67–74（複数行、`TASK="..."`、閉じ引用符は74行目末尾） | 75（`tmux -S "$SOCK" new-session ... -- "$TASK"`） |
| `self/capafy-loop/capafy-loop-cli.sh` | `STARTUP` | 8（単一行、`STARTUP='...'`） | 12（`tmux -S "$SOCK" new-session ... -- "$STARTUP"`） |
| `self/reddit-loop/reddit-loop-cli.sh` | `STARTUP` | 9（単一行） | 13（`tmux -S "$SOCK" new-session ... -- "$STARTUP"`） |
| `self/life-manager-loop/life-manager-loop-cli.sh` | `STARTUP` | 8（単一行） | 12（`tmux -S "$SOCK" new-session ... -- "$STARTUP"`） |
| `earn/clip-promote/clip-promote-cli.sh` | `STARTUP` | 24（単一行） | 39（`"$CLAUDE" --name "$SESSION" ... -- "$STARTUP"`） |
| `earn/video/video-cli.sh` | `STARTUP` | 17（単一行） | 32（`"$CLAUDE" --name "$SESSION" ... -- "$STARTUP"`） |
| `earn/clip/clip-cli.sh` | `STARTUP` | 18（単一行） | 33（`"$CLAUDE" --name "$SESSION" ... -- "$STARTUP"`） |
| `_shared/adversary-daily.sh` | `PROMPT` | 20–21（`PROMPT=$(sed ... || echo ...)`） | 23（`claude -p "$PROMPT" --output-format text ...`） |

★ iteration-2 FIND-006 対応: self-fix.sh 行は前回改訂時点の誤記（67–76/77）を修正した
（正しくは67–74/75、75行目のtmux起動直後の76-77行目は`date +%s > "$STARTMARK"`と
ログechoというspawn後のbookkeeping文であり、代入span/起動行のいずれにも該当しない）。
他7行は2回にわたり実ファイルと照合済みで正確。★ 運用注記: 上表の行番号は本 spec 執筆時点
（2026-07-07）の実ファイルに基づく。実装時点で改めて `grep -n`/`awk` で該当変数の代入開始行・
終了行・起動行を再確認し、ズレていた場合は表ではなく実装時点の実ファイルを正として扱う
（対象8ファイルは頻繁に drift しうる loop CLI であり、行番号は不変条件ではない）。★

★ iteration-3 FIND-007 対応: 同一 feature 内の他要件（現状 `_shared/adversary-daily.sh` に対する
REQ-P5a のみ）が同じファイルを触る場合、本要件（REQ-P7a）の起動行 byte-identical 検査の基準は
「REQ-P7a 自身の編集直前」の状態である（feature 全体の開始時点ではない、per-operation。
REQ-SAFE-1 の「コピーのタイムスタンプは編集操作より前」と同じ規約）。したがって
`adversary-daily.sh` の場合、REQ-P5a が23行目に `--model opus` を追加した後の状態が
REQ-P7a にとっての「実装前」であり、その状態を基準に起動行の不変性を検証する。★

**Edge Cases**:
- 元の TASK=/STARTUP=/PROMPT= 代入span自体（上表の「代入span」列）は実装前後で byte-identical
  でなければならない（diff で確認可能。既存の巨大な引用符付き文字列を直接編集しない）。
- `_shared/adversary-daily.sh` は特記（iteration-1 FIND-001 で確認済み）: 参照先の
  `~/anicca/skills/_shared/adversary-daily-prompt.tmpl` は実在せず、`sed` は必ず失敗して
  `echo "Review feature ${SLOT} per ..."` の fallback 文字列が実際の実行時 `$PROMPT` になる。
  したがって追記行は `sed`/`echo` どちらの分岐が実行されたかに関わらず必ず通る位置
  （= 分岐が確定した行21の後、起動行23の前、unconditional）に置かなければならない。
- `adversary-daily.sh` の促し文は「FAIL verdict 時のみ通知」に限定した文言でなければならない
  （他7ファイルは「重要な結果が出たら」の一般文言）。
- 促し文は「narration・定常報告には使わない」という抑制も含む。
- 起動行（上表「起動行」列）自体は変更してはならない（`"$VAR"` 参照のまま、追記は変数の値側で
  行う）。
**Acceptance Criteria**:
- 8ファイル全てで、代入span（上表）が実装前バックアップと byte-identical
- 8ファイル全てで、代入span の最終行の次の行から起動行の前の行までの範囲内に、該当変数名を用いた
  自己参照 concatenation パターン（例: `STARTUP="${STARTUP} ...` または `STARTUP="$STARTUP ...`、
  `self-fix.sh` は `TASK=`、`adversary-daily.sh` は `PROMPT=`）にマッチし、かつ "PushNotification"
  を含む行が最低1行存在する
- 8ファイル全てで、起動行自体が実装前バックアップと byte-identical

### REQ-P7b: 促し文の内容妥当性（judgment tier）
**EARS**: WHEN REQ-P7a の8ファイルへの追記が完了した時点で、THE SYSTEM SHALL 各ファイルの追記行
（REQ-P7a の自己参照 concatenation 行）の意味内容が「重要な結果（数字・ID を含む成果、realized P&L、
致命的エラー）が出たら PushNotification で Dais へ verbatim 送信してから終了する。narration・
定常報告には使わない」という趣旨と一致していることを、fresh-context adversary のレビューで確認する。
**Acceptance Criteria**:
- adversary が8ファイル全てについて趣旨一致を PASS 判定
- adversary は追記行が REQ-P7a の acceptance criteria が示す位置（代入span後・起動行前）に
  実際にあることも併せて目視確認する（PROP-P7a の shell アサーションの独立ダブルチェック）

### REQ-P7c: PushNotification の実送信 E2E
**EARS**: WHEN 検証フェーズで新規 `claude -p --model sonnet` 子セッションが起動された時点で、
THE SYSTEM SHALL その子セッションから PushNotification ツールを実際に呼び出し、成功応答
（tool result のエラーなし応答）を受け取る。
**Edge Cases**:
- dry run・mock・simulated な呼び出しは不可（HARD RULE 0.24 準拠）。実際に Dais 宛て通知が
  送信されなければならない。
**Acceptance Criteria**:
- 子セッションのログ/transcript に PushNotification tool call + 成功 tool_result が記録されている

### REQ-P8: superpowers hooks.json の SessionStart entry 削除
**EARS**: WHEN fable5-config-slimdown の実装が完了した時点で、THE SYSTEM SHALL
`~/.claude/plugins/cache/superpowers-marketplace/superpowers/5.0.7/hooks/hooks.json` の
`hooks.SessionStart` から using-superpowers 全文注入 entry（command が `session-start` に一致するもの）
を削除する。
**Edge Cases**:
- 同ファイル内の他 hook（SessionStart 以外のイベント、または SessionStart 内の無関係な entry）は
  変更してはならない。
- skill 本体（`skills/using-superpowers/SKILL.md` 等）は一切変更しない。
- 編集前に元ファイルが `~/.claude/backups/fable5-slimdown-2026-07-07/hooks.json` へコピーされて
  いなければならない。
**Acceptance Criteria**:
- `jq -e '[.hooks.SessionStart // [] | .[].hooks[]?.command | select(test("session-start"))] | length == 0' <hooks.json>`
- `jq . <hooks.json>` が exit 0

## エッジケース要件（横断、team-lead 指定）

### REQ-SAFE-1: 編集/削除前バックアップ
**EARS**: WHEN P1・P2a・P2b・P4・P6a・P8 の対象ファイルのいずれかを編集または削除する前に、
THE SYSTEM SHALL その元ファイルを `~/.claude/backups/fable5-slimdown-2026-07-07/` へコピー済みに
しておく。
**Edge Cases**:
- コピーのタイムスタンプは編集操作より前でなければならない（順序が守られていることの証跡）。
- P3 移動対象の3ファイルは「削除」ではなく「移動」だが、移動先自体が実質的なバックアップを兼ねる
  ため、本要件の対象は P1・P2a・P2b・P4・P6a・P8 の6ファイルに限定する
  （P6b の live checkout 側は git history 自体が復元手段のため対象外、P5 は git 管理下の
  `~/anicca` repo のため git history が復元手段で対象外）。
**Acceptance Criteria**:
- 上記6ファイルそれぞれについて `~/.claude/backups/fable5-slimdown-2026-07-07/<basename>` が存在

### REQ-SAFE-2: JSON validity
**EARS**: WHEN `~/.claude/settings.json`・`.claude/settings.json`（worktree）・
`/Users/anicca/anicca-project/.claude/settings.json`（live checkout）・
`~/.claude/plugins/cache/superpowers-marketplace/superpowers/5.0.7/hooks/hooks.json` のいずれかが
編集された時点で、THE SYSTEM SHALL 編集後の当該ファイルが `jq .` でパース可能な状態を維持する。
**Acceptance Criteria**:
- 4ファイル全てで `jq . <file>` が exit 0

### REQ-SAFE-3: 不変条件（cozempic / enabledPlugins / includeGitInstructions / context7.md）
**EARS**: THE SYSTEM SHALL この feature のいかなる実装ステップにおいても、
`~/.claude/settings.json` 内の cozempic 由来 hook entry・`enabledPlugins`・`includeGitInstructions`
の値、および `~/.claude/rules/context7.md` の内容を変更しない。
**Acceptance Criteria**:
- 実装前後で `enabledPlugins` の JSON 値が byte-identical
- 実装前後で `includeGitInstructions` の値が byte-identical
- 実装前後で cozempic 由来 hook entry（command 文字列に `cozempic` を含むもの）の集合が
  byte-identical
- 実装前後で `~/.claude/rules/context7.md` の内容が byte-identical（md5 一致）

### REQ-SAFE-4: MOVE REF-CHECK ゲート（REQ-P3a の別名としての明示）
**EARS**: WHEN P3 の3ファイルいずれかの移動が計画された時点で、THE SYSTEM SHALL 移動を実行する前に
`~/.openclaw/skills`・`~/anicca/skills`・`~/.openclaw/cron` を絶対パス・チルダ・`$HOME` の3形式で
grep し、CLAUDE.md 以外からの参照が1件でも見つかった場合はその特定ファイルの移動を中止して報告する。
**Acceptance Criteria**: REQ-P3a と同一（本要件は横断エッジケース一覧としての重複明示、
実装・検証は1本化してよい）

## Non-functional constraints

- No dry run（HARD RULE 0.24）: REQ-P7c は実際の PushNotification 送信を伴う。
- 耐久性: P1・P2b・P8 は `~/.claude/plugins/cache/` 内の編集であり、plugin update/reinstall で
  復活しうる。この事実は本 spec のスコープ内アサーションには影響しない（drift 検知は
  `.vcsdd/features/fable5-config-slimdown/tests/verify.sh` の恒久保存で別途担保、Phase 2a で実装）。
- 秘密情報: この feature はいかなる secret/credential も新規生成・記録しない。
