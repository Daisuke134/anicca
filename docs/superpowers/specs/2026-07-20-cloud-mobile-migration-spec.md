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
| 1 | **auto-sync 機構**: Mac Mini の live 資産 repo（~/.openclaw、~/anicca、~/anicca-project docs）を定期 commit+push する仕組み。既存 gateway cron に載せる（新 launchd を作らない。cron 正本 = openclaw gateway）。gitleaks pre-push 付き | cron 登録実測 + 1回実走で push 成功 + gitleaks 0 leaks | implemented; pending Fable live registration/run |
| 2 | **status-to-repo**: colony-status.sh の出力を docs/STATUS-live.md に定期書き出し（#1 の sync に同乗）。phone から repo を見るだけで loop 稼働/残高が分かる | STATUS-live.md が repo に現れ、値が実測と一致 | implemented; local live output verified |
| 3 | **phone runbook**: docs/reference/phone-runbook.md — Claude iOS Code タブの接続手順（GitHub App で 3 repo 許可）、Termius+Tailscale SSH 手順、緊急時（loop 死亡/ディスク満杯）の一次対応コマンド集 | ファイル存在 + 手順が実環境の値（repo 名/IP）と一致 | implemented; pending Fable verification |
| 4 | **cloud session 実証**: Fable が Claude web で anicca-project session を1回開き、AGENTS.md/rules が効いてることを確認 | cloud session の実行ログ | pending(Fable) |

## 進捗記録
- 2026-07-20: spec 作成。#1-3 を Sol へ発注。
- 2026-07-20: #1-3 の repo 内成果物を実装。`bash -n`、ShellCheck、隔離 git remote への同期テストが成功。`colony-status.sh` の live 出力から `docs/STATUS-live.md` を生成。gateway cron 登録と live repo での commit/push は Fable 実行待ち（Sol は repo 外を書き換えていない）。
