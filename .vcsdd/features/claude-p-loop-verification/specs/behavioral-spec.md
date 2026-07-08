# Behavioral Spec — claude-p-loop-verification (Phase 1a, mode: lean)

## Context

design spec 正本: `docs/superpowers/specs/2026-07-08-claude-p-loop-verification-evidence-design.md`。
claude-p（human-funded Claude Code loops）の全 earn loop が、pass ごとに機械検証済み evidence を含む mail
報告を送り、自分の output を自分で検証し、metrics/lessons ledger で self-improve する状態にする。判断
（どの案件に応募するか・どう改善するか等）は agent の裁量、コード化するのは検証・記帳・mail 送信のみ
（`~/.claude/rules/building-effective-ai-agents.md` 準拠、regex による judgment のハードコード禁止）。

## Ground truth（実装確認済み、2026-07-08 時点）

- `~/anicca/skills/report/loop-report.sh` — 引数 `<loop_name> <did> <result> <earned_usdc> [evidence_url]`。
  `AGENTMAIL_API_KEY` unset なら stderr でなくログのみに `NO-OP` を書いて `exit 0`（呼び出し元を絶対に
  block しない）。`evidence_url` 省略時デフォルトは文字列 `"none"`。現状 evidence の中身に対する検証は
  一切ない（空文字も `"none"` 単独も無条件で送信される）。ログ: `~/.openclaw/logs/loop-report.log`。
  `~/.openclaw/.env` に `AGENTMAIL_API_KEY` は存在する（値は確認しない）が、このスクリプト自身はそれを
  source しない — 呼び出し元（tmux STARTUP prompt 等）が事前に `set -a; . ~/.openclaw/.env; set +a` して
  いる前提。
- `~/anicca/skills/earn/clip/self_heal.py` — `run_self_heal()` が IG reel を CDP 経由で実ページ読み確認し
  (`reel_verify.stabilize_reads` + `reel_verify.select_confirmed_href` のトークン照合)、確認できたら
  ledger に `{"status":"posted","post_url":"https://www.instagram.com"+href, ...}` を追記する。この検証
  機構は既存・完成済み（spec Goal 2 でいう「維持」対象）。
- `~/anicca/skills/earn/clip-promote/record-payout.mjs` — `recordPayout({sig, wallet, ledger, cost_usdc,
  task, wake})` が `~/anicca/skills/_shared/lib/solana-verify.mjs` の `sigStatus()`（on-chain confirm）と
  `usdcDeltaForSig()`（実際の USDC 増分 > 0）を確認し、`~/anicca/skills/_shared/lib/ledger.mjs` の
  `alreadyRecordedSig()` で sig 単位の重複排除をした上で `record()` に渡す。既存・完成済み（維持対象）。
- `~/anicca/skills/earn/video/metrics.py` — `read_reel_metrics(url, tid, port)` が CDP 経由で IG reel の
  実 views/likes/comments を読み、`~/.cloak/earn-video-metrics-<handle>.jsonl` に追記する。既存・完成済み
  （IG 側の維持対象）。TikTok 側の `yt-dlp --dump-json --skip-download <url>` 相当の検証は現状未実装。
- `~/anicca/skills/earn/video/record_earn.py` — `is_real_usdc_inflow(e)` がスキーマゲート（token==USDC,
  amount>0, direction==in, tx_hash 非空, verified==True）。`verify_onchain(entry)` は **常に `False` を
  返すハードコードされたスタブ**（コメント: "NOT wired yet"）— これが P0-4 の対象。`record_earn(entry,
  ledger_path, onchain_check=None)` は `onchain_check` を注入可能な引数として既に持っており（デフォルト
  `verify_onchain`）、テストは既にこのシームでスタブ注入している。producer（`~/.cloak/earn-video-inflows.jsonl`、
  ファイル自体は存在する）が `verified:true` を書く実装は未配線。
- `~/anicca/skills/earn/lib/evolve.mjs` — pm-trade の3層 self-improve パターン（`summarizeByGenome` →
  `evaluatePromotion` → `promote`）の実装。`DEFAULT_LEDGER_PATH`/`DEFAULT_TRACE_PATH` は
  `skills/earn/state/{earn-ledger,pm-trade.trace}.jsonl`。on-chain 確認済み（`tx` あり かつ
  `status==="0x1"`）行のみ集計する money-safety ゲート (`HARD 0.24`) は既存・完成済み。spec の「Self-improve
  拡張」はこの **パターン**（ledger→改善候補→gate→昇格）を clip/video/gig に copy+tweak するもので、
  evolve.mjs 自体を改変するものではない。
- `~/anicca/skills/self/verify-loops.sh` — `count()`/`fresh()`/`liveurl()` の3ヘルパーで capafy/reddit/
  life-manager の3 loop のみを検証している。clip/clip-promote/video/affiliate/gig/bounty/pm-earner/
  founder-loop は **一切カバーされていない**。
- `~/anicca/skills/self/verify-loops-audit.sh` — `verify-loops.sh` を実行し、stale な artifact を
  `self-fix.sh <name> "<blocker>"` へ escalate し、結果を `loop-report.sh audit ...` で mail する。6h ごと
  launchd 実行が前提（本 feature 外で既に配線済みと design spec は仮定）。
- `~/anicca/skills/self/healthcheck-runtime-loop.sh` — `hrl_classify()`（純関数、`DEAD_UNLOADED|DEAD_NO_PID|
  MISSING_ARTIFACT|STALE|OK` を返す）と `check()`（orchestrator、`launchctl list`/`self-fix.sh` を呼ぶ）が
  実装済み。a3cdd4/franklin/pm-earner/founder-proxy の4対象をカバー。ファイル自身のコメントに明記の通り
  **launchd に未配線**（"NOT wired into cron/launchd by this script — scheduling is a separate, reviewed
  step"）— P0-5 の対象。
- `~/anicca/skills/self/self-fix.sh` — `<loop-name> "<blocker+hint>"` の完全汎用インターフェース
  （`LOOP="${1:?loop name}"; LOOP="${LOOP%-loop}-loop"` で正規化）。既に healthcheck-runtime-loop.sh から
  a3cdd4/franklin/pm-earner/founder-proxy という非 tmux loop 名でも呼ばれており、新しい loop 名を追加する
  のに self-fix.sh 側の変更は不要。
- `~/anicca/skills/self/founder-loop/founder-loop.sh` — 1 wake ごとに `record-earn.mjs`（Base RPC で
  founder wallet `0x810f6d61f7606deee2657d3083e150a222bc29c5` への外部 USDC Transfer ログを確認、INV-1..7
  の anti-fake ゲート済み）を呼び、`~/.anicca-founder/state/STATE.md` を更新する。**`loop-report.sh` 呼び
  出しは一切ない** — P0-6 の対象。ledger: `~/.anicca-founder/state/earn-ledger.jsonl`（存在確認済み）。
- `~/anicca/skills/human-funded/gig/gig-cli.sh`・`~/profitable-claude/skills/human-funded/{affiliate,
  bounty}/*-cli.sh` — tmux 常駐 headless claude の STARTUP prompt が、cron 経由で日次/時次 pass を回し、
  各 pass の末尾で `loop-report.sh <loop> "<summary>" <result> <usdc> "<evidence or none>"` を **既に**
  呼んでいる（agent 自身が evidence 文字列を組み立てる = judgment は agent、送信のみが決定論ツール）。
  `~/gig/applied.jsonl`・`~/gig/earnings.jsonl`・`~/gig/lessons.jsonl`・`~/gig/shared-lessons.jsonl` は存在
  する。`~/profitable-claude/skills/human-funded/bounty/state/gated.json` は存在、`state/attempts.jsonl`
  は `run.sh EARN_MODE=attempt` が初めて書く時点で作られる（現状未作成）。affiliate 側の `state/`・
  `queue/`・`posted/` ディレクトリは存在するが affiliate 専用の metrics ledger は存在しない。

## In scope（この feature が触ってよい境界。design spec §開発環境と同一）

`~/anicca/skills/report/loop-report.sh`、`~/anicca/skills/earn/{clip,clip-promote,video}/`（および
`~/anicca/skills/earn/video/record_earn.py`）、`~/anicca/skills/self/{verify-loops.sh,
verify-loops-audit.sh,healthcheck-runtime-loop.sh,founder-loop/}`、`~/profitable-claude/skills/
human-funded/{gig,affiliate,bounty}/`。gig/affiliate/bounty の tmux STARTUP prompt 文字列自体
（`*-cli.sh` 内の `STARTUP=` 変数）も、evidence gate の新フォーマット（`none: <理由>`）に合わせて更新して
よい — これは prompt 文言の更新であり agent の判断ロジックを書き換えるものではない。

## Out of scope

`automaton`（body `~/.anicca`）・`Franklin`（body `~/.blockrun`）の body ファイルは一切触らない。
`autohedge`・`daily-nl-report`・tier1/tier2 共通基盤。`evolve.mjs` 自体の改変（pm-trade は copy 元として
参照するのみ、変更しない）。gig/affiliate/bounty の STARTUP prompt 内の **業務判断ロジック**（どの案件に
応募するか、どう improve するか）— これは常に agent 自身が pass 内で判断する。

## Requirements（EARS、全て MUST。「任意/推奨」は書かない）

### A. loop-report.sh — env 自己解決 + evidence gate（P0-1, P0-7）

- **REQ-LV-001**: WHEN `loop-report.sh` が起動し `AGENTMAIL_API_KEY` が unset の場合、THE SYSTEM SHALL
  `~/.openclaw/.env` が存在すれば `set -a; . ~/.openclaw/.env; set +a` 相当で自己解決を試みてから改めて
  `AGENTMAIL_API_KEY` の有無を判定する。自己解決後もなお unset の場合のみ、現行どおり
  `~/.openclaw/logs/loop-report.log` に `NO-OP (AGENTMAIL_API_KEY unset)` を記録して `exit 0` する
  （呼び出し元を絶対に block しない、既存の fail-closed 契約は変更しない）。
- **REQ-LV-002**: WHEN `AGENTMAIL_API_KEY` の自己解決に成功したが、その後の実際の送信（curl）が
  `HTTP_STATUS` 200/201 以外で失敗した場合、THE SYSTEM SHALL 従来どおりログへ `FAIL http=<code>` を記録
  する（無変更、退行禁止の確認のみ）。
- **REQ-LV-003（evidence gate、空/`none`単独の恒久防止）**: WHEN `loop-report.sh` が呼ばれ、第5引数
  `evidence_url` が (a) 空文字列、または (b) 前後空白を除去して大文字小文字を無視した上で厳密に文字列
  `"none"` のみ（コロン以降の理由が無い）である場合、THE SYSTEM SHALL mail 送信を行わずに
  `~/.openclaw/logs/loop-report.log` へ `REJECTED (empty-or-bare-none evidence)` を記録し、`exit 1` で
  終了する。`evidence_url` が `"none: <理由>"`（コロンの後に1文字以上の非空白理由が続く）の形、または
  `"none"` 以外の非空文字列である場合は REQ-LV-001/002 の通り通常どおり処理する。
- **REQ-LV-004**: WHERE `loop-report.sh` を呼び出す全ての loop 起動プロンプト
  （`~/anicca/skills/earn/clip-promote/clip-promote-cli.sh` を除く — clip-promote は既に別経路で
  evidence を扱う。対象は `~/profitable-claude/skills/human-funded/{gig,affiliate,bounty}/*-cli.sh` の
  `STARTUP` 文字列）が evidence_url に「投稿が無ければ文字列 `none`」という指示を含む箇所は、THE SYSTEM
  SHALL その指示を「投稿/応募/納品が無ければ `none: <具体的理由>`（例: `none: queue-empty this pass`）
  の形式で必ず理由を付けること」に更新する。判断（何が理由か）は agent が行う — 理由テキストの内容を
  コード側でハードコードしない。

### B. loop 別 検証アーキテクチャ（Goal 1・2、設計 spec §検証アーキテクチャ表 準拠）

- **REQ-LV-010（clip、維持）**: WHILE `~/anicca/skills/earn/clip/self_heal.py` の `run_self_heal()` が
  `status:"resolved"` を返す場合、THE SYSTEM SHALL 既存どおり ledger（`CLIP_LEDGER`、例
  `~/.openclaw/state/clip-earn-ledger.jsonl`）に `post_url` 付きの `status:"posted"` 行を追記し、
  呼び出し元の loop は同じ post_url を `loop-report.sh clip ... "<post_url>"` の evidence として渡す。
  この経路は改変しない（回帰テストのみ要求）。
- **REQ-LV-011（clip-promote、維持）**: WHILE `record-payout.mjs` の `recordPayout()` が `status:"recorded"`
  を返す場合、THE SYSTEM SHALL その `sig`（Solana tx signature）を呼び出し元 loop の
  `loop-report.sh clip-promote ...` evidence として渡す。この経路は改変しない（回帰テストのみ要求）。
- **REQ-LV-012（video: engagement 検証を TikTok にも拡張）**: WHEN video loop が TikTok へ投稿した URL を
  持つ場合、THE SYSTEM SHALL `yt-dlp --dump-json --skip-download <url>` を実行し、その JSON 出力から
  `view_count`（存在すれば `like_count` も）を抽出する新しい純関数（`parse_ytdlp_json(json_text) ->
  {view_count:int|None, like_count:int|None}`、malformed/欠損は `None`、絶対に値を捏造しない）を実装する。
  IG 側は既存 `metrics.py` の `read_reel_metrics()` を維持する。
- **REQ-LV-013（video: 抽出した engagement metrics の記録）**: WHEN REQ-LV-012 の抽出（TikTok）または既存
  `read_reel_metrics()`（IG）が `ok:true` 相当の結果を返した場合、THE SYSTEM SHALL その結果を既存
  `~/.cloak/earn-video-metrics-<handle>.jsonl` に（既存の追記フォーマットを維持したまま）追記する。
- **REQ-LV-014（affiliate: 存在確認 + metrics 記録、新設）**: WHEN affiliate loop が TikTok スライドショー
  URL を投稿した場合、THE SYSTEM SHALL `yt-dlp --dump-json --skip-download <url>` の**実行成功可否**
  （プロセスの exit code、HTTP 200 では判定不可 — design spec 実証済み）で存在確認を行い、成功時は
  REQ-LV-012 と同じ `parse_ytdlp_json` を再利用して views を抽出し、新設ファイル
  `~/.cloak/affiliate-metrics.jsonl` に `{ts, slideshow_url, views, commission_jpy, ok}` 形式で1行追記
  する。既存の `commission-watermark.json` は変更しない（読むだけ）。
- **REQ-LV-015（gig: funnel 検証、新設）**: WHEN gig loop が1 pass を終える場合、THE SYSTEM SHALL
  `~/gig/applied.jsonl` の当該 pass 分の行から `status` の集計（`applied`→`replied`→`受注/成約`→
  `検収完了/支払`）を行う純関数 `summarize_gig_funnel(applied_rows) -> {applied:int, replied:int, won:int,
  paid:int}` を実装し、新設ファイル `~/gig/gig-funnel.jsonl` に `{ts, pass_id, applied, replied, won,
  paid}` を1行追記する。この関数は CloakBrowser の実読み取り結果（`applied.jsonl`）のみを入力とし、
  ブラウザ状態そのものへの新規アクセスを増やさない。
- **REQ-LV-016（bounty: funnel 検証、新設）**: WHEN bounty loop が1 pass（discover/gate/attempt/track の
  いずれか）を終える場合、THE SYSTEM SHALL `~/profitable-claude/skills/human-funded/bounty/state/
  gated.json`（survivors 件数）と `state/attempts.jsonl`（`status:claim`/`pr`非null/`stalled` の件数）
  から純関数 `summarize_bounty_funnel(gated, attempts_rows) -> {checked:int, survivors:int, claimed:int,
  submitted:int, stalled:int}` を実装し、新設ファイル `~/profitable-claude/skills/human-funded/bounty/
  state/bounty-funnel.jsonl` に `{ts, pass_id, checked, survivors, claimed, submitted, stalled}` を1行
  追記する。
- **REQ-LV-017（pm-earner、維持 + 明示的検証手段の追加）**: WHERE claude-p の pm-earner loop（wallet は
  `~/anicca/skills/earn/polymarket-trade/redeem.py` が使う deposit wallet）が redeem 済み残高を報告する
  場合、THE SYSTEM SHALL `https://data-api.polymarket.com/positions?user=<wallet>`（無認証 GET）への実
  呼び出し結果と、`redeem.py` が既に行っている on-chain 確認（`hex(receipt.status)=="0x1"`）の両方を
  evidence の根拠として扱う。この2つの確認経路自体は改変しない（design spec: 「維持」）。新規に書く純
  関数は `positions API` の JSON をパースして `{market, size, redeemable}` の配列へ正規化する
  `parse_positions_response(json_text) -> list[dict]` のみとし、判断（どのポジションを redeem するか）
  は変更しない。
- **REQ-LV-018（founder-loop、維持 + mail 配線、P0-6）**: WHEN `founder-loop.sh` が1 wake を完了し STATE.md
  を書き終えた場合、THE SYSTEM SHALL その wake の `realised_earn_usdc` と `prev_realised_earn_usdc` の差分
  が正であれば `result=success`・そうでなければ `result=queue-empty` として、
  `bash ~/anicca/skills/report/loop-report.sh founder "<one-line summary using STATUS>" <result>
  <realised_earn_usdc の当wake分の増分、無ければ0> "<evidence: 差分が正なら increase 額 + wallet
  0x810f6d61f7606deee2657d3083e150a222bc29c5、そうでなければ 'none: <STATUS の内容>'>"` を呼び出す。
  この呼び出しは `record-earn.mjs`（ledger 唯一の書き手、INV-H2）を一切変更しない — mail 送信は
  `founder-loop.sh` 内の追加ステップとしてのみ配線する。

### C. metrics ledger → self-improve 展開（Goal 3、pm-trade パターンの copy+tweak）

- **REQ-LV-020**: WHERE clip/video/gig の各 loop 起動プロンプト（`clip-cli.sh`・`video`系 cron prompt・
  `gig-cli.sh` の `STARTUP`）が1 pass を開始する場合、THE SYSTEM SHALL pass 冒頭で自身の metrics ledger
  （clip: `CLIP_LEDGER`、video: `~/.cloak/earn-video-metrics-<handle>.jsonl`、gig:
  `~/gig/gig-funnel.jsonl` + `~/gig/earnings.jsonl`）と、対応する lessons ledger（下記 REQ-LV-030）を
  読んでから今回 pass の行動を選ぶ、という一文をプロンプトに含める。この判断ロジック自体は agent が行う
  — どの改善を選ぶかをコード側で分岐させない。
- **REQ-LV-021**: WHERE 上記いずれかの loop が pass 末尾に到達した場合、THE SYSTEM SHALL 「前回より良い
  選択をする」の評価材料として、直近と1つ前の metrics ledger 行を週次比較できる形（同一 loop の ledger
  ファイルに `ts` フィールドを持つ行が既に存在する — REQ-LV-013/015/016 で保証）で記録済みであることを
  検証テストで確認する（新規の比較ロジックは実装しない。比較そのものは agent が pass 内で行う）。

### D. lessons ledger（Goal 4）

- **REQ-LV-030（gig、既存確認のみ）**: THE SYSTEM SHALL `~/gig/lessons.jsonl`（既存、gig-cli.sh STARTUP
  の B3 で書かれる）をこの feature の対象外として変更しない — 既に spec の意図（失敗を次 pass の判断に
  読み込む）を満たしている。
- **REQ-LV-031（clip/video/bounty/affiliate、新設）**: WHERE clip/video/bounty/affiliate のいずれかの
  loop 起動プロンプトが、その pass で「意図通りに行かなかったこと」（例: 投稿失敗、応募却下、TikTok API
  失敗）を認識した場合、THE SYSTEM SHALL その loop 専用の lessons ledger（clip:
  `~/.cloak/clip-lessons.jsonl`、video: `~/.cloak/video-lessons-<handle>.jsonl`、bounty:
  `~/profitable-claude/skills/human-funded/bounty/state/lessons.jsonl`、affiliate:
  `~/profitable-claude/skills/human-funded/affiliate/state/lessons.jsonl`）に1行
  `{ts, pass_id, mistake, lesson}` を追記する一文を STARTUP プロンプトに含める。どの出来事が
  "mistake" かの判断は agent が行う。

### E. verify-loops-audit 全 loop カバー + escalation（Goal 5）

- **REQ-LV-040**: THE SYSTEM SHALL `~/anicca/skills/self/verify-loops.sh` に、既存の capafy/reddit/
  life-manager の3ブロックに加えて、以下8 loop 分の `count()`/`fresh()`/`liveurl()`（該当する場合）
  ブロックを追加する（既存3ブロックのフォーマット・関数を再利用し、新しいヘルパー関数は作らない）:
  clip=`CLIP_LEDGER`、clip-promote=`clip-promote` の ledger、video=
  `~/.cloak/earn-video-metrics-<handle>.jsonl`、affiliate=`~/.cloak/affiliate-metrics.jsonl`
  （REQ-LV-014）、gig=`~/gig/gig-funnel.jsonl`（REQ-LV-015）、bounty=
  `~/profitable-claude/skills/human-funded/bounty/state/bounty-funnel.jsonl`（REQ-LV-016）、
  pm-earner=`~/anicca/skills/earn/state/earn-ledger.jsonl`、founder-loop=
  `~/.anicca-founder/state/earn-ledger.jsonl`。
- **REQ-LV-041**: WHEN REQ-LV-040 で追加した8 loop のいずれかの artifact が stale と判定された場合
  （既存 `verify-loops-audit.sh` の stale 判定パターン、`stale_hrs()` 相当のしきい値をその loop の実際の
  pass 頻度 — clip/video/gig=時間単位、affiliate/bounty=日次、pm-earner/founder-loop=分単位 — に合わせて
  設定）、THE SYSTEM SHALL 既存の `self-fix.sh <loop-name> "<blocker>"` 呼び出しパターンを再利用して
  escalate する（`self-fix.sh` 自体は既に汎用インターフェースであり変更不要 — Ground truth 参照）。
- **REQ-LV-042**: WHEN `verify-loops-audit.sh` が6hごとの scorecard を送る場合、THE SYSTEM SHALL
  REQ-LV-040 で追加した8 loop 分の状態も既存の `loop-report.sh audit ...` 呼び出しの本文に含める
  （既存の capafy/reddit/lm 部分の出力形式は変更しない、追記のみ）。

### F. healthcheck-runtime-loop.sh の launchd 配線（P0-5）

- **REQ-LV-050**: THE SYSTEM SHALL `~/anicca/skills/self/healthcheck-runtime-loop.sh` を起動する launchd
  plist を新規作成し（既存の他 loop の healthcheck plist と同じ `~/Library/LaunchAgents/` 配置・命名慣習
  に倣う）、`launchctl load` する。実行間隔は既存スクリプトの各対象のしきい値（a3cdd4=20分、
  franklin=90分、pm-earner=40分、founder-proxy=120分）のうち最小値（20分）以下の周期とする。
- **REQ-LV-051**: WHEN REQ-LV-050 の plist がロードされた場合、THE SYSTEM SHALL `launchctl list | grep
  <label>` でジョブが `launchctl list` に現れることを確認できる状態にする（`healthcheck-runtime-loop.sh`
  自体のロジック変更は行わない）。

### G. 残りの P0 修正

- **REQ-LV-060（P0-2、disk 回収）**: THE SYSTEM SHALL 承認済み範囲（`~/.cache/anicca-*` の回収、ログ
  rotate）のみを対象に disk 使用量を削減する。`~/.cache/claudevm`・`~/.cache/colima` 等、Dais 承認待ちの
  大物ディレクトリには一切触れない。
- **REQ-LV-070（P0-3、video warmup 停滞バグ）**: THE SYSTEM SHALL video loop の warmup 進行条件
  （day 3→4 で停滞していた実装箇所）を実際にログ/コードを読んで特定し、根本原因を修正した上で、修正後に
  warmup が day 4 以降へ進行することを実ログで確認する。この修正の対象コードパスはこの Phase では未確定
  — Phase 2（実装）着手時に該当ファイルを grep/Read で特定し、spec に反映してから着手する（存在しない
  symbol を仮定しない）。
- **REQ-LV-080（P0-4、record_earn.py on-chain フック配線）**: THE SYSTEM SHALL
  `~/anicca/skills/earn/video/record_earn.py` の `verify_onchain(entry)` を、常時 `False` を返すスタブ
  から、`~/anicca/skills/self/founder-loop/record-earn.mjs` と同じ検証パターン（Base RPC で該当
  `tx_hash` の USDC Transfer ログを確認し、`to` が earner の実 wallet と一致し `value` が `amount` と
  一致することを確認する）を Python で実装したものに置き換える。`record_earn(entry, ledger_path,
  onchain_check=None)` の既存シーム（`onchain_check` 注入可能）は変更しない — デフォルト値を新しい実装に
  差し替えるだけで、テストは引き続きスタブ注入で行える。

## Non-functional constraints

- No dry run（`~/.claude/CLAUDE.md`）: Phase 3 以降の E2E evidence は実際の mail 送信・実際の投稿/応募・
  実際のオンチェーン確認でなければならない。
- 判断のハードコード禁止: どの案件に応募するか、どの改善を採用するか、mistake が何かの判定は全て agent
  自身が行う。この spec がコード化するのは「検証」「記帳」「mail 送信」の3つの決定論ツールのみ
  （`~/.claude/rules/building-effective-ai-agents.md` 準拠）。
- 既存の fail-closed 契約（`loop-report.sh` は credential 欠如時に呼び出し元を絶対に block しない、
  `record_earn.py`/`record-earn.mjs` は on-chain 未確認なら絶対に記帳しない）は一切弱めない。
