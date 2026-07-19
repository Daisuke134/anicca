# Marketing Engine Strangler Fig slice 1

## Goal

`clip` と `capafy-marketing` が複製している Instagram ACCOUNT PROVISION と DURABLE GOLDEN SESSION の prompt を `skills/earn/marketing-engine/` の単一実装へ移し、既存 loop の投稿・warmup 挙動を変えない。

## Invariants

1. `marketing-engine/account_state.sh` は `resolve_ig_handle <state_file>`、`resolve_ig_port <state_file>`、`ig_provision_reason <handle> <cooked_marker>` を提供する。
2. resolver は末尾側の `status in {ready,warming}` かつ poisoned/frozen/blocked flag がなく handle を持つ行を選ぶ。既存 Capafy public 関数は shim として同じ結果を返す。
3. ACCOUNT PROVISION prompt は account state file、handle prefix、instance、Gmail plus-tag prefix、bio 文言を変数で受ける。
4. DURABLE GOLDEN SESSION は browser `sessionid` を保存せず、`Client().login(user, pw)`、`get_timeline_feed()` 生存確認、`dump_settings` の順を必須とする。この canonical 文言は1ファイルだけに置く。
5. `clip_pass.sh` と `capafy-ig-marketing-daily.sh` は canonical renderer を参照し、PROVISION prompt 本文を保持しない。
6. clip と capafy の既存 account state、browser isolation、success status、failure marker、投稿、warmup の意味は変えない。
7. 1本でも既存 test が red なら載せ替え失敗。commit・pushしない。

## Exit proof

| ID | 証拠 | 状態 |
|---|---|---|
| T1 | 変更 shell 6本 `bash -n`。`shellcheck` 5本 green（dynamic source の SC1091 のみ除外） | green |
| T2 | baseline/after とも poisoned `useclaudeskills`=`handle=none`、marker=`cooked-marker` | green |
| T3 | Capafy account-state/provision 28/28、Python 6/6、loop audit 3/3 | green |
| T4 | clip shell 8/8、pytest 53/53。baseline と after が同数 | green |
| T5 | PROVISION と DURABLE GOLDEN SESSION の定義数が baseline 2、after 1 | green |
| T6 | feature branch commit を remote push | pending |

## TODO

| 順序 | 作業 | 状態 |
|---|---|---|
| 1 | 共有 account-state module と Capafy shim | completed |
| 2 | canonical provision prompt renderer と2 loop wiring | completed |
| 3 | resolver、構文、Capafy、clip test | completed |
| 4 | 重複数と diff 監査 | completed |
| 5 | commit・push | in_progress |
