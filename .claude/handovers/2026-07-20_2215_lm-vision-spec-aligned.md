# Handover 2026-07-20 22:15

- spec: `/Users/anicca/anicca-project/docs/superpowers/specs/2026-07-19-anicca-one-repo-consolidation-spec.md`
  （§9 = product vision / UX matrix / TG copy bank 逐語、§10 = 残 TODO 表）
  補助 spec: `/Users/anicca/anicca-project/docs/superpowers/specs/2026-07-17-life-manager-cloud-alignment-and-dev-loop.md`（§5c 実測ログ）
- 残 TODO の正本 = 上記 spec の **§10 TODO 表**（13件、順序付き）。TaskList と二重トラック。
- 未 commit の変更に関する注意点: なし（spec は全て commit+push 済み。branch `feature/clip-rewards`。
  作業 repo 由来の `aniccaios/*.pbxproj` 削除 stage + `work/bug-bounty-743` 変更が index に残っているが本作業とは無関係 — 触らない）。
  実測済み事実1件: prod TG webhook の `allowed_updates` に `callback_query` を追加登録済み（2026-07-20 実測。ボタン無反応の真因だった）。

## /goal（次セッション用）

/goal Life Manager を spec §10 の TODO 表13件の順に完遂する。正本 = /Users/anicca/anicca-project/docs/superpowers/specs/2026-07-19-anicca-one-repo-consolidation-spec.md（§9 = vision/UX/copy 正本、§10 = TODO 表）+ 補助 /Users/anicca/anicca-project/docs/superpowers/specs/2026-07-17-life-manager-cloud-alignment-and-dev-loop.md（§5c 実測ログ）。まず両 spec を読み、§10 を上から順に着手。

Done = §10 の13行すべてが、各行の done 条件列に書かれた実 side-effect の証拠（実 call 録音の whisper 文字起こし・実 TG 着信・実メール message_id・launchctl list 実出力・API 200 実測・実投稿 URL・on-chain tx）で spec §10 に実測値つき「done」と記録され、commit+push されている状態。順1の実証束が最優先ゲート — DAIL Y の実 call E2E が green になるまで順5以降のコード変更に着手しない。順2-4（launchctl 常設 / Unipile 再発行→flip / secret rotate）は順1と独立なので並行可。

検証規律: 「出た?/まだ?」質問はいかなる形でも出荷しない（§9.5 裁定）。DB の answered_at や自己申告ログは証拠にならない — 録音・実 TG・実メール・on-chain を自分の目で見る。テスト/lint green はコード変更の前提であり Done の証拠ではない。各 TODO close 時に §10 の該当行を実測値で更新+commit+push。

実装は flow A hybrid: Fable が plan、Sol subagent が実装（worktree .worktrees/lm-p0 系、VCSDD phase 順、adversary fresh spawn）、Fable が実 E2E で最終検証。spec の decision（§9.5-9.11 の copy・gate・廃止裁定）を実装側で曲げない。

Stop: 同一 TODO で3手法連続 FAIL → §10 に false だった仮説を記録して次の独立 TODO へ進み、最後にまとめて報告 ／ prod schema 破壊・課金経路変更・承認外 broadcast が必要になった時 ／ Unipile flip は token 再発行の 200 実測前に行わない ／ copy（§9.11）の変更は Dais 編集領域なので提案までに留める。progress は spec §10 が唯一の live 状態。会話でなく file に書く。
