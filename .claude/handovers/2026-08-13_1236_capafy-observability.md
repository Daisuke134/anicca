# Capafy observability/recovery handover

## 正本

- 仕様書: `/Users/anicca/anicca/docs/superpowers/specs/2026-08-01-capafy-self-improving-revenue-loop-design.md`
- 残TODOの唯一の実行順: `## 12. Remaining implementation backlog` → `#### Current atomic queue — authoritative order`
- 最初の未完了項目: `1. Restore authoritative money reconciliation before every report and every Builder early return.`

## Git routing

- 既存worktree: `/Users/anicca/anicca`
- branch: `feature/dist1-mcp-launchd`
- upstream/push: `origin/feature/dist1-mcp-launchd`
- verified commit: `22dfc0cb983c763732b483edc73b33278854e52c`
- このworktreeにはCapafy外の稼働生成物、x402ログ、reddit state、`.codegraph/.gitignore`削除が残っている。reset/clean/stash/switch禁止。次セッションはfetch後にHEAD/upstream/dirtyを再確認し、実装は `/Users/anicca/anicca/.worktrees/capafy-observability-recovery` と新規branch `feature/capafy-observability-recovery` を上記commitから作る。spec更新も同branchで行う。reviewは検証対象commitの一時detached snapshotを使う。

## 実測済み状態

- Capafy API: 累計5注文、有料2件、gross `$19.98`、refund `$0.00`。有料日は2026-06-23と2026-08-08。2026-08-05/10/12は各1件・`$0.00`で意味は未確認。
- payout API: `balancePayout=8.0`, `balancePending=6.4`, `balanceConfirmed=0`, `totalPayout=0`。
- ローカルearn ledgerは2026-08-03で停止し、8月の4注文を欠落。Telegram/company projectionは1注文・`$9.99`のまま。
- inventory: 32件 = online 21 / review-rejected 9 / draft 2。
- Builder: 08:10、last exit 0。ただし`CAP_FULL`でreconcile/agent/self-improvement前に終了し、同一no-opの永続dedupeで日次TGも止まる。
- goal monitor: 09:30のみ、last exit 2。projection mismatch / event_id conflict。最終正常配信は2026-08-03。hourlyと23:50 daily-closeの本番jobは存在しない。
- outcome monitor: 60秒、last exit 0だが`verified -> unresolved`とevent conflictを反復。
- healthcheck: source/installed plistは300秒だがlaunchctl未load。
- Marketer: 16:00、last exit 2。`active Instagram browser tab is missing`。durable lifecycleは`@capafy.skills8m4q2z` commercial-ready、Reel `https://www.instagram.com/reel/DbhCWLhorxy/`で、live browser truthと矛盾。

## 境界と最初の一手

- 今回は調査・spec更新・handoverのみ。production code、launchd state、投稿、商品操作は変更していない。
- Codexが個別商品を作る/投稿することは禁止。修理後の実行主体は既存launchd loop。
- 最初の安全な実装はTODO 1のみ。`capafy_earn_reconcile.py`をTDDで直し、`capafy-loop-daily.sh`の`CAP_FULL`より前にreconcileを移し、live APIとfixtureで5件/$19.98、ゼロドル注文保持、二回目idempotentを証明する。
- 完了主張前にfresh adversarial reviewerが一次証拠で反証する。仕様のTODO状態・検証・commitを更新してpushしてから次項目へ進む。

## 検証状況

- 調査はlive Capafy authenticated API、launchctl readback、production state/logで実施。
- 今回はコード未変更のためテスト未実行。specは`git diff --check`通過、commit/push済み。
- 実装後は各項目のDone条件に加え、live readbackとTelegram messageIdを必要とする。fixture/mockだけで完了にしない。

## 新セッション用prompt

完全版は隣の `2026-08-13_1236_capafy-observability-goal.txt` をそのまま送信する。
