# Connector O1B-22 coverage continuation 設計

## 目的

rolling 21日coverageに`open`が残る限り、検索一巡・一操作失敗・一source失敗を日次loopの終了へ変換しない。

## 状態機械

- `open = 0`だけが`complete`。
- unknown external effectがあれば、二重応募せず`reconcile_effect`を次actionにする。
- auth/transport/inventory回復が必要なら`recover_source`を次actionにする。
- source失敗・empty・検索一巡・候補exhaustionは`refresh_inventory`を次actionにする。
- 全てのcontinuationはboundedな`next_run_at`を持ち、同一processのbusy-loopにはしない。
- outcomeが空でも`open > 0`なら停止せず`refresh_inventory`を予定する。

## 完了条件

verified coverageだけを入力にし、`open = 0`以外で必ず次actionと次回時刻が作られ、plain cloneや未知statusを拒否する。
