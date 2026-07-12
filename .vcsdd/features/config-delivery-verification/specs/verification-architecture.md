# Verification Architecture — config-delivery-verification

## Purity Boundary Map

- **Pure Core** (deterministic, no side effects, unit-testable with in-memory fixtures only):
  - `diffDeclaredVsActual(declaredMap, actualMap) -> DriftEntry[]` — REQ-001, REQ-002, REQ-006 の
    核。2つの `{key: value}` オブジェクトを受け取り、`declared !== actual` なキーごとに
    `{key, declared, actual}` を返す。ネットワーク・ファイル・プロセスに一切触れない。
  - `classifyObservability(rawObservation) -> "OBSERVED" | "UNOBSERVABLE"` — REQ-004 の核。
    `healthcheck-runtime-loop.sh` の `hrl_classify` と同じ役割の純粋分類関数。
  - `resolveExpectedValue(instanceDeclaredConfig, key) -> value | undefined` — REQ-003 の核。
    plist/registry から読み取った「そのインスタンス自身の宣言値」をそのまま返すだけの
    素通し関数（インスタンス名で分岐する if-else を持たない = REQ-003/REQ-007 の
    ハードコード禁止を機械的に保証する形）。
  - `resolveClaudePTimeoutMs(configValue) -> number` — REQ-009 の核。
    `mainloop-timeout-lib.sh:resolve_mainloop_timeout_sec` と同じ規約（オーバーライド値の
    検証・クランプ・デフォルトへのフォールバック）を `SLEEP_BASE_S` に適用する。

- **Effectful Shell** (I/O, プロセス起動, 外部コマンド — thin adapters only):
  - `readPlistDeclaredEnv(plistPath) -> {key: value}` — plist ファイルを読み、
    `EnvironmentVariables` 辞書を返す（`plutil -convert json -o -` あるいは同等のパース）。
  - `readRuntimeEnvOfLabel(launchdLabel) -> {pid, env} | null` — `launchctl list` でラベルから
    PID を解決し、`ps -Awwe -o pid,command -p <pid>` の出力から `KEY=VALUE` トークン列を
    パースする。PID が見つからない/`ps` が失敗する場合は `null`（→ pure core 側で
    `UNOBSERVABLE` に分類される）。
  - `readRegistryFile(path) -> object | null` — registry.json（正本 or ランタイムコピー）を
    読んで JSON.parse する。存在しない/parse失敗時は `null`。
  - `runClaudePWithTimeout(args, timeoutMs) -> Promise` — REQ-009 の effectful 実装。
    `runtime/loop/index.mjs:1016-1047` の既存 `setTimeout` + `proc.kill('SIGKILL')` パターンを
    `brain.mjs:thinkClaudeP` に移植する。
  - detector 自体はここまで（read のみ）。`launchctl bootout/bootstrap` によるプロセス再起動は
    detector のコードパスに**含まれない**（REQ-005）— REQ-008 の検証対象になる実際の再起動は、
    この feature の実装作業として手動/別コマンドで行い、その結果を detector で観測するだけ。

## Proof Obligations

| ID | Description | Tier | Required | Tool |
|----|-------------|------|----------|------|
| PROP-001 | `diffDeclaredVsActual` は同一 fixture に対し決定論的に同じ乖離リストを返す（REQ-006） | 1 | true | bash `chk()`（`test-healthcheck-runtime-loop.sh` 方式）または node `node:test` |
| PROP-002 | `diffDeclaredVsActual` は引数オブジェクトを mutate しない（REQ-006） | 1 | true | node `node:test`（Object.freeze した入力を渡して例外なく完走することで確認） |
| PROP-003 | ANICCA_BRAIN 宣言=claude-p/実際=proxy の fixture で乖離1件を返す（REQ-001） | 0 | true | bash `chk()` |
| PROP-004 | ANICCA_BRAIN 宣言=実際 一致の fixture で乖離0件・PASS（REQ-001） | 0 | true | bash `chk()` |
| PROP-005 | 正本 dormant / コピー live の registry fixture で `hl_trade.status` 乖離1件（REQ-002） | 0 | true | bash `chk()` |
| PROP-006 | 複数コピー fixture で、一致コピーと不一致コピーを独立に報告する（REQ-002） | 1 | true | bash `chk()`（複数入力の組み合わせ） |
| PROP-007 | Franklin fixture（宣言=proxy/実際=proxy）で PASS、claude-p fixture（宣言=claude-p/実際=proxy）で FAIL — 同一関数・異なる宣言値のみ（REQ-003） | 1 | true | bash `chk()`（2 fixture を同一関数に通す比較） |
| PROP-008 | detector ソースに instance 名でのハードコード分岐（switch/if-else on label string for expected value）が存在しない（REQ-003, REQ-007） | 0 | true | grep（コードレビュー時に機械実行、CIではなく実装レビューのチェックリスト項目） |
| PROP-009 | PID未検出/ps失敗/ファイル欠落の fixture で PASS ではなく `reason: "unobservable"` を含む FAIL を返す（REQ-004） | 0 | true | bash `chk()` |
| PROP-010 | 観測不能ケースが「乖離なし」（空配列)に丸め込まれるコードパスが存在しない（REQ-004） | 1 | true | bash（REQ-001/002 の全 fixture ペア × observability=false の組み合わせテスト） |
| PROP-011 | detector ソースに `kickstart`/`bootout`/`bootstrap`/`kill(`/`SIGKILL`/`SIGTERM`/対象ファイルへの`writeFile` 呼び出しが存在しない（REQ-005） | 0 | true | grep |
| PROP-012 | detector を fixture に対して連続実行してもfixtureファイルの mtime が変化しない（REQ-005） | 1 | true | bash（`stat -f %m` 前後比較） |
| PROP-013 | detector ソースに severity/danger/critical 等の分類のための regex・キーワードリストが存在しない（REQ-007） | 0 | true | grep |
| PROP-014 | 再起動後の実インスタンスに対する detector 実行で `ANICCA_BRAIN` 乖離0件（REQ-008, fresh evidence） | 0 | true | 実機 `ps -Awwe` + detector 実行（Phase 2b/5 で実施、モック不可） |
| PROP-015 | `thinkClaudeP` がタイムアウト内に正常終了する fixture プロセスで正常 resolve（REQ-009） | 1 | true | node `node:test`（短時間で exit するダミー `spawn` ターゲット） |
| PROP-016 | `thinkClaudeP` がタイムアウトを超えてハングする fixture プロセスで `SIGKILL` + `claude_p_timeout` reject（REQ-009） | 1 | true | node `node:test`（`sleep 999` 等のダミープロセスをタイムアウト値を短く設定して検証） |
| PROP-017 | `resolveClaudePTimeoutMs` のデフォルトは 120（`SLEEP_BASE_S`）で、オーバーライド値がクランプ・検証される（REQ-009） | 1 | true | bash `chk()`（`mainloop-timeout-lib.sh` と同型のテスト） |
| PROP-018 | detector が `ps` の生コマンドライン中の秘密鍵らしきキーの値をマスクせず出力しない（NFR-Security） | 1 | true | bash/node（秘密鍵ライクな値を含む fixture 文字列を通し、出力に平文で現れないことを確認） |

## Verification Strategy

- **Tier 0（証明不要・自明な事実比較）**: PROP-003/004/005/008/009/011/013/014 —
  単純な等価比較・grep による静的確認・実機での1回きりの直接観測。フォーマル手法は不要
  （`healthcheck-runtime-loop.sh` の `--classify` 方式と同じ扱い）。
- **Tier 1（property/fixture ベースのテスト）**: PROP-001/002/006/007/010/012/015/016/017/018 —
  bash の `chk()` パターン（`test-healthcheck-runtime-loop.sh` を踏襲）または node の
  `node:test` で、複数の入力パターンを列挙してテストする。ネットワーク不要、全て文字列/
  オブジェクト fixture の注入で完結（この repo は Rust/Python ではなく bash+Node.js が
  実体のため、kani/hypothesis ではなく既存の repo 内テスト規約をそのまま採用する）。
- **Tier 2（軽量フォーマル手法）**: 該当なし（lean mode、乖離検出ロジックの複雑度は
  Tier 2 の投資に見合わない — 単純なキー・バリュー比較のため Tier 1 の網羅的 fixture
  テストで十分）。
- **Tier 3（強いフォーマル証明）**: 該当なし。

## Language/Tooling Note

`state.json` の `language` フィールドは `typescript` だが、この feature が実際に触る
コードは `runtime/loop/*.mjs`（Node.js ESM）と `skills/self/*.sh`（bash）である。
Tier 0/1 の検証はこの2つの既存ランタイムのネイティブなテスト規約
（`node:test` / bash `chk()` パターン）を使う。存在しない `--max-turns` CLI フラグや
Rust 専用ツール（kani）を持ち出さない（車輪の再発明・幻想ツール使用の禁止）。
