# Capafy IG account self-heal spec

## Goal

`capafy-ig-marketing-daily` が cooked account を再利用せず、`~/.cloak/clip-accounts-capafy.json` から active handle を解決し、active account 不在時は clip loop の実証済み PROVISION 手順で fresh account を作る。

## Invariants

1. `~/.cloak/clip-accounts-capafy.json` は account array `{handle,profile,port,lang,status,session_owner,created,...}`。末尾側の `status in {ready,warming}` かつ poisoned/frozen/blocked でない行を active account とする。
2. daily script、warmup script、goal monitor は handle literal や daily source の文字列解析を持たず、共通 resolver から handle/port を取得する。
3. cooked marker 存在時または active handle 不在時、daily pass は PROVISION のみ実行し、produce/post/bio を実行しない。
4. PROVISION は `ig-account-create` proven flow を使う。residential home IP、NO proxy、Gmail plus-address `keiodaisuke+capafy<tag>@gmail.com`、`gog gmail ... in:anywhere` OTP、day-0 link 無し bio、既存 :9222 tab 非操作、isolated context の新 tab を必須とする。
5. browser `sessionid` は保存・`login_by_sessionid` 使用禁止。fresh account password で `Client().login`、`get_timeline_feed()`、`dump_settings(~/.cloak/instagrapi-<handle>.json)` の順に durable golden session を作る。
6. feed 生存確認成功時のみ state に `status=warming`, `session_owner=instagrapi` を append し cooked marker を削除する。失敗時は `status=provision_failed` を appendし、marker を残し、Telegramへ `provision-blocked:<reason>` を送る。
7. fresh account は day 1-2 投稿ゼロ。`warm.py` の day>=3 到達後のみ既存 posting flow が live になる。

## Exit proof

| ID | 証拠 | 状態 |
|---|---|---|
| T1 | daily / warmup / helper の `bash -n`、poster の `py_compile` 成功 | green |
| T2 | `EMPTY resolver=[]`、`ACTIVE resolver=[capafy_fresh]` を実測 | green |
| T3 | probe 実測: empty=`provision_needed=yes reason=no-active-account`、active=`provision_needed=no` | green |
| T4 | account-state 17/17、capafy audit 3/3、clip unittest 53/53 | green |
| T5 | goal monitor probe が active handle/port/state path を解決し、source parsing を使わない | green |
| T6 | verified change set を本 commit へ収録し remote push | green |

`clip` unittest は poison/login refusal の negative test で意図的に `ChallengeRequired` / `LoginRequired` を stderr へ出すが、test runner は `Ran 53 tests ... OK`、exit code 0。
