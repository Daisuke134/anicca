# Behavioral Spec — config-delivery-verification

## Context (verified facts, gathered this session — not推測)

### Bug 1 — agent-economy-loop の脳が plist と乖離

- `~/Library/LaunchAgents/ai.anicca.agent-economy-loop.plist` の `EnvironmentVariables` に
  `ANICCA_BRAIN` = `claude-p` と書かれている（本セッションで `cat` して確認 — grep 出力
  `<key>ANICCA_BRAIN</key><string>claude-p</string>`）。
- しかし稼働中プロセス PID `94249`（`launchctl list` の `ai.anicca.agent-economy-loop` 行が示す
  PID と一致、`ps -p 94249 -o pid,comm` = `node`）の実 env を `ps -Awwe -o pid,command -p 94249`
  で読むと、コマンドライン展開後の実 env に **`ANICCA_BRAIN=proxy`** が含まれる（本セッションで
  実行し確認済み。他の観測値: `ANICCA_HOME=/Users/anicca/.anicca-founder`,
  `XPC_SERVICE_NAME=ai.anicca.agent-economy-loop`, `ANICCA_WALLET_ADDRESS=0x810f...`,
  `ANICCA_FUNDING=self`, `OPENAI_BASE_URL=http://127.0.0.1:8402/v1`）。
- `~/.anicca-founder/logs/daemon.err.log`（676行、本セッションで `wc -l` 確認）の直近ログに
  `[loop] THINK failed: proxy_down: connect ECONNREFUSED 127.0.0.1:8402` /
  `HTTP 500: This operation was aborted` が複数件、`claude-p failed` は全ログ中
  **1件のみ**（`grep -c "claude-p failed"` = 1）。`earn/polymarket` を含む行は16件
  （`grep -o "narrate\|polymarket-trade\|earn/polymarket"` の集計）。proxy 経路が支配的である
  ことの直接証拠。
- コードで確認した機構（`/Users/anicca/anicca/runtime/loop/brain.mjs`）:
  `think(ctx, config)` は `config.ANICCA_BRAIN`（`process.env.ANICCA_BRAIN` 由来）を見て分岐する
  だけで、plist の内容を直接読むことは一切ない。plist を編集しても、稼働中プロセスの `process.env`
  は launchd が **再読込（bootout → bootstrap もしくは kickstart -k）されるまで古いまま**。
  デーモンの自己更新による内部 exec も既存 env を継承するため、ファイル編集だけでは絶対に
  反映されない。
- 対比（**訂正**: 前版が引用した `brain.mjs:5-6` は各値の動作を説明するコメントに過ぎず、
  「どちらが正しいか」には一言も触れていない — 幻覚引用だったため削除する）:
  `ANICCA_BRAIN=proxy` が Franklin（self-funded, `ANICCA_FUNDING=self`）にとって正しい根拠は、
  コードコメントではなく実在する経済的事実として書く。本セッションで
  `runtime/loop/config.mjs:20-24` を実際に Read して確認した実在コメント（`DEFAULTS` の
  `OPENAI_BASE_URL`/モデル選定に関する記述）:
  > 「Paid frontier was draining the treasury on the funded tier ($14->$10.5) while yield
  > earned ~$0 — net-negative. A free brain + earning skills = the only way a self-paying
  > agent stays net-positive at small capital. (Frontier is for capable instances on
  > flat-rate billing, e.g. Claude on a subscription — NOT a self-paying Anicca burning
  > x402 per wake.)」
  Franklin は `ANICCA_FUNDING=self` で推論代を自分の crypto wallet から x402 で払う
  self-paying agent であり、有料の `claude-p` 脳に切り替えると x402 支払いのたびに財布が
  減る。したがって Franklin にとっては無料の `proxy`（`free/glm-4.7` 等）が正しい設定であり、
  claude-p（human-funded, Anthropic サブスクリプションの定額課金で動く
  `ai.anicca.agent-economy-loop` / `ai.anicca.pm-earner` / `ai.anicca.founder-loop`）に
  とってのみ `claude-p` が期待値である。「1つの正しい値」は存在しない — インスタンスごとに
  期待値が異なる。

### Bug 2 — hl_trade の registry status が実行時コピーに届いていない

- 正本 `/Users/anicca/anicca/skills/registry.json` は `hl_trade.status = "dormant"`
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
- 機構をコードで確認（`/Users/anicca/anicca/runtime/loop/index.mjs:156-169`）:
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

- `/Users/anicca/anicca/skills/self/healthcheck-runtime-loop.sh` は既に
  「pure 分類関数（`hrl_classify`）＋ effectful オーケストレーター（`check`）」という
  purity boundary パターンを持ち、`--classify` サブコマンドで pure 関数だけを直接呼んで
  テストしている（`test-healthcheck-runtime-loop.sh` が実例）。config-drift detector も
  同じ分離規約に従う。
- `/Users/anicca/anicca/skills/self/mainloop-timeout-lib.sh` は「純粋な値解決関数
  （`resolve_mainloop_timeout_sec`）を本体スクリプトから分離してテスト可能にする」という
  同種の規約の別実例。
- `runtime/loop/index.mjs:1016-1047`（`SKILL_TIMEOUT_S`, デフォルト120秒、`cfgNum` は
  `runtime/loop/index.mjs:1128` の素通しヘルパー — `val != null ? Number(val) : fallback`
  で検証もクランプも行わない、`config.mjs` にはない）に、子プロセスを終了させる既存パターンが
  既にある。本セッションで `index.mjs:1037-1041` を実際に読んで確認した実装は**二段階**:
  ```
  const timer = setTimeout(() => {
    timedOut = true;
    try { proc.kill('SIGTERM'); } catch {}
    setTimeout(() => { try { proc.kill('SIGKILL'); } catch {} }, 2000);
  }, timeoutMs);
  ```
  すなわち「タイムアウト経過 → `SIGTERM` → 2000ms 待機 → まだ生きていれば `SIGKILL`」。
  REQ-009 のタイムアウト機構はこの二段階パターンをそのまま踏襲する（単純な即時 `SIGKILL`
  ではない — 前版の記述は誤りだったため訂正する）。`claude --help` / `claude -p --help` を
  本セッションで実行し確認した通り、この CLI バージョンに `--max-turns` フラグは
  **存在しない** — `--max-turns`は例として書かれていたが実在しないため採用しない。

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
等、期待値解決ルールは REQ-003 参照、対象となるプロセス集合と対応する plist の発見方法は
REQ-010 参照）に対して実行される THE SYSTEM SHALL
「plist の `EnvironmentVariables.ANICCA_BRAIN` 宣言値」と「REQ-010 で発見した PID の
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
**EARS**: WHEN config-drift detector が「正本 `skills/registry.json`」と「REQ-010 の発見手順で
見つかったランタイムコピー群（現時点で観測されている実例: `~/.blockrun/skills/registry.json`,
`~/.anicca-founder/skills/registry.json`, `~/.franklin2-home/.blockrun/skills/registry.json` —
これはハードコードされた対象列挙ではなく REQ-010 の発見結果の一例）」を与えられて実行される
THE SYSTEM SHALL 各 slot の `status` フィールドを正本とコピーで比較し、不一致がある slot
ごとに `{key: "<slot>.status", copyPath, declared, actual}` を乖離として返す。
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
- 対象コピーの集合は REQ-002 のコード内に静的リストとして埋め込まれておらず、REQ-010 の
  発見関数の戻り値をそのまま受け取ることをコードレビューで確認する。

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

**スコープの明示（REQ-009 との切り分け）**: この read-only 禁止は「detector が監視対象
（agent-economy-loop 等の稼働プロセスそのもの）に対して kill/restart すること」を禁じる。
REQ-009 の `SIGTERM`→`SIGKILL` は `runtime/loop/brain.mjs` 自身が `thinkClaudeP` の中で
自分が spawn した `claude -p` 子プロセスをタイムアウト管理する既存の効果的シェル層の話
であり、config-drift detector のコードではない。両者は別コンポーネントであり矛盾しない。

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

**再起動の前提条件（MUST、本番の稼働ループ＝実際に金が動く体を再起動するため）**:
1. **in-flight wake が無いこと**: `launchctl bootout` は対象プロセスに `SIGTERM` を送る。
   `runtime/loop/index.mjs:324-334` に既に実装済みの `process.on('SIGTERM', ...)` ハンドラが、
   `currentChildKiller` 経由で in-flight のスキル子プロセスを最大5秒待って終了させ、
   `kind: "shutdown"` のledgerレコードを1行書いてから終了する（本セッションでコードを
   実際に読んで確認済み）。したがって bootout 実行後、対象の `daemon.err.log` /
   `ledger.jsonl` に `shutdown` レコードが**新しいPIDの最初のレコードより前のタイムスタンプで
   書かれていること**を確認してから、初めて「安全に再起動が完了した」とみなす。
2. **未決済のポジションが再起動で失われないこと**: `runtime/loop/index.mjs` を本セッションで
   grep した結果、モジュールスコープの可変状態は `currentChildKiller` /
   `loopDetectStreak` / `loopDetectSlot` / `shuttingDown` / `registryForAlwaysAct` /
   `activeSkillSlots` のみで、ポジション/建玉を保持するインメモリ変数は存在しない。
   実際に確認したポジション追跡の実装は2パターンとも「プロセスの外」に状態を持つ:
   - `hasOpenRiskPositionOfYield`（`catalog-gate.mjs:101`）は**既に読み込んだ ledger.jsonl の
     スキャン結果**（ディスク上のファイル、プロセスメモリではない）を参照する。
   - `hasOpenRiskPositionOfHlTrade`（`catalog-gate.mjs:128`）は `queryFn`
     （本番配線: `hl.py account` の `open_positions`）を**毎回ライブに Hyperliquid へ問い合わせる**
     — インメモリキャッシュではない。
   したがって、このインスタンスが保有する建玉はプロセスの再起動によって失われない
   （ledger はディスク上、hl_trade はエクスチェンジ側のライブ照会）。
   **受け入れ条件としての確認手順**: 再起動を実行する**前**に、そのインスタンスが
   現在保有する未決済ポジション一覧を対応するクエリ（`hl.py account` 等、そのインスタンスの
   registry で live な各 earn slot に対応するアカウント照会コマンド）で取得し記録する。
   再起動**後**に同じクエリを再実行し、ポジション一覧が再起動前と一致することを確認する
   （この一致確認そのものが REQ-008 の受け入れ条件の一部であり、一致しない場合は
   PASS と報告しない）。

**Edge Cases**:
- 再起動後も古い PID が生き残っている（bootout が不完全）: detector は
  `launchctl list` から得た**現在の**PIDに対して観測するため、古いPIDの残存を誤って
  PASS と報告しない（新PIDでの観測のみが真）。
- 再起動直後、プロセスがまだ env を確定させる前の一瞬（起動レース）: REQ-004 の
  fail-closed（観測不能→FAIL）が適用され、PASS を誤って返さない。
- `shutdown` レコードが書かれる前にプロセスが強制終了された（5秒のグレース期間を
  超えて子プロセスが応答しなかった等）: `shutdown` レコードの不在を検知し、
  「安全な再起動が確認できなかった」ケースとして扱う（REQ-004 の fail-closed に従い
  PASS としない）。
**Acceptance Criteria**:
- 本 feature の実装完了時点で、`launchctl list | grep ai.anicca.agent-economy-loop` の
  PID に対し `ps -Awwe -o command -p <PID>` を実行して `ANICCA_BRAIN=claude-p` を
  直接確認できる（この検証は Phase 2b/5 で実際に実行し、fresh evidence として記録する。
  「plist を編集した」だけでは PASS と認めない）。
- detector を実インスタンスに対して実行し、`ANICCA_BRAIN` の乖離が0件であるという
  出力を得る。
- 再起動前後のポジション一致確認クエリの出力（fresh evidence）を記録する。
- `daemon.err.log`/`ledger.jsonl` に `shutdown` レコードが新PIDの初回レコードより前の
  タイムスタンプで存在することを確認する。

### REQ-009: 1 wake の所要時間が SLEEP_BASE_S を超えないことの検証とタイムアウト保護
**EARS**: WHEN `runtime/loop/brain.mjs` の `thinkClaudeP`（`ANICCA_BRAIN=claude-p` 経路）が
`claude -p` 子プロセスを起動する THE SYSTEM SHALL その子プロセスの実行時間に上限
（`resolveClaudePTimeoutMs` が解決する値、デフォルト180秒）を設け、上限を
超えたら `runtime/loop/index.mjs:1037-1041` の既存パターンと同じ**二段階**（`SIGTERM` を
送り、2000ms 待って生存していれば `SIGKILL`）で終了させ、明示的なタイムアウトエラー
（例: `claude_p_timeout`）を返す。

**タイムアウト値の解決規則（MUST、具体値で定義 — 曖昧な「適切に」は禁止）**:
- デフォルト = 180秒。wake cadence と単一モデル呼び出しの deadline は独立させる。
- オーバーライド（例: `CLAUDE_P_TIMEOUT_S` のような専用の環境変数、`mainloop-timeout-lib.sh`
  の `CLAUDE_P_MAINLOOP_TIMEOUT_SEC` と同型の命名規約）は「正の有限整数の秒数」である
  ときのみ採用し、それ以外（未設定・非数値・0・負数）はデフォルトへフォールバックする
  （`runtime/loop/index.mjs:1128` の既存 `cfgNum` は `val != null ? Number(val) : fallback`
  という素通しヘルパーで、この検証もクランプも行わない — 本 feature が独自に追加する）。
- **クランプ上限 = `min(解決済み SLEEP_BASE_S, 300秒)`**
  （`mainloop-timeout-lib.sh:resolve_mainloop_timeout_sec` が「次にスケジュールされる
  発火（plist の `StartInterval`=21600秒）を超えないようにクランプする」のと同じ**構造**を、
  この機能の実際の文脈——「次の wake を追い越さず、長周期 loop でも単一呼び出しを
  長時間許可しない」——に当てはめたもの。12時間 cadence は12時間 timeout を意味しない。
  オーバーライドを指定しても5分を超えず、短い cadence では cadence 自体が上限になる。

**Edge Cases**:
- `SLEEP_BASE_S=43200` の長周期 loop でも、単一 `claude -p` 呼び出しは既定180秒で timeout
  する。cadence を deadline として流用しない。
- 本セッションで `claude --help` / `claude -p --help` を実行して確認した通り、この CLI
  バージョンに `--max-turns` フラグは**存在しない**。したがってタイムアウト保護は
  CLI フラグではなく、`runtime/loop/index.mjs:1016-1047`／`:1037-1041` の既存
  `SKILL_TIMEOUT_S` の二段階 kill パターンを `brain.mjs` 側に同じ規約で移植する形で実装する。
- タイムアウトによる kill 後も `thinkClaudeP` は例外を投げ、`ANICCA_BRAIN=claude-p` は
  proxy に silent fallback しない。ledger に `claude_p_timeout` を記録して次 wake で再試行する。
- `SIGTERM` を受けても2000ms以内に終了しない子プロセス: `SIGKILL` を送る
  （`index.mjs:1037-1041` と同じ猶予時間）。
- CLI の子孫プロセスを含む専用 process group 全体を終了する。direct child だけを kill して
  helper を orphan として残してはならない。親 loop 終了時も同じ group を強制終了する。
- prompt と ledger の `model` は tier 用 proxy model ではなく、実際に CLI へ渡す
  `ANICCA_BRAIN_MODEL` を記録する。
**Acceptance Criteria**:
- `thinkClaudeP` にタイムアウト値より短い時間で正常終了する fixture プロセスを渡すと、
  正常な resolve が返る。
- タイムアウト値より長くハングする fixture プロセスを渡すと、タイムアウト経過後に
  まず `SIGTERM` が送られ、2000ms以内に終了しなければ `SIGKILL` が送られて子プロセスが
  終了し、`claude_p_timeout` を含むエラーで reject される（ハング状態のまま resolve も
  reject もされない、という現状のバグが再現しないことをテストで確認する）。
- タイムアウト既定180秒、無効な override の既定値 fallback、
  `min(SLEEP_BASE_S, 300秒)` の hard ceiling を `resolveClaudePTimeoutMs` の純粋関数で確認する。
- fixture が作る grandchild も timeout 後に存在しないこと、および Claude-p の prompt/ledger
  model が `ANICCA_BRAIN_MODEL` と一致することを確認する。

### REQ-010: 監視対象集合の発見は静的列挙ではなく稼働中プロセスからの逆算による
**EARS**: WHEN config-drift detector が REQ-001（plist宣言）または REQ-002（registry
ランタイムコピー）の監視対象集合を決定する THE SYSTEM SHALL その集合を、detector の
コード内にハードコードされたインスタンス名/パスの静的リストからではなく、**現在実際に
稼働している `runtime/loop/index.mjs` プロセスを列挙し、そのプロセス自身の実行時 env から
発見する**。
- REQ-002（registry コピー発見）: `ps -Awwe -o pid,command` を全プロセスに対して実行し、
  コマンドラインに `runtime/loop/index.mjs` を含むプロセスを列挙する。各プロセスの実行時
  env から `ANICCA_HOME` を読み取り、`$ANICCA_HOME/skills/registry.json` を
  そのプロセスのランタイムコピーとして扱う（本セッションで確認した実例:
  PID 94249 の `ANICCA_HOME=/Users/anicca/.anicca-founder`）。
- REQ-001（plist宣言の対応付け）: 同じプロセス列挙の実行時 env から `XPC_SERVICE_NAME`
  を読み取り（本セッションで確認済み: PID 94249 の実 env に
  `XPC_SERVICE_NAME=ai.anicca.agent-economy-loop` が含まれる — これは launchd が
  KeepAlive/StartInterval ジョブの子プロセスに自動的に注入する値であり、detector が
  推測する必要はない）、`~/Library/LaunchAgents/<XPC_SERVICE_NAME>.plist` をそのプロセスの
  宣言側とする。
**Edge Cases**:
- 新しいインスタンス（4個目以降）が起動されたとき、detector のコード変更なしに
  発見される（=`runtime/loop/index.mjs` を実行するプロセスである限り、静的リストの
  更新漏れという理由で監視対象から漏れることは原理的に起きない）。
- `ps -Awwe` に `runtime/loop/index.mjs` を含む行が1つも無い（全インスタンス停止中）:
  監視対象0件は「乖離0件のPASS」ではなく「対象なし」として明示的に区別して報告する
  （沈黙を PASS と誤読させない）。
- `ANICCA_HOME` または `XPC_SERVICE_NAME` が実行時 env に存在しないプロセスが見つかった:
  REQ-004 に従い、そのプロセスについて `reason: "unobservable"` の FAIL を返す
  （黙って対象から除外しない）。
**Acceptance Criteria**:
- `ps -Awwe` 出力の fixture に `runtime/loop/index.mjs` を含む3行を与えたとき、発見関数は
  3個の `{pid, anicca_home, xpc_service_name}` を返す。
- 同じ fixture に4行目を追加しても、発見関数のコードを変更せずに4個返る
  （静的リストのメンテナンスが不要であることをテストで示す）。
- detector のソースコードに、既知のインスタンス名（`agent-economy-loop`, `franklin-loop`,
  `franklin2-loop`, `pm-earner` 等）やランタイムコピーの絶対パス
  （`~/.blockrun`, `~/.anicca-founder`, `~/.franklin2-home` 等）を**対象集合の定義として**
  埋め込むリテラルが存在しないことをコードレビューで確認する（テスト fixture 内の
  期待値としての言及は可、対象発見ロジック本体への埋め込みは不可）。

## Non-Functional Requirements

- **Performance bound**: config-drift detector 全体（REQ-001+REQ-002、対象インスタンス数
  ≤10、ランタイムコピー数 ≤5 の現実的な規模）は 5秒以内に完了する（`ps`/ファイル読み取りの
  実測レイテンシから導出。ネットワークI/Oを含まないため妥当な上限）。
- **Security**（**訂正**: 前版は `runtime/loop/env-filter.mjs` の `scrubPrivateKeys` を
  「秘密鍵らしきキー全般をマスクする」根拠として引いたが、本セッションで実装を実際に
  Read して確認したところ、その正規表現は `/(_WALLET_KEY|_PRIVATE_KEY|_PRIV_KEY)$/`
  という**末尾一致のみ**であり、`ANTHROPIC_API_KEY` や `CLAUDE_CODE_OAUTH_TOKEN` は
  マッチせず素通りする（`brain.mjs:110-115` はこれらを意図的に子プロセスへ渡す —
  それが正しい仕様）。「秘密鍵らしきキー等」という非閉集合の主張は誤りだったため、
  `scrubPrivateKeys` への依存をやめ、以下の閉じた設計に置き換える）:
  detector は `ps -Awwe` から取得した実行時コマンドラインの**生の文字列を一切保持・ログ・
  出力しない**。detector が読み取ってよいのは、その REQ が明示的に比較対象として定義した
  キーの値**だけ**（現時点で REQ-001 は `ANICCA_BRAIN` のみ、REQ-002 は registry.json の
  `<slot>.status` フィールドのみ — いずれも秘密ではない）。それ以外のキー（生成された
  `env` オブジェクトに含まれる `ANTHROPIC_API_KEY` / `CLAUDE_CODE_OAUTH_TOKEN` /
  `ANICCA_WALLET_ADDRESS` 等）は、パース処理の中間表現としてメモリに一時的に存在しうるが、
  detector の戻り値・ログ・標準出力のいずれにも含めてはならない。
  **受け入れ条件（検証可能）**: `ANTHROPIC_API_KEY=sk-test-secret-value` を含む合成
  `ps` 出力 fixture を detector に通したとき、detector の戻り値・stdout・ログのどこにも
  文字列 `sk-test-secret-value` が現れないことをテストで確認する。
- **No regression**: この feature は既存の `runtime/loop/index.mjs` / `brain.mjs` の
  正常系の挙動（proxy 経路のデフォルト動作、既存の `SKILL_TIMEOUT_S` ロジック）を
  変更しない。REQ-009 は `thinkClaudeP` に**タイムアウトを追加するだけ**であり、
  それ以外の分岐・フォールバック挙動は不変とする。
