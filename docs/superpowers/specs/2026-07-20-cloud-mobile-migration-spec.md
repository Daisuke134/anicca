# 2026-07-20 Cloud/Mobile 移行 spec（phone-only 運用への配線）

## Goal
Dais が phone（Claude iOS の Code タブ / Codex app）だけで開発・監視・操作できる。MacBook 返却後も何も失わない。

## 前提（実測済み）
- Claude Code on the web/mobile: GitHub App 接続、fresh VM に repo clone、repo 内 CLAUDE.md/.claude/rules/skills/.mcp のみ移送（→ 既に push 済みなので cloud session は同じ規律で動く）。
- Mac Mini へは Tailscale (100.99.82.95) SSH が phone からも可能。loops は Mac Mini 常駐のままで問題ない。
- ~/.openclaw は private repo (anicca-dais) に push 済み（secrets untrack 済み）。

## 不変条件（MUST）
1. **launchd loop の実行実体は Mac Mini に残る**。cloud は「編集・指示・監視」の面。loop 自体の cloud 移設は本 spec の scope 外（別 spec）。
2. **credential は GitHub に載せない**。sync 機構は .gitignore を尊重し、gitleaks を通ってから push。
3. 状態把握は self-report でなく実測（launchctl / git log / colony-status.sh）。

## TODO（Sol 実装、Fable 検証）
| # | task | done 条件 | state |
|---|---|---|---|
| 1 | **auto-sync 機構**: Mac Mini の live 資産 repo（~/.openclaw、~/anicca、~/anicca-project docs）を定期 commit+push する仕組み。既存 gateway cron に載せる（新 launchd を作らない。cron 正本 = openclaw gateway）。gitleaks pre-push 付き | cron 登録実測 + 1回実走で push 成功 + gitleaks 0 leaks | done |
| 2 | **status-to-repo**: colony-status.sh の出力を docs/STATUS-live.md に定期書き出し（#1 の sync に同乗）。phone から repo を見るだけで loop 稼働/残高が分かる | STATUS-live.md が repo に現れ、値が実測と一致 | done |
| 3 | **phone runbook**: docs/reference/phone-runbook.md — Claude iOS Code タブの接続手順（GitHub App で 3 repo 許可）、Termius+Tailscale SSH 手順、緊急時（loop 死亡/ディスク満杯）の一次対応コマンド集 | ファイル存在 + 手順が実環境の値（repo 名/IP）と一致 | implemented; pending Fable verification |
| 4 | **cloud session 実証**: Fable が Claude web で anicca-project session を1回開き、AGENTS.md/rules が効いてることを確認 | cloud session の実行ログ | pending(Fable) |
| 5 | **MacBook Pro 返却（物理・今日/明日）**: Dais が初期化（Apple ID サインアウト→設定>一般>転送またはリセット）→ 箱 or プチプチ + 充電器・ケーブル同梱 → 郵送: 〒630-0192 奈良県生駒市高山町8916-5 奈良先端科学技術大学院大学 脳・行動モデリング研究室 谷本様 TEL 0743-72-5354（金曜来学 or 郵送、先方指定）。前提の「MacBook 依存ゼロ」は確認済み（Dais 明言 + Mac Mini 側監査済み） | 発送完了 | pending(Dais 物理) |
| 6 | **floor 残り弾の適用**: floor-reduction/ の sessionstart-hooks.patch・global-claude-md.diff・memory-md.diff・floor-guard-patch.diff を Sol が適用+検証（.bak 必須、global CLAUDE.md/MEMORY は Dais 規律のため意味を変えない移設のみ） | 適用後 新session /context で floor 低下 + 全 hook/session 正常動作 | pending(Sol) |
| 7 | **global rules 単一実体化 Phase 2**: ~/.claude/CLAUDE.md ⇄ ~/.codex/AGENTS.md を実体1つ+import/link に（docs/loop-engineering/49 の裁定に従う）。Sol が提案 diff → 適用 → 両 CLI で規律ロード検証 | 両 CLI が同一実体から規律を読む実測 | pending(Sol) |

## 進捗記録
- 2026-07-20: **skills ロード診断完了 (A)**。`~/.agents/skills` の実体65個と `~/.claude/skills` の symlink 11本を実測。fresh `claude -p` の自動公開一覧には8個が出現し、`flowa` / `flowb` / `fable-prompter` の3個だけが非表示。この3個は全て frontmatter が `disable-model-invocation: true` で、fresh session からの明示 `/flowa` / `/flowb` / `/fable-prompter` はそれぞれ `*_EXPLICITLY_LOADED` を返した。従って真因は symlink ロード不良ではなく、意図された自動呼び出し抑止。仮説は (1) symlink 追跡 depth: 全11本 depth=1・`SKILL.md` 存在で否定、(2) frontmatter `name` 不一致: 11/11 directory名と一致で否定、(3) plugin cache: 明示 slash の fresh 解決成功により否定、(4) `.skill-lock.json`: `~/.claude` 配下に存在せず否定。marketplace `caveman/skills-lock.json` は別物。全11個のロードを「8自動公開 + 3明示呼び出し」で実証したため設定変更は不要。rollback は `~/.claude/skills.bak-20260720` の存在を確認。
- 2026-07-20: spec 作成。#1-3 を Sol へ発注。
- 2026-07-20: #1-3 の repo 内成果物を実装。`bash -n`、ShellCheck、隔離 git remote への同期テストが成功。`colony-status.sh` の live 出力から `docs/STATUS-live.md` を生成。gateway cron 登録と live repo での commit/push は Fable 実行待ち（Sol は repo 外を書き換えていない）。
- 2026-07-20: auto-sync の明示 pathspec に gitignored directory が含まれると `git add` 全体が失敗する不具合を修正。各 path を `git check-ignore -q` で事前除外し、eligible path が残らない repo は skip する。OpenClaw の ignored `agents/anicca/agent/codex-home` を含む回帰 fixture で、他 path が add 対象に残ることを確認。anicca の明示対象に `.worktrees` は含めない。`bash -n`、ShellCheck、`test-cloud-migration.sh` PASS。auto-sync の live 実行はしていない。
- 2026-07-20: auto-sync live 実走を最大3回実施。各回とも `anicca-project=pushed`、`openclaw=error (git add: agents/anicca/agent/codex-home is ignored)`、`anicca=error (git add: .worktrees is ignored)`。ignored descendant の exclude pathspec 追加は fixture で RED→GREEN まで確認したが live Git の明示 root 拒否を解消できず、PASS 条件未達のため gateway cron 登録・手動発火・#1/#2 done 更新は未実施。
- 2026-07-20: Fable 引き継ぎの2修正（ignored 一覧の巨大 exclude 生成削除、ignored embedded repo の skip）を維持。OpenClaw staged leak は `skills/cfo-core/data/anicca-hourly.err` の `curl-auth-user` と特定し、staging から除外して `~/.openclaw/.gitignore` に追加（secret 値は非表示）。Gitleaks 公式 README と live CLI v8.30.1 の stdin mode を確認し、`scan_staged` を `git diff --cached --binary --no-ext-diff --diff-filter=ACMRTUXB | gitleaks stdin` に変更。回帰 test を RED→GREEN、`test-cloud-migration.sh` PASS、OpenClaw の staged-only scan exit 0 を確認。cron 登録前の3 repo live 実走は次工程。
- 2026-07-20: live fix loop 2回目で `openclaw=pushed`、`anicca=skipped`、`anicca-project=pushed`、error 0。初回の OpenClaw push は、既存未push commit に含まれた GitHub 上限超過生成物（155 MB JSONL、578 MB backup archive）で拒否されたため、復旧 ref `backup/pre-cloud-sync-rewrite-20260720-1404` を作成し、実ファイルを保持したまま履歴から除外・gitignore 化して remote `c1325812` へ push。gateway cron `cloud-mobile-auto-sync`（ID `a4577898-066f-4ac7-af17-5594f0039b45`）を every 30m / isolated / no-deliver で登録し live list で確認。手動 run `manual:a4577898-066f-4ac7-af17-5594f0039b45:1784556530436:1` は status ok、3 repo 結果は pushed/skipped/pushed。`docs/STATUS-live.md` の remote commit は `d5a1ef52ce88edf1b9b23ece49ff59d3a7aa291e`。
