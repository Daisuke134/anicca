# Behavioral Spec — config-delivery-verification

## Context (verified facts, gathered this session — not推測)

### Bug 1 — agent-economy-loop の脳が plist と乖離

- `~/Library/LaunchAgents/ai.anicca.agent-economy-loop.plist` の `EnvironmentVariables` に
  `ANICCA_BRAIN` = `claude-p` と書かれている（本セッションで `cat` して確認 — grep 出力
  `<key>ANICCA_BRAIN</key><string>claude-p</string>`）。
- しかし稼働中プロセス PID `94249`（`launchctl list` の `ai.anicca.agent-economy-loop` 行が示す
  PID と一致、`ps -p 94249 -o pid,comm` = `node`）の実 env を `ps -Awwe -o pid,command -p 94249`
  で読むと、コマンドライン展開後の実 env に **`ANICCA_BRAIN=proxy`** が含まれる（本セッションで
  実行し確認済み。他の観測値: `ANICCA_HOME=/Users/operator/.anicca-founder`,
  `XPC_SERVICE_NAME=ai.anicca.agent-economy-loop`, `ANICCA_WALLET_ADDRESS=0x810f...`,
  `ANICCA_FUNDING=self`, `OPENAI_BASE_URL=http://127.0.0.1:8402/v1`）。
- `~/.anicca-founder/logs/daemon.err.log`（676行、本セッションで `wc -l` 確認）の直近ログに
  `[loop] THINK failed: proxy_down: connect ECONNREFUSED 127.0.0.1:8402` /
  `HTTP 500: This operation was aborted` が複数件、`claude-p failed` は全ログ中
  **1件のみ**（`grep -c "claude-p failed"` = 1）。`earn/polymarket` を含む行は16件
  （`grep -o "narrate\|polymarket-trade\|earn/polymarket"` の集計）。proxy 経路が支配的である
  ことの直接証拠。
- コードで確認した機構（`/Users/operator/anicca/runtime/loop/brain.mjs`）:
  `think(ctx, config)` は `config.ANICCA_BRAIN`（`process.env.ANICCA_BRAIN` 由来）を見て分岐する
  だけで、plist の内容を直接読むことは一切ない。plist を編集しても、稼働中プロセスの `process.env`
  は launchd が **再読込（bootout → bootstrap もしくは kickstart -k）されるまで古いまま**。
  デーモンの自己更新による内部 exec も既存 env を継承するため、ファイル編集だけでは絶対に
  反映されない。
- 対比: `runtime/loop/brain.mjs:5-6` のコメント通り、`ANICCA_BRAIN=proxy` は Franklin
  （self-funded, `ANICCA_FUNDING=self` 、自分の crypto wallet から推論代を払う）にとっては
  **正しい設定**であり、claude-p（human-funded, `ai.anicca.agent-economy-loop` /
  `ai.anicca.pm-earner` / `ai.anicca.founder-loop`）にとってのみ `claude-p` が期待値である。
  「1つの正しい値」は存在しない — インスタンスごとに期待値が異なる。

### Bug 2 — hl_trade の registry status が実行時コピーに届いていない

- 正本 `/Users/operator/anicca/skills/registry.json` は `hl_trade.status = "dormant"`
  （本セッションで `sed -n '124,140p'` して確認、`dormantReason` に理由記載あり）。
  git commit `40066df4e0ad0935859af72161bac7498000ca7e`, `2026-07-12 18:57:09 +0900`
  （`git log -1 --format='%H %ci' -- skills/registry.json` で確認）。
- しかし実行時コピー3箇所は全て `hl_trade.status = "live"` のまま（本セッションで
  `python3 -c "json.load(...)"` により3ファイルとも確認）:
  - `~/.blockrun/skills/registry.json`
  - `~/.anicca-founder/skills/registry.json`
  - `~/.franklin2-home/.blockrun/skills/registry.json`
- 該当プロセスの起動時刻（`ps -o lstart`、本セッション確認）は `franklin-loop`(PID 79192)
  = 2026-07-12 09:53:28、`franklin2-loop`(PID 86698) = 2026-07-12 04:49:41 —
  いずれも registry 変更コミット（18:57:09）より前。
- 機構をコードで確認（`/Users/operator/anicca/runtime/loop/index.mjs:156-169`）:
  ```
  const registryPath = process.env.ALWAYS_ACT_REGISTRY_PATH_OVERRIDE
    || path.join(repoRoot, 'skills', 'registry.json');
  const registry = JSON.parse(await fs.readFile(registryPath, 'utf8'));
  registryForAlwaysAct = registry;
  activeSkillSlots = liveSlotNames(registry);
  ```
  これはモジュールのトップレベルで**プロセス起動時に1回だけ**実行される。wake ごとの
  再読込コードは存在しない（`grep -n "registry" runtime/loop/index.mjs` で該当行は
  この1箇所のみ）。プロセスが生きている限り、registry.json をいくら書き換えても
  そのプロセスの `activeSkillSlots` は起動時点のスナップショットのまま。

### 共通の病理

宣言（plist ファイル / git 上の registry.json）と実行時の実態（プロセスの `process.env` /
メモリ上に読み込まれた registry オブジェクト）が乖離しても、それを検知する仕組みが
どこにも存在しない。

### 既存の隣接資産（車輪の再発明禁止 — 踏襲すべきパターン）

- `/Users/operator/anicca/skills/self/healthcheck-runtime-loop.sh` は既に
  「pure 分類関数（`hrl_classify`）＋ effectful オーケストレーター（`check`）」という
  purity boundary パターンを持ち、`--classify` サブコマンドで pure 関数だけを直接呼んで
  テストしている（`test-healthcheck-runtime-loop.sh` が実例）。config-drift detector も
  同じ分離規約に従う。
- `/Users/operator/anicca/skills/self/mainloop-timeout-lib.sh` は「純粋な値解決関数
  （`resolve_mainloop_timeout_sec`）を本体スクリプトから分離してテスト可能にする」という
  同種の規約の別実例。
- `runtime/loop/index.mjs:1016-1047`（`SKILL_TIMEOUT_S`, デフォルト120秒）に、
  子プロセスへ `setTimeout` + `SIGKILL` を送る既存パターンが既にある。REQ-009 の
  タイムアウト機構はこのパターンを踏襲する（`claude --help` / `claude -p --help` を
  本セッションで実行し確認した通り、この CLI バージョンに `--max-turns` フラグは
  **存在しない** — `--max-turns`は例として書かれていたが実在しないため採用しない）。

## Purity Boundary Analysis

- **Pure core（決定論的・副作用なし・フォーマル検証可能）**: 「宣言された設定マップ」と
  「観測された実行時マップ」という2つの単純なキー・バリュー構造を入力に取り、乖離
  （キー・宣言値・実際値・対象識別子のリスト）を返す diff 計算のみ。文字列パース後の
  構造体を渡せば足りる。ps の生出力パース、plist の生パース、registry.json の
  JSON.parse そのものは pure core の外（後述）。
- **Effectful shell（I/O 境界）**:
  - plist ファイルの読み取り（`plutil -p` あるいは同等）
  - `launchctl list` によるラベル→PID解決（read-only、observe のみ）
  - `ps -Awwe -o pid,command -p <pid>` による実行時 env の取得とパース
  - registry.json ファイル群（正本 + N個のランタイムコピー）の読み取りと JSON.parse
  - 秒単位のタイムアウト計測とプロセス終了シグナル送信（REQ-009 のみ。detector 自体は
    一切のプロセスを終了させない — REQ-005 参照）

## Requirements

### REQ-001: ANICCA_BRAIN 宣言値と実行時値の乖離検出
**EARS**: WHEN config-drift detector が human-funded インスタンス（`ai.anicca.agent-economy-loop`
等、期待値解決ルールは REQ-003 参照）に対して実行される THE SYSTEM SHALL
「plist の `EnvironmentVariables.ANICCA_BRAIN` 宣言値」と「`launchctl list` で得た PID の
`ps -Awwe` 実行時コマンドライン中の `ANICCA_BRAIN=` 値」を比較し、不一致なら乖離1件として
`{key: "ANICCA_BRAIN", instance, declared, actual}` を返す。
**Edge Cases**:
- plist に `ANICCA_BRAIN` キーが存在しない: `declared` は「未宣言（コードのデフォルト値 `proxy`
  を継承する）」として明示し、実行時値と比較する（欠落を「乖離なし」として握り潰さない）。
- `launchctl list` にラベルが存在しない（アンロード済み/plist破損）: REQ-004（fail-closed）に従い
  FAIL を返す。乖離0件として PASS 扱いにしてはならない。
**Acceptance Criteria**:
- 本 feature 実測ケースを固定 fixture として与えたとき（`declared="claude-p"`,
  `actual="proxy"`, instance=`ai.anicca.agent-economy-loop`）、detector は乖離1件を返す。
- `declared` と `actual` が一致する fixture（例: Franklin の `declared="proxy"`,
  `actual="proxy"`）では乖離0件・PASS を返す。

### REQ-002: registry.json スキル slot status の宣言値と実行時コピーの乖離検出
**EARS**: WHEN config-drift detector が「正本 `skills/registry.json`」と「1つ以上の
ランタイムコピー（例: `~/.blockrun/skills/registry.json`,
`~/.anicca-founder/skills/registry.json`, `~/.franklin2-home/.blockrun/skills/registry.json`）」
を与えられて実行される THE SYSTEM SHALL 各 slot の `status` フィールドを正本とコピーで比較し、
不一致がある slot ごとに `{key: "<slot>.status", copyPath, declared, actual}` を乖離として返す。
**Edge Cases**:
- ランタイムコピーのファイルが存在しない、または JSON parse に失敗する: REQ-004 に従い
  FAIL を返す（「そのコピーは無視して他だけ判定」してはならない）。
- 正本に存在しない slot がランタイムコピーにのみ存在する（廃止済み slot の残骸）: 乖離として
  報告する（「正本にないから無視」は不可 — 実行時に生きている可能性があるため）。
**Acceptance Criteria**:
- 正本 fixture `{hl_trade: {status: "dormant"}}` とコピー fixture
  `{hl_trade: {status: "live"}}` を与えたとき、detector は `hl_trade.status` の乖離1件を返す。
- 正本とコピーが完全一致する fixture では乖離0件・PASS を返す。
- 複数コピーを与えたとき、乖離のある/なしをコピーごとに独立して報告する（1コピーが一致していても
  他のコピーの乖離を握り潰さない）。

### REQ-003: インスタンスごとの期待値解決（self-funded 例外の保証）
**EARS**: WHEN config-drift detector が期待値と実際値を比較する THE SYSTEM SHALL
インスタンス識別子（launchd label あるいは `ANICCA_FUNDING` / `ANICCA_HOME` の組）ごとに
別々の「宣言された設定」を入力として受け取り、**単一のグローバル期待値をハードコードして
全インスタンスに適用してはならない**。
**Edge Cases**:
- Franklin（`ANICCA_FUNDING=self`, launchd label `ai.anicca.franklin-loop` /
  `ai.anicca.franklin2-loop`）に対して `ANICCA_BRAIN=proxy` を判定するとき、detector は
  Franklin 自身の plist に書かれた宣言値（`proxy`）と実行時値を比較するのであって、
  「claude-p が正しい」という他インスタンス用の期待値を Franklin に適用してはならない。
- 新しいインスタンスが追加されたとき、detector のコード変更なしに、そのインスタンス自身の
  plist 宣言値を「その instance の期待値」として扱えること（=期待値はインスタンスの
  設定ファイルから読み取るのであって、detector 内の switch/if-else 表に埋め込まれた
  インスタンス名リストであってはならない）。
**Acceptance Criteria**:
- Franklin の plist（`ANICCA_BRAIN=proxy` 宣言、実行時値も `proxy`）を fixture として与えると
  乖離0件・PASS を返す。同じ detector 関数に、claude-p インスタンスの plist
  （宣言`claude-p`、実行時値`proxy`）を与えると乖離1件・FAIL を返す — **同一の比較ロジックに
  インスタンスごとに異なる宣言値を渡しているだけ**であり、detector 内部にインスタンス名で
  分岐する if-else / regex が存在しないことをコードレビューで確認できる。

### REQ-004: 実行時状態が観測不能な場合の fail-closed
**EARS**: WHEN config-drift detector が実行時の実態を観測しようとして失敗する
（対象プロセスが存在しない、`ps` コマンドがエラーを返す、ファイルが読めない、
JSON parse に失敗する等）THE SYSTEM SHALL その対象を PASS として扱わず、
`{key, instance, declared, actual: null, reason: "unobservable"}` という明示的な FAIL として
報告する。
**Edge Cases**:
- `launchctl list` がラベルにマッチする行を返さない（アンロード）: FAIL（PASS ではない）。
- `ps -p <pid>` が対象 PID なしでエラー終了する（プロセスが既に終了していた）: FAIL。
- registry.json のランタイムコピーパスが存在しない: FAIL。
**Acceptance Criteria**:
- 「プロセスが見つからない」fixture を与えたとき、detector の戻り値に PASS は含まれず、
  `reason: "unobservable"` を含む FAIL エントリが含まれる。
- 観測不能なケースを「乖離なし」（空配列）と誤判定するコードパスがないことを、
  観測不能 fixture ×全 REQ-001/002 のテストケースで確認する。

### REQ-005: Read-only 保証（detector は一切のプロセス/ファイルを変更しない）
**EARS**: WHEN config-drift detector が実行される THE SYSTEM SHALL 対象プロセスに対して
kill・restart・シグナル送信を一切行わず、対象ファイル（plist / registry.json）に対して
書き込みを一切行わない。
**Edge Cases**:
- detector 内部から `launchctl kickstart` / `launchctl bootout` / `launchctl bootstrap`
  を呼び出すコードパスが存在しないこと。
- detector 内部から `fs.writeFile` 等でこの feature が読む対象ファイルへ書き込むコードパスが
  存在しないこと。
**Acceptance Criteria**:
- detector のソースコードに `kickstart`, `bootout`, `bootstrap`, `kill(`, `SIGKILL`,
  `SIGTERM`, `writeFile`（対象ファイルへの）のいずれの呼び出しも存在しないことを
  grep で機械確認できる。
- detector をテスト fixture に対して連続実行しても、fixture 元ファイルの mtime が
  変化しないことをテストで確認する。

### REQ-006: 乖離計算は純粋関数として分離される（purity boundary）
**EARS**: WHERE 乖離の計算ロジック THE SYSTEM SHALL 「宣言された設定マップ」と
「観測された実行時マップ」という2つの純粋なデータ構造だけを引数に取り、乖離リストだけを
返す純粋関数として実装され、ファイル I/O・プロセス起動・`ps`/`launchctl` 呼び出しを
一切含まない。
**Edge Cases**:
- 同じ引数で複数回呼んでも常に同じ結果を返す（決定論的）。
- 引数のオブジェクトを変更（mutate）しない（`.claude/rules/coding-style.md` の
  immutability 原則に従う）。
**Acceptance Criteria**:
- pure diff 関数は、ネットワークもファイルシステムも一切アクセスせずに、文字列/オブジェクト
  fixture だけを渡してユニットテストで検証できる（`healthcheck-runtime-loop.sh` の
  `hrl_classify` / `--classify` サブコマンドの分離規約を踏襲）。
- 同一 fixture を10回連続で関数に通したとき、返り値が bit-for-bit 同一であることをテストで
  確認する。

### REQ-007: detector は事実のみを返し、危険性の判断をハードコードしない
**EARS**: WHEN config-drift detector が乖離を報告する THE SYSTEM SHALL
「キー・宣言値・実際値・対象識別子」という事実だけを返し、その乖離が「危険」か
「許容範囲」かの判定（severity/danger 判定）を regex やキーワード羅列の if-else で
行わない。判断は呼び出し側（エージェント自身、あるいは REQ-008 のような具体的な
検証手順）に委ねる。
**Edge Cases**:
- `ANICCA_BRAIN` の乖離と `hl_trade.status` の乖離を、detector 内部で
  「これは重大」「これは軽微」と分類するコードが存在しないこと（→
  `~/.claude/rules/building-effective-ai-agents.md` のハードコード禁止則）。
**Acceptance Criteria**:
- detector のソースコードに severity/danger/critical といった分類のための
  regex・キーワードリスト・if-elseチェーンが存在しないことをコードレビューで確認する
  （事実の等価比較 `declared !== actual` 以外の判断分岐がないこと）。

### REQ-008: claude-p 脳が agent-economy-loop の稼働プロセスに実際に届いていることの検証
**EARS**: WHEN `ai.anicca.agent-economy-loop` の launchd job が（この feature の実装作業の
一部として）`launchctl bootout` → `launchctl bootstrap`（もしくは同等の完全な再読込）で
再起動された後、config-drift detector が同インスタンスに対して再実行される THE SYSTEM SHALL
新しい PID の実行時 `ANICCA_BRAIN` 値が `claude-p` であり、REQ-001 の乖離が0件（PASS）
であることを報告する。
**Edge Cases**:
- 再起動後も古い PID が生き残っている（bootout が不完全）: detector は
  `launchctl list` から得た**現在の**PIDに対して観測するため、古いPIDの残存を誤って
  PASS と報告しない（新PIDでの観測のみが真）。
- 再起動直後、プロセスがまだ env を確定させる前の一瞬（起動レース）: REQ-004 の
  fail-closed（観測不能→FAIL）が適用され、PASS を誤って返さない。
**Acceptance Criteria**:
- 本 feature の実装完了時点で、`launchctl list | grep ai.anicca.agent-economy-loop` の
  PID に対し `ps -Awwe -o command -p <PID>` を実行して `ANICCA_BRAIN=claude-p` を
  直接確認できる（この検証は Phase 2b/5 で実際に実行し、fresh evidence として記録する。
  「plist を編集した」だけでは PASS と認めない）。
- detector を実インスタンスに対して実行し、`ANICCA_BRAIN` の乖離が0件であるという
  出力を得る。

### REQ-009: 1 wake の所要時間が SLEEP_BASE_S を超えないことの検証とタイムアウト保護
**EARS**: WHEN `runtime/loop/brain.mjs` の `thinkClaudeP`（`ANICCA_BRAIN=claude-p` 経路）が
`claude -p` 子プロセスを起動する THE SYSTEM SHALL その子プロセスの実行時間に
`SLEEP_BASE_S`（デフォルト120秒、`runtime/loop/config.mjs` 由来）を上限とするタイムアウトを
設け、上限を超えたら `SIGKILL` で終了させ、明示的なタイムアウトエラー
（例: `claude_p_timeout`）を返す。
**Edge Cases**:
- 現状（本セッションで `brain.mjs` を読んで確認）、`thinkClaudeP` の `spawn()` 呼び出しには
  **一切のタイムアウトが設定されていない** — `proc.on('exit', ...)` のみで、ハングした場合
  永久に resolve/reject されない。この欠落自体が REQ-009 の対象。
- 本セッションで `claude --help` / `claude -p --help` を実行して確認した通り、この CLI
  バージョンに `--max-turns` フラグは**存在しない**。したがってタイムアウト保護は
  CLI フラグではなく、`runtime/loop/index.mjs:1016-1047` の既存 `SKILL_TIMEOUT_S`
  パターン（`setTimeout` + `proc.kill('SIGKILL')`）を `brain.mjs` 側に同じ規約で移植する
  形で実装する。
- タイムアウトによる kill 後も `thinkClaudeP` は例外を投げるだけで、既存の
  `think()` のフォールバック（`brain.mjs:34-44`、proxy へのフォールスルー）は変更しない
  （この feature はタイムアウト保護の追加のみで、フォールバックロジック自体は
  対象外 — 既存の catch がそのまま proxy へ fall through する）。
**Acceptance Criteria**:
- `thinkClaudeP` にタイムアウト値より短い時間で正常終了する fixture プロセスを渡すと、
  正常な resolve が返る。
- タイムアウト値より長くハングする fixture プロセスを渡すと、タイムアウト経過後に
  `SIGKILL` で子プロセスが終了し、`claude_p_timeout` を含むエラーで reject される
  （ハング状態のまま resolve も reject もされない、という現状のバグが再現しないことを
  テストで確認する）。
- タイムアウト値のデフォルトが `SLEEP_BASE_S`（120秒）であり、`config.mjs` の
  既存の設定解決規約（`cfgNum`）経由でオーバーライド可能であることをテストで確認する。

## Non-Functional Requirements

- **Performance bound**: config-drift detector 全体（REQ-001+REQ-002、対象インスタンス数
  ≤10、ランタイムコピー数 ≤5 の現実的な規模）は 5秒以内に完了する（`ps`/ファイル読み取りの
  実測レイテンシから導出。ネットワークI/Oを含まないため妥当な上限）。
- **Security**: detector が `ps -Awwe` の生コマンドライン全体を観測・記録する際、
  `runtime/loop/env-filter.mjs` の `scrubPrivateKeys` と同等の考え方で、秘密鍵らしき
  キー（`*_PRIVATE_KEY`, `*_SECRET*`, `ANTHROPIC_API_KEY`, `CLAUDE_CODE_OAUTH_TOKEN` 等）
  の値をログ・出力にそのまま残してはならない（値をマスクした上で「このキーが存在する/しない」
  「値が一致/不一致」という事実だけを報告する）。
- **No regression**: この feature は既存の `runtime/loop/index.mjs` / `brain.mjs` の
  正常系の挙動（proxy 経路のデフォルト動作、既存の `SKILL_TIMEOUT_S` ロジック）を
  変更しない。REQ-009 は `thinkClaudeP` に**タイムアウトを追加するだけ**であり、
  それ以外の分岐・フォールバック挙動は不変とする。
