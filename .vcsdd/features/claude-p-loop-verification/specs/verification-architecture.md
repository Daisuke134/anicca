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
| REQ-LV-041 | **SUPERSEDED by REQ-LV-100〜104**（下表参照） | 対象外（旧 `fresh()` ベースのテストは書かない） |
| REQ-LV-042 | なし | REQ-LV-103 参照 |
| REQ-LV-050/051 | なし（launchd plist の作成・load はオペレーション） | `launchctl list \| grep <label>` の実行結果で確認（実環境検証、Tier 3） |
| REQ-LV-060 | なし | `df -h /` の前後比較 + 承認済みパス以外が変更されていないことの `find`/`git status`相当確認 |
| REQ-LV-070 | 未確定（Phase 2で該当コードを特定してから確定） | 実ログで warmup day が4以降に進行することを確認（実行環境検証） |
| REQ-LV-080 | `verify_onchain`の新実装のうち「Transfer log を owner/amount 条件でフィルタする部分」は`~/anicca/skills/self/founder-loop/record-earn.mjs`の`parseRawLogs`/`sumExternal`と同型のPython純関数として抽出可能（新設・純粋） | 実 Base RPC (`https://mainnet.base.org`) への `eth_getLogs` 呼び出しを伴う統合テスト。既存の `onchain_check`注入シームにより、既存のスキーマゲート単体テスト（`is_real_usdc_inflow`）は無改変で green のまま |

### v2追加分の purity boundary（Cadence / EDD / Dashboard / Loop Scaling / OpenClaw統合）

| REQ | 純関数（Tier 1: unit test 可） | 副作用境界（Tier 2/3: integration / 実行環境検証） |
|---|---|---|
| REQ-LV-100 | なし（config宣言） | 各loopのhealthcheck設定ファイルにcadence contractのJSONが実際に書かれていることを確認 |
| REQ-LV-101 | `cadence_met(ledger_rows, today_jst_date, contract) -> bool`（新設・純粋、`~/anicca/skills/self/verify-loops.sh`の既存`fresh()`とは独立した新関数） | 実ledgerファイルを読んで`cadence_met`に通す統合テスト |
| REQ-LV-102 | 判定自体は`cadence_met`（REQ-LV-101）を再利用、新規純関数なし | JST 21:00到達をシミュレートし（時刻を注入可能にする）、`cadence_met=false`のloopに対し`self-fix.sh`が実際に起動されることをログで確認する統合テスト |
| REQ-LV-103 | `streak(ledger_rows, today_jst_date, contract) -> int`（新設・純粋: `cadence_met`を日ごとに遡って呼ぶだけの合成関数） | `verify-loops-audit.sh`実行後の`loop-report.sh audit ...`本文に`streak=N`形式の文字列が含まれることを確認 |
| REQ-LV-104 | なし（既存`fresh()`呼び出し箇所の削除・置換という差分） | `verify-loops.sh`の8loopブロックのdiffを読み、`fresh()`呼び出しが残っていないことを`grep`で確認（capafy/reddit/lmの3ブロックには残ることを確認） |
| REQ-LV-110 | 各loop固有`evaluator.py`の`evaluate_stage1/evaluate_stage2` — 既存`~/anicca/skills/earn/self-improve/evaluator.py`と同型で、fixture/ledger読み取り→`combined_score`返却のみ、I/O副作用なし（新設・純粋、loopごとに1本） | 実ledgerデータをfixtureとして与え、`combined_score`が実際に計算されることを確認する統合テスト |
| REQ-LV-111 | `beats_previous_week(this_week_score, last_week_score) -> bool`（新設・純粋） | metrics ledgerへの実追記（週次行）を確認する統合テスト |
| REQ-LV-112 | `lib/promote_gate.py`相当の決定論pre-check関数（新設・loopごと、または既存`lib/promote_gate.py`を汎用化して共用） | 実`claude --model opus --dangerously-skip-permissions --print`呼び出しを伴うE2E（Tier 3、pre-checkを通過したcandidateに対してのみ発火することを確認） |
| REQ-LV-113 | なし（プロンプト文言追加） | `grep`で該当文言が各loopのSTARTUP promptに含まれることを確認 |
| REQ-LV-120 | なし（`telemetry-collect.sh`拡張は既存ロジックへの追加分岐） | `telemetry-collect.sh`実行後、`~/.anicca-founder/state/loop-registry.json`が実際に書かれ、8loop分のオブジェクトを含むことを確認する統合テスト |
| REQ-LV-121 | `git diff`相当で`apps/landing/**`への差分がゼロであることを機械的に確認可能（新規の純関数は不要、既存の書き込み制限チェックの再利用） | この feature の実装コミットが`apps/landing/**`を一切変更していないことを`git diff --stat`で確認 |
| REQ-LV-122 | 対象外（この feature の実装スコープ外、依存関係の明記のみ） | 対象外 |
| REQ-LV-130 | `scale_eligible(streak, weekly_score, weekly_score_threshold, disk_free_gb) -> bool`（新設・純粋） | config YAMLを読み実際のstreak/scoreと突き合わせる統合テスト |
| REQ-LV-131 | spawnイベント行の組み立て`build_spawn_event(loop_type, account, instance_suffix, spawned_by, ts) -> dict`（新設・純粋） | 実際に`ig-account-create`skillを呼び新アカウントを作成するE2E（Tier 3、実SNSアカウント作成を伴う）+ `loop-registry.jsonl`への実追記確認 |
| REQ-LV-132/133/134 | `cooldown_ok(last_spawn_ts, now_ts, min_interval_days) -> bool`、`fleet_at_capacity(current_count, max_count) -> bool`（いずれも新設・純粋） | `loop-registry.jsonl`の実データに対してこれらの関数を通す統合テスト |
| REQ-LV-135 | `is_ban_suspected(consecutive_failures, threshold) -> bool`（新設・純粋） | 実際に`loop-registry.json`の`status`が`"paused"`に更新され、lessons ledgerに実際に1行追記されることを確認する統合テスト |
| REQ-LV-140 | なし（確定済み分類の記録、agentによる再分類作業は不要） | 5分類の件数合計（30+23+7+24+19=103）が`~/.openclaw/cron/jobs.json`の実`enabled:true`件数（103、確認済み）と一致することを確認 |
| REQ-LV-141 | なし（6前提条件の解消はオペレーション） | 前提条件1〜5は各対象ファイル（`ai.openclaw.gateway.plist`存在、`_dispatcher/scripts/cron-bash.sh`呼び出し箇所の置換、`loop-report.sh`通知経路への統一、`aniccaai-dashboard-refresh`の書き込み先変更）の実環境確認。前提条件6（`anicca-event-bot-trigger`のgog CLI依存）はPhase 2着手時に実際に`gog`コマンドの依存関係を調査し確定させてから着手する（Phase 1時点ではUNVERIFIEDのまま） |
| REQ-LV-142 | なし（5ステップの移行はオペレーション） | 各ステップ完了後に前段の成果物（例: ステップ①後は(a-1)/(a-2)/(a-3)対象84件中の該当分がclaude-p側のtmux core/launchdに実際に存在すること、ステップ③の7日間並走中に二重投稿が発生していないこと）を実環境で確認する統合テスト、ステップごとに1本 |
| REQ-LV-143 | なし | `git -C ~/.openclaw log --oneline -1`相当のコマンドを実行し、未pushの変更（`git status --short`）がゼロであることを確認 |
| REQ-LV-144 | なし（Dais明示goの有無はコードで判定できない人間判断） | 削除コマンドの実行ログに、Dais本人からの明示go指示への参照（メッセージID/タイムスタンプ等）が記録されていることを確認 |
| REQ-LV-145 | 対象外（他REQの再検証） | REQ-LV-001〜018/020〜031/100〜104の既存テストスイートを移植先loop（(a-1)/(a-2)/(a-3)/(b)、合計84件相当のloop群）に対しても実行しgreenを確認 |

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
| PROP-LV-011 | **SUPERSEDED**（旧REQ-LV-041のstale escalation） — PROP-LV-020/021に置換 | — | — | 対象外（旧`fresh()`ベースの検証は行わない） |
| PROP-LV-012 | REQ-LV-050/051 (launchd配線) | 3 | true | `launchctl list \| grep <label>`が新設jobを返すこと。main agentが実環境で確認（adversaryはlaunchdを操作できない） |
| PROP-LV-013 | Goal 1/6 E2E（1 loopにつき1本、evidence付きmail 1サイクル） | 3 | true | 各loopについて: 実 pass実行 → 実evidence（URL/tx/数値）発生 → `loop-report.sh`が実際にHTTP 200/201でmail送信 → `~/.openclaw/logs/loop-report.log`に`SENT`行が残る、をmain agentが実行し記録する。fresh-context adversary（Opus 4.8）がこのログ+ledger行を読みPASS/FAILを判定する |

### v2追加分の Proof obligations（Cadence / EDD / Dashboard / Loop Scaling / OpenClaw統合）

| ID | Requirement | Tier | Required (lean) | Verification method |
|---|---|---|---|---|
| PROP-LV-020 | REQ-LV-101 (`cadence_met`の日境界判定) | 1 | true | `today="2026-07-08"`、ledger行のtsが同日JST→true；前日のみ→false；空配列→false。JST日境界をまたぐUTC深夜のtsケース（例: UTC 2026-07-08T16:00Z = JST 2026-07-09T01:00）も1ケース追加し、UTC日付ではなくJST暦日で判定されることを明示的に確認 |
| PROP-LV-021 | REQ-LV-102 (21:00 JST escalation、過去実績で抑制されない) | 2 | true | ある loop の直近ledger行が7日前（＝旧`fresh()`方式なら閾値内でPASSしていたはずのケース）で当日行が無い状態を作り、JST 21:00到達をシミュレートした`verify-loops-audit.sh`実行で`self-fix.sh`が実際に起動されることを確認（「7日前に投稿があるからOK」にならないことの直接証明） |
| PROP-LV-022 | REQ-LV-103 (`streak`の連続日数計算) | 1 | true | 直近3日連続で`cadence_met=true`→`streak=3`；2日連続の後1日欠落→`streak`はその欠落日以降0にリセット（欠落日を跨いだ加算をしない） |
| PROP-LV-023 | REQ-LV-110 (loop固有evaluatorの`combined_score`、LLM judge不使用) | 1 | true | 固定fixtureデータに対し`combined_score`が決定論的に同じ値を返すこと（同一入力→同一出力、2回実行して比較）；既存`evaluator.py`同様、評価対象コードが発注/投稿系モジュールを一切importしていないことをコードレビュー相当のgrepで確認（sandbox境界） |
| PROP-LV-024 | REQ-LV-111 (`beats_previous_week`) | 1 | true | `this=10,last=5`→true；`this=5,last=10`→false；`this=5,last=5`（同点）→false（tieはbeatにならない、既存`evaluatePromotion`のbaseline-floor思想と整合） |
| PROP-LV-025 | REQ-LV-112 (promote gate 2段ゲート) | 3 | true | pre-checkを意図的に失敗させたcandidateではadversary呼び出しが一切発生しないこと（呼び出しログで確認）、pre-check通過candidateではadversary呼び出しが発生しPASS/FAILいずれの場合も昇格判断がその結果と一致すること |
| PROP-LV-026 | REQ-LV-120 (`loop-registry.json`書き出し) | 2 | true | `telemetry-collect.sh`実行後、`~/.anicca-founder/state/loop-registry.json`に8loop分のオブジェクトが存在し、各`status`がREQ-LV-101の`cadence_met`結果と一致することを確認 |
| PROP-LV-027 | REQ-LV-121 (landing直接write禁止) | 2 | true | この feature の全実装コミットに対し `git diff --stat` で `apps/landing/` 配下のファイルが1件も変更されていないことを確認 |
| PROP-LV-028 | REQ-LV-130 (`scale_eligible`3条件AND) | 1 | true | `streak=7,score>threshold,disk=5`→true；`streak=6`（1不足）→false；`disk=4.9`→false；3条件全て満たすが`score==threshold`（超過でなく同値）→false（`>`であって`>=`でない） |
| PROP-LV-029 | REQ-LV-132/133/134 (guardrail純関数群) | 1 | true | `cooldown_ok`: 直近spawnから設定日数未満→false；`fleet_at_capacity`: 現在数==上限→true、現在数<上限→false |
| PROP-LV-030 | REQ-LV-135 (`is_ban_suspected`) | 1 | true | `consecutive_failures < threshold`→false；`==threshold`→true；閾値到達で`loop-registry.json`のstatusが実際に`"paused"`へ更新されることを統合テストで確認 |
| PROP-LV-031 | REQ-LV-140 (cron棚卸し確定分類の件数一致) | 1 | true | 5分類の確定件数 30+23+7+24+19 を合計すると103になること（純粋な算術検算）；`~/.openclaw/cron/jobs.json`の実`enabled:true`件数（103、確認済み）と一致することを確認 |
| PROP-LV-032 | REQ-LV-144 (Dais明示go precondition) | 3 | true | OpenClaw削除コマンドを実行するpassのログに、Dais本人からの明示go指示（メッセージ本文またはタイムスタンプ参照）が記録されていること。この記録が無い状態でステップ⑤のコマンドが実行された形跡がないことを事後的にログで確認する（fail-closed: 記録が無ければ削除は実行されていないはず） |
| PROP-LV-033 | REQ-LV-141 (6前提条件の解消確認) | 2 | true | 前提条件1〜5それぞれについて対応する実ファイル/実装（`ai.openclaw.gateway.plist`の代替launchd plist存在、`cron-bash.sh`呼び出し箇所が置換済み、`loop-report.sh`への通知経路統一、`aniccaai-dashboard-refresh`のpush先変更）を実環境で確認。前提条件6は「UNVERIFIED」のまま残っていないこと（Phase 2着手時に確定情報がspecに追記されていること）を確認 |
| PROP-LV-034 | REQ-LV-142 (5ステップの順序遵守、並行スキップ禁止) | 2 | true | ステップ②着手時にステップ①の成果物（(a-1)/(a-2)/(a-3)対象のskillが実際に`~/anicca/skills`へ移設済み）が存在することを確認してから着手した記録が残っていること；ステップ③の7日間並走中、二重投稿の検知ログがあった場合は該当jobが実際にdisableされていることを確認 |

## Verification tiers legend

- Tier 1: 純関数の単体テスト。決定論的フィクスチャ、実ネットワーク/実ブラウザ/実ファイル書き込みなし。
- Tier 2: 実ファイル読み書き・実プロセス起動（`yt-dlp`実行等）を伴う統合テスト。実SNS投稿・実送金は行わない。
- Tier 3: 実行環境上の real E2E（実mail送信・実launchd登録・実オンチェーン確認）。main agentが実行し、
  fresh-context adversary（`~/.claude/CLAUDE.md`モデル分業表: Opus 4.8）がログ/ledger/mailログを読んで
  判定する。dry run禁止（`~/.claude/CLAUDE.md` No dry run）。

## Gate

Phase 1c（spec review）は上記 REQ-LV-001〜145（v2改訂分含む）が (a) 存在しない symbol/path を
参照していないこと（Ground truth節の実ファイル確認と一致していること）、(b) 判断（何に応募するか・
何を改善するか・何がmistakeか・どのアカウントをscaleするか）がコード側でハードコードされていない
こと、(c) 各 REQ に Tier 1 or Tier 2 の具体的な verification method が付いていることの3点を
fresh-context adversary が確認し PASS/FAIL を出す。
REQ-LV-070（video warmup バグ）のみ、実装対象コードパスが Phase 1 時点で未特定であることを spec review
で明示し、Phase 2 着手時に spec を1行追記してから着手することを条件付き PASS の対象とする。
REQ-LV-041 は REQ-LV-100〜104 により SUPERSEDED（併記ではなく置換）— spec review はこの置換が
矛盾なく行われていること（旧 stale 判定ロジックが8 loop 分から完全に除去され、cadence判定に
一本化されていること）も確認する。REQ-LV-140（cron棚卸し確定分類、30+23+7+24+19=103で件数一致
確認済み）はPhase 1時点で既に確定しておりPASSの対象。REQ-LV-141の前提条件6（`anicca-event-bot-trigger`
のgog CLI依存）とREQ-LV-144（Dais明示go）は、Phase 1時点ではそれぞれ依存確認・go指示そのものが
未確定であるため、REQ-LV-070と同様に条件付きPASSの対象とし、Phase 2着手時（前提条件6）または
ステップ⑤着手時（REQ-LV-144）に確定情報をspecへ追記する。
