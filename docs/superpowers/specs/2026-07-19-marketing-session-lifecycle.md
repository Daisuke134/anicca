# Marketing Engine Account Session Lifecycle

## Goal

clip と capafy の共有 provision は account 作成日を day1 とし、day1-2 は browser warmup のみ、day3 で instagrapi golden session を一度だけ確立する。保存 session が死んだ account は password relogin せず破棄対象にする。

## 不変条件

- provision 成功は signup、profile、credential 保存、state append まで。day1 に `Client().login`、`login_by_sessionid`、`~/.cloak/instagrapi-<handle>.json` 作成を行わない。
- provision row は `status=warming`、`session_owner=browser`、`started_warming=<作成日>`、`created=<作成日>` を持つ。
- day は `started_warming` から `経過日数 + 1` で数える。作成日は day1。day1-2 は ready にしない。
- day3 以降の warming account は settings file が未作成かつ golden-login 未試行の場合だけ `Client().login` を一度実行する。`get_timeline_feed()` 成功後だけ settings を dump し、`session_owner=instagrapi`、`status=ready` にする。
- settings file または golden-login 試行記録が存在する account に password login を行わない。保存 session が死んだ場合も relogin しない。
- goal-monitor の `--verify-only` は `session_owner=instagrapi` かつ day>=3 の account だけに実行する。browser owner または day1-2 は skipped とし cooked marker を作らない。
- `clip_pass.sh` と `clip_daily.sh` は共有 `marketing-engine/provision_prompt.sh` を参照し、独自 lifecycle 文言を持たない。
- account state 配列の row 数と既存 row 順序を保つ。

## 原因仮説と実測

| 仮説 | 実測 | 判定 |
|---|---|---|
| 共有 provision が day1 private API login を要求する | `provision_prompt.sh` が `Client().login`、feed、dump を成功条件にする | 採用 |
| clip の2経路が同じ lifecycle を使う | `clip_pass.sh` は共有 renderer へ `ready` を渡し、`clip_daily.sh` は独自 signup-only prompt を持つ | 棄却。実装が矛盾 |
| warmer が day3 golden session を作る | `warm_step.py` は warm log の day だけ見て `ready` にし、session を作らない | 棄却 |
| goal-monitor は若い browser account を除外する | account owner/day gate なしで全 active account に `--verify-only` を実行する | 棄却 |

## Production state 実測

- `@useclaudeskills` は `status=warming_day1`、`session_owner=browser`、`started_warming=2026-07-18`。実測 account day は2。
- 旧 goal-monitor が作った `.capafy-ig-account-cooked` は存在した。新 owner/day gate の verify probe は `verify_eligible=no`、`poisoned=false`、verify invocation 0回を返し、false marker を除去した。
- legacy `~/.cloak/instagrapi-useclaudeskills.json` は存在する。削除せず、day3 warmer は settings を load/verify し、password relogin を行わない。

## 検証

- `bash -n` で変更 shell script 全て green。
- `python3 -m py_compile skills/earn/clip/warm_step.py` green。
- clip pytest 全件と clip shell tests 全件 green。
- capafy account-state/provision test 全件 green。
- stub 実測で day1 prompt に login/session dump がなく browser/warming/started_warming がある。
- stub 実測で day2 は login 0回、day3 は login 1回と feed 1回と dump 1回、2回目は load-only で login 0回。
- stub 実測で browser owner/day1-2 の goal-monitor は verify-only 0回、cooked marker なし。

## TODO

| Task | 状態 |
|---|---|
| 現状実測、spec、feature worktree | completed |
| day1 signup-only provision | completed |
| day3 golden session one-shot | completed |
| young-account poison false-positive | completed |
| full tests と stub lifecycle 実測 | in_progress |
| commit と push | pending |

## 根拠

- instagrapi Usage Guide: https://subzeroid.github.io/instagrapi/usage-guide/interactions.html — “for long-lived automation, prefer `login()` once, then `dump_settings()` and reuse the saved settings.”
- repo 内 measured policy: `skills/earn/clip/scripts/instagrapi_post.py` は saved settings が死んでも password relogin を拒否する。
