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
