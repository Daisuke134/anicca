# Task 3 implementer report

## Status

実装完了。agent-economy のコード release root を `~/loops/life-manager` に固定し、既存の
`~/loops/agent-economy` instance state namespace は変更していない。plist は全候補を検証して
から書き込み、`.worktrees` と source checkout を拒否する。namespaced current/previous は sealed
`RELEASE.json` の release identity を検証し、current の切替と rollback は sibling symlink の
atomic rename を使う。generic loop/cutter の既定値は従来の `~/loops` 経路を維持した。

## TDD evidence

RED（テスト追加後、production変更前）:

```text
node --test test/agent-economy-control-plane.test.mjs
```

結果: 9 tests / pass 6 / fail 3。agent-economy の namespaced current、worktree 拒否、release
metadata identity が未実装だったため失敗した。

GREEN（focused）:

```text
node --test test/agent-economy-control-plane.test.mjs test/install-release-state.test.mjs
```

結果: 11 tests / pass 11 / fail 0。sealed release fixture、二段 cut の current/previous、
`--rollback` による exact target 復元、不正 previous の fail-closed、installer の release
readback と instance state 維持を実測した。`test/install-agent-economy.test.mjs` は存在しないため、
既存の `test/install-release-state.test.mjs` に agent-economy の focused fixture を追加した。

Agent Economy 全体:

```text
npm run test:agent-economy
```

結果: 87 tests / pass 87 / fail 0。

追加確認:

```text
node --test test/install-release-state.test.mjs test/install-isolation.test.mjs
python3 -m py_compile bin/plistgen.py
bash -n bin/cut-loop-release.sh skills/agent-economy/launch.sh install.sh
node --check test/agent-economy-control-plane.test.mjs
node --check test/install-release-state.test.mjs
git diff --check
```

全て終了コード0。live launchctl、daemon 起動、実 install、実 release promotion、provider/network
effect は実行していない。

## Implementation notes

- `loops/agent-economy/loop.toml` は `release_root=~/loops/life-manager` と stable current を宣言し、
  plist に sealed release の id/SHA を read back する。
- `bin/plistgen.py` は build/write を二段階に分け、どの job の unsafe path でも plist を一件も
  書かない。agent-economy だけ current symlink、release-root containment、metadata identity、
  read-only seal を必須にし、他 loop の pre-cut rendering は残した。
- `bin/cut-loop-release.sh` は `--rollback` を追加し、通常 cut では旧 current を exact previous
  に保存してから current を切り替える。`LOOPS_ROOT` 未指定は従来どおり `$HOME/loops`、
  basename が `life-manager` の namespace では metadata/seal validation を強制する。
- `skills/agent-economy/launch.sh` と agent-economy installer は current が同一 namespaced
  release、sealed `RELEASE.json`、metadata SHA/release id と一致することを確認してから daemon
  を実行する。state は別 namespace のまま。

## Commit

この report と指定 production/test files を単一 commit にまとめる。push は行わない。

## Rethink fix (2026-08-27)

前回の stable-current 実装を再監査し、実行時 code/state 境界を修正した。plist の
`ProgramArguments`、`ANICCA_REPO`、`ANICCA_CODE_ROOT` は current symlink ではなく生成時に
検証した exact resolved release を指す。launch は `BASH_SOURCE` から同じ release を導出し、
current を再読込しない。pinned daemon/index/run-skill/self-update は git pull、skill rsync、
node_modules link、periodic self-update を行わず、skill code は CODE_ROOT、ledger/identity/state
は ANICCA_HOME を使う。agent-economy installer は executable skill code を state home へコピー
せず、既存 state/identity を準備する。

Release metadata は実際の archived git SHA と `git_commit` を記録し、plist/launch/install/cutter
で release id、SHA、namespace、current、seal を検証する。release 全体を read-only にし、
effective-cron は `CEO_EFFECTIVE_CRON_DIR`（agent-economy は `$ANICCA_HOME/state/effective-cron`）
へ出す。cutter は `$LOOPS_ROOT/.release-lock` の mkdir+PID stale-reclaim lock 下で cut/rollback
を行い、rollback は current→previous の順で atomic link rename、post-readback、失敗時復元を行う。
plist の各ファイル書込みも sibling temp + `os.replace` にした。指定された x402-sell の5 leaf
entrypoint は `$ANICCA_HOME/skills/earn/x402-sell/state` を明示的に選び、report slot は相対
state writer が無いため変更していない。

Rethink focused GREEN:

```text
node --test test/agent-economy-control-plane.test.mjs test/install-release-state.test.mjs
```

結果: 15 tests / pass 15 / fail 0。exact no-current plist、current 移動後の pin、CODE_ROOT→HOME
state 分離、atomic plist、全 release seal、二回 rollback、invalid previous、installer の no-code-sync
を実測した。

既存 path checks:

```text
node --test skills/cook/lib/__tests__/run-sh-wiring.test.mjs skills/earn/__tests__/run-identity.test.mjs skills/earn/x402-sell/__tests__/scout-market.test.mjs skills/earn/x402-sell/__tests__/product-gaps.test.mjs
```

結果: 24 tests 中 23 PASS。`skills/earn/__tests__/run-identity.test.mjs` は worktree に `viem` が
無いため module load failure。`resale`/`serve-listen` の focused checks も同じ未導入依存（`@x402/fetch`、
`express`）で load/boot failureとなり、state-path変更由来ではない。

```text
npm run test:agent-economy
```

結果: 81 tests / pass 79 / fail 2。失敗は `viem` 欠如による既存 `ensure-wallet` と TaskMarket の
module load failure。live launchctl、daemon 起動、provider/network effect は実行していない。

追加 `py_compile`、対象 shell `bash -n`、対象 JS `node --check`、`git diff --check` は全て exit 0。

## Rethink commit

この追補を前回 commit の上に新規 commit として記録する（amend/push は行わない）。
