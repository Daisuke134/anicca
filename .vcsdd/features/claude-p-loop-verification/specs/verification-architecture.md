# Verification Architecture — claude-p-loop-verification (Phase 1b, mode: lean)

## Purity boundary map

このfeatureが触る全ファイルについて、「純関数として単体テスト可能な部分」と「副作用境界（実ネット
ワーク/実ブラウザ/実オンチェーン/実ファイルシステム）」を分離する。既存コードが既にこの分離を実践して
いる箇所（`hrl_classify`、`evaluatePromotion`、`record_earn`の`onchain_check`注入シーム等）はそのパター
ンを再利用し、新しい分離方式を発明しない。

| REQ | 純関数（Tier 1: unit test 可） | 副作用境界（Tier 2/3: integration / 実行環境検証） |
|---|---|---|
| REQ-LV-001/002 | なし（env source は bash の副作用そのもの） | `loop-report.sh` に一時 `HOME`（`$TMPDIR`配下にfake `.openclaw/.env`）を与えて起動し、`AGENTMAIL_API_KEY`が自己解決されることをログ出力で確認する統合テスト |
| REQ-LV-003 | `lr_valid_evidence(evidence_url) -> 0\|1`（新設・純粋: 文字列判定のみ、I/O なし） — `hrl_classify`/`sf_should_continue`と同じ「`--<flag>`引数で直接呼べる」パターンをこのファイルにも追加する | `loop-report.sh` を実際に `""`/`"none"`/`"none: reason"`/`"https://..."` の4パターンで呼び、exit code とログ行を確認する統合テスト |
| REQ-LV-004 | なし（prompt文字列の文言変更） | `*-cli.sh` の `STARTUP` 変数に更新後の文言が含まれることを `grep` で確認 |
| REQ-LV-010/011 | 既存（`reel_verify.*`, `sigStatus`/`usdcDeltaForSig`）— 変更なし、回帰テストのみ | 既存の Tier 2/3 テストをそのまま再実行し green を確認（新規テスト不要） |
| REQ-LV-012 | `parse_ytdlp_json(json_text) -> {view_count, like_count}`（新設・純粋: 文字列/dictパースのみ） | 実 TikTok URL に対して実際に `yt-dlp --dump-json --skip-download` を実行し、`parse_ytdlp_json` に通す統合テスト |
| REQ-LV-013 | `build_video_metrics_row(parsed, url, ts) -> dict`（新設・純粋） | 実ファイルへの追記（`open(path,"a")`）を伴う統合テスト |
| REQ-LV-014 | `parse_ytdlp_json`（REQ-LV-012と共用、重複実装しない） | 実行成功可否の判定（exit code）＋実ファイル追記の統合テスト |
| REQ-LV-015 | `summarize_gig_funnel(applied_rows) -> {applied,replied,won,paid}`（新設・純粋） | `~/gig/applied.jsonl` の実ファイルを読み、`~/gig/gig-funnel.jsonl` への実追記を確認する統合テスト |
| REQ-LV-016 | `summarize_bounty_funnel(gated, attempts_rows) -> {checked,survivors,claimed,submitted,stalled}`（新設・純粋） | `state/gated.json` + `state/attempts.jsonl` の実ファイルを読み、`state/bounty-funnel.jsonl` への実追記を確認する統合テスト |
| REQ-LV-017 | `parse_positions_response(json_text) -> list[dict]`（新設・純粋） | `https://data-api.polymarket.com/positions?user=<実wallet>` への実 GET を伴う統合テスト（無認証、既存 `redeem.py:196` の呼び出しパターンを踏襲） |
| REQ-LV-018 | `founder_report_args(prev_earn, total_earn, status) -> {result, earned_usdc, evidence}`（新設・純粋: STATE.md の数値2つと STATUS 文字列から `loop-report.sh` への4引数を決定論的に組み立てる） | `founder-loop.sh` を実行し、実際に `loop-report.sh` が正しい引数で呼ばれたことをログ（`~/.openclaw/logs/loop-report.log`）で確認する統合テスト |
| REQ-LV-020/021 | なし（プロンプト文言の追加） | `grep` で該当文言が `STARTUP`/cron prompt に含まれることを確認。ledger の `ts` フィールド存在は既存 jq/python チェックで確認 |
| REQ-LV-030 | 対象外（変更なし） | 対象外 |
| REQ-LV-031 | なし（プロンプト文言の追加） | `grep` で文言確認 + 実際に1行でも `{ts,pass_id,mistake,lesson}` 形式が書かれた実ファイルの存在確認（該当 loop の次の実 pass 後） |
| REQ-LV-040 | なし（`verify-loops.sh`はシェルスクリプトの宣言的追加、既存`count`/`fresh`/`liveurl`関数をそのまま呼ぶだけ） | `bash verify-loops.sh` を実行し、8 loop 分のブロックが出力されることを確認する統合テスト |
| REQ-LV-041 | 既存 `self-fix.sh` の識別子正規化ロジックは変更しない | stale artifact を人工的に作り（mtime を過去に設定）、`verify-loops-audit.sh` 実行後に `self-fix.sh` が該当 loop 名で起動されることをログで確認する統合テスト |
| REQ-LV-042 | なし | `verify-loops-audit.sh` 実行後の `loop-report.sh audit ...` 呼び出し引数（本文）に8 loop 分の状態文字列が含まれることを確認 |
| REQ-LV-050/051 | なし（launchd plist の作成・load はオペレーション） | `launchctl list \| grep <label>` の実行結果で確認（実環境検証、Tier 3） |
| REQ-LV-060 | なし | `df -h /` の前後比較 + 承認済みパス以外が変更されていないことの `find`/`git status`相当確認 |
| REQ-LV-070 | 未確定（Phase 2で該当コードを特定してから確定） | 実ログで warmup day が4以降に進行することを確認（実行環境検証） |
| REQ-LV-080 | `verify_onchain`の新実装のうち「Transfer log を owner/amount 条件でフィルタする部分」は`~/anicca/skills/self/founder-loop/record-earn.mjs`の`parseRawLogs`/`sumExternal`と同型のPython純関数として抽出可能（新設・純粋） | 実 Base RPC (`https://mainnet.base.org`) への `eth_getLogs` 呼び出しを伴う統合テスト。既存の `onchain_check`注入シームにより、既存のスキーマゲート単体テスト（`is_real_usdc_inflow`）は無改変で green のまま |

## 検証手段の対応（設計spec §検証アーキテクチャ表 との対応）

| loop | 検証手段 | Tier | このfeatureでの実装状態 |
|---|---|---|---|
| clip | `self_heal.py`実ページ読み + browser実測 | 既存(Tier 2/3) | 維持のみ（回帰テスト） |
| clip-promote | `record-payout.mjs`のon-chain confirmed検証 | 既存(Tier 2/3) | 維持のみ（回帰テスト） |
| video | TikTok=`yt-dlp --dump-json`、IG=`metrics.py`browser実測 | 新設(TikTok, Tier 2) + 既存(IG) | REQ-LV-012/013 |
| affiliate | `yt-dlp`実行成功可否 + commission-watermark.json | 新設(Tier 2) | REQ-LV-014 |
| gig | CloakBrowser実読み(応募/受注/入金ページ) | 既存(会話は既存applied.jsonl) + 新設funnel集計(Tier 1+2) | REQ-LV-015 |
| bounty | board API/実ページ | 既存(gated.json/attempts.jsonl書き込みは既存run.sh) + 新設funnel集計(Tier 1+2) | REQ-LV-016 |
| pm-earner | data-api.polymarket.com/positions(無認証) + tx status==0x1 | 既存(tx確認) + 新設(positionsパース, Tier 1) | REQ-LV-017 |
| founder-loop | on-chain残高照合(record-earn.mjs) | 既存(維持) + 新設mail配線(Tier 2) | REQ-LV-018 |

## Proof obligations（lean mode: Tier 1 必須、Tier 2 は主要経路のみ、Tier 3 は主エージェントの実行確認）

| ID | Requirement | Tier | Required (lean) | Verification method |
|---|---|---|---|---|
| PROP-LV-001 | REQ-LV-003 (`lr_valid_evidence`の3分岐) | 1 | true | `lr_valid_evidence ""` → reject; `lr_valid_evidence "none"` → reject; `lr_valid_evidence "none: queue empty"` → accept; `lr_valid_evidence "https://..."` → accept。4ケース全て assert |
| PROP-LV-002 | REQ-LV-001 (env自己解決、fail-closed維持) | 2 | true | (a) `.env`にkeyがある一時HOMEで起動→`AGENTMAIL_API_KEY`が解決されログにNO-OPが出ない side-effect が確認できること（実送信は別途モックしてもよい）。(b) `.env`が存在しない/keyが無い一時HOMEで起動→従来どおり`NO-OP`ログ+`exit 0`（block しない）ことを確認 |
| PROP-LV-003 | REQ-LV-012/014 (`parse_ytdlp_json`) | 1 | true | 正常JSON→`view_count`抽出成功；`view_count`欠損JSON→`None`（例外を投げない）；不正JSON文字列→`None`（クラッシュしない） |
| PROP-LV-004 | REQ-LV-015 (`summarize_gig_funnel`) | 1 | true | 空配列→全て0；`applied`のみの行×3→`{applied:3,replied:0,won:0,paid:0}`；`applied`→`replied`→`検収完了`まで揃った行が混在するケースで正しく集計されること |
| PROP-LV-005 | REQ-LV-016 (`summarize_bounty_funnel`) | 1 | true | `survivors`空 + `attempts`空→全て0；`status:claim,pr:null`が1件→`claimed:1,submitted:0`；`pr`非null→`submitted`にカウント；`status:stalled`→`stalled`にカウントし`claimed`から二重計上しない |
| PROP-LV-006 | REQ-LV-017 (`parse_positions_response`) | 1 | true | 正常な複数ポジションJSON→件数一致の`list[dict]`；空配列レスポンス→`[]`；不正JSON→`[]`（クラッシュしない、`redeem.py`のfail-closed方針と一致） |
| PROP-LV-007 | REQ-LV-018 (`founder_report_args`) | 1 | true | `prev=0,total=5.0`→`result="success", earned_usdc=5.0`；`prev=5.0,total=5.0`（増分なし）→`result="queue-empty", earned_usdc=0`；`total<prev`はあり得ない前提だが防御的に`earned_usdc`を負にしない（0にクランプ） |
| PROP-LV-008 | REQ-LV-080 (`verify_onchain`新実装のログフィルタ純関数) | 1 | true | 既存`record-earn.mjs`の`parseRawLogs`/`sumExternal`テスト観点をPython側に移植: 正しいUSDC contract + 正しいtopic0 + 正しいto-topicの行のみ真として扱う；他コントラクトのログは無視；`amount`不一致は拒否 |
| PROP-LV-009 | REQ-LV-080 (`record_earn`の既存シーム無改変) | 1 | true | 既存の`record_earn(entry, ledger_path, onchain_check=lambda e: True)`スタブ注入テストが変更なしでgreenのまま通ることを確認（回帰） |
| PROP-LV-010 | REQ-LV-040 (verify-loops.sh 8loop拡張) | 2 | true | `verify-loops.sh`を実行し、出力に`[clip]`〜`[founder-loop]`の8ブロック全てが含まれることを文字列一致で確認 |
| PROP-LV-011 | REQ-LV-041 (stale escalation) | 2 | true | 8 loopのうち1つ（例: gig-funnel.jsonl）のmtimeを意図的にしきい値超で古くし、`verify-loops-audit.sh`実行後に`self-fix.sh gig ...`相当の起動ログが`~/.openclaw/logs/verify-loops-audit.log`に現れることを確認 |
| PROP-LV-012 | REQ-LV-050/051 (launchd配線) | 3 | true | `launchctl list \| grep <label>`が新設jobを返すこと。main agentが実環境で確認（adversaryはlaunchdを操作できない） |
| PROP-LV-013 | Goal 1/6 E2E（1 loopにつき1本、evidence付きmail 1サイクル） | 3 | true | 各loopについて: 実 pass実行 → 実evidence（URL/tx/数値）発生 → `loop-report.sh`が実際にHTTP 200/201でmail送信 → `~/.openclaw/logs/loop-report.log`に`SENT`行が残る、をmain agentが実行し記録する。fresh-context adversary（Opus 4.8）がこのログ+ledger行を読みPASS/FAILを判定する |

## Verification tiers legend

- Tier 1: 純関数の単体テスト。決定論的フィクスチャ、実ネットワーク/実ブラウザ/実ファイル書き込みなし。
- Tier 2: 実ファイル読み書き・実プロセス起動（`yt-dlp`実行等）を伴う統合テスト。実SNS投稿・実送金は行わない。
- Tier 3: 実行環境上の real E2E（実mail送信・実launchd登録・実オンチェーン確認）。main agentが実行し、
  fresh-context adversary（`~/.claude/CLAUDE.md`モデル分業表: Opus 4.8）がログ/ledger/mailログを読んで
  判定する。dry run禁止（`~/.claude/CLAUDE.md` No dry run）。

## Gate

Phase 1c（spec review）は上記 REQ-LV-001〜080 が (a) 存在しない symbol/path を参照していないこと
（Ground truth節の実ファイル確認と一致していること）、(b) 判断（何に応募するか・何を改善するか・何が
mistakeか）がコード側でハードコードされていないこと、(c) 各 REQ に Tier 1 or Tier 2 の具体的な
verification method が付いていることの3点を fresh-context adversary が確認し PASS/FAIL を出す。
REQ-LV-070（video warmup バグ）のみ、実装対象コードパスが Phase 1 時点で未特定であることを spec review
で明示し、Phase 2 着手時に spec を1行追記してから着手することを条件付き PASS の対象とする。
