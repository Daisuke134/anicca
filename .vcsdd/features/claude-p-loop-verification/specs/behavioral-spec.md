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
- `~/profitable-claude/skills/human-funded/gig/gig-cli.sh`・`~/profitable-claude/skills/human-funded/
  {affiliate,bounty}/*-cli.sh`（F4修正: `~/anicca/skills/human-funded/gig/`は実在しない——実在するのは
  `~/profitable-claude/skills/human-funded/gig/`のみ、`ls`で確認済み。In scope節・REQ-LV-004は元々
  正しいパスで記載していた）— tmux 常駐 headless claude の STARTUP prompt が、cron 経由で日次/時次 pass を回し、
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
- **REQ-LV-019（Goal 6: E2E完了判定 + fresh-context adversary PASS、F5修正: 独立REQとして採番。
  「任意」ではなくMUST）**: THE SYSTEM SHALL REQ-LV-100が対象とする7 loop（clip/affiliate/video/gig/
  bounty/pm-earner/founder-loop）+ clip-promote の計8 loopそれぞれについて、「実行→投稿/応募→検証→
  mail（evidence入り）」の1サイクルをfresh evidence（実行中に新規発生したURL/tx/数値、過去の実行結果の
  再利用は不可）付きで完了させる。THE SYSTEM SHALL その完了の証跡（evidence mail のログ行
  `~/.openclaw/logs/loop-report.log`の`SENT`行、対応するledger/metrics ledgerの新規行）をfresh-context
  adversary（`~/.claude/CLAUDE.md`モデル分業表: Opus 4.8）に提示し、PASS判定を得る。8 loopのうち
  1つでもこのサイクルが未確認、またはadversaryがPASSを出していない場合、このfeatureはGoal 6未達成
  として扱う（MUST、optionalな検証手段ではない）。

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
- **REQ-LV-041（SUPERSEDED by REQ-LV-100〜104 — v2改訂、Dais 2026-07-08指示）**: ~~WHEN REQ-LV-040 で
  追加した8 loop のいずれかの artifact が stale と判定された場合（`stale_hrs()` 相当の時間ベースしきい値
  で判定）、escalate する~~。「artifact が古い（stale）か」という時間経過ベースの health 判定は、
  「今日、契約した頻度で成果が出たか」という **Cadence Contract**（§H、REQ-LV-100〜104）に完全に置き換
  わる。この行は削除せず、なぜ旧要件が無効化されたかの記録としてのみ残す。escalation の呼び出し先
  （`self-fix.sh <loop-name> "<blocker>"`）自体は変更しない — REQ-LV-102 が新しい判定条件で同じ
  escalation 経路を呼ぶ。
- **REQ-LV-042（v2改訂: cadence 状態を含める形に更新）**: WHEN `verify-loops-audit.sh` が6hごとの
  scorecard を送る場合、THE SYSTEM SHALL REQ-LV-040 で追加した8 loop 分の状態を、旧来の stale/fresh 表記
  ではなく REQ-LV-103 の日次 scorecard 形式（`✅posted-today` / `❌missed` + streak）で
  `loop-report.sh audit ...` 呼び出しの本文に含める（既存の capafy/reddit/lm 部分の出力形式は変更しない、
  8 loop 分の追記のみを cadence 形式にする）。

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

## v2 追加要件（Dais 5点指示、2026-07-08 改訂。design spec正本 commit `ae2b8eecd` 反映）

新規に確認したground truth: `~/anicca/skills/self/healthcheck-lib.sh:40`（`HC_OUTPUT_STALE_HRS`、
デフォルト30h、capafy/reddit/life-manager系tmux loopの既存artifact-staleness判定）、
`~/anicca/skills/earn/self-improve/evaluator.py`（`evaluate_stage1()`/`evaluate_stage2()`が
`combined_score`を返す。`scope_guard.check()`をstage1の前に必ず実行、`gate_math.risk_adjusted_score()`
でリスク調整、`FAIL_SENTINEL=0.0`、LLM judgeを一切使わない=Verifier's Law準拠、ledgerへの書き込み・
発注モジュールのimportを一切行わないsandbox境界）、`~/anicca/skills/earn/self-improve/promote_gate.sh`
（`lib/promote_gate_run.py`へのthin wrapper。決定論的pre-check（`lib/promote_gate.py`: scope_guard/
stage1/stage2/trip-wire）を通過した候補にのみ、`self-fix.sh`と同型の実`claude --model opus
--dangerously-skip-permissions --print`同期呼び出しで最終adversary判定を行う。使い方:
`promote_gate.sh <candidate_program_path> <run_dir> [--dry-run]`）、
`~/anicca/skills/self/telemetry-collect.sh`（instance毎=a3cdd4/franklin/claude-pに1つずつ、
自分のbody配下にのみ`state/telemetry.json`を書く。read-onlyなpublic RPC/API読み取りのみ。launchd未配線
=別途レビューされたステップという既存の断り書きあり）、`~/anicca/skills/earn/clip/_instance_paths.sh`
（`ANICCA_INSTANCE`環境変数と`_SFX`サフィックスパターン。CLIP_QUEUE/CLIP_POSTED/CLIP_ACCTS/CLIP_LEDGER/
CLIP_PENDING_VERIFYの5パスがこのパターンに従う）、`/Users/anicca/anicca-project/apps/landing/public/
dashboard.json`（既存トップレベルキー: `updated_at, mrr, followers, views, spend, profit_usd, goals,
basic_income, socials, meta, lifeline_status, cfo_source, lineage, leaderboard,
total_net_worth_usd, alive, self_funded_pct, frontier_pct` — `loops`キーはまだ存在しない）、
`~/.openclaw/cron/jobs.json`（実件数確認: 全221件、うち`enabled:true`は103件 — design spec記載の
「enabled 103 jobs」と一致確認済み）。

### H. Cadence Contract（health の bar を artifact 存在 → 日次 cadence へ置換）

design spec §Cadence Contract表（`docs/superpowers/specs/2026-07-08-...-design.md:56-72`）は、7 loop
（clip/affiliate/video/gig/bounty/pm-earner/founder-loop — clip-promoteは投稿頻度がcampaign依存のため
Cadence Contract対象外・REQ-LV-120で別途status定義する）の判定基準が単一ではないことを明示している:
clip/affiliate/video/gig=「当日 ledger 行の存在」、bounty=「`gated.json`の`checked`**増分**（行の存在では
なく前日比の差分）」、founder-loop=「**STATE.mdのmtime**（`~/.anicca-founder/state/earn-ledger.jsonl`
への追記は`record-earn.mjs`のINV-1〜7ゲートを通過した実際の外部入金があった時のみ発生し、稼ぎゼロの日
でもpassは正常実行される — Ground truth §founder-loop.sh参照。ゆえに **ledgerが空 = cadence未達では
ない**、passが動いたことをSTATE.mdのmtimeで別途判定する）」、pm-earner=「**複合契約**（1 pass/時 AND
redeem確認/日 の2条件AND）」。以下の REQ-LV-100/101 はこの判定基準を1つの汎用スキーマ/関数で機械的に
区別できるよう設計する（F1修正: v2で単一の「行の存在」判定に固定していたのを是正）。

★ G1修正（iteration-2 spec review blocking）: pm-earnerのcompound内`hourly-pass`サブ条件を当初
`kind:"pass-marker"`（JST暦日イコール判定）で表現していたが、これは「その日のうち一度でも動いたか」
という**日単位**の粒度しか判定できず、「00:01に1回だけ`earner.log`が更新され、その後23時間59分
pm-earner loopが完全停止していた」ケースでも`true`を返してしまう——design spec が要求する
`cadence:"1/hour"`（**1時間ごとに動いているか**という時間単位の粒度）を実際には一切検証できない。
これはF1が指摘した「artifactが存在するだけで健全と誤判定する」欠陥クラスを、修正後の`compound`/
`pass-marker`の組み合わせを通じて再導入するものだった。修正: `~/anicca/skills/self/
healthcheck-runtime-loop.sh:97`（`check "claude-p-pm" "ai.anicca.pm-earner" interval
"$HERE/../earn/polymarket-trade/earner.log" 40`——pm-earnerの**同じ`earner.log`**に対し、既に
40分のrecency閾値でstaleness判定している実装が存在する）をcopy+tweakした新kind`"recency"`を追加し、
`hourly-pass`条件のみこちらを使う設計に変更した（下記REQ-LV-100/101参照）。**判定基準は5種**になる。

- **REQ-LV-100（cadence contract宣言、`kind`判別子で5種を区別。G1修正: hourly-pass専用に`recency`を追加）**:
  THE SYSTEM SHALL 7 loop（clip/affiliate/video/gig/bounty/pm-earner/founder-loop）それぞれについて、
  design spec §Cadence Contract表の契約を、`kind`フィールドで判定方式を明示した機械可読スキーマとして
  各loopのhealthcheck設定（新設または既存スクリプトへの追記、loop毎に1箇所）に宣言する:
  - `kind:"row-exists"`（clip/affiliate/video/gig）: `{"kind":"row-exists","cadence":"1/day","unit":"reel","boundary_tz":"Asia/Tokyo"}`
  - `kind:"increment"`（bounty）: `{"kind":"increment","field":"checked","source":"gated.json（bounty-funnel.jsonlのpass毎の値から前日比を算出）","boundary_tz":"Asia/Tokyo"}`
  - `kind:"pass-marker"`（founder-loop）: `{"kind":"pass-marker","source":"~/.anicca-founder/state/STATE.md mtime","boundary_tz":"Asia/Tokyo"}`（`earn-ledger.jsonl`は参照しない — ledgerは収益metric専用でcadence判定から分離する）
  - `kind:"recency"`（**G1新設**、時間単位の経過チェック。JST暦日境界に依存しない——`boundary_tz`フィールドを持たない）:
    `{"kind":"recency","source":"<path or description>","max_age_min":<int>}`。
  - `kind:"compound"`（pm-earner、**G1修正**: `hourly-pass`サブ条件は`pass-marker`ではなく`recency`を使う）:
    `{"kind":"compound","conditions":[{"id":"hourly-pass","kind":"recency","cadence":"1/hour","source":"earner.log mtime","max_age_min":40},{"id":"daily-redeem","kind":"row-exists","cadence":"1/day","unit":"redeem","boundary_tz":"Asia/Tokyo"}]}`
    （`max_age_min:40`は`healthcheck-runtime-loop.sh:97`が同じ`earner.log`に対して既に使っている
    staleness閾値をそのまま流用——新規の値を発明しない、copy+tweak）。
- **REQ-LV-101（純判定関数、5種のkindを分岐する単一dispatcher、JST日境界。G1修正: `recency`分岐を追加）**:
  THE SYSTEM SHALL `cadence_met(today_jst_date, contract, evidence) -> bool`（新設・純粋、I/Oなし。
  `evidence`の実データ収集は呼び出し元の責務——このシグネチャはF1修正の核心: 単一の「ledger行の存在」
  判定から、`contract["kind"]`で分岐する5方式へ一般化する）を実装する。分岐仕様:
  - `kind=="row-exists"`: `evidence={"event_dates":[...]}`（呼び出し元がledgerの行タイムスタンプから
    抽出したJST暦日文字列のリスト）。`today_jst_date in evidence["event_dates"]`を返す。
  - `kind=="increment"`: `evidence={"today_value":int,"previous_value":int}`（呼び出し元が
    `contract["source"]`から当日の最新値と直近の前暦日の値を読む——bountyは`bounty-funnel.jsonl`の
    pass毎`checked`値のうち当日分の最新行とその前暦日の最終行を使う）。
    `evidence["today_value"] > evidence["previous_value"]`を返す（単なる行の存在ではなく**差分>0**の
    明示チェック——旧`fresh()`が持っていた「artifact存在だけで健全と誤判定する」欠陥をここで再導入
    しないための直接的な修正）。
  - `kind=="pass-marker"`: `evidence={"marker_jst_date":str}`（呼び出し元が`contract["source"]`ファイル
    のmtimeをJST暦日文字列に変換した値——founder-loopなら`STATE.md`のmtime。ledgerのtsは使わない）。
    `today_jst_date == evidence["marker_jst_date"]`を返す。**日単位の粒度のみ判定可能**——時間単位の
    cadenceには`recency`（下記）を使う。
  - `kind=="recency"`（**G1新設**）: `evidence={"marker_epoch_seconds":int,"now_epoch_seconds":int}`
    （呼び出し元が`contract["source"]`ファイルのmtimeと現在時刻を、それぞれUNIXエポック秒として渡す
    ——`~/anicca/skills/self/healthcheck-runtime-loop.sh`の`artifact_age_min()`（`(now - mtime)/60`）
    と同じ計算をエポック秒レベルで行う）。`(evidence["now_epoch_seconds"] - evidence["marker_epoch_seconds"])
    <= contract["max_age_min"] * 60`を返す——JST暦日境界を一切参照しない、純粋な経過時間チェック。
    「00:01に1回だけ動いてその後23時間59分停止」のケースは、21:00 JST時点で経過時間が`max_age_min`
    （40分）を大幅に超えるため確実に`false`になる。
  - `kind=="compound"`: `evidence={"by_condition":{<condition id>: <そのconditionのkindに応じたevidence>}}`。
    `contract["conditions"]`内の**全ての**sub-contractについて`cadence_met(today_jst_date, condition,
    evidence["by_condition"][condition["id"]])`を再帰的に呼び、**全てtrueの場合のみ**true（論理AND、
    ORでも多数決でもない）を返す——pm-earnerの「1 pass/時（`recency`） AND redeem確認/日（`row-exists`）」
    を機械的に表現する。
- **REQ-LV-102（21:00 JST 締切 + escalation、REQ-LV-041 を置換）**: WHEN JST 21:00 の時点で
  `cadence_met()`（REQ-LV-101、loopのcontract kindに応じた分岐で判定）が当日分について `false` を返す
  loop が存在する場合、THE SYSTEM SHALL 既存の `self-fix.sh <loop-name> "<blocker>"` 呼び出し
  （変更しない、Ground truth参照）を、「7日前に投稿があった」等の過去実績を理由に抑制することなく
  毎日 escalate する。
- **REQ-LV-103（streak KPI + 日次 scorecard、5種のkindに対応）**: THE SYSTEM SHALL 各 loop の連続達成
  日数を計算する純関数 `streak(evidence_by_date, today_jst_date, contract) -> int`（新設・純粋:
  `evidence_by_date`は日付文字列→その日の`cadence_met`用evidenceのdict。当日から遡って各日の
  `cadence_met(date, contract, evidence_by_date[date])`が真である連続日数を数える。kindに関わらず
  同じ再帰ロジックで動作する——`cadence_met`自体がkindを分岐するため`streak`側の分岐は不要）を実装し、
  `verify-loops-audit.sh`の6hごとscorecard（REQ-LV-042、置換後）に loop ごと `✅posted-today (streak=N)`
  / `❌missed (streak=0)` の形式で含める。
- **REQ-LV-104（G1修正: pm-earnerのhourly-pass分のevidence収集方法を明示）**: THE SYSTEM SHALL
  `verify-loops.sh`/`verify-loops-audit.sh`（REQ-LV-040〜042）の判定ロジックを、旧来の `fresh()`
  （26h/30h等の固定しきい値によるartifact年齢判定）呼び出しから、Cadence Contract対象7 loop分は
  REQ-LV-101/102/103 の cadence 判定（loopのcontract kindに応じて `event_dates`/
  `today_value・previous_value`/`marker_jst_date`/`marker_epoch_seconds・now_epoch_seconds`/
  `by_condition`のいずれかのevidenceを実際に収集して`cadence_met`へ渡す）へ、clip-promote分は
  REQ-LV-120の`clip_promote_status()`（payout ledgerの当日行有無）へ、それぞれ完全に置き換える。
  **pm-earnerのcompound契約は2種類のevidence収集を組み合わせる**——`hourly-pass`サブ条件
  （`kind:"recency"`）は`~/anicca/skills/earn/polymarket-trade/earner.log`のmtimeと現在時刻を
  それぞれエポック秒として収集し（`healthcheck-runtime-loop.sh`の`artifact_age_min()`と同じ
  ファイルを参照する）、`daily-redeem`サブ条件（`kind:"row-exists"`）は既存 pm-earner ledger
  （`~/anicca/skills/earn/state/earn-ledger.jsonl`）のredeem行タイムスタンプからJST暦日文字列を
  収集する——2つの異なる収集方法の結果を`{"by_condition":{"hourly-pass":{...}, "daily-redeem":{...}}}`
  にまとめて`cadence_met`へ渡す。旧 `fresh()` 呼び出しは capafy/reddit/life-manager の既存3ブロック
  （この feature の対象外）でのみ残す — REQ-LV-040が追加した8 loop分のブロックからは`fresh()`を
  完全に除去する（clip-promoteも例外にしない）。

### I. EDD（Evaluation-Driven Development）

- **REQ-LV-110（evaluator、loop毎、決定論・LLM judge禁止）**: THE SYSTEM SHALL clip/affiliate/video/
  gig/bounty の各 loop について、`~/anicca/skills/earn/self-improve/evaluator.py`の
  `evaluate_stage1/evaluate_stage2`パターン（fixture/ledgerを読み取り専用で読み、`combined_score`
  という1つのスカラーを返す。LLM judgeを一切使わない = Verifier's Law準拠。ledgerへの書き込み・
  実行系モジュールのimportを一切行わない sandbox 境界を維持する）を copy+tweak した loop 固有の
  evaluator（新設、`~/anicca/skills/self/self-improve/<loop>/evaluator.py`）を実装する。design spec
  §EDD表の evaluation metric を各 loop の `combined_score` の定義とする（例: clip=`views/reel(48h窓)
  + follower増分 + payout USDC`、gig=`funnel: 応募→返信率→受注率→入金JPY/週`）。
- **REQ-LV-111（週次比較、machine-checkable）**: THE SYSTEM SHALL 各 loop の evaluator を週次で実行し、
  今週の`combined_score`が先週の`combined_score`を上回るかどうかを純関数
  `beats_previous_week(this_week_score, last_week_score) -> bool`（新設・純粋）で判定する。この判定結果
  を loop の metrics ledger（REQ-LV-013/014/015/016/017で新設・維持したもの）に
  `{ts, week_start, combined_score, beats_previous_week}` として追記する。
- **REQ-LV-112（promote gate、pm-tradeパターンをcopy+tweak）**: WHEN loopの改善候補（prompt/戦略
  ファイルの変更案）が生成された場合、THE SYSTEM SHALL `~/anicca/skills/earn/self-improve/
  promote_gate.sh`と同型の2段ゲート（① `lib/promote_gate.py`相当の決定論pre-check、② pre-checkを
  通過した候補にのみ実行する同期`claude --model opus --dangerously-skip-permissions --print`による
  fresh adversary判定）を経てのみ、その改善候補を昇格（実際のprompt/戦略ファイルへ反映）する。
  pre-checkを通過しない、またはadversaryがPASSを出さない候補は昇格しない（`~/.claude/CLAUDE.md`の
  adversaryモデル分業表: Opus 4.8 準拠）。
- **REQ-LV-113（lessons ledger との接続）**: THE SYSTEM SHALL 各 loop の起動プロンプトに、pass 冒頭で
  自身の metrics ledger と lessons ledger（REQ-LV-020/021/030/031 で既に規定済み）に加え、直近の
  evaluator 実行結果（`combined_score`とREQ-LV-111の`beats_previous_week`）も読んでから今回 pass の
  改善判断を行う、という一文を追加する。改善候補そのものの内容判断は agent が行う — evaluator/gateは
  決定論ツールとしてのみコード化する。

### J. Dashboard（aniccaai.com 連携、既存 write 制限を維持）

- **REQ-LV-120（loop-registry.json、新設、claude-p自身のbody配下にのみ書く。F2修正: clip-promoteの
  status定義を明示）**: THE SYSTEM SHALL `~/anicca/skills/self/telemetry-collect.sh`を拡張し
  （既存のper-instance telemetry.json書き込みロジックには手を入れない、新しい出力を追加するのみ）、
  claude-pのbody配下（`~/.anicca-founder/state/loop-registry.json`）に、8 loop 分
  （REQ-LV-100のCadence Contract対象7loop + clip-promote）の
  `{loop, type, account, status, streak, artifact_url_today, weekly_metric, cumulative_earn_usdc,
  model}`配列を書き出す。`status`の算出方法は2系統に分かれる:
  - Cadence Contract対象7loop（clip/affiliate/video/gig/bounty/pm-earner/founder-loop）:
    `status`はREQ-LV-101の`cadence_met()`結果（`"posted-today"`/`"missed"`）、`streak`はREQ-LV-103の値。
  - **clip-promote（Cadence Contract対象外、REQ-LV-100参照）**: `status`は独立の判定基準を使う——
    `record-payout.mjs`の`recordPayout()`が`status:"recorded"`を返した行（Ground truth §REQ-LV-011
    参照、`task`が`"promote.fun clip payout"`のペイアウトledger行）が当日JST日付に存在すれば
    `"payout-today"`、無ければ`"no-payout-today"`とする（`cadence_met()`は呼ばない——campaign依存の
    投稿頻度にはcadence契約が定義されていないため）。`streak`は同じ判定基準（payout-today）を日毎に
    遡って連続日数を数える（REQ-LV-103の`streak()`と同じ再帰ロジックだが、evidenceの元がpayout ledger
    である点のみ異なる）。
  `weekly_metric`はREQ-LV-110の`combined_score`をそのまま使う（新規の計算ロジックを重複実装しない、
  clip-promoteはこのfeatureのEDD対象外——REQ-LV-110参照——のため`weekly_metric`は既存ledgerの週次
  payout合計とする）。
- **REQ-LV-121（landingへの直接write禁止、既存制約の維持）**: THE SYSTEM SHALL
  `loop-registry.json`を`~/anicca-project/apps/landing/**`または`apps/landing/public/dashboard.json`
  へ一切直接書き込まない（プロジェクトCLAUDE.md「aniccaai.comへの書き込み制限」表: claude-pは自分の
  body file を書くのみ、dashboard-syncがpull・renderする既存契約を維持）。`apps/landing/public/
  dashboard.json`への`loops`セクションのmerge作業はdashboard-sync（Dais owned）の責務であり、この
  feature の実装スコープ外とする。
- **REQ-LV-122（frontend実装順序、規約遵守）**: WHERE dashboard-sync側で`aniccaai.com/dashboard`に
  `loops`セクションのUIを新規追加する作業が発生する場合（この feature 自体の実装スコープ外だが、
  依存関係として明記する）、THE SYSTEM SHALL `gpt-tasteskill` → `frontend-design` skill → 実ブラウザ
  検証、の順序を変えない（プロジェクトCLAUDE.md「フロントエンド作成順序」準拠）。

### K. Loop Scaling（fleet 増殖ガードレール）

- **REQ-LV-130（scale-eligible gate、純関数）**: THE SYSTEM SHALL 各 loop type について
  `scale_eligible(streak, weekly_score, weekly_score_threshold, disk_free_gb) -> bool`（新設・純粋）
  を実装する。真になる条件は design spec §Loop Scaling 準拠: `streak >= 7` AND
  `weekly_score > weekly_score_threshold` AND `disk_free_gb >= 5`。しきい値はloop type毎に
  config（新設、既存`~/anicca/skills/earn/self-improve/config.yaml`と同じYAML形式）で明示する。
- **REQ-LV-131（spawner、判断はagent・実行はツール）**: WHEN ある loop type が REQ-LV-130 で
  `scale_eligible=true`と判定され、かつ agent がfleet拡張を選んだ場合、THE SYSTEM SHALL 既存
  `ig-account-create` skill（実証済み: email-only signup、既存@aiclipsvaultで実績あり）で新アカウント
  を作成し、`~/anicca/skills/earn/clip/_instance_paths.sh`の`ANICCA_INSTANCE`環境変数パターン
  （`_SFX`サフィックス）を踏襲した新しい loop instance 用パス一式を導出し、既存の`*-cli.sh`を
  account引数でパラメータ化したtmux core起動 + healthcheck plist生成を行い、その結果を新設
  `loop-registry.jsonl`（追記専用のspawnイベントログ、REQ-LV-120の`loop-registry.json`＝現在の
  状態スナップショットとは別ファイル）に`{ts, loop_type, account, instance_suffix, spawned_by}`
  として1行追記する。
- **REQ-LV-132（guardrail: warmup必須）**: WHERE 新規作成されたアカウントが投稿を開始する場合、
  THE SYSTEM SHALL そのplatform既存のwarmupスケジュール（clip/videoの既存warmup機構、design spec
  P0-3のwarmupバグ修正後の挙動）を必ず経由させる — warmupをスキップした即時投稿は禁止する。
- **REQ-LV-133（guardrail: 同一platform新規作成のcooldown）**: THE SYSTEM SHALL 同一platform
  （IG/TikTok等）への新規アカウント作成頻度を、config（REQ-LV-130と同じconfig）で明示された
  最小間隔（N日に1つ）以下にする。`loop-registry.jsonl`の直近spawnイベントのtimestampをこの判定の
  入力とする。
- **REQ-LV-134（guardrail: fleet上限）**: THE SYSTEM SHALL 各loop typeのfleet上限（同時稼働instance
  数の最大値）をconfigで明示し、`loop-registry.jsonl`から算出した現在稼働instance数がこの上限に
  達している場合はREQ-LV-131のspawnerを実行しない（fail-closed）。
- **REQ-LV-135（guardrail: ban検知→pause）**: WHEN あるinstanceの投稿が連続N回失敗した場合
  （Nはconfigで明示、design specは具体値を指定していないため実装時にconfigデフォルト値を明記する）、
  THE SYSTEM SHALL 該当instanceを`loop-registry.json`上で`status:"paused"`に更新し、そのloop固有の
  lessons ledger（REQ-LV-030/031）に`{ts, instance, reason:"ban-suspected", consecutive_failures}`
  を追記する。pause中のinstanceはREQ-LV-131のspawner判断（同一platformのfleet数カウント）に
  引き続き算入する（pauseは削除ではない）。

### L. OpenClaw 統合（Dais指示: OpenClaw廃止 → claude-p統合。棚卸し2026-07-08確定版 v2.2、
スコープ縮小指示反映）

Ground truth追加確認: `enabled:true`の103件（全221件中、確認済み）の内訳は design spec v2.2
（生データ: 別セッションのscratchpad `enabled_jobs_with_paths.json` — このfeatureのリポジトリには
存在しないため中身は直接確認していない。分類件数の合計 30+23+7+24+19=103 が jobs.json の実
`enabled:true`件数と一致することのみ確認済み）どおり以下5分類・確定件数とする。件数は前回確定版
（30/23/7/24/19）から変わらないが、**移行方針がDaisのスコープ縮小指示で大きく変わった**——旧版は
5分類中4分類（(a-1)(a-2)(a-3)(b)）が「claude-pへ移行」だったが、v2.2では**無条件migrateはゼロ**に
なり、実際に移行するのは(a-1)の中でも「機械検証ツールが存在するチャネルのみ」に絞られる:

| カテゴリ | 件数 | 移行方針（v2.2、Dais スコープ縮小指示反映） |
|---|---|---|
| (a-1) SNS投稿系（Larry/reelclaw/monk-factory×2/music/slideshow 等） | 30 | **Wave 1: claude-pへ移行——ただし無条件copy禁止**。各チャネルに検証ツール（metrics実測手段）が存在するものだけを、cadence contract + evaluator + lessons.jsonlを最初から装着して移設する。検証ツールが無いチャネルは移行しない |
| (a-2) growth/marketing（cold-email/SEO/backlink/reviews 等） | 23 | **Wave 2: copyせず再設計**（このfeatureの直接実装スコープ外、別途スケジュール）。旧実装には検証/評価loopが皆無で効果が一度も実証されていない（Dais確認済み）。metricが機械計測可能なチャネル（SEO=GSC API、cold-email=返信率、backlink=live URL+票数、reviews=ASC API）のみ、EDD evaluator込みで新規に組み直す。既存OpenClaw実装のcopyは一切行わない |
| (a-3) comedy live 応募系 | 7 | **移行しない**（OpenClawと共に停止。必要になればanicca-dais repoのgit historyから復元可能） |
| (b) Life Manager（naist/meetup/歯科/gcal/mail-triage 等） | 24 | **移行しない**（Dais指示「全部持ち込む必要はない」）。ただしlateness-heartbeat/pipecat-phoneはOpenClaw cronではなくlaunchd直で動いておりOpenClaw削除後も生存する——この2系統は現状維持（`~/anicca/skills/anicca-life-manager/`・`~/anicca/skills/self/life-manager-loop/`の既存実体はこのfeatureのスコープでは触らない） |
| (c) OpenClaw自己保守（cron-doctor/watch-sweep/exec-guard 等） | 19 | **移行しない — OpenClaw廃止と同時に不要化**。死活監視はhealthcheck-runtime-loop系が代替 |

- **REQ-LV-140（棚卸し確定リストの記録、v2.2反映）**: THE SYSTEM SHALL 上記5分類・確定件数
  （30/23/7/24/19、合計103）と、v2.2の移行方針（Wave 1限定migrate/Wave 2再設計/その他は移行しない）を
  この spec に記録済みの事実として扱う（agentによる再分類は不要 — design spec正本が既に確定している）。
  個々のjob（103件）とカテゴリの対応表そのものは design spec の生データ参照先（scratchpad
  `enabled_jobs_with_paths.json`）を正とし、この feature 側では複製しない。
- **REQ-LV-141（移行gate、新規MUST——v2.2の核心制約）**: THE SYSTEM SHALL 「そのチャネルのoutputを
  機械検証できるツールがある」ことを移行の絶対的前提条件とする。post/送信の存在確認 + metrics実測
  （views/replies/clicks等）ができないチャネルはclaude-pに持ち込まない。(a-1)の30件それぞれについて
  検証ツールの有無をagentが確認し（判断はagent、記録は決定論——`{channel, has_verification_tool:bool,
  verification_method}`の形で記録）、`true`のチャネルのみがREQ-LV-143のWave 1移行対象になる。
  移行された各loopは初日からcadence contract（REQ-LV-100〜104、self-healのbar）+ evaluator
  （REQ-LV-110〜113、self-improveのbar）+ loop-report mail（REQ-LV-001〜004、evidence付き）を持つ
  ——後から追加するのではなく初日から装着する。
- **REQ-LV-142（移行前提条件、6項目、順に解消。design spec §OpenClaw統合 準拠、変更なし）**:
  THE SYSTEM SHALL 移行着手前に以下6項目を順に解消する:
  1. スケジューラ代替: cron実行を担う`ai.openclaw.gateway`launchdデーモン（実在確認済み:
     `~/Library/LaunchAgents/ai.openclaw.gateway.plist`）を、claude-p側のlaunchd plist + tmux core
     パターン（既存clip型、REQ-LV-050/051と同じ構成）で代替する。
  2. dispatcherパス: `~/.openclaw/skills/_dispatcher/scripts/cron-bash.sh`（実在確認済み、design spec
     記載の`_dispatcher/cron-bash.sh`の実パス）が`~/.openclaw/skills/`をハードコードしているため、
     skill移設時にこの呼び出しをdispatcher経由ではなく直接launchd/core promptへの呼び出しに置換する
     （dispatcherごと移植しない）。
  3. Telegram announce代替: 103件中90件の結果通知がOpenClawのTelegram bot依存であるため、
     `loop-report.sh`（AgentMail経由keiodaisuke@gmail.com、REQ-LV-001〜004）+ REQ-LV-042の日次
     scorecardに通知経路を統一する。
  4. dashboard-sync: `aniccaai-dashboard-refresh`ジョブ（jobs.json記載、現状productsリポジトリへの
     直接git pushを行っており、プロジェクトCLAUDE.md「dashboard-syncはDais owned、Anicca write禁止」
     と食い違う実装になっている）の書き込み経路を、REQ-LV-120〜121の`loop-registry.json`経路
     （claude-p自身のbodyに書くのみ、landing直接writeなし）に統合し、書き込み主体をCLAUDE.mdの制約と
     一致させる。
  5. ロジックのportability確認: `openclaw`CLIの直接呼び出しは0件（design spec確認済み）である一方、
     skill実体は`~/.openclaw/skills/`固有のものが大半（例外: `capafy-autopublish`は既に
     `~/anicca/skills`へ移設済み、life/ask・life/notify相当の実体は`~/anicca/skills/anicca-life-manager/`
     と`~/anicca/skills/self/life-manager-loop/`に既存——ただし(b)は移行しないため、この実体は
     REQ-LV-141のWave 1移行対象には含まれない）。
  6. `anicca-event-bot-trigger`ジョブのgog CLI依存がOpenClaw外で動作するかは **UNVERIFIED** —
     Phase 2着手時に実際に`gog`コマンドの依存関係を確認し、spec に確定情報を追記してから
     このjobの移行に着手する（存在しない前提で進めない。なお`anicca-event-bot-trigger`が(a-1)に
     属するかは棚卸し生データ参照——このfeature側では複製しない）。
- **REQ-LV-143（移行手順、v2.2スコープ反映——実際に移行するのはWave 1の一部のみ）**: THE SYSTEM
  SHALL REQ-LV-142の6前提条件を解消し、REQ-LV-141の移行gateを適用した上で、以下の順序で実施する:
  ① **Wave 1**: (a-1)の30件それぞれにREQ-LV-141の移行gateを適用し、検証ツールが存在すると判定された
  チャネルのみを`~/anicca/skills`（earn系）へ移設しclaude-p core化（fuelを`openai-codex`から
  Anthropic Sonnetへ切替、cadence+evaluator+lessons.jsonlを初日から装着）。検証ツールが無いチャネルは
  スキップする（移行しない） → ② **Wave 2（このfeatureの直接実装スコープ外、別taskとして後日着手）**:
  (a-2)のうちmetric機械計測可能な4種（SEO/cold-email/backlink/reviews）を、既存OpenClaw実装を
  copyせずゼロから再設計し、EDD evaluator込みで新規構築する。この feature はWave 2の**存在と方針**
  のみを記録し、実装はスコープに含めない → ③ 7日間並走観察（Wave 1で実際に移行したチャネルのみが
  並走対象。OpenClaw側の対応jobは並走中disableしない。二重投稿を検知した場合のみ該当jobを即座に
  disable。(a-3)/(b)/(c)、及び(a-1)中の検証ツール無しチャネル、(a-2)全件は最初から移行していないため
  並走対象にならない——単にOpenClaw側でそのまま稼働し続け、次のgateway disableで停止する） →
  ④ OpenClaw gatewayをdisable → ⑤ 最終削除（REQ-LV-144/145のprecondition充足後にのみ実行）。
  各ステップは前段が完了して初めて着手する（並行スキップ禁止）。
- **REQ-LV-144（削除前MUST: state保全確認、変更なし）**: WHEN ステップ⑤（最終削除）に進む前に、
  THE SYSTEM SHALL `~/.openclaw`のstate/ledgerが`anicca-dais` repo（private）にpush済みであることを
  `git -C ~/.openclaw log --oneline -1`相当のコマンドで実際に確認する（プロジェクトCLAUDE.md
  「不可侵store」= `~/.openclaw`の保全要件と一致）。未pushの変更が残っている場合は削除を実行しない。
- **REQ-LV-145（削除前MUST: Dais明示go、不可逆broadcast、変更なし）**: THE SYSTEM SHALL ステップ⑤
  （OpenClaw gateway/state/cronの最終削除）を、REQ-LV-144の確認に加えて **Dais の明示的な go 指示**
  を precondition として実行する（`~/.claude/CLAUDE.md`「No-human-loop」の3例外の1つ:
  「設計外の不可逆 broadcast」に該当するため）。Dais の明示 go がない限り、ステップ④
  （gateway disable後の観察状態）で止まり、⑤へは進まない。
- **REQ-LV-146（v2.2反映: 検証水準維持の対象をWave 1移行分のみに限定）**: THE SYSTEM SHALL ステップ①
  （Wave 1）で実際に移行された各job（(a-1)の30件中、REQ-LV-141の移行gateを通過したチャネルのみ——
  30件全件ではない）について、この spec の他の要件（evidence mail: REQ-LV-001〜004/019、metrics/
  lessons ledger: REQ-LV-020〜031、cadence contract: REQ-LV-100〜104）を新しいclaude-p loopとしても
  満たすことを確認する（移植先で検証水準が後退しない）。(a-2)のWave 2再設計分・(a-3)/(b)/(c)の
  非移行分はこの feature の直接検証対象に含めない。

## Non-functional constraints

- No dry run（`~/.claude/CLAUDE.md`）: Phase 3 以降の E2E evidence は実際の mail 送信・実際の投稿/応募・
  実際のオンチェーン確認でなければならない（REQ-LV-019がこの制約をGoal 6の独立MUST要件として規定する）。
- 判断のハードコード禁止: どの案件に応募するか、どの改善を採用するか、mistake が何かの判定は全て agent
  自身が行う。この spec がコード化するのは「検証」「記帳」「mail 送信」の3つの決定論ツールのみ
  （`~/.claude/rules/building-effective-ai-agents.md` 準拠）。
- 既存の fail-closed 契約（`loop-report.sh` は credential 欠如時に呼び出し元を絶対に block しない、
  `record_earn.py`/`record-earn.mjs` は on-chain 未確認なら絶対に記帳しない）は一切弱めない。
