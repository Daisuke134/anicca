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
| REQ-LV-019（F5新設: Goal 6独立REQ） | なし（E2Eサイクル自体とadversary判定は副作用そのもの、純粋関数化できない） | 8loop（7 loop + clip-promote）それぞれについて実pass実行→実evidence発生→`loop-report.sh`実送信のフルサイクルをmain agentが実行し、`~/.openclaw/logs/loop-report.log`の`SENT`行+対応ledgerの新規行をfresh-context adversary（Opus 4.8）に提示しPASS判定を得る（Tier 3、PROP-LV-013と同一の検証対象を独立REQとして明示） |
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
| REQ-LV-100（G1修正: `recency` kind追加、5種のスキーマ） | なし（config宣言、`kind`判別子で5種のスキーマを区別） | 各loopのhealthcheck設定ファイルに、loopごとに正しい`kind`（row-exists/increment/pass-marker/recency/compound）のcadence contract JSONが実際に書かれていること、pm-earnerのcompound内`hourly-pass`条件が`kind:"pass-marker"`ではなく`kind:"recency"`かつ`max_age_min:40`であることを確認 |
| REQ-LV-101（F1修正: 単一シグネチャで5 kindを分岐するdispatcher。G1修正: `recency`分岐を追加） | `cadence_met(today_jst_date, contract, evidence) -> bool`（新設・純粋、`contract["kind"]`で5分岐: row-exists=`evidence["event_dates"]`にtoday含むか／increment=`evidence["today_value"]>evidence["previous_value"]`／pass-marker=`evidence["marker_jst_date"]==today`／**recency=`(evidence["now_epoch_seconds"]-evidence["marker_epoch_seconds"])<=contract["max_age_min"]*60`（G1新設、JST暦日境界を参照しない秒差判定）**／compound=`contract["conditions"]`全件のAND再帰。`~/anicca/skills/self/verify-loops.sh`の既存`fresh()`とは独立した新関数） | 5 kindそれぞれについて実データ（clip/affiliate/video/gigのledger行、bountyの`bounty-funnel.jsonl`前日比、founder-loopの`STATE.md`mtime、pm-earnerの`earner.log`mtimeをエポック秒で+redeem行）を読んで`cadence_met`に通す統合テスト |
| REQ-LV-102 | 判定自体は`cadence_met`（REQ-LV-101、loopのkindに応じた分岐）を再利用、新規純関数なし | JST 21:00到達をシミュレートし（時刻を注入可能にする）、いずれかのkindで`cadence_met=false`のloopに対し`self-fix.sh`が実際に起動されることをログで確認する統合テスト |
| REQ-LV-103 | `streak(evidence_by_date, today_jst_date, contract) -> int`（新設・純粋: `evidence_by_date`は日付→その日のevidence。`cadence_met`を日ごとに遡って呼ぶだけの合成関数——kind分岐は`cadence_met`側が担うため`streak`自体はkindに非依存） | `verify-loops-audit.sh`実行後の`loop-report.sh audit ...`本文に`streak=N`形式の文字列が含まれることを確認（5 kind全てで） |
| REQ-LV-104（G1修正: pm-earnerのhourly-pass分はrecency用エポック秒収集、daily-redeem分はrow-exists用JST暦日収集と明示） | なし（既存`fresh()`呼び出し箇所の削除・置換という差分） | `verify-loops.sh`の8loopブロック（REQ-LV-040参照、clip-promote含む）のdiffを読み、`fresh()`呼び出しが残っていないこと、7 loop分は各loopのkindに応じた正しいevidence収集（event_dates/today_value・previous_value/marker_jst_date/marker_epoch_seconds・now_epoch_seconds/by_condition）、clip-promote分は`clip_promote_status()`（REQ-LV-120）が呼ばれていることを`grep`+実行確認（capafy/reddit/lmの3ブロックには`fresh()`が残ることを確認）。pm-earnerのcompound評価が`hourly-pass`（`earner.log`のmtimeをエポック秒で収集）と`daily-redeem`（ledgerのredeem行をJST暦日で収集）という2つの異なる収集経路を実際に呼び分けていることも確認 |
| REQ-LV-110 | 各loop固有`evaluator.py`の`evaluate_stage1/evaluate_stage2` — 既存`~/anicca/skills/earn/self-improve/evaluator.py`と同型で、fixture/ledger読み取り→`combined_score`返却のみ、I/O副作用なし（新設・純粋、loopごとに1本） | 実ledgerデータをfixtureとして与え、`combined_score`が実際に計算されることを確認する統合テスト |
| REQ-LV-111 | `beats_previous_week(this_week_score, last_week_score) -> bool`（新設・純粋） | metrics ledgerへの実追記（週次行）を確認する統合テスト |
| REQ-LV-112 | `lib/promote_gate.py`相当の決定論pre-check関数（新設・loopごと、または既存`lib/promote_gate.py`を汎用化して共用） | 実`claude --model opus --dangerously-skip-permissions --print`呼び出しを伴うE2E（Tier 3、pre-checkを通過したcandidateに対してのみ発火することを確認） |
| REQ-LV-113 | なし（プロンプト文言追加） | `grep`で該当文言が各loopのSTARTUP promptに含まれることを確認 |
| REQ-LV-120（F2修正: clip-promote用の独立status判定を追加） | `clip_promote_status(payout_rows, today_jst_date) -> {"status":"payout-today"\|"no-payout-today"}`（新設・純粋: `record-payout.mjs`の`status:"recorded"`行のtsが当日JST日付に存在するかのみを見る、`cadence_met`は呼ばない）。他7loop分は`cadence_met`/`streak`（REQ-LV-101/103）をそのまま再利用、新規純関数なし | `telemetry-collect.sh`実行後、`~/.anicca-founder/state/loop-registry.json`が実際に書かれ、8loop分（7 loop分の`cadence_met`ベースstatus + clip-promoteの`clip_promote_status`ベースstatus）のオブジェクトを含むことを確認する統合テスト |
| REQ-LV-121 | `git diff`相当で`apps/landing/**`への差分がゼロであることを機械的に確認可能（新規の純関数は不要、既存の書き込み制限チェックの再利用） | この feature の実装コミットが`apps/landing/**`を一切変更していないことを`git diff --stat`で確認 |
| REQ-LV-122 | 対象外（この feature の実装スコープ外、依存関係の明記のみ） | 対象外 |
| REQ-LV-130 | `scale_eligible(streak, weekly_score, weekly_score_threshold, disk_free_gb) -> bool`（新設・純粋） | config YAMLを読み実際のstreak/scoreと突き合わせる統合テスト |
| REQ-LV-131 | spawnイベント行の組み立て`build_spawn_event(loop_type, account, instance_suffix, spawned_by, ts) -> dict`（新設・純粋） | 実際に`ig-account-create`skillを呼び新アカウントを作成するE2E（Tier 3、実SNSアカウント作成を伴う）+ `loop-registry.jsonl`への実追記確認 |
| REQ-LV-132/133/134 | `cooldown_ok(last_spawn_ts, now_ts, min_interval_days) -> bool`、`fleet_at_capacity(current_count, max_count) -> bool`（いずれも新設・純粋） | `loop-registry.jsonl`の実データに対してこれらの関数を通す統合テスト |
| REQ-LV-135 | `is_ban_suspected(consecutive_failures, threshold) -> bool`（新設・純粋） | 実際に`loop-registry.json`の`status`が`"paused"`に更新され、lessons ledgerに実際に1行追記されることを確認する統合テスト |
| REQ-LV-140 | なし（確定済み分類+v2.2移行方針の記録、agentによる再分類作業は不要） | 5分類の件数合計（30+23+7+24+19=103）が`~/.openclaw/cron/jobs.json`の実`enabled:true`件数（103、確認済み）と一致することを確認 |
| REQ-LV-141（v2.2新設: 移行gate） | `channel_migration_eligible(has_verification_tool) -> bool`（新設・純粋、恒等関数に近いが判定を明示的にコード化——判断＝どのチャネルに検証ツールがあるかはagent、結果の記録＝決定論） | (a-1)の30件それぞれについて`{channel, has_verification_tool, verification_method}`の記録が実際に作られていること、`has_verification_tool=false`のチャネルがWave 1移行対象（REQ-LV-143①）に含まれていないことを確認する統合テスト |
| REQ-LV-142 | なし（6前提条件の解消はオペレーション） | 前提条件1〜5は各対象ファイル（`ai.openclaw.gateway.plist`存在、`_dispatcher/scripts/cron-bash.sh`呼び出し箇所の置換、`loop-report.sh`通知経路への統一、`aniccaai-dashboard-refresh`の書き込み先変更）の実環境確認。前提条件6（`anicca-event-bot-trigger`のgog CLI依存）はPhase 2着手時に実際に`gog`コマンドの依存関係を調査し確定させてから着手する（Phase 1時点ではUNVERIFIEDのまま） |
| REQ-LV-143（v2.2反映: Wave 1限定migrate、Wave 2は実装スコープ外） | なし（5ステップの移行はオペレーション） | ステップ①完了後、実際に`~/anicca/skills`へ移設されたチャネルが全て`has_verification_tool=true`（REQ-LV-141）であること、`has_verification_tool=false`のチャネルが1件も移設されていないことを確認。ステップ②（Wave 2）はこのfeatureの実装コミットに含まれていないこと（`git diff --stat`でWave 2対象の新規実装ファイルがゼロであることを確認）。ステップ③の7日間並走中に二重投稿が発生していないことを実環境で確認する統合テスト、ステップごとに1本 |
| REQ-LV-144 | なし | `git -C ~/.openclaw log --oneline -1`相当のコマンドを実行し、未pushの変更（`git status --short`）がゼロであることを確認 |
| REQ-LV-145 | なし（Dais明示goの有無はコードで判定できない人間判断） | 削除コマンドの実行ログに、Dais本人からの明示go指示への参照（メッセージID/タイムスタンプ等）が記録されていることを確認 |
| REQ-LV-146（v2.2反映: 検証対象をWave 1移行分のみに縮小） | 対象外（他REQの再検証） | REQ-LV-001〜004/019/020〜031/100〜104の既存テストスイートを、Wave 1で実際に移行されたloop群（(a-1)のうち`has_verification_tool=true`のチャネルのみ、30件全件ではない）に対してのみ実行しgreenを確認。(a-2)/(a-3)/(b)/(c)はこのfeatureの検証対象に含まれないことも確認（含まれていたら誤り） |

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
| PROP-LV-038（F5新設: REQ-LV-019、Goal 6独立REQとしての完了判定） | REQ-LV-019 (8loop全てでE2E+adversary PASSが揃うまでGoal 6は未達) | 3 | true | PROP-LV-013の8loop分の実行結果（各loopのSENT行+ledger新規行+adversary個別PASS）を集計し、1つでも欠けている状態では「Goal 6未達成」と判定されること（8loop中7loop分がPASSでも全体PASSにならないことを明示的に確認する集計チェック） |

### v2追加分の Proof obligations（Cadence / EDD / Dashboard / Loop Scaling / OpenClaw統合）

| ID | Requirement | Tier | Required (lean) | Verification method |
|---|---|---|---|---|
| PROP-LV-020 | REQ-LV-101 の `kind=="row-exists"`分岐（clip/affiliate/video/gig、日境界判定） | 1 | true | `today="2026-07-08"`、`evidence["event_dates"]`に同日JST文字列が含まれる→true；前日のみ→false；空配列→false。JST日境界をまたぐUTC深夜のtsケース（例: UTC 2026-07-08T16:00Z = JST 2026-07-09T01:00）を呼び出し元のevidence構築時に正しくJST暦日へ変換していることを確認するケースを1件追加 |
| PROP-LV-021 | REQ-LV-102 (21:00 JST escalation、過去実績で抑制されない) | 2 | true | ある loop（row-exists kind）の直近ledger行が7日前（＝旧`fresh()`方式なら閾値内でPASSしていたはずのケース）で当日行が無い状態を作り、JST 21:00到達をシミュレートした`verify-loops-audit.sh`実行で`self-fix.sh`が実際に起動されることを確認（「7日前に投稿があるからOK」にならないことの直接証明） |
| PROP-LV-022 | REQ-LV-103 (`streak`の連続日数計算、kindに非依存) | 1 | true | 直近3日連続で`cadence_met=true`→`streak=3`；2日連続の後1日欠落→`streak`はその欠落日以降0にリセット（欠落日を跨いだ加算をしない）。row-exists kindのfixtureで検証（他kindでも同じ`streak`関数を再利用することはPROP-LV-035〜037内で追加確認） |
| PROP-LV-035（F1修正: bounty固有の`increment` kindケース） | REQ-LV-101 の `kind=="increment"`分岐 | 1 | true | `today_value=5,previous_value=3`（増分+2）→true；`today_value=5,previous_value=5`（増分0）→**false**（旧`fresh()`が誤判定していたのと同じ「行の存在だけでOKにする」欠陥がここで再現しないことの直接証明——checkedが増えていないpassでも当日`bounty-funnel.jsonl`行自体は存在するが、増分ゼロなら`cadence_met`はfalseを返す）；`today_value=3,previous_value=5`（減少、あり得ない前提だが防御的に）→false |
| PROP-LV-036（F1修正: founder-loop固有の`pass-marker` kindケース） | REQ-LV-101 の `kind=="pass-marker"`分岐 | 1 | true | `marker_jst_date`が当日と一致→true（`earn-ledger.jsonl`が空でもtrueになりうることを明示的に確認——ledger空≠cadence未達の直接証明）；前日のマーカー→false。統合テストでは実際に`~/.anicca-founder/state/STATE.md`のmtimeのみを読み、`earn-ledger.jsonl`を一切参照しないことをコード上で確認（grep相当） |
| PROP-LV-037（F1修正: pm-earner固有の`compound` kindケース、AND。G1修正: `hourly-pass`のboolはPROP-LV-040の`recency`分岐から導出されたものを使う——単なる不透明boolではない） | REQ-LV-101 の `kind=="compound"`分岐 | 1 | true | `hourly-pass=true, daily-redeem=true`→true；`hourly-pass=true, daily-redeem=false`→**false**（片方だけでは満たされない、ANDであることの直接証明）；`hourly-pass=false, daily-redeem=true`→false；両方false→false。ここで使う`hourly-pass`の`true`/`false`値はPROP-LV-040の`kind=="recency"`分岐の実出力（決め打ちのbool定数ではない）を用いる——compoundとrecencyの結合を実際にテストする |
| PROP-LV-040（**G1新設**: pm-earner `hourly-pass`固有の`recency` kindケース——iteration-2 blocking finding直接対応） | REQ-LV-101 の `kind=="recency"`分岐 | 1 | true | ★G1で指摘された正確なシナリオ★: `marker_epoch_seconds`=当日00:01のエポック秒、`now_epoch_seconds`=同日21:00のエポック秒（経過≈75540秒）、`max_age_min`=40（`healthcheck-runtime-loop.sh:97`と同じ値）→ **false**（「00:01に1回だけ動いてその後23時間59分停止していた日」を正しく`hourly-pass=false`と判定できることの直接証明、G1が指摘した「pass-markerでは`true`になっていた」誤判定が再発しないことの回帰テスト）。加えて: 経過1500秒（25分、`max_age_min*60=2400`秒未満）→true；経過2400秒ちょうど（境界）→true（`<=`なので境界含む）；経過2401秒→false |
| PROP-LV-023 | REQ-LV-110 (loop固有evaluatorの`combined_score`、LLM judge不使用) | 1 | true | 固定fixtureデータに対し`combined_score`が決定論的に同じ値を返すこと（同一入力→同一出力、2回実行して比較）；既存`evaluator.py`同様、評価対象コードが発注/投稿系モジュールを一切importしていないことをコードレビュー相当のgrepで確認（sandbox境界） |
| PROP-LV-024 | REQ-LV-111 (`beats_previous_week`) | 1 | true | `this=10,last=5`→true；`this=5,last=10`→false；`this=5,last=5`（同点）→false（tieはbeatにならない、既存`evaluatePromotion`のbaseline-floor思想と整合） |
| PROP-LV-025 | REQ-LV-112 (promote gate 2段ゲート) | 3 | true | pre-checkを意図的に失敗させたcandidateではadversary呼び出しが一切発生しないこと（呼び出しログで確認）、pre-check通過candidateではadversary呼び出しが発生しPASS/FAILいずれの場合も昇格判断がその結果と一致すること |
| PROP-LV-026（F2修正: clip-promoteの独立status判定を追加検証） | REQ-LV-120 (`loop-registry.json`書き出し) | 2 | true | `telemetry-collect.sh`実行後、`~/.anicca-founder/state/loop-registry.json`に8loop分のオブジェクトが存在し、7loop分の`status`がREQ-LV-101の`cadence_met`結果と一致すること、かつclip-promoteの`status`が`clip_promote_status`（payout ledgerの当日行有無、`cadence_met`は呼ばれていないこと）と一致することを確認 |
| PROP-LV-027 | REQ-LV-121 (landing直接write禁止) | 2 | true | この feature の全実装コミットに対し `git diff --stat` で `apps/landing/` 配下のファイルが1件も変更されていないことを確認 |
| PROP-LV-028 | REQ-LV-130 (`scale_eligible`3条件AND) | 1 | true | `streak=7,score>threshold,disk=5`→true；`streak=6`（1不足）→false；`disk=4.9`→false；3条件全て満たすが`score==threshold`（超過でなく同値）→false（`>`であって`>=`でない） |
| PROP-LV-029 | REQ-LV-132/133/134 (guardrail純関数群) | 1 | true | `cooldown_ok`: 直近spawnから設定日数未満→false；`fleet_at_capacity`: 現在数==上限→true、現在数<上限→false |
| PROP-LV-030 | REQ-LV-135 (`is_ban_suspected`) | 1 | true | `consecutive_failures < threshold`→false；`==threshold`→true；閾値到達で`loop-registry.json`のstatusが実際に`"paused"`へ更新されることを統合テストで確認 |
| PROP-LV-031 | REQ-LV-140 (cron棚卸し確定分類の件数一致) | 1 | true | 5分類の確定件数 30+23+7+24+19 を合計すると103になること（純粋な算術検算）；`~/.openclaw/cron/jobs.json`の実`enabled:true`件数（103、確認済み）と一致することを確認 |
| PROP-LV-032 | REQ-LV-145 (Dais明示go precondition) | 3 | true | OpenClaw削除コマンドを実行するpassのログに、Dais本人からの明示go指示（メッセージ本文またはタイムスタンプ参照）が記録されていること。この記録が無い状態でステップ⑤のコマンドが実行された形跡がないことを事後的にログで確認する（fail-closed: 記録が無ければ削除は実行されていないはず） |
| PROP-LV-033 | REQ-LV-142 (6前提条件の解消確認) | 2 | true | 前提条件1〜5それぞれについて対応する実ファイル/実装（`ai.openclaw.gateway.plist`の代替launchd plist存在、`cron-bash.sh`呼び出し箇所が置換済み、`loop-report.sh`への通知経路統一、`aniccaai-dashboard-refresh`のpush先変更）を実環境で確認。前提条件6は「UNVERIFIED」のまま残っていないこと（Phase 2着手時に確定情報がspecに追記されていること）を確認 |
| PROP-LV-034 | REQ-LV-143 (5ステップの順序遵守、並行スキップ禁止、Wave 1限定migrate) | 2 | true | ステップ②（Wave 2）着手前にステップ①（Wave 1）の成果物（(a-1)対象のうち検証ツールありチャネルのskillが実際に`~/anicca/skills`へ移設済み、検証ツール無しチャネルは移設されていないこと）が存在することを確認してから着手した記録が残っていること；ステップ③の7日間並走中、二重投稿の検知ログがあった場合は該当jobが実際にdisableされていることを確認 |
| PROP-LV-039（v2.2新設: REQ-LV-141移行gate） | REQ-LV-141 (`channel_migration_eligible`、検証ツール無しチャネルを除外) | 1 | true | `has_verification_tool=true`→移行対象に含まれる；`has_verification_tool=false`→移行対象から除外される。(a-1)の30件の記録のうち`has_verification_tool=false`の件数分だけWave 1実移行件数が30より少ないことを確認（30件全件が無条件移行されていないことの直接証明） |

## Verification tiers legend

- Tier 1: 純関数の単体テスト。決定論的フィクスチャ、実ネットワーク/実ブラウザ/実ファイル書き込みなし。
- Tier 2: 実ファイル読み書き・実プロセス起動（`yt-dlp`実行等）を伴う統合テスト。実SNS投稿・実送金は行わない。
- Tier 3: 実行環境上の real E2E（実mail送信・実launchd登録・実オンチェーン確認）。main agentが実行し、
  fresh-context adversary（`~/.claude/CLAUDE.md`モデル分業表: Opus 4.8）がログ/ledger/mailログを読んで
  判定する。dry run禁止（`~/.claude/CLAUDE.md` No dry run）。

## Gate

Phase 1c（spec review）は上記 REQ-LV-001〜146（v2.2改訂分含む）が (a) 存在しない symbol/path を
参照していないこと（Ground truth節の実ファイル確認と一致していること）、(b) 判断（何に応募するか・
何を改善するか・何がmistakeか・どのアカウントをscaleするか）がコード側でハードコードされていない
こと、(c) 各 REQ に Tier 1 or Tier 2 の具体的な verification method が付いていることの3点を
fresh-context adversary が確認し PASS/FAIL を出す。
REQ-LV-070（video warmup バグ）のみ、実装対象コードパスが Phase 1 時点で未特定であることを spec review
で明示し、Phase 2 着手時に spec を1行追記してから着手することを条件付き PASS の対象とする。
REQ-LV-041 は REQ-LV-100〜104 により SUPERSEDED（併記ではなく置換）— spec review はこの置換が
矛盾なく行われていること（旧 stale 判定ロジックが REQ-LV-040 の8 loop 分から完全に除去され、
7 loop分は REQ-LV-101 の5 kind分岐dispatcherへ、clip-promote分は REQ-LV-120 の`clip_promote_status()`
へ一本化されていること。F1修正: `cadence_met`が単一の「行の存在」判定から`kind`別4分岐へ一般化され、
G1修正でpm-earnerのhourly-pass専用に`recency`が追加され5分岐になったことも確認する）も確認する。
REQ-LV-140（cron棚卸し確定分類、30+23+7+24+19=103で件数一致
確認済み）はPhase 1時点で既に確定しておりPASSの対象。REQ-LV-141（v2.2新設の移行gate）は
Wave 1の30件それぞれの検証ツール有無判定がPhase 2実装時点で確定する性質のものであり、Phase 1時点では
判定結果そのものが存在しないため条件付きPASSの対象とする。REQ-LV-142の前提条件6
（`anicca-event-bot-trigger`のgog CLI依存）とREQ-LV-145（Dais明示go）も同様に、Phase 1時点では
それぞれ依存確認・go指示そのものが未確定であるため、REQ-LV-070と同様に条件付きPASSの対象とし、
Phase 2着手時（REQ-LV-141の30件判定・前提条件6）またはステップ⑤着手時（REQ-LV-145）に確定情報を
specへ追記する。
