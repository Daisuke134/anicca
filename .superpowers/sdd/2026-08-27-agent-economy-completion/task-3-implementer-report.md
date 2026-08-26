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

## Rethink Fix Round2 (2026-08-27)

指定された x402 `improve`/`register`/`review` の state writer は、pinned mode で
`$ANICCA_HOME/skills/earn/x402-sell/state`（または明示 `ANICCA_X402_STATE_DIR`）だけを使い、
`ANICCA_HOME` が無い場合は release-relative fallback をせず fail-closed にした。seller plist
生成も `ANICCA_HOME`、`ANICCA_CODE_ROOT`、explicit state dir を渡す。installer の agent-economy
branch は registry loop 全体、npm install、`$HOME/loops/node_modules` symlink を bypass し、
既存の state/identity だけを保持する。generic install は従来経路のまま。

cut は archived git tree 直後に deterministic `SOURCE-MANIFEST.json`（relative path、normalized
mode、content SHA）を生成し、node_modules/RELEASE/manifest 自身を除外して digest を
`RELEASE.json` に記録する。plist/install/launch は source manifest の canonical bytes、entries、
digest、実 SHA/`git_commit` を再計算する。current/previous の更新は `.release-lock` 下で旧
両ポインタを snapshot し、current swap failure の注入時に previous を復元（旧 previous が無ければ
削除）、成功後は両方の expected target/readback を検証する。rollback も current→previous の順に
swap し、両ポインタを post-validate する。

Round2 focused GREEN:

```text
node --test test/agent-economy-control-plane.test.mjs test/install-release-state.test.mjs
```

結果: 17 tests / pass 17 / fail 0。source manifest 改変拒否、実 cut metadata、atomic pointer
failure recovery、反復 rollback、installer no-code-sync、x402 state contract を含む。

x402 store focused command:

```text
node --test skills/earn/x402-sell/__tests__/store-actions.test.mjs skills/earn/x402-sell/__tests__/store-improve.test.mjs skills/earn/x402-sell/__tests__/seller-boot.test.mjs skills/earn/x402-sell/__tests__/register-boot.test.mjs
```

結果: 8 tests 中 6 PASS、2 test file が worktree の `viem` 未導入で module load failure。
seller/register boot fixture 自体は 6/6 PASS。

`npm run test:agent-economy` は 83 tests 中 81 PASS。失敗は `viem` 欠如による
`ensure-wallet` と TaskMarket の既存 module load failure。対象 shell/JS syntax、`py_compile`、
`git diff --check` は全て exit 0。live launchctl/install/provider mutation は行っていない。

## Rethink Fix Round3 (2026-08-27)

Rollback は current/previous の両方を exact expected target として post-validate し、片方でも
失敗した場合は元の snapshot を戻して復元自体も validate してから non-zero を返す。通常 cut は
旧 current/previous の存在を明示的に snapshot し、post-current-swap readback failure 時に旧 current
が無ければ current を削除し、旧 previous の有無も同じ形で復元する。

依存 integrity は Task 2 の既存 `dependency_digest` と同じ TSV 行形式を
`DEPENDENCY-MANIFEST.tsv` として保存し、path/mode/content hash/symlink target と node_modules
containment を strict plist/install/launch で再計算する。source manifest は generated dependency
manifest を除外し、source symlink は release 内 target のみ許可する（internal symlink は受理、
absolute/relative escape は拒否）。

Round3 focused GREEN:

```text
node --test test/agent-economy-control-plane.test.mjs test/install-release-state.test.mjs
```

結果: 18 tests / pass 18 / fail 0。dependency manifest 改変、internal/escape symlink、旧 current
なしの post-swap failure 復元、rollback 両ポインタ failure 復元、反復 rollback を実測した。

```text
npm run test:agent-economy
```

結果: 84 tests / pass 82 / fail 2。失敗は worktree に `viem` が無いことによる
`runtime/compute-proxy/__tests__/ensure-wallet.test.mjs` と TaskMarket の module load failure。
対象 shell/JS syntax、`py_compile`、`git diff --check` は全て exit 0。live launchctl/install/provider
mutation は行っていない。

## Rethink Fix Round4 (2026-08-27)

Rollback の second-pointer swap failure は、current を元 target に戻した後、current/previous の
exact target と metadata を検証してから distinct safe error を返す。normal cut の current swap
failure も旧 previous の presence/target と旧 current（または current absence）を検証してから
non-zero を返す。依存 manifest builder は全 entry を相対 path の global lexical order で並べ、
symlink は lstat inode mode、regular file は stat mode に統一した。source manifest も同じ mode
規則を使い、内部 symlink を受理し release 外 target を拒否する。

Round4 focused GREEN:

```text
node --test test/agent-economy-control-plane.test.mjs test/install-release-state.test.mjs
```

結果: 18 tests / pass 18 / fail 0。tricky source symlink（internal/non-executable target）、
dependency manifest mutation/order、current/previous swap failure、旧 current 欠如の exact absence
復元、反復 rollback を実測した。

追加確認: `py_compile`、対象 shell `bash -n`、focused test `node --check`、`git diff --check` は
全て exit 0。Round4 は npm 全体 suite を再実行せず、直前 Round3 の 84 中 82（依存欠如2件）を
有効な全体証拠として保持した。live launchctl/install/provider mutation は行っていない。

## Rethink Fix Round5 (2026-08-27)

pointer 復元は共通 helper 相当の復元・presence/target/metadata 検証を、rollback の previous
swap failure と normal cut の current swap failure に適用した。テスト専用 failure flag は
`replace_link` 後の実際の rename failure handler を通し、通常分岐を事前 short-circuit しない。
launch の依存 manifest は全件収集後に path の byte 順で global sort し、`@`/大文字/underscore/
ネスト path の順序と symlink inode mode を固定した。

Round5 focused GREEN:

```text
node --test test/agent-economy-control-plane.test.mjs test/install-release-state.test.mjs
```

結果: 18 tests / pass 18 / fail 0。actual pointer-swap failure、exact snapshot restoration、
absence、manifest global ordering、symlink-to-nonexec mode を実測した。

追加確認: `py_compile`、対象 shell `bash -n`、focused test `node --check`、`git diff --check` は
全て exit 0。Round5 は npm 全体 suite を再実行せず、直前 Round3 の 84 中 82（依存欠如2件）を
有効な全体証拠として保持した。live launchctl/install/provider mutation は行っていない。

## Rethink Fix Round5 (2026-08-27)

`restore_pointer_snapshot` を共通 helper として追加し、target/absence の復元後に exact presence・
readlink target・metadata を検証する。rollback の previous-pointer rename failure と normal cut の
current-pointer rename failure、および post-readback failure の全経路がこの helper を使い、復元
失敗は distinct fatal error として返す。test-only failure flags は replace_link 内の one-shot return
で実際の rename failure handler を通すため、事前 short-circuit ではない。

launch の dependency manifest は全エントリ収集後 `Buffer.compare(Buffer.from(path))` の byte
順に global sort し、cutter/Python の相対 path order と一致させた。source/dependency symlink は
lstat inode mode、regular file は stat mode に統一した。

Round5 focused GREEN:

```text
node --test test/agent-economy-control-plane.test.mjs test/install-release-state.test.mjs
```

結果: 18 tests / pass 18 / fail 0。実 rename failure、exact current/previous snapshot restoration、
current absence、global dependency ordering、internal/non-executable symlink を実測した。

追加確認: `py_compile`、対象 shell `bash -n`、focused test `node --check`、`git diff --check` は
全て exit 0。Round5 は npm 全体 suite を再実行していない。live launchctl/install/provider mutation
は行っていない。

## Rethink Fix Round6 (2026-08-27)

Recovery は stage-aware に整理した。normal current rename failure では unchanged current を先に
validate し、変更済み previous だけを復元して両方を validate。rollback の second-pointer rename
failure では unchanged previous を保持し、変更済み current だけを復元して両方を validate。
post-readback failure では current/previous の復元を独立に両方試行し、片側失敗でももう片側を
skip しない。validation-only launch preflight (`ANICCA_VALIDATE_RELEASE_ONLY=1`) を追加し、wallet/
daemon effect 前に source/dependency/seal checks だけを完了できる。

Round6 focused GREEN:

```text
node --test test/agent-economy-control-plane.test.mjs test/install-release-state.test.mjs
```

結果: 20 tests / pass 20 / fail 0。復元片側失敗でも他方を試行する fixture、absence、preflight の
`@scope`/uppercase/underscore/nested dependency order、non-executable symlink、依存改変拒否を実測。

追加確認: `py_compile`、対象 shell `bash -n`、focused test `node --check`、`git diff --check` は
全て exit 0。npm 全体 suite は Round6 では再実行していない。live launchctl/install/provider mutation
は行っていない。

## Rethink Fix Round7 (2026-08-27)

`ANICCA_VALIDATE_RELEASE_ONLY=1` の成功 exit を daemon executable/path validation の後へ移動し、
release/source/dependency/seal に加えて daemon の存在・実行権を確認した後、wallet/daemon effect
直前でのみ成功するようにした。validation-only fixture は有効 daemon で成功し、missing と
non-executable daemon で fail-closed、依存改変でも拒否する。

Round7 focused GREEN:

```text
node --test test/agent-economy-control-plane.test.mjs test/install-release-state.test.mjs
```

結果: 20 tests / pass 20 / fail 0。

追加確認: `py_compile`、対象 shell `bash -n`、focused test `node --check`、`git diff --check` は
全て exit 0。npm 全体 suite は再実行していない。live launchctl/install/provider mutation は
行っていない。

## Rethink commit

この追補を前回 commit の上に新規 commit として記録する（amend/push は行わない）。
