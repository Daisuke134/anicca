# Anicca プロジェクト

全体方針（検索優先/push/no-human-loop/GLVS/TOKEN の物理/TaskList/モデル分業/ツール既定）は `~/.claude/CLAUDE.md` が正本。ここは repo 固有だけ。
**このファイルは毎 API 呼び出しで再読込される固定費。詳細は書かず、参照1行にする。**

## 根本原則

BP = 答え。オリジナルは書かない。判断には最低1つの引用（ソース名+URL+核心の一文）。引用のない判断は削除する。
**研究したら即 MD 化（HARD）**: 検索・研究したらその turn 内で `docs/` の MD に書き出して commit+push する。chat だけに残すのは研究を捨てるのと同じ。handover/article prompt にはその MD の full path を含める。
**記事ネタは queue へ（HARD）**: Dais が「これ記事になる/raw material」と言ったら、その turn 内で article loop の `topics/queue/` にカードを書いて commit+push（場所は `ls -d ~/profitable-claude/skills/*/topics/queue ~/profitable-claude/skills/*/article*/topics/queue 2>/dev/null` で解決、frontmatter は既存カードに倣う: lane/voice/sources/angle）。散らばせたネタは存在しないのと同じ。

## 🧬 ANICCA COLONY — LIVE SSOT

→ `.claude/rules/colony.md`

## 開発（GLVS の Build/Verify = VCSDD の実コマンド）

→ `.claude/rules/vcsdd-flow.md`

## spec = SSOT（HARD。会話は揮発、file は不揮発）

**spec は「書いて終わり」ではなく、発見のたびに更新し続ける生きた現実の地図。** 次に引き継ぐ agent は
会話を見られない。spec だけを見て現実を理解する。だから spec が古い/嘘だと、後続は幻をデバッグする。

| 発火条件 | やること（その turn 内で。後回し禁止） |
|---|---|
| 実測で事実が判明した | spec/STATUS の該当行を実測値に書き換え + commit&push |
| 前の記述が誤りと分かった | **消して是正を書く**（併記しない）。誤りだった旨も1行残す |
| 詰まった / 仮説が外れた | 何を試して何が false だったかを spec に書く（次の人が同じ穴を掘らない） |
| 新タスクが生えた | TaskCreate + spec の TODO 表に追加（二重トラック） |
| 状態が変わった | TaskUpdate（着手=in_progress、完了=completed） |

- **登録していないタスクは存在しない。spec に書いていない発見は捨てたのと同じ。**
- 断定は実 tool_result のみ。**tool 出力の捏造は最悪の罪** — 存在しない機能を「実装した」と書けば、
  後続は存在しない問題の真因を一晩探す（実例: 2026-07-15 の「x402 seed step を実装・commit した」は
  全て虚偽。grep 0ヒット、commit d9f1e0f2c は存在せず、次セッションが丸一晩を溶かした）。
- x402/colony の SSOT = `docs/STATUS.md` + `docs/superpowers/specs/2026-07-14-x402-zero-to-one-spec.md`。
  新ファイルを乱立させず、この2本を更新する。

## HONESTY

symbol/function/import の存在は使う前に Read/Grep で確認する（できなければ `// UNVERIFIED:`）。テスト/ビルド成功はこの session 内で実行してから claim する。見ていないエラーを創作しない。分からない時は「分からない」と言う。
Hook: PostToolUse が Edit/Write 後に構文チェック、Stop hook が session 終了前に再チェック。commit 前の独立監査 = `.claude/agents/fact-checker.md`。

## 実行環境 / 配置

Mac Mini（`anicca-mac-mini-1`、Tailscale 100.99.82.95）で直接実行。自分に SSH しない。MacBook = `ssh cbns03@100.108.140.123`。VPS は使わない。

| ローカル | push 先 | 役割 |
|---|---|---|
| `~/anicca-project/` | anicca-products (public) | iOS/web/api/mobile。Anicca instance からの直接 write 禁止 |
| `~/.openclaw/` | anicca-dais (private) | gateway/cron/skills/state（cron 正本、trunk=main-internal） |
| `~/anicca/` | anicca (public OSS) | OSS フレームワーク |

**Life Manager**: cloud 本番 = `anicca-products` **origin/main** `apps/life-call/`（Railway。dev/feature branch には無い）。local 版 = `~/Projects/life-manager`（Daisuke134/life-manager、収斂予定）。SSOT spec → `docs/superpowers/specs/2026-07-17-life-manager-cloud-alignment-and-dev-loop.md`、vision → `docs/loop-engineering/46-life-manager-northstar-and-personal-loops.md`

GitHub Actions の新規追加は禁止（`netlify-deploy.yml` の1個のみ）。定期実行は `~/.openclaw` の gateway cron が正本。
詳細（folder tree / architecture 図 / write 制限 / fleet全体の現状）→ `docs/reference/local-env-and-architecture.md`（tracked、全 Claude/Codex session が読める。CLAUDE.local.md は gitignored の個人設定のみ）。

## ブランチ & デプロイ

→ `.claude/rules/ios-deploy.md`

## 概要

**Anicca** = プロアクティブ行動変容エージェント（iOS Swift/SwiftUI + Node/Express + PostgreSQL/Prisma + RevenueCat + OpenClaw agent）。
team = generalist（ccteams）。委譲時は skill `generalist-playbook` と `working-method` を読ませる → `.claude/active-team.md`。

## 言語

回答は常に日本語。
