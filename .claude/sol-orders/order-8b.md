# 発注: spec §10 順8b — LM-33b panel read API（5 endpoints、read-only）

正本: /Users/anicca/anicca-project/docs/superpowers/specs/2026-07-19-anicca-one-repo-consolidation-spec.md
必読節: §9.9（5要素: ①今日 timeline+call実績 ②3 organ スコア ③FINANCIAL 台帳 ④gates 状態 ⑤設定）、§9.6（gate 定義）。8a の panel-auth session を前提（origin/dev に merge 済み PR #326）。
役割: Sol = build+execute+verify+spec 更新+commit+push。質問 = bash ~/.agents/skills/agmsg/scripts/send.sh lm-p0 sol-order8b fable-main '<msg>'。
対象: anicca-products、worktree .worktrees/lm-p0-order8b（base = 最新 origin/dev）、branch feature/lm33b-panel-api → PR to dev。GHA 追加可。

## 仕様（全部 session 必須・read-only・JSON）
1. GET /api/panel/timeline — 今日の解釈済み calendar（interpreter 流用）+ lm_wake_log の call 実績（called_at/answered_at）。
2. GET /api/panel/scores — 3 organ スコア v1 は実データの素朴集計: DAILY=今週 call 応答率、PHYSICAL=未通院検知数（無ければ 0 と「未実装」flag）、FINANCIAL=台帳有無。捏造スコア禁止 — データ無い organ は "no_data": true を返す（正直原則）。
3. GET /api/panel/ledger — lm_api_cost 集計 + FIN 台帳（無ければ空配列 + no_data）。
4. GET /api/panel/gates — location/送金先 gate の解錠状態（order7 の判定関数流用）+ 解錠方法文言（§9.11 discovery copy 参照）。
5. GET /api/panel/settings — call_language / 時間帯 / 接続状態（calendar/gmail/TG）。書き込みは不可（鏡）。
6. negative: session 無し→401。他人 uid のデータが漏れない設計（session→uid 束縛を test で証明）。

## 検証
npm test 全 green + 各 endpoint の unit test（fixture DB で 200 + shape 検証）実出力。staging 不可のため curl 実測は Fable の L3 に委ねる — ローカルで server を起動し fixture で 5 endpoints を叩く script を用意し、その実行 exit 0 を報告に含めること。

## 禁止
prod deploy / 書き込み endpoint / スコアの捏造（no_data を隠さない）/ secret 出力。

DONE 報告 agmsg: test 実出力 + ローカル 5 endpoints 実行結果 + PR URL。
