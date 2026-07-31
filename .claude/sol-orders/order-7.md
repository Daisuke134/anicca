# 発注: spec §10 順7 — LM-32 feature discovery 告知 loop（週1・未解錠 gate のみ）

正本: /Users/anicca/anicca-project/docs/superpowers/specs/2026-07-19-anicca-one-repo-consolidation-spec.md
必読節: §9.6（CONTEXT GATES 表 + 「feature discovery: 週1程度・解錠済みは告知しない」）、§9.11 FEATURE DISCOVERY 節（逐語 copy 2種: location / 口座・wallet。この文字列そのまま、表から生成）、§9.5（1メッセージ=1用件。質問ではなく招待 — inline ボタン [やり方を見る][今はしない]）。
役割: あなた(Sol) = build+execute+verify+spec 更新+commit+push。質問 = bash ~/.agents/skills/agmsg/scripts/send.sh lm-p0 sol-order7 fable-main '<msg>'。
対象: anicca-products、worktree .worktrees/lm-p0-order7（base = 最新 origin/dev、order6 merge 済み）、branch feature/lm32-discovery → PR to dev。GitHub Actions の追加は可。

## 何を作るか
週1回、未解錠 gate を1つだけ選んで TG で知らせる loop。scheduler の既存 tick 基盤に週次 job として追加（新 cron/launchd を作らない — in-process が現行アーキ）。

## 仕様
1. gate 状態の判定（user ごと）: location gate = 最新 live location が無い or 期限切れ（order6 の保存先を参照）／ 送金先 gate = 送金先未登録（lm_users の該当列。無ければ additive migration で用意 — FIN organ が後で使う）。
2. 送信条件: (a) 未解錠 gate が1つ以上 (b) 前回 discovery 送信から7日以上（lm_users に last_discovery_at、additive）(c) 1通に1 gate のみ（複数未解錠なら rotation）(d) 解錠済み gate には絶対に送らない。
3. copy は §9.11 の表の文字列を i18n テーブル（string map）に移して参照。コード直書き禁止。
4. ボタン: [やり方を見る]（location: TG の共有手順を返信）[今はしない]（通常週次に従う）。既存 telegram callback 基盤流用。
5. L1 unit test: 判定・7日 throttle・rotation・解錠済み除外の境界。L2 eval 不要（deterministic）。

## 検証
npm test 全 green（実出力）。staging deploy は Railway 認証復旧待ちのため BLOCKED-on-Dais と PR に明記し skip 可。実 TG 着信は Fable の E2E — 送信関数を単体で叩ける test hook / script を用意すること。

## 禁止
prod deploy / prod webhook 変更 / §9.11 copy 改変 / 解錠済み gate への送信経路 / 週1超の頻度 / secret 出力。

DONE 報告 agmsg: test 実出力 + PR URL + Fable E2E 用の実行手順1行。
