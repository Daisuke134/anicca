# Fable 5 Config Slimdown（P1〜P8）— 設計 spec

日付: 2026-07-07 / 発注: Dais（「P1 to P8 を spec-driven でやれ」）

## 開発環境

| 項目 | 値 |
|---|---|
| worktree | `.worktrees/fable5-config-slimdown/` |
| branch | `feature/fable5-config-slimdown`（origin/dev 起点） |
| VCSDD | `.vcsdd/features/fable5-config-slimdown/`（mode: lean） |
| 実装の主対象 | **repo 外のライブ設定**（`~/.claude/*`、plugin cache、`~/anicca`）。repo 内で変更するのは本 spec・検証スクリプト・`.claude/settings.json`（effortLevel）のみ |

## 背景・根拠

Anthropic 公式ドキュメント「Prompting Claude Fable 5」（Dais が 2026-07-07 に session へ貼付、code.claude.com/docs 系）:

> "Skills developed for prior models are often too prescriptive for Claude Fable 5 and **can degrade output quality**. Review and consider removing older instructions if default performance is better."

> "Separate, fresh-context verifier subagents tend to **outperform self-critique**."

> "Claude Fable 5 runs safety classifiers that target offensive cybersecurity techniques ... configure server-side or client-side **fallback to Claude Opus 4.8**."

recon（Explore agent 2体、2026-07-07 実施）で全対象の実パス・行番号を確認済み。本 spec の「現状」欄は全て実ファイル確認に基づく（推測ゼロ）。

## スコープ境界（触ってよいファイル = これが全部）

| # | ファイル | 変更 |
|---|---|---|
| P1 | `~/.claude/plugins/cache/ww-w-ai/claude-code-token-saver/2.1.0/hooks/git-context-lite.sh` | heredoc 文言修正 |
| P2 | `~/.claude/rules/loop-engineering.md` | 削除（backup 後） |
| P2 | `~/.claude/plugins/cache/ww-w-ai/claude-code-token-saver/2.1.0/hooks/session-architecture.md` | 最小版へ置換 |
| P3 | `~/.claude/rules/{building-voice-agents,building-effective-ai-agents,loop-command}.md` | `~/.claude/references/` へ移動 |
| P3/P5/P6 | `~/.claude/CLAUDE.md` | 参照表・モデル分業表の更新 |
| P4 | `~/.claude/settings.json` | UserPromptSubmit の ssot-guard entry 削除 |
| P5 | `~/anicca/skills/_shared/adversary-daily.sh` | `--model opus` 追加 |
| P6 | `~/anicca-project/.claude/settings.json`（worktree 版 + live checkout 版の両方） | `effortLevel: xhigh → high` |
| P7 | `~/anicca/skills/{self/self-fix.sh, self/capafy-loop/capafy-loop-cli.sh, self/reddit-loop/reddit-loop-cli.sh, self/life-manager-loop/life-manager-loop-cli.sh, earn/clip-promote/clip-promote-cli.sh, earn/video/video-cli.sh, earn/clip/clip-cli.sh, _shared/adversary-daily.sh}`（計8ファイル、本文と一致） + spawn プロンプト定義箇所 | 通知促し文の追加 |
| P8 | `~/.claude/plugins/cache/superpowers-marketplace/superpowers/5.0.7/hooks/hooks.json` | SessionStart entry 削除 |
| - | `docs/superpowers/specs/`（本 spec）、`.vcsdd/features/fable5-config-slimdown/` | spec + 検証 |

**触ってはいけないもの**: `~/.claude/settings.json` 内の cozempic 由来 inline hook 群 / `~/.openclaw/` 全部 / superpowers plugin の skill 本体 / `enabledPlugins`（plugin 単位無効化はしない）/ `includeGitInstructions`（false のまま維持）/ `~/.claude/rules/context7.md`（現行のまま残す）。

## 各項目: 現状 → 目標状態（全て MUST）→ 検証

### P1: git-lite hook の矛盾除去

- **現状**: `git-context-lite.sh:63-83` の heredoc が「Never without explicit user request: Commit, push...」「Avoid `git add -A`」を毎セッション注入。global CLAUDE.md の Push 節（「意味のある編集をしたら都度 `git add -A && commit && push`。確認は求めない」）と真っ向矛盾。
- **目標**: heredoc から矛盾ブロック（commit/push/PR の user-request 要求、`git add -A` 禁止）を削除し、代わりに `Commit/push policy = ~/.claude/CLAUDE.md「Push」節に従う（編集→即 commit+push、確認不要）` の1行を置く。**残すもの**: secrets 保護（.env/credentials/*.pem）、破壊的操作（reset --hard 等）への注意、main への force push 禁止、HEREDOC コミットメッセージ、interactive flag 禁止、empty commit 禁止。
- **検証**: `! grep -q "Never without explicit user request" $F && ! grep -q 'Avoid .git add -A' $F && grep -q 'CLAUDE.md' $F && grep -qi 'secret' $F`

### P2: 旧モデル向け「思考の振り付け」の削除

- **現状**: ① `~/.claude/rules/loop-engineering.md`（「内部で4回の検証ループを必ず回す」）が全セッション注入。② `session-architecture.md`（93行）が Thinking Patterns（Dialectic/Metacognition 等）、Response style 詳細、stale 情報（`runAgent.ts:682-684` 行番号、`claude-opus-4-6` fallback 助言）を注入。
- **目標**: ① `loop-engineering.md` を backup 後に削除。② `session-architecture.md` を **20行以下**の最小版に置換。残す内容は次の4点のみ: 独立 tool call は1メッセージに束ねる / 軽いツール優先（Grep/Glob/LSP → 部分 Read → 全文 Read）/ 既存ファイルは Edit（Write しない）/ ブラウザ MCP・WebFetch 等の重い往復は subagent に吸収させる。Thinking Patterns・Response style・具体行番号・旧モデル名への言及は全削除。
- **検証**: `[ ! -f ~/.claude/rules/loop-engineering.md ] && [ $(wc -l < $SA) -le 20 ] && ! grep -qE "Thinking Patterns|Dialectic|runAgent|opus-4-6|Hard bans" $SA`

### P3: 知識ファイルのオンデマンド化

- **現状**: `~/.claude/rules/` の全 md が全プロジェクト・全セッションに自動注入される。`building-voice-agents.md`(7.5K) は voice 作業時のみ必要、`building-effective-ai-agents.md`(6.1K) の核心ルールは MEMORY.md に既存（`feedback_build_agents_not_hardcode_regex`）、`loop-command.md`(4.8K) は CLAUDE.md から参照済みのリファレンス。
- **目標**: `~/.claude/references/` を新設し3ファイルを移動。global CLAUDE.md「その他の参照」表を更新: `rules/loop-command.md` → `references/loop-command.md` にパス修正（GLVS 節内の参照も）+ 2行追加（voice agent 実装時 → `references/building-voice-agents.md` / agent 設計時 → `references/building-effective-ai-agents.md`）。`context7.md` は rules/ に残す。
- **移動前ガード（MOVE REF-CHECK、memory 準拠）**: `~/.openclaw/skills`・`~/anicca/skills`・`~/.openclaw/cron` を3形式（`/Users/anicca/...`・`~/...`・`$HOME/...`）で grep し、CLAUDE.md 以外からの参照が見つかったら移動を中止して報告する。
- **検証**: `[ -f ~/.claude/references/building-voice-agents.md ] && [ ! -f ~/.claude/rules/building-voice-agents.md ]`（3ファイル分）`&& grep -q "references/loop-command.md" ~/.claude/CLAUDE.md && ! grep -q "rules/loop-command.md" ~/.claude/CLAUDE.md`

### P4: SSOT guard の二重注入解消

- **現状**: `~/.claude/hooks/ssot-guard.sh` が `~/.claude/settings.json` の SessionStart **と** UserPromptSubmit の両方に登録され、毎プロンプト同一テキストを再注入。
- **目標**: UserPromptSubmit 側の ssot-guard entry のみ削除。SessionStart 側は残す。cozempic の隣接 entry には触れない。編集前に `~/.claude/backups/settings.json.<date>` へ backup、編集後 `jq . ~/.claude/settings.json` で JSON validity 確認。
- **検証**: `jq -e '[.hooks.UserPromptSubmit // [] | .[].hooks[]?.command | select(test("ssot-guard"))] | length == 0' ~/.claude/settings.json && jq -e '[.hooks.SessionStart[].hooks[]?.command | select(test("ssot-guard"))] | length == 1' ~/.claude/settings.json`

### P5: refusal fallback（セキュリティ系は Opus）

- **現状**: ① `~/anicca/skills/_shared/adversary-daily.sh:23` が `--model` 未指定 = default（Fable 5）で起動。コメントの「Opus adversary」意図と食い違い、かつ adversary=Opus ルール（CLAUDE.md モデル分業 2026-07-07）違反。② セキュリティ監査 earn（`earn/audit`）は registry 宣言のみ・実装0行だが、実装時に Fable の safety classifier（攻撃的サイバー）で refusal 停止するリスクが未文書。
- **目標**: ① `adversary-daily.sh:23` に `--model opus` を追加。② global CLAUDE.md モデル分業表に1行追加: 「セキュリティ監査・攻撃寄りサイバー/bio 系タスク | Opus 4.8（Fable 5 は safety classifier で refusal を返しうる。refusal 検知時も Opus 4.8 へ fallback）」。
- **検証**: `grep -q '\-\-model opus' ~/anicca/skills/_shared/adversary-daily.sh && grep -q 'refusal' ~/.claude/CLAUDE.md`

### P6: effort を high 既定へ

- **現状**: `~/anicca-project/.claude/settings.json:7` = `"effortLevel": "xhigh"`。ガイド: 「Use high as the default for most tasks, with xhigh for the most capability-sensitive workloads」「On routine work at higher effort, Claude Fable 5 can gather context and deliberate beyond what the task needs」。
- **目標**: ① worktree 内 `.claude/settings.json` を `"effortLevel": "high"` に変更し dev へ merge。② live checkout（feature/clip-rewards）の同ファイルにも同一変更を入れ即 commit+push（同一内容なので後日 merge 衝突しない）。③ global CLAUDE.md モデル分業表のメイン行を「Fable 5（high。設計・監査・難デバッグ等の最重要作業のみ xhigh に一時上げ）」へ更新。
- **検証**: `jq -e '.effortLevel == "high"' ~/anicca-project/.claude/settings.json && grep -q 'high。設計・監査・難デバッグ' ~/.claude/CLAUDE.md`

### P7: loop への send-to-user 配線（PushNotification）

- **現状**: founder-loop に通知経路が構造的に無い（STATE.md + stdout のみ）。claude を spawn する loop CLI 7本 + self-fix.sh の spawn プロンプトに、成果を Dais へ届ける指示が無い。ガイド: 「Defining the tool is not sufficient on its own; without an instruction in the system prompt, Claude Fable 5 rarely calls it.」
- **目標**: 次の8ファイルの spawn プロンプト（`$TASK` 等の定義箇所）に促し文を1行追加: 「**重要な結果（数字・ID を含む成果、realized P&L、致命的エラー）が出たら PushNotification ツールで Dais へ verbatim 送信してから終了する。narration・定常報告には使わない。**」対象: `self/self-fix.sh`, `self/capafy-loop/capafy-loop-cli.sh`, `self/reddit-loop/reddit-loop-cli.sh`, `self/life-manager-loop/life-manager-loop-cli.sh`, `earn/clip-promote/clip-promote-cli.sh`, `earn/video/video-cli.sh`, `earn/clip/clip-cli.sh`, `_shared/adversary-daily.sh`（FAIL verdict 時のみ通知）。
- **検証**: `grep -l "PushNotification" <8ファイル> | wc -l` = 8。E2E: `claude -p --model sonnet` の子セッションから PushNotification を実送信し、tool result の成功応答を確認する（実 side-effect、dry run 禁止準拠）。

### P8: superpowers 全文注入の停止

- **現状**: `~/.claude/plugins/cache/superpowers-marketplace/superpowers/5.0.7/hooks/hooks.json` の SessionStart entry が using-superpowers SKILL.md 全文（「1%でも可能性があれば MUST」）を毎セッション注入。plugin 単位無効化は skill 群が道連れになるため不可。
- **目標**: 同 hooks.json から SessionStart entry のみ削除（JSON validity 維持）。skill 本体・他 hook は残す。skill の使い分けは既に global/project CLAUDE.md の GLVS 表が担っており、CLAUDE.md への追記は不要。
- **検証**: `jq -e '[.hooks.SessionStart // [] | .[].hooks[]?.command | select(test("session-start"))] | length == 0' <hooks.json>` かつ `jq . <hooks.json>` が valid。

## 耐久性（plugin cache 編集の宿命）

P1・P2b・P8 は plugin cache（`~/.claude/plugins/cache/`）内の編集であり、**plugin update/reinstall で復活しうる**。対策: 検証スクリプト `.vcsdd/features/fable5-config-slimdown/tests/verify.sh` を drift 検知器として恒久保存し、memory に「plugin update 後は verify.sh を再実行」と記録する。

## ロールバック

編集/削除前に必ず `~/.claude/backups/fable5-slimdown-2026-07-07/` へ元ファイルをコピーする（~/.claude は git repo ではないため backup が唯一の復元手段）。

## E2E 判定（GATE 3 相当）

Maestro 不要（iOS 非対象）。代替 E2E = **新規 `claude -p` セッションを実起動**し、次を子セッション自身に報告させる: 「セッション開始時に注入されたテキストに『You have superpowers』『Never without explicit user request』『Thinking Patterns』『LOOPエンジニアリング検証プロトコル』が含まれるか」→ 全て「含まれない」が期待値。+ P7 の PushNotification 実送信。

## Done（完了条件）

1. verify.sh 全アサーション PASS（実装前は全 FAIL = RED を記録）
2. fresh-context adversary（Opus 明示）が spec 準拠を PASS 判定
3. E2E: 新セッション fresh evidence + PushNotification 実送信成功
4. push 完了: `~/anicca`（main）、anicca-project（worktree→dev merge + live checkout の P6 commit）
5. worktree remove + branch 削除
6. memory 更新（drift 検知の運用 + 変更サマリ）
