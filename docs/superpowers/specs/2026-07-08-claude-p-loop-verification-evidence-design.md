# claude-p Loop Verification + Evidence + Self-Improve Design（2026-07-08）

## 開発環境

- 実装 repo: `~/anicca`（skills/earn, skills/self, skills/report）+ 一部 `~/profitable-claude`
- spec 正本: 本ファイル（anicca-project/docs/superpowers/specs/）
- VCSDD feature: `claude-p-loop-verification`（mode: lean、全フェーズ実施）
- 境界: `~/anicca/skills/report/loop-report.sh`, `~/anicca/skills/earn/{clip,clip-promote,video}/`, `~/anicca/skills/self/{verify-loops*.sh,healthcheck-runtime-loop.sh,founder-loop/}`, `~/profitable-claude/skills/human-funded/{gig,affiliate,bounty}/`。他 instance（automaton/Franklin）の body には触れない。

## Goal（done 条件、全て MUST）

1. claude-p の全 earn loop（clip / clip-promote / video / affiliate / gig / bounty / pm-earner / founder-loop）は、pass ごとに **機械検証済み evidence**（実 URL・実数値・実 tx）を含む mail 報告を keiodaisuke@gmail.com に送る。evidence が無い場合は `none: <理由>` を明記する（空欄は禁止）。
2. 各 loop は自分の output を**自分で検証できる**（下表の検証手段が実装され、検証結果が metrics ledger に記録される）。
3. 各 loop は metrics（views/engagement/応募数/受注/入金/PnL）を JSONL ledger に追跡し、self-improve がその ledger を入力に改善提案→実行する。
4. 失敗は lessons ledger（`state/lessons.jsonl`）に記録され、次 pass の判断に読み込まれる。
5. verify-loops-audit が全 earn loop をカバーし、6h ごとに scorecard mail を送る。stale/broken 検知時は self-fix.sh に自動 escalate する。
6. E2E 完了判定: 各 loop で「実行→投稿/応募→検証→mail（evidence 入り）」の1サイクルが fresh evidence 付きで確認され、fresh-context adversary（Opus 4.8）が PASS を出す。

## 検証アーキテクチャ（loop 別、リサーチ実証済みの手段のみ）

| loop | artifact | 検証手段（実証済み） | metrics ledger | mail evidence（MUST） |
|---|---|---|---|---|
| clip | IG reel URL（`~/.openclaw/state/clip-earn-ledger.jsonl`） | 既存 `self_heal.py` の IG 実ページ読み（維持）+ view/like は browser 実測 | `clip-metrics.jsonl`（新設: reel_url, views, likes, ts） | reel URL + 実測 views |
| clip-promote | campaign 投稿 + Solana payout | 既存 `record-payout.mjs` の on-chain confirmed 検証（維持） | 既存 ledger | 投稿 URL + payout tx |
| video | IG/TikTok 投稿 mp4 + URL | TikTok: `yt-dlp --dump-json --skip-download <url>` で view_count/like_count（無認証実証済み）。IG: 既存 `metrics.py` browser 実測 | 既存 `earn-video-metrics-*.jsonl`（投稿到達で稼働開始） | 投稿 URL + mp4 path + 実測 views |
| affiliate (slideshow) | TikTok slideshow URL + commission | yt-dlp JSON 取得成功可否で存在確認（HTTP 200 は判定不可・実証済み）+ commission-watermark.json | `affiliate-metrics.jsonl`（新設） | slideshow URL + views + commission JPY |
| gig (Coconala) | 応募（`~/gig/applied.jsonl`）・納品物・入金 | 公式 API 不在（実証済み）→ CloakBrowser(:9222) で応募状況/受注/入金ページを実読 | `~/gig/earnings.jsonl` + 新設 `gig-funnel.jsonl`（applied→replied→won→paid） | 応募 URL + funnel 数値 + 入金額 |
| bounty | gated.json survivors + 提出 | board API/実ページ | `bounty-funnel.jsonl`（新設） | checked/survivors/submitted 数 |
| pm-earner | on-chain redeem（`earn-ledger.jsonl`） | `https://data-api.polymarket.com/positions?user=<wallet>`（無認証・実証済み）+ tx status==0x1（既存維持） | 既存 ledger（維持） | realized PnL + tx hash |
| founder-loop | `~/.anicca-founder/state/earn-ledger.jsonl` | on-chain 残高照合 | 既存 ledger | earn_usdc + wallet 残高 |

判定ロジック（何を improve するか、どの案件に応募するか等）は agent 自身が行う。上記は**決定論ツール（検証・記帳）のみ**をコード化する（BUILD AGENTS RIGHT 準拠）。

## P0 修正（現状の障害、全て MUST）

| # | 障害（実証済み） | 修正 |
|---|---|---|
| P0-1 | `loop-report.sh` が AGENTMAIL_API_KEY unset で同日内 SENT/NO-OP 混在（37 SENT vs 46 NO-OP） | script 冒頭で `~/.openclaw/.env` を直接 source して key を自己解決。unset 時は no-op でなく stderr へ ERROR 記録 |
| P0-2 | gig loop が ENOSPC でクラッシュ多発（disk 85%、残 2-4GB） | 承認済み `~/.cache/anicca-*` 回収 + ログ rotate。大物（claudevm/colima）は Dais 承認待ちのまま触れない |
| P0-3 | video loop が warmup day 3→4 に1週間停滞、9日間 noop、投稿ゼロ | warmup 進行条件のバグ特定・修正。投稿フェーズ到達まで |
| P0-4 | `record_earn.py` の on-chain 検証フックが未配線（常に False） | 配線して実収益記帳を有効化 |
| P0-5 | `healthcheck-runtime-loop.sh` 完成済みだが launchd 未配線 | plist 作成・load（pm-earner/founder-loop の死活+stale 監視が有効になる） |
| P0-6 | founder-loop に mail 報告なし | pass 完了ごとに `loop-report.sh founder <summary> <result> <usdc> <evidence>` を配線 |
| P0-7 | evidence 空欄 mail の恒久防止 | `loop-report.sh` に evidence gate: 引数が空/`none` 単独なら reject（exit 1）し、呼び出し元 prompt に `none: <理由>` 形式を義務付け |

## Self-improve 拡張（pm-trade の3層パターンを copy+tweak、新規発明しない）

- pm-trade の `metrics ledger → 改善候補 → fresh adversary gate → 昇格` パターンを clip / video / gig に展開する。
- 各 loop の tmux core STARTUP prompt に「pass 冒頭で lessons.jsonl と metrics ledger を読み、前回より良い選択をする。pass 末尾で mistake があれば lessons.jsonl に1行追記する」を追加（判断は agent、記帳は決定論）。
- 改善の方向: gig=提案文の勝率、clip/video/affiliate=views/engagement、pm=realized PnL。「昨日より今日、今日より明日多く稼ぐ」を metrics ledger の週次比較で machine-checkable にする。

## モデル

全 tmux core = `--model sonnet`（現状維持・確認済み）。self-fix / adversary = Opus 4.8（モデル分業表準拠）。

## Cadence Contract（health の bar、Dais 2026-07-08 指示）

health の判定基準は「artifact が存在する」ではなく「**今日、契約した頻度で成果が出たか**」とする。各 loop は cadence contract を宣言し、healthcheck はそれで判定する:

| loop | cadence contract（MUST） | 判定（JST 日境界） |
|---|---|---|
| clip | 1 reel/日/アカウント 投稿 | 当日 ledger 行 + live 検証（IG 実ページ） |
| affiliate | 1 slideshow/日 投稿 | 当日 ledger 行 + yt-dlp JSON 取得成功 |
| video | warmup 中: warmup_day が毎日 +1 進行。卒業後: 1 投稿/日 | 当日 audit ledger 行の内容で判定 |
| gig | N 件/日 応募（N は agent が市場を見て設定、下限1）+ funnel 更新 | applied.jsonl 当日行 |
| bounty | 1 巡回/日（checked が増加） | gated.json の checked 増分 |
| pm-earner | 1 pass/時 + redeem 確認/日 | earner.log + ledger |
| founder-loop | 1 pass/日 + ledger 更新 | STATE.md mtime + ledger |

- 当日 21:00 JST までに contract 未達 → healthcheck が self-fix.sh へ escalate（「7日前に投稿があるからOK」は不合格）。
- 日次 scorecard mail: loop ごとに ✅posted-today / ❌missed + **streak（連続達成日数）**を表示。streak が health の KPI。
- 既存 `OUT_STALE_HRS`（30h）方式はこの cadence contract 判定に置き換える。

## EDD（Evaluation-Driven Development、self-improve の bar）

verification（二値、self-heal の bar）と evaluation（スカラー、self-improve の目的関数）を分離する。**pm-trade の openevolve パターン（evaluator→score→adversary gate→昇格）を全 loop に一般化する。**

| loop | evaluation metric（週次 score） | 改善対象（genome） |
|---|---|---|
| clip | views/reel（48h窓）+ follower 増分 + payout USDC | クリップ選定基準・caption・投稿時刻 |
| affiliate | views/slideshow + commission JPY/週 | 商品選定・slideshow 構成 |
| video | views/投稿 + 収益化進捗 | ニッチ・台本・頻度 |
| gig | funnel: 応募→返信率→受注率→入金 JPY/週 | 提案文・案件選定基準・価格 |
| bounty | survivors 発見数/週 + payout | board 選定・gate 条件 |
| pm | realized PnL/週（既存 combined_score、実装済み） | 戦略コード（既存） |

- 各 loop に `evaluator`（metrics ledger → score 算出、決定論）を置き、**「今週 > 先週」を machine-checkable にする**（昨日より今日、今日より明日多く稼ぐの実装形）。
- 改善候補（prompt/戦略ファイルの変更）は fresh adversary（Opus 4.8）gate PASS でのみ昇格（pm-trade の promote_gate.sh を copy+tweak）。
- mistakes は loop ごとの `state/lessons.jsonl` に記録し、pass 冒頭で必読。

## Dashboard（aniccaai.com、Dais 指示）

- 各 loop の状態を `~/anicca/skills/self/telemetry-collect.sh`（既存）を拡張して `loop-registry.json` に集約: {loop名, type, account, status(✅/❌ posted-today), streak, 当日 artifact URL, 週次 metric, 累計収益, model}。
- dashboard-sync（Dais owned）が loop-registry.json を fetch → `apps/landing/public/dashboard.json` に "loops" セクションとして merge → aniccaai.com/dashboard に描画。
- frontend 実装順序は規約通り: gpt-tasteskill → frontend-design → 実ブラウザ検証。
- claude-p loop 自身は landing に直接 write しない（既存の write 制限を維持）。

## Loop Scaling = 全 loop 共通の double-down 機構（Dais 2026-07-08: clipping 専用にしない）

scaling は clip 固有機能ではなく、**self-improve の第3の出力**として全 loop 共通のハーネスに置く。金を最大化する entity の基本動作 = 「計測 → 稼いでいるものに資源を倍賭け、稼げないものを縮退 → 再計測」。

- **portfolio allocator（週次、evaluator の直後）**: 全 loop の {週次 score, 実収益, streak} を読み、資源配分を判断する。判断は agent（Sonnet）、実行手段と gate は決定論ツール。
  - **double-down（稼いでいる loop）**: (a) アカウント増殖（SNS系: spawner で新アカウント + core 複製） (b) pass 頻度 up（トレード系: interval 短縮） (c) 資本増額（pm/hl: ポジション上限 up、上限は config） (d) 変種展開（同じ型を隣接ニッチ/プラットフォームへ copy）
  - **縮退（稼げない loop）**: pass 頻度 down → それでも0が続けば pause（削除はしない、registry に縮退理由を記録）
- **scale-eligible 条件（決定論 gate、増殖の前提）**: cadence streak ≥7日 AND 週次 evaluation score が閾値超 AND **実収益 > 0 が ledger で検証済み** AND disk 空き ≥5GB。
- **spawner（ツール、判断は agent）**: `ig-account-create` skill（実証済み: email-only、@aiclipsvault）等で新アカウント作成 → loop instance を `loop-registry.jsonl` に登録 → 既存 cli.sh を account 引数でパラメータ化した tmux core + healthcheck plist を自動生成（clip-producer の ANICCA_INSTANCE env パターンを copy）。SNS 以外の loop の double-down（頻度/資本）も同じ registry 経由で記録し dashboard に反映。
- **guardrail（MUST）**: 新アカウントは platform 毎の warmup schedule に従う / 同一 platform の新規作成は N 日に1つ / fleet 上限・資本上限は config で明示 / ban 検知（投稿失敗連続）で該当 instance を pause し lessons.jsonl に記録 / 資本増額は on-chain 検証済み realized profit の範囲内。
- 「1アカウントの clipping」→「数百アカウントの clipping factory」も、「PM の勝ち戦略に資本を寄せる」も、同一の allocator+registry+gate が担う。

## OpenClaw 統合（Dais 指示: OpenClaw を廃止し claude-p に統合。棚卸し 2026-07-08 完了）

enabled 103 job の実データ分類（jobs.json + skill 実体確認済み、生データ: scratchpad/enabled_jobs_with_paths.json）:

| カテゴリ | 件数 | 移行方針（Dais 2026-07-08 スコープ縮小指示反映） |
|---|---|---|
| (a-1) SNS投稿系（Larry/reelclaw/monk-factory×2/music/slideshow 等） | 30 | **Wave 1: claude-p へ移行**。ただし無条件 copy 禁止 — 各チャネルに検証ツール（metrics 実測手段）が存在するものだけを、cadence contract + evaluator + lessons.jsonl を最初から装着して移設する。検証ツールが無いチャネルは移行しない |
| (a-2) growth/marketing（cold-email/SEO/backlink/reviews 等） | 23 | **Wave 2: copy せず再設計**。旧実装には検証/評価 loop が皆無で効果が一度も実証されていない（Dais 確認済み）。metric が機械計測可能なチャネル（SEO=GSC API、cold-email=返信率、backlink=live URL+票数、reviews=ASC API）のみ、EDD evaluator 込みで新規に組み直す |
| (a-3) comedy live 応募系 | 7 | **移行しない**（OpenClaw と共に停止。必要になれば anicca-dais repo の git history から復元可能） |
| (b) Life Manager（naist/meetup/歯科/gcal/mail-triage 等） | 24 | **移行しない**（Dais 指示「全部持ち込む必要はない」）。ただし lateness-heartbeat / pipecat-phone は OpenClaw cron ではなく launchd 直で動いており OpenClaw 削除後も生存する — この2系統は現状維持 |
| (c) OpenClaw 自己保守（cron-doctor/watch-sweep/exec-guard 等） | 19 | **移行しない — OpenClaw 廃止と同時に不要化**。死活監視は healthcheck-runtime-loop 系が代替 |

移行 gate（MUST）: **「そのチャネルの output を機械検証できるツールがある」ことが移行の前提条件**。post の存在確認 + metrics 実測（views/replies/clicks）ができないチャネルは claude-p に持ち込まない。移行された各 loop は初日から cadence contract（self-heal の bar）+ evaluator（self-improve の bar）+ loop-report mail（evidence 付き）を持つ。

移行の前提条件（MUST、順に解消する）:
1. **スケジューラ代替**: cron 実行は `ai.openclaw.gateway` デーモンが担っている → claude-p 側は launchd plist + tmux core パターン（既存 clip 型）で代替。
2. **dispatcher パス**: `_dispatcher/cron-bash.sh` が `~/.openclaw/skills/` をハードコード → skill 移設時に呼び出しを直接 launchd/core prompt に置換（dispatcher ごと移植しない）。
3. **Telegram announce 代替**: 103件中90件の結果通知が OpenClaw の Telegram bot 依存 → `loop-report.sh`（AgentMail→Gmail）+ 日次 scorecard に統一。
4. **dashboard-sync**: `aniccaai-dashboard-refresh` が products repo へ直接 git push している実装（CLAUDE.md の「dashboard-sync は Dais owned、Anicca は write 禁止」と食い違い）→ 移行時にこの push 経路を本 spec の Dashboard 節の loop-registry 経路に統合し、書き込み主体を明確化する。
5. ロジック自体は portable（`openclaw` CLI 直呼びは 0 件）。skill 実体は ~/.openclaw/skills/ 固有（例外: capafy-autopublish は移設済み、life/ask・life/notify は ~/anicca/skills に実体あり）。
6. `anicca-event-bot-trigger` の gog CLI 依存は OpenClaw 外で動くか要確認（UNVERIFIED）。

手順: ① (a-1)→(a-2)→(a-3) の順に skill を ~/anicca/skills（earn系）へ移設し claude-p core 化 → ② (b) を life-manager core 化 → ③ 7日間並走観察（OpenClaw 側 job は並走中 disable しない、二重投稿だけ即 disable）→ ④ gateway disable → ⑤ **最終削除は state/ledger の anicca-dais repo push 確認 + Dais の明示 go で実行**（不可逆 broadcast）。

## 除外（この spec のスコープ外）

autohedge（DeepSeek・別プロジェクト）、daily-nl-report（automaton 帰属）、Franklin/automaton の body。tier1/tier2 は OpenClaw 廃止と同時に healthcheck-runtime-loop 系へ吸収（上記⑥まで現状維持）。
