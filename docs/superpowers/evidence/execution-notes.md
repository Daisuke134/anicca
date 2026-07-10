# Execution Notes — 残TODO #5-#9.5 (goal 実行ログ)

正本 spec: `docs/superpowers/specs/2026-07-10-connector-loop-design.md` §8/§10/§11
scope 境界(Dais 2026-07-11): profitable-claude = 銀行口座+Dais 自身の稼ぎ。crypto(PM/SOL/HL)+Franklin = 別CC(anicca repo main loop)担当、ここでは触らない。

## 現在の open items / state

| # | 作業 | state | evidence MD |
|---|---|---|---|
| 6 | CEO を生かす + cron drift | 🔄 in_progress | 06-ceo.md |
| — | 収益ループ1本を閉じる | ⬜ pending | revenue-loop.md |
| 5 | connector 7日 streak | ⬜ pending (cron ad89027d 自動発火待ち) | 05-connector.md |
| 8 | LM Phase B (Reddit+IG セルフマーケのみ, issue-driven OFF) | ⬜ pending | 08-lm-phaseB.md |
| 9.5 | SNS factory 移行 (準備のみ, 退役=Dais go 待ち) | ⬜ blocked-on-go | 095-sns-migration.md |

## #6 CEO — 真因(investigation 2026-07-11 裏取り済)
- **ceo-decisions 0行の真因**: `bin/ceo-run.sh`(no-args=週次agent-judgment) を起動する scheduler が皆無。launchd `ai.anicca.ceo-runner.plist` は `--light-pass`(決定論budget-checkのみ)専用。
- **cost 自己申告 fabrication**: 記録は各loop agent が pass 末に `record-cost-event.sh` を叩く自己申告方式(正しい設計)。affiliate は「記録した」と申告したが実際は未実行=偽申告。照合機構が無いのが gap。
- **registry**: pm/hl/sol=external は crypto=別CC担当で正しい。capafy/article=bank-earning だが未live。external loop に last_observed_at 無し=CEO が silent-blind。
- **enforcement**: 正しく動作、閾値未達で未発火なだけ(変更不要)。
- **cron codex-harness**: plugin 04:49 導入+07:50 gateway 再起動で修理済。4件(reelclaw/larry/watercolor, daily 0 7)は stale 表示、次回 07:00 JST run で自動復帰見込み。lm-video-store が 07-11 直近 ok で harness 復活を実証。

## #6 実行計画
1. [ops] CEO core を1回 live 起動 → 実 decision + enforcement 観測 ← 実行中
2. [VCSDD lean] scheduler plist 新設(週次 no-args) + cost 自己申告照合(REQ-CEO-020) + registry last_observed_at
3. [ops] cron 4件 stale の自然復帰を 07:00 後に確認

## 決定事項
- crypto は別CC。LM は Reddit+IG セルフマーケのみ(issue-driven OFF、削除せず)。
