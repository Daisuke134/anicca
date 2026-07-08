# Behavioral Spec — claude-p-ceo-loop (Phase 1a, mode: lean)

## Context

design spec 正本: `docs/superpowers/specs/2026-07-08-claude-p-loop-verification-evidence-design.md`
§「会社型3層アーキテクチャ」「CEO LOOP」「採用する BP」節。既存 `founder-loop`（狭い記録ループ、
自分の ledger に earn を記録し目標達成を確認するだけ）を **CEO** に昇格させる — 全 manager loop
（clip/clip-promote/video/affiliate/gig/bounty/pm-earner）の {cadence streak, 週次 evaluation score,
実収益, token/USD spend} を読み、稼ぐ loop に資源を倍賭け・稼げない loop を縮退させる portfolio
allocation を決め、自分自身の判断を「配分を変えた翌週に会社全体の実績が上がったか」で検証する。
判断（どの loop を倍賭けするか、何を改善候補にするか）は agent（Sonnet）の裁量、コード化するのは
「配分計算式（bandit）」「budget gate（決定論フィルタ）」「記帳・書込・mail 送信」の3種の決定論
ツールのみ（`~/.claude/rules/building-effective-ai-agents.md` 準拠、regex による judgment のハード
コード禁止）。

## Ground truth（実装確認済み、2026-07-08 時点）

- `~/anicca/skills/self/founder-loop/founder-loop.sh` — 1 wake ごとに `record-earn.mjs`（Base RPC で
  founder wallet `0x810f6d61f7606deee2657d3083e150a222bc29c5` への外部 USDC Transfer を確認、
  INV-1..7 の anti-fake ゲート済み）を呼び、`~/.anicca-founder/state/STATE.md` を atomic 書込し、
  `report-args.mjs::founderReportArgs()`（純関数）経由で `loop-report.sh founder ...` を呼ぶ
  （P0-6 実装済み）。INV-H1（STATE 先読み）〜INV-H6（rc 伝播）を守る。**CEO 化はこのファイルに
  「配分ステップ」を追加で足す形であり、既存の money-wake ロジック・`$RECORD`（唯一のledger writer、
  INV-H2）を一切変更しない。**
- `~/anicca/skills/self/founder-loop/record-earn.mjs` — 唯一のledger writer。cursor はブロック高で
  atomic 書込（`writeCursorAtomic`: tmp書込 → `fs.renameSync`）。この atomic tmp+rename パターンを
  CEO の新規状態ファイル（bandit state / loop-registry / rollback snapshot）でも再利用する。
- `~/anicca/skills/self/cadence.py` — `cadence_met(today_jst_date, contract, evidence) -> bool`（5種の
  kind: row-exists/increment/pass-marker/recency/compound、既存・完成済み）、
  `streak(evidence_by_date, today_jst_date, contract) -> int`（既存・完成済み、gap で0リセット）。
  純関数、I/O なし。CEO はこれをそのまま呼び、独自の streak/cadence 判定ロジックを再発明しない。
- `~/anicca/skills/self/cadence-contracts.json` — clip/affiliate/video/gig/bounty/founder-loop/pm-earner
  の cadence contract 宣言（既存・完成済み）。clip-promote は意図的に不在（コメント: campaign依存の
  ため専用 status 判定、`clip-promote-status.mjs::clipPromoteStatus(payoutRows, todayJstDate)` を使う。
  既存・実装済み、`claude-p-loop-verification` feature が `currentPhase: 6`＝収束済みであることを
  state.json で確認済み）。**実ファイルのトップレベルキーは `['_comment', 'clip', 'affiliate', 'video',
  'gig', 'bounty', 'founder-loop', 'pm-earner']` の8件で、`_comment` は値が `str`（Cadence Contract宣言の
  説明文）、他7件は値が `dict`（Phase 1c adversary が実ファイルを直接読み検証済み）。この `_comment`
  キーを loop として拾うと `contract["kind"]` で `TypeError` になるため、REQ-CEO-001 は値の型で除外する
  （キー名の除外リストのハードコードではなく、型判定という決定論フィルタ）。**
- `~/anicca/skills/self/self-improve/weekly_report.py` — loop（clip/affiliate/video/gig/bounty）ごとに
  今週/先週の metrics ledger を分割し、`<loop>/evaluator.py::evaluate_stage1` で `combined_score` を
  算出、`lib/weekly_compare.py::beats_previous_week(this, last) -> bool`（strict `>`、tie は beat では
  ない）で比較し、`<ledger>-weekly.jsonl`（元 ledger とは別ファイル、REQ-LV-111の cadence 誤判定防止
  fix 済み）に追記する。既存・完成済み。pm-earner 専用の週次スコアは既存 `combined_score`（pm-trade
  実装、design spec表内で言及）を別途参照する。
- `~/anicca/skills/self/self-improve/lib/ledger_metrics.py` — `score_from_rows(rows, view_weight,
  earn_weight)` が `earn_usdc`→`earn_jpy`→`commission_jpy` の fallback chain で実収益を合算する
  （既存・完成済み）。CEO の「実収益」読み取りはこの既存関数の出力（各 loop の `-weekly.jsonl` 最新行の
  `combined_score`、および ledger 生データの直接合算）を再利用する。
- `~/anicca/skills/self/loop-scale/guardrails.py` — `scale_eligible(streak, weekly_score, threshold,
  disk_free_gb) -> bool`（3条件AND、既存・完成済み）、`cooldown_ok(last_spawn_ts, now_ts,
  min_interval_days) -> bool`、`fleet_at_capacity(current_count, max_count) -> bool`、
  `is_ban_suspected(consecutive_failures, threshold) -> bool`（全て既存・完成済み、task #13 の
  spawner/registry 本体は未実装だが guardrail 純関数は実装済み）。CEO はこれらをそのまま呼び、
  fleet 増殖判断の条件式を再実装しない。
- `~/anicca/skills/self/telemetry-collect.sh` — instance 別 `telemetry.json` を書く既存スクリプト
  （claude-p分は `~/.anicca-founder/state/telemetry.json`）。**`loop-registry.json` はまだどのスクリプト
  も書いていない**（`find` で0件確認済み） — task #12/#13 が本格実装予定だが未着手。この feature が
  `loop-registry.json` の最初の書き手になる可能性があるため、REQ-CEO-040/041 でファイル不在時の
  bootstrap と、他プロセス（将来の task #13 spawner）が書く可能性のあるキーを破壊しない non-destructive
  merge を規定する。
- `~/anicca/skills/report/loop-report.sh` — `<loop_name> <did> <result> <earned_usdc> [evidence]`。
  evidence gate（`lr_valid_evidence`、空文字/`"none"`単独を reject、`"none: <理由>"`は許可、既存・
  完成済み、REQ-LV-003）。CEO の週次 mail もこの既存インターフェースをそのまま呼ぶ。
- **loop-report.sh 呼び出しフックの実在確認（Phase 1c iteration-6 adversary指摘B12を受け、team-lead
  指示によりteam-lead自身ではなくbuilderが実ファイルシステムを直接確認——B12のadversaryは`~/anicca`と
  `~/.openclaw`のみ検索し、`~/profitable-claude`を見落としていた）**: `grep -n "loop-report" <file>`で
  実際に確認済み。**clip**: `~/anicca/skills/earn/clip/clip-cli.sh`のSTARTUP変数内に
  `bash ~/anicca/skills/report/loop-report.sh clip ...`が存在（確認済み）。**video**:
  `~/anicca/skills/earn/video/video-cli.sh`、同型で`loop-report.sh video ...`が存在（確認済み）。
  **clip-promote**: `~/anicca/skills/earn/clip-promote/clip-promote-cli.sh`、同型で
  `loop-report.sh clip-promote ...`が存在（確認済み）。**affiliate**:
  `~/profitable-claude/skills/human-funded/affiliate/affiliate-cli.sh`のSTARTUP変数内に
  `bash ~/anicca/skills/report/loop-report.sh affiliate "<summary>" ...`が存在（確認済み——
  `~/.openclaw/skills/anicca-glitchy-affiliate/`は現在使われていない旧パス）。**gig**:
  `~/profitable-claude/skills/human-funded/gig/gig-cli.sh`のSTARTUP変数内に
  `bash ~/anicca/skills/report/loop-report.sh gig "<summary>" ...`が存在（確認済み）。**bounty**:
  `~/profitable-claude/skills/human-funded/bounty/bounty-cli.sh`のSTARTUP変数内に
  `bash ~/anicca/skills/report/loop-report.sh bounty "<summary>" ...`が存在（確認済み）。**pm-earner**:
  `~/anicca/skills/earn/polymarket-trade/`配下の全17ファイルを`grep -rln "loop-report"`したが
  **0件、フックは存在しない**（確認済み——pm-earnerはLLMなしのPythonスクリプト群であり、
  tmux STARTUP promptという概念自体を持たない）。この6/7の実在確認とpm-earnerの不在確認を根拠に
  REQ-CEO-020のscopeをclip/clip-promote/video/affiliate/gig/bountyの6 loopに限定し、pm-earnerの
  cost trackingはOut of scopeへ移す（B12の直接修正）。
- **Mahoraga**（`gh clone pockanoodles/Mahoraga`、実クローンして確認済み）
  `backend/orchestrator/routing/strategies/linucb.py::LinUCBRouter` — arm ごとに `A`（d×d 行列）/`b`
  （d×1 ベクトル）を持ち、`select_agent(context, available_agents)` で UCB
  （`exploit + alpha*sqrt(explore_sq)`）最大の arm を返し、`update(context, agent, reward, weight)` で
  `A`/`b` を更新する。`save_state`/`load_state` は tmp書込 → `os.replace` の atomic パターン。
  `backend/orchestrator/routing/strategies/thompson.py::ThompsonSamplingRouter` — arm ごとに
  `Beta(alpha, beta)` を持ち、`select_agent` は `np.random.beta` サンプル最大の arm を返し、
  `update(context, agent, reward)` は `reward > threshold` なら `alpha += 1`、そうでなければ
  `beta += 1`。`backend/orchestrator/routing/budget_pacer.py::BudgetPacer` — rolling window 平均コスト
  が `ceiling` を超えると Lagrange 乗数 `lambda_` を dual ascent で増やす `update(task_cost)`、
  `hard_limit` を超える arm を候補から除外する `filter_agents(available, task_cost_estimates)`
  （候補が空になったら最安 arm へフォールバック、候補を絶対に空にしない）。
- **agent-os**（`gh clone kai-linux/agent-os`、実クローンして確認済み）
  `orchestrator/budgets.py` — `monthly_spend_by_agent(cfg, month_key)` が `cost_events.jsonl` を UTC
  月境界で集計、`budget_for_agent(cfg, agent)` は per_agent → default の順で解決し未設定なら `None`
  （budget無効）、`remaining_budget()`/`is_hard_stopped()`、`filter_budget_compliant_agents(agents, cfg,
  month_key)` が hard-stop超過を除外（**budgetsセクション自体が無ければ入力をそのまま返す = fail-open**、
  `warn_if_budgets_missing` で一度だけ警告）、`check_budget_alerts()` が `(month, agent, threshold)` ごと
  に1回だけ alert を fire（`budget_alerts.jsonl` の `key` で dedup）。

## In scope（この feature が触ってよい境界）

`~/anicca/skills/self/founder-loop/`（既存ファイルへの追記1箇所のみ: `exit "$RC"` 直前への CEO pass
呼び出し挿入、REQ-CEO-070参照）、新設 `~/anicca/skills/self/founder-loop/ceo/`（bandit.py / budget.py /
budget_pacer.py / allocator.py / ceo-pass.sh、全て新規）、`~/.anicca-founder/state/`（新規state file群:
`loop-registry.json`, `ceo-bandit-state.json`, `ceo-budget-pacer-state.json`, `ceo-cost-events.jsonl`,
`ceo-budget-config.json`, `ceo-budget-alerts.jsonl`, `ceo-fx-config.json`, `ceo-miss-streak.json`,
`ceo-verification.jsonl`, `ceo-rollback.json`, `ceo-lessons.jsonl`, `ceo-escalations.jsonl`）。
`~/anicca/skills/self/cadence.py`・`cadence-contracts.json`・`self-improve/**`・`loop-scale/guardrails.py`
は **読むだけ**（import して呼ぶのみ、変更しない）。**B11/B12反映（REQ-CEO-020の統合ポイント、
実在確認済みの6 loopに限定）**: roster内の6 loop（clip/clip-promote/video/affiliate/gig/bounty、
**pm-earnerは含まない**）が既に持つ pass-end reporting フックへの `record_cost_event` 呼び出し追加は、
各 loop 側の該当フック1行への追記としてこの feature の実装スコープに含める（既存の`loop-report.sh`
呼び出しパターンへ1行追加するのみ、pass自体の判断ロジックは変更しない）——対象ファイルは
`~/anicca/skills/earn/{clip,video,clip-promote}/<loop>-cli.sh` と
`~/profitable-claude/skills/human-funded/{affiliate,gig,bounty}/<loop>-cli.sh` の計6ファイル
（Ground truth節で実在確認済み、Phase 1c iteration-6 adversary指摘B12の直接反映）。

## Out of scope

`record-earn.mjs`（唯一のledger writer、INV-H2、一切改変しない）、`automaton`/`Franklin` の body、
task #13 の spawner 本体（新アカウント作成の実装自体、`ig-account-create` 呼び出し）——CEO は
`scale_eligible`/`cooldown_ok`/`fleet_at_capacity` を呼んで fleet 増殖の**可否判定**をするだけで、
実際のアカウント作成は task #13 の実装を待つ（この feature は「fleet_size_target を allocation
テーブルに書く」までがスコープ）。task #19 の EXPLORER loop・task #20 の「manager loop の外部検索
自己改善」は別 feature。`apps/landing/**`（dashboard-sync は Dais owned、write 禁止、既存制約を維持）。
**pm-earner（`~/anicca/skills/earn/polymarket-trade/`）のcost tracking統合は明示的にOut of scope**
（Phase 1c iteration-6 adversary指摘B12の直接反映）: `record_cost_event`呼び出しフックの実装は、
pm-earner自身がloop-report.sh相当のpass-end reportingフック（tmux STARTUP prompt、またはそれに
相当する仕組み）を持つに至った時点までdeferする。それまでの間、`ceo-cost-events.jsonl`に
pm-earner分の行は恒久的に存在せず、REQ-CEO-021が定めるfallbackルール（`weekly_spend_usd=0`扱い、
budget hard-stop gate対象外）で扱われる——これはpm-earnerがbudget/reward機構から不当に除外される
のではなく、cost trackingという前提機能がまだ無いことの機械的な帰結である。

## Cross-cutting invariants（全REQに例外なく適用、Phase 1c iteration-4/5 adversary指摘B7/B8/B9/B10/B11の
構造修正）

4 iteration にわたり同じ2クラスの欠陥（順序ギャップ・通貨変換漏れ）が箇所を変えて再発し、iteration-5
ではさらにiteration-4自身の修正（`registry_updates`アキュムレータ）が3番目の欠陥クラス（複数ステップが
同じ共有可変状態へ異なる粒度で書き込み、内部マージ順序が未定義になる）を生んだ。これを受け、
**アキュムレータへの逐次queueという仕組み自体を廃止**し、より単純な設計（道A、Dais/team-lead指示）に
置き換える。個々のREQはこれらの不変条件を**満たすことが前提**であり、各REQの本文はこれらを繰り返し
引用するのではなく従うだけでよい（矛盾する記述があれば、この節が優先する）。

- **INV-CEO-1（通貨変換の完全経由、B10修正: 列挙にREQ-CEO-060を追加）**: `_usd`/`_usdc` と名の付く
  **全ての**パラメータ・引数・**フィールド（jsonlスキーマのフィールド名を含む）**は、必ず
  REQ-CEO-050 の `realized_profit_usd(entries, fx_config) -> float` の戻り値でなければならない。
  `sum_earn_by_currency()`（REQ-CEO-002(c)）の生出力、`combined_score`（`score_from_rows`のblended値、
  REQ-CEO-002(b)）、loop固有のnative通貨値（JPY等）が、これらのパラメータ・フィールドへ**現在この
  specに列挙されているか否かに関わらず**直接渡ることは恒久的に禁止される。**このspecに新しい
  money-consuming関数・新しい`_usd`/`_usdc`型のjsonlフィールドが追加される場合、その追加と同じ変更で
  「`realized_profit_usd()`を経由する」ことを明記しなければならない** — 経由の明記を欠いたまま
  `_usd`/`_usdc`型のパラメータ・フィールドを定義すること自体がspec違反である。現時点でこの不変条件の
  対象となる項目（列挙、REQ-CEO-002(c)/050も同じ列挙を保持する。**Phase 1c iteration-5 adversaryが
  spec全文を`_usd`/`_usdc`でgrepし直接検証した結果、以下4件が全件——B10で追加されたREQ-CEO-060を
  含めてこれ以上の該当は存在しない**）: `company_score`（REQ-CEO-050）、
  `capital_increase_within_realized_profit`の第3引数`realized_profit_usd`（REQ-CEO-030(b)）、
  `compute_reward`の第1引数`realized_earn_usdc`（REQ-CEO-010）、`ceo-escalations.jsonl`の
  `weekly_realized_profit_usd`フィールド（REQ-CEO-060、B10新規追加）。
- **INV-CEO-2（実行順序の完全配置、B9修正: アキュムレータ方式を廃止し単一組立関数に統合。B11修正:
  scopeを明示）**: **このCEO WEEKLY pass（REQ-CEO-058の①〜⑫）に属する**副作用（ファイル書込・
  mail送信・ログ追記等）を持つ**全ての**REQは、①〜⑫のいずれか1箇所に必ず明示的な位置を持たなければ
  ならない。位置未定義の副作用REQはそれ自体がspec違反である。**このspecに新しい副作用REQが追加され
  る場合、その追加と同じ変更で、それがCEO WEEKLY passに属するならREQ-CEO-058のステップ列に配置し、
  属さないなら「なぜ属さないか（呼び出し主体・cadenceの違い）」を明記しなければならない**（別REQ・
  別変更での配置は許可しない）。**この「属さない」の明示的な前例が2件ある**（Phase 1c iteration-5
  adversary指摘B11の直接反映——INV-CEO-2の当初案が無条件の「全REQ」だったため、この2件との整合性が
  取れていないという自己矛盾を生んでいた）: (a) REQ-CEO-020は roster内の各 earn loop 自身の
  pass-end（CEO WEEKLY passではない、PER-LOOP-PASS）に属するため対象外、(b) REQ-CEO-070は
  「①〜⑫のシーケンス全体をfounder-loop.shのどこから呼び出すか」を定義するものであり、シーケンスの
  **呼び出し元**であって内部の1ステップではないため対象外。加えて、`loop-registry.json`
  への実I/O書込は**1 WEEKLY pass につき高々1回**（REQ-CEO-044、ステップ⑨）に限定される。
  **この不変条件をB9修正で強化する**: iteration-4版は「複数ステップがin-memoryの`registry_updates`
  アキュムレータへ逐次queueし、最後に1回だけ書く」設計だったが、③-c/⑥/⑧-cという異なるステップが
  同じ共有可変dictへ異なる粒度（subkey単位 vs loop全体dict単位）で書き込む結果、どのステップの
  queueが後続のqueueをどう上書きするかという「内部マージ順序」がspec上未定義になり、rollback発火
  passで③-cがqueueした`"budget"`サブキーが⑥の復元でまるごと消える、という新たな欠陥（B9）を生んだ
  ——Phase 1c iteration-3(B4)→iteration-4(B6)→iteration-5(B9)と、直した箇所の隣に新しい穴が3回連続
  再発したため、パッチではなく仕組みそのものを単純化する。**新設計（アキュムレータ廃止）**: WEEKLY
  passの各ステップは、`registry_updates`のような共有可変状態を一切持たず、**それぞれ自分自身の
  ローカルな戻り値（他ステップと独立した、まっさらな dict）だけを返す**（③-cは`budget_snapshot_
  by_loop`、⑥は`rollback_restore`〔非発火なら`None`〕、⑧-cは`allocation_decisions`）。これら3つの
  ローカル戻り値は、REQ-CEO-044の`build_next_registry()`という**唯一の組立関数**へ、ステップ⑨で
  一度だけ**明示的な名前付き引数として**渡され、そこで初めて`existing_registry`と統合された
  「次の`loop-registry.json`全体」が1回で組み立てられ、1回のatomic書込で書かれる。複数ステップが
  同一の共有可変dictへ時間差で書き込むという構造自体が無くなるため、「どちらの書込が勝つか」という
  順序依存の問い自体が発生しない（B9の直接反証: 欠陥のクラスを構造的に消す）。

## Requirements（EARS、全て MUST。「任意/推奨」は書かない）

### A. 入力読み取り（週次フルパス + 日次軽量点検）

- **REQ-CEO-001（B1修正: 非dict値キーの除外）**: THE SYSTEM SHALL loop roster を
  `derive_roster(cadence_contract: dict) -> list[str]` で導出する。この関数は
  `~/anicca/skills/self/cadence-contracts.json` を dict としてロードし、**値が `dict` であるキーのみ**
  を候補とし（`_comment`（値は `str`）のような非 loop キーを型判定で除外する — キー名のハードコード
  除外リストではなく、値の型という決定論フィルタ。cadence contract は必ず `{"kind": ...}` を持つ
  `dict` であるという既存スキーマそのものを判定根拠にする）、そこから `founder-loop`（CEO 自身の
  body であり allocation 対象ではないため）を除いたものに `clip-promote`（cadence-contracts.json に
  意図的に不在、REQ-CEO-004参照）を加えた集合を **動的に導出する**（固定 Python リストのハードコード
  禁止 — 新しい loop の cadence contract が追加されれば自動的に CEO の roster にも入る）。
  実ファイル（8キー、`_comment`含む）に対して roster は7件（clip/affiliate/video/gig/bounty/pm-earner/
  clip-promote）になる。
- **REQ-CEO-002（M3修正: 通貨タグの発生源を明示）**: WEEKLY（JST 月曜、`is_ceo_weekly_due`）THE SYSTEM
  SHALL roster の各 loop について次を読み取り1つの snapshot dict に組み立てる: (a) `cadence.streak()`
  （cadence-contracts.json の該当 contract + 実 evidence）で cadence streak、(b) 該当 loop の
  `-weekly.jsonl`（`weekly_report.py` 出力、無ければ `weekly_report.run()` をこの pass 内で1回実行して
  生成）の最新行の `combined_score`/`beats_previous_week`（この経路は無変更——`score_from_rows` の
  fallback chain をそのまま使う既存の per-loop 週次スコア）、(c)
  `sum_earn_by_currency(rows: list[dict]) -> list[{amount: float, currency: str}]`（新設・純粋: 既存
  `score_from_rows` のように1本のblended floatに畳み込む（＝どのfallbackフィールドが勝ったか失われる）
  のではなく、`earn_usdc`合計を`{amount: Σearn_usdc, currency:"usd"}`、`earn_jpy`+`commission_jpy`
  合計を`{amount: Σ(earn_jpy+commission_jpy), currency:"jpy"}`として**常に2件のentry**を返す
  （データが無い通貨は`amount:0`のentryのまま——「どのフィールドが勝ったか」を推測する分岐を持たない、
  常に両通貨バケットを機械的に合算するだけの決定論関数。Phase 1c iteration-2 adversary指摘M3の直接
  修正: `score_from_rows`はどのfallbackフィールドを使ったか返さないため、通貨タグの発生源がspec上
  存在しなかった問題を、単一pairではなく複数通貨entryのlistという設計で解消する）で loop の実収益を
  読む。**この`ledger_earn_entries`（list）は REQ-CEO-050 の`realized_profit_usd()`に渡すまで一切
  USD換算しない。INV-CEO-1が列挙する全ての`_usd`/`_usdc`型パラメータ（company_score算出
  〔REQ-CEO-050〕、REQ-CEO-030(b)の資本ガードレール、REQ-CEO-010の`compute_reward`の
  `realized_earn_usdc`を含む）は必ず`realized_profit_usd()`経由でUSD換算してから使う——生の通貨の
  まま`_usd`/`_usdc`型パラメータへ渡すことは一切ない**（Phase 1c iteration-2 adversary指摘M4・
  iteration-4 adversary指摘B8の直接修正: iteration-1版のspecはここで「loop単体の判断には生の通貨の
  ままの値を使う」と誤った指示をしており、それがM4の直接原因だった。iteration-3で新設したREQ-CEO-058
  ステップ③がREQ-CEO-010の呼び出しを追加した際、この列挙にREQ-CEO-010を追加し忘れたことがB8の
  直接原因だった——今後この種の列挙漏れが起きないよう、INV-CEO-1が「将来のREQ追加時も自動適用される
  恒久ルール」として本節の外側で独立に定義されている）、
  (d) `weekly_spend_by_loop()`（REQ-CEO-021、新設: その JST 週(月〜日)の loop 別合計 spend、bandit
  reward 計算 REQ-CEO-010/014 用）**と** `monthly_spend_by_loop()`（REQ-CEO-021、既存: UTC 暦月の
  loop 別合計 spend、budget hard-stop gate REQ-CEO-022/023 用）の両方の token/USD spend（時間窓の
  異なる2種、目的ごとに使い分ける——週次で動くbanditのrewardに月次集計を使うと月初/月末で分母が
  不連続に変動し誤ったreward信号になるため分離する）。
- **REQ-CEO-003**: DAILY（毎日、JST）THE SYSTEM SHALL REQ-CEO-002 と同じ snapshot 読み取りを実行する
  が、bandit 更新（REQ-CEO-010）・allocation 書込（REQ-CEO-040）・self-verification（REQ-CEO-050）は
  実行しない（読み取りのみの軽い点検 — 会社設計 spec の「週次＋日次の軽い点検」に対応）。
- **REQ-CEO-004（実シンボル名に修正）**: clip-promote の実収益/streak相当は既存実装
  `clip-promote-status.mjs::clipPromoteStatus(payoutRows, todayJstDate)`（payout ledger の当日行有無
  ベース、`cadence_met` は呼ばない、既存・完成済み）をそのまま呼んで読む（cadence.py の5 kind 判定を
  clip-promote に無理に当てはめない、独自実装を再発明しない）。

### B. bandit ベースの資源配分エンジン（Mahoraga copy+tweak）

- **REQ-CEO-010（M2修正: BudgetPacerのLagrange λを reward に統合。B8修正: 第1引数のUSD経由を明記）**:
  WEEKLY、THE SYSTEM SHALL `ceo/bandit.py` に Mahoraga の `LinUCBRouter`/`ThompsonSamplingRouter` を
  移植した実装（config で `linucb`/`thompson` を選択可能、デフォルト `linucb`）を用い、各 loop を1
  arm として、`compute_reward(realized_earn_usdc, weekly_spend_usd, lambda_) -> float`（新設・純粋:
  `base = weekly_spend_usd>0 の場合 realized_earn_usdc/weekly_spend_usd、そうでなければ
  realized_earn_usdc`、`reward = base - lambda_ * weekly_spend_usd`）を reward として
  `update(context, loop, reward)` を呼ぶ。**第1引数`realized_earn_usdc`には、当該loopの
  `ledger_earn_entries`（REQ-CEO-002(c)）を REQ-CEO-050 の `realized_profit_usd(entries, fx_config) ->
  float` に通した後のUSD換算済みの値を必ず渡す**（REQ-CEO-030(b)と同一パターン、INV-CEO-1の対象
  関数として明記——`ledger_earn_entries`の生合計や`combined_score`をそのまま渡すことは一切ない。
  JPY建てloop（gig/affiliate）でこれを怠ると reward が`fx_config["jpy_usd_rate"]`倍不正確になり、
  bandit の UCB ランキング〔⑧-b〕・double-down 判断〔⑧-c〕全体を歪める——Phase 1c iteration-4
  adversary指摘B8の直接修正）。`lambda_` は REQ-CEO-014 の `BudgetPacer.lambda_`（その週の会社全体
  spend の rolling average が
  ceiling を超えるほど大きくなる Lagrange 乗数）を渡す — これにより design spec「採用する BP」で
  明記された Mahoraga の Lagrange 乗数 budget pacer が実際に reward 計算へ組み込まれる（cited だが
  未使用というギャップの解消）。`context` は roster snapshot（streak/combined_score/spend等）から
  組み立てる固定次元の特徴ベクトルとする。
- **REQ-CEO-011**: THE SYSTEM SHALL bandit の状態（LinUCB の `A`/`b`、または Thompson の
  `alpha`/`beta`）を `~/.anicca-founder/state/ceo-bandit-state.json` に Mahoraga の `save_state`/
  `load_state` と同型の tmp書込→atomic rename で永続化する。
- **REQ-CEO-012**: THE SYSTEM SHALL 各 loop の UCB スコア（または Thompson サンプル値）を算出し
  agent に提示するが、**allocation テーブルへの最終書込内容（token 予算・pass 頻度・資本上限・
  fleet サイズ目標）は agent が決める** — bandit スコアが最大の loop を機械的に自動選択して
  そのまま書き込む処理は実装しない（判断のハードコード禁止、`~/.claude/rules/
  building-effective-ai-agents.md` 準拠）。
- **REQ-CEO-013**: `~/.anicca-founder/state/ceo-bandit-state.json` が存在しない場合、THE SYSTEM SHALL
  cold-start（Mahoraga の `_init_agent` と同型: 単位行列 `A`、prior ベースの `b`、または
  Thompson の `alpha=beta=1.0`）で初期化する。
- **REQ-CEO-014（M2新設: Mahoraga BudgetPacerのLagrange dual-ascent配線）**: THE SYSTEM SHALL
  `ceo/budget_pacer.py` に Mahoraga の `BudgetPacer`（`update(task_cost)`によるLagrange乗数`lambda_`の
  dual ascent、ceiling/window/hard_limit/eta のconfig化、既存Mahoragaデフォルト値を初期値として採用）
  を移植する。WEEKLY、THE SYSTEM SHALL `weekly_spend_by_loop()`（REQ-CEO-021）の返り値を全loop分
  合算した会社全体の当該週spend合計（1つのfloat）を `BudgetPacer.update()` に1回渡し、更新後の
  `lambda_` を REQ-CEO-010 の reward 計算（各loopのreward計算にはREQ-CEO-021の同じ
  `weekly_spend_by_loop()`が返すその loop 自身の週次spendを使う——company全体の`lambda_`という
  1つの重みを、loop固有の`weekly_spend_usd`というペナルティ対象に適用する）へ渡す。状態は
  `~/.anicca-founder/state/ceo-budget-pacer-state.json` に Mahoraga の `save`/`load` と同型の
  tmp書込→atomic renameで永続化する。**agent-os由来の月次hard-stop gate（REQ-CEO-020〜025）とは
  別レイヤーである** — agent-os側は「その月、その loop への新規資源投入を機械的に禁止する」ハード
  ゲート、Mahoraga BudgetPacerは「会社全体の週次spendがceilingに近づくほどbanditのrewardにソフトな
  コストペナルティをかける」重み付けシグナルであり、両者は重複ではなく異なる目的で共存する（この
  区別を明示することで、将来の実装者が「片方は不要」と誤解しないようにする）。

### C. token/USD 予算 gate（agent-os copy+tweak）

- **REQ-CEO-020（B11修正: 呼び出し主体とcadenceを確定。B12修正: scopeをloop-report.shフックが実在する
  6 loopに限定しpm-earnerを除外）**: **PER-LOOP-PASS**（roster内の各 earn loop自身の pass 終了時点、
  CEO の WEEKLY pass ではない — この REQ は REQ-CEO-058 の①〜⑫には含まれない、INV-CEO-2の
  「副作用REQは①〜⑫に配置」の対象外である理由をここに明示する）、THE SYSTEM SHALL 当該loopのその1
  passの実行コスト（token/USD 見積り、呼び出し元＝各 earn loop 自身の pass-end reporting フック）を
  `record_cost_event({ts, month_key(UTC), loop, usd_estimate})` として `~/.anicca-founder/state/
  ceo-cost-events.jsonl` に追記する（agent-os `record_cost_events` の単一loop・単一イベント版として
  copy+tweak、atomic 追記）。**呼び出し元は roster のうち clip/clip-promote/video/affiliate/gig/bounty
  の6 loop自身であり、CEOではない** — この6 loopは Ground truth 節で実ファイルを直接`grep`確認済みの
  とおり既に自分の pass 終了時に `loop-report.sh <loop> ...` を呼ぶ既存フックを持つ（clip/video/
  clip-promoteは`~/anicca/skills/earn/<loop>/<loop>-cli.sh`、affiliate/gig/bountyは
  `~/profitable-claude/skills/human-funded/<loop>/<loop>-cli.sh`のSTARTUP変数内）。この既存フックへ
  `record_cost_event` の呼び出しを1行追加する統合ポイントとして実装する（In scope節参照）。
  **pm-earnerはこのREQのscopeに含まれない** — `~/anicca/skills/earn/polymarket-trade/`配下を実際に
  `grep -rln "loop-report"`した結果0件であり（Ground truth節参照）、そもそもtmux STARTUP promptという
  概念を持たないLLMなしPythonスクリプト群のため「既存フックへの1行追加」という前提が成立しない
  ——pm-earnerのcost trackingはOut of scope節のとおり実装対象外とし、REQ-CEO-021が定める
  fallbackルールで扱う（Phase 1c iteration-6 adversary指摘B12の直接修正: 旧版はGround truthが
  「gig/affiliate/bountyが既に呼んでいる」という正しい主張をしながらパスを明記せず、かつ
  callerリストにpm-earnerを含めてしまっていたため、B11の"1行追加のみ"という前提がpm-earnerには
  成立しないという矛盾を見逃していた。team-lead指示により`~/profitable-claude`を含めて実際に
  6/7 loopのフック実在を確認し、pm-earnerのみ真に不在であることを確定させた）。CEO自身が各loopの
  コストを見積もることはできない——実際にpassを実行しているのは各loop自身であり、コストを知っている
  のもその loop 自身だけであるため、呼び出し元は必然的に各 loop）。
- **REQ-CEO-021（B12新設: pm-earnerのspendデータ恒久欠如に対するfallbackルール）**: THE SYSTEM SHALL
  `monthly_spend_by_loop(cfg, month_key)` で `ceo-cost-events.jsonl` を UTC 暦月境界で loop ごとに
  集計する（agent-os `monthly_spend_by_agent` の `agent`→`loop` 読み替え、ロジック無変更、budget
  hard-stop gate REQ-CEO-022/023 が使う）。THE SYSTEM SHALL 加えて `weekly_spend_by_loop(rows,
  week_start_jst_date) -> dict[str, float]`（新設・純粋: `ceo-cost-events.jsonl` の各行の `ts` を
  JST 週（月〜日）でバケット化して loop ごとに合算、`weekly_report.py::_rows_in_week` と同じ週境界
  バケット化パターンを再利用）を実装し、REQ-CEO-010（per-loop reward 分母）と REQ-CEO-014（company
  全体の`BudgetPacer.update()`入力、全loop分を合算した1つの週次総額）が使う。**fallbackルール
  （B12: REQ-CEO-020のscopeからpm-earnerが除外された結果、`ceo-cost-events.jsonl`にpm-earner分の
  行が恒久的に存在しないことへの明示的な対処）**: `monthly_spend_by_loop()`/`weekly_spend_by_loop()`
  の戻り値dictにpm-earnerのキーは存在しない（他loopと同様、データが無いloopをゼロ埋めしたキーとして
  作らない、既存の集計ロジック無変更のまま自然にこうなる）。これを読む側は`dict.get(loop, 0.0)`で
  デフォルト0として扱う（新規分岐の追加ではなく、Pythonのdict既定動作をそのまま使うだけ）。結果:
  (a) REQ-CEO-010の`compute_reward(realized_earn_usdc, weekly_spend_usd=0.0, lambda_)`は既存定義
  「`weekly_spend_usd>0`の場合`earn/spend`、そうでなければ`earn`そのもの」により`base=
  realized_earn_usdc`をそのまま使う（ゼロ除算耐性は既存仕様のまま、pm-earner固有の特別分岐を新設
  しない）。(b) REQ-CEO-022の`filter_budget_compliant_loops`は`spend_by_loop`に無いloopをspend=0として
  扱う既存のfail-open fallback（REQ-CEO-023と同型）により、pm-earnerは当月hard-stop超過判定が
  常にfalseになる——pm-earnerはbudget hard-stop gateの対象外になるが、これはcost trackingが無い
  ことのfail-openな直接帰結であり、新たな例外分岐ではない。(c) REQ-CEO-014の`BudgetPacer.update()`
  へ渡す会社全体の週次spend合計は、pm-earner分（常に0）を含めて他loop分をそのまま合算するだけで
  （`weekly_spend_by_loop()`に無いキーは合算に寄与しない=0を足すのと同義）、既存の合算ロジックに
  一切変更を要さない。
- **REQ-CEO-022**: WEEKLY の allocation 書込（REQ-CEO-040）の直前、THE SYSTEM SHALL
  `filter_budget_compliant_loops(candidate_loops, cfg, month_key)`（agent-os
  `filter_budget_compliant_agents` の copy+tweak）を呼び、当月 hard-stop 超過の loop を
  **新規の資源増加（double-down）候補から除外**する。hard-stop 超過は loop の稼働自体を止めない
  （既存の allocation を維持したまま増額のみ拒否 — 完全停止は cadence/scale-down の判断とは別軸）。
- **REQ-CEO-023（B7反映: 実行位置をREQ-CEO-058ステップ③に明記）**: `~/.anicca-founder/state/
  ceo-budget-config.json` が存在しない、または該当 loop の entry が無い場合、THE SYSTEM SHALL その
  loop を unlimited（gate なし）として扱う（fail-open、agent-os `budget_for_agent` が `None` を
  返すケースと同型）。この fail-open が発生したことをログに一度だけ記録する（`warn_if_budgets_missing`
  相当、プロセス非常駐のため「一度だけ」はログファイル内に既に同種の行が無いことのチェックで実現
  する）。**この判定とログ記録は REQ-CEO-058 ステップ③（毎pass無条件実行、rollback発火pass・
  cooldown中passを含む）で行う**（INV-CEO-2の完全配置要求への対応、Phase 1c iteration-4 adversary
  指摘B7の直接修正: 当月spend状況の把握は「今週allocationを変更するかどうか」とは独立した観測行為
  であるため、REQ-CEO-010/014と同じく無条件実行にする——budget状況は行動を決める前提情報であり、
  行動そのものではない）。
- **REQ-CEO-024（B7反映: 実行位置を明記）**: THE SYSTEM SHALL soft-warn / hard-stop の mail 通知を
  `(month_key, loop, threshold_name)` の組ごとに **最大1回**だけ `loop-report.sh` 経由で送る
  （`check_budget_alerts` の dedup key パターンを copy+tweak、fired key は `ceo-budget-alerts.jsonl`
  に永続化）。**この mail 送信は REQ-CEO-058 ステップ③で行う**（REQ-CEO-023 と同じ位置、同じ理由で
  無条件実行——mail送信はファイル書込ではなく別チャネルのため、INV-CEO-2の「loop-registry.json単一
  書込」制約の対象外）。
- **REQ-CEO-025（B7反映、B9修正: queueではなく自己完結したローカル戻り値を返す）**: THE SYSTEM SHALL
  `remaining_budget()`/`is_hard_stopped()`（agent-os copy+tweak）を `budget_snapshot()` 相当の
  ダッシュボード向け構造で算出し、`budget_snapshot_for_registry(cfg, loop, spend) -> dict`（新設・
  純粋、無変更）の出力を、roster全loop分まとめた**この REQ 自身のローカルな戻り値**
  `budget_snapshot_by_loop: dict[str, dict]`（`{loop: budget_snapshot_for_registry の出力, ...}`）
  として返す（この REQ 自身は `loop-registry.json` への直接I/Oを一切行わない、共有可変状態への
  書込も一切行わない——INV-CEO-2により実I/OはREQ-CEO-044の1箇所に一元化されるため）。**この
  `budget_snapshot_by_loop` は、REQ-CEO-058 ステップ⑨で `build_next_registry()`〔REQ-CEO-044〕へ
  名前付き引数としてそのまま渡される** — Phase 1c iteration-4 adversary指摘B7、iteration-5
  adversary指摘B9の直接修正: iteration-4版は`registry_updates`という複数ステップが共有する可変dict
  へ`registry_updates[loop]["budget"]`のように書き込む「queue」方式だったが、この方式は⑥（rollback
  復元）が同じ共有dictへ異なる粒度（loop全体dict単位）で書き込むと③-cのbudget queueが消えるという
  新たな欠陥（B9）を生んだ。この版はそもそも共有可変状態を持たず、各ステップが完全にローカルで
  完結した戻り値を返し、それらをステップ⑨の1関数だけが最後に組み立てる——「どのqueueが後から来た
  queueを上書きするか」という問い自体が発生しない構造。**この算出はREQ-CEO-058 ステップ③で行う**
  （REQ-CEO-023/024と同じ位置、同じ理由で無条件実行）。

### D. double-down / 縮退の実行

- **REQ-CEO-030（M4修正: capital_increase gateへUSD換算後の値を渡す）**: 実収益(週次)>0 かつ週次
  evaluation score が閾値超 の loop について、THE SYSTEM SHALL agent が「倍賭け」を選んだ場合、その
  実行手段は以下のいずれかを allocation テーブルへの書込という決定論ツールで表現する: (a) pass 頻度
  up（`pass_frequency_multiplier` を1超に設定）、(b) 資本上限 up（`capital_cap_usd` を増額、増額量は
  当該 loop の直近実現 realized profit の範囲内 — design spec のguardrail「資本増額は on-chain 検証済み
  realized profit の範囲内」を機械チェックする純関数 `capital_increase_within_realized_profit(new_cap,
  old_cap, realized_profit_usd) -> bool` を設ける。**この第3引数`realized_profit_usd`には、当該loopの
  `ledger_earn_entries`（REQ-CEO-002(c)）を REQ-CEO-050 の `realized_profit_usd(entries, fx_config) ->
  float` に通した後のUSD換算済みの値を必ず渡す** — JPY建てloop（gig/affiliate）の生のJPY金額を無変換
  で渡すと、USD建ての`capital_cap_usd`と比較する際にガードレールが`fx_config["jpy_usd_rate"]`倍
  （デフォルト設定で約150倍）緩くなる、Phase 1c iteration-2 adversary指摘M4の直接修正）、(c) fleet
  サイズ増（`fleet_size_target` を増やす、ただし REQ-CEO-031 の gate を通過した場合のみ書込を許可）。
- **REQ-CEO-031**: fleet サイズ増を allocation テーブルに書く前に、THE SYSTEM SHALL
  `guardrails.scale_eligible(streak, weekly_score, threshold, disk_free_gb)` かつ
  `guardrails.cooldown_ok(last_spawn_ts, now_ts, min_interval_days)` かつ NOT
  `guardrails.fleet_at_capacity(current_count, max_count)` の3つ全てを満たすことを確認する
  （既存 guardrail 純関数の再利用、条件式の再実装禁止）。1つでも false なら fleet 増加は
  allocation テーブルに書かれない（現状維持）。
- **REQ-CEO-032（m3反映: consecutive_bad_weeksの永続化先を明示）**: 週次 evaluation score が2週連続で
  0以下、または `beats_previous_week` が2週連続 false の loop について、THE SYSTEM SHALL agent が
  「縮退」を選んだ場合、`pass_frequency_multiplier` を1未満に下げる。それでもなお改善しない場合
  （さらに次の週も同条件）、THE SYSTEM SHALL 当該 loop の `status` を `"paused"` に設定する
  （`is_ban_suspected` と同型の閾値パターンを流用可能だが、ban疑いとは独立したフィールドとして扱う）。
  `should_scale_down`（REQ-CEO-032実装関数）が入力に取る`consecutive_bad_weeks`は、
  `loop-registry.json`の各loopエントリ内の**`"consecutive_bad_weeks"`という専用サブキー**（`"allocation"`/
  `"budget"`と同階層の per-loop カウンタ）に永続化する。更新後の値は REQ-CEO-040 の
  `allocation_decisions[loop]["consecutive_bad_weeks"]` として返され、REQ-CEO-044の
  `build_next_registry()`が非破壊マージで保持する対象キーの1つとなる（Phase 1c iteration-2
  adversary指摘m3の反映:
  `ceo-miss-streak.json`は会社全体の`consecutive_miss_count`専用であり、loop単体のこのカウンタとは
  別物・別ファイル）。
- **REQ-CEO-033**: THE SYSTEM SHALL 縮退・pause の実行として loop の skill/config ファイルを
  削除する処理を一切実装しない（design spec「削除しない」の直接遵守、`status:"paused"` は
  `loop-registry.json` 上のフラグに過ぎない）。
- **REQ-CEO-034**: `status:"paused"` へ変更した場合、THE SYSTEM SHALL 理由（該当週の score/realized
  profit の実データ）を `~/.anicca-founder/state/ceo-lessons.jsonl` に1行追記する（`{ts, loop,
  action:"paused", reason, evidence}`、判断は agent、記帳は決定論）。

### E. allocation テーブルの loop-registry.json への書込

- **REQ-CEO-040（B7反映、B9修正: queueではなく自己完結したローカル戻り値を返す）**: THE SYSTEM SHALL
  ⑧-cでagentが決定した WEEKLY の allocation テーブル（loop ごとの `token_budget`,
  `pass_frequency_multiplier`, `capital_cap_usd`, `fleet_size_target`, `status`）と
  `consecutive_bad_weeks`（REQ-CEO-032）を、roster全loop分まとめた**この REQ 自身のローカルな戻り値**
  `allocation_decisions: dict[str, dict]`（`{loop: {"allocation": {...}, "consecutive_bad_weeks":
  ...}, ...}`、⑧の条件分岐が false だったloop・その週agentが何も決定しなかったloopはキー自体を
  含まない）として返す（この REQ 自身は `loop-registry.json` への直接I/Oを一切行わない、共有可変
  状態への書込も一切行わない）。**この`allocation_decisions`は、REQ-CEO-058 ステップ⑨で
  `build_next_registry()`〔REQ-CEO-044〕へ名前付き引数としてそのまま渡される**（Phase 1c
  iteration-4 adversary指摘B7、iteration-5 adversary指摘B9の直接修正——REQ-CEO-025と同じ設計原則:
  共有可変アキュムレータへのqueueをやめ、各ステップが完全にローカルな戻り値を返すだけにする）。
- **REQ-CEO-041**: `loop-registry.json` が存在しない場合、THE SYSTEM SHALL 空 `{}` として扱い
  bootstrap する（クラッシュしない、record-earn.mjs の「初回はcursor初期化のみ」と同型のfail-safe）。
- **REQ-CEO-042**: THE SYSTEM SHALL allocation テーブルの各数値フィールド（`pass_frequency_multiplier`
  等）に対し、config で定義された妥当範囲（例: 頻度倍率 0.1〜10、資本上限は REQ-CEO-030(b)の
  realized-profit範囲内チェック）を外れる値を`allocation_decisions`へ含める前に reject する（決定論
  ゲート、agent の入力ミスや暴走した数値が無条件でそのまま資源配分に反映されることを防ぐ）。
- **REQ-CEO-043**: THE SYSTEM SHALL この feature の実装コミットが `apps/landing/**` を一切変更しない
  （dashboard-sync=Dais owned の既存書込制限を維持、loop-registry.json は claude-p 自身の body内）。
- **REQ-CEO-044（B7新設、B9修正: アキュムレータではなく単一組立関数への名前付き引数渡し）**: THE
  SYSTEM SHALL `build_next_registry(existing_registry: dict, budget_snapshot_by_loop: dict[str, dict],
  rollback_restore: dict[str, dict] | None, allocation_decisions: dict[str, dict]) -> dict`（新設・
  純粋: roster内の各loopについて、`next_registry[loop] = {**existing_registry.get(loop, {}), "budget":
  budget_snapshot_by_loop.get(loop, existing_registry.get(loop, {}).get("budget")),
  "allocation": (rollback_restore[loop]["allocation"] if rollback_restore and loop in
  rollback_restore else allocation_decisions.get(loop, {}).get("allocation",
  existing_registry.get(loop, {}).get("allocation"))), "consecutive_bad_weeks":
  allocation_decisions.get(loop, {}).get("consecutive_bad_weeks",
  existing_registry.get(loop, {}).get("consecutive_bad_weeks"))}`という**明示的な優先順位**で
  1回の計算により組み立てる——`existing_registry`の他キー（`fleet`/`account_list`等、将来 task #13
  の spawner が書く）はそのまま保持。**優先順位の根拠**: `rollback_restore`が非`None`のloopに対して
  は必ずそのloopの`"allocation"`を最優先で使う（REQ-CEO-058⑧の条件分岐により、`rollback_restore`が
  非`None`のpassでは`allocation_decisions`は構造的に空——⑥と⑧-cが同一pass内で両方非空になることは
  ない、B6修正で既に保証済み——が、この関数自身も優先順位を明示することで、万一の想定外呼び出しに
  対しても安全側〔rollback優先〕に倒れるフェイルセーフとする）。4引数全てを一度に受け取り、
  1回の計算で`next_registry`全体を組み立てるため、「どのステップの書込が後から来た書込を上書き
  するか」という共有可変状態の内部マージ順序問題（Phase 1c iteration-5 adversary指摘B9）が構造的に
  発生しない——複数ステップが同じ可変dictへ時間差で書き込むという仕組み自体が存在しないため。
  `merge_allocation`（旧`"allocation"`単体置換関数）はこの関数の内部ロジックの一部として吸収され、
  独立した公開関数としては不要になる。THE SYSTEM SHALL `build_next_registry()`の結果を tmp書込→
  atomic rename で `~/.anicca-founder/state/loop-registry.json` に1回だけ書く。**この書込が、
  `loop-registry.json`への1 WEEKLY pass あたりの唯一のI/O書込である**（REQ-CEO-025/040/053を含む、
  `loop-registry.json`の内容を決めるいかなるREQも、このREQ以外の場所で直接I/Oを行わない、
  INV-CEO-2参照）。実行位置は REQ-CEO-058 ステップ⑨（Phase 1c iteration-4 adversary指摘B7・
  iteration-5 adversary指摘B9の直接修正）。

### F. CEO 自己検証 loop（machine-checkable）

- **REQ-CEO-050（M1修正: 通貨変換してから合算、M3/M4修正: 変換を1つの共有関数に集約）**: THE SYSTEM
  SHALL次の2段の純関数を実装する。① `convert_to_usd(amount, currency, fx_config) -> float`（新設・
  純粋: `currency=="usd"`なら`amount`そのまま、`currency=="jpy"`なら`amount / fx_config["jpy_usd_rate"]`）。
  ② `realized_profit_usd(entries: list[{amount,currency}], fx_config) -> float`（新設・純粋:
  `entries`の各要素に`convert_to_usd`を適用し合算するだけ——`entries`は1件の loop の
  `ledger_earn_entries`（REQ-CEO-002(c)の`sum_earn_by_currency`出力、通常2件: usd分・jpy分）を渡す
  想定だが、任意件数の`{amount,currency}`リストに対して汎用的に動く）。**この`realized_profit_usd()`
  が、loopの実収益をUSDへ変換する唯一の共有経路である** — INV-CEO-1が列挙する全ての`_usd`/`_usdc`型
  パラメータ（company_score算出〔本REQ〕、REQ-CEO-030(b)の資本ガードレール、REQ-CEO-010の
  `compute_reward`の`realized_earn_usdc`）がこの同じ関数を呼ぶ（Phase 1c iteration-2 adversary
  指摘M4「M1の修正がcompany_score以外の呼び出し箇所に伝播していない」、iteration-4 adversary指摘B8
  「M5修正で新設されたREQ-CEO-010呼び出し箇所に伝播していない」への直接対応: 変換ロジックを個々の
  呼び出し箇所に別々実装するのではなく、1つの共有関数を全呼び出し元が使うことで「一部だけ直して
  別の箇所を直し忘れる」再発を、この列挙とINV-CEO-1という2重の明記で構造的に防ぐ）。WEEKLY、THE
  SYSTEM SHALL
  `company_score(week) = Σ(roster内の各loopの`realized_profit_usd(その loop の
  ledger_earn_entries, fx_config)`)`（**`-weekly.jsonl`の`combined_score`ではなく**、REQ-CEO-002(c)
  由来の実収益をUSD換算してから loop 横断で合算——`combined_score`をそのまま合算すると gig/affiliate
  のJPY建て金額と他loopのUSD建て金額が無変換で混在し、company_scoreの週次変動が実際の会社業績と
  無関係にJPY建てloopの規模に支配されてしまうため — Phase 1c iteration-1 adversary指摘M1の直接修正。
  各loop自身の週次`beats_previous_week`判定（`weekly_report.py`の既存出力、REQ-CEO-002(b)）はこの
  変更の影響を受けない、`combined_score`自体は無変更）を算出する。`fx_config`は
  `~/.anicca-founder/state/ceo-fx-config.json`（`{"jpy_usd_rate": <float>}`、agentが定期更新、
  不在時はfallback rate 150.0を使い一度だけfail-openログを出す — REQ-CEO-023と同型のパターン）から
  読む。算出した`company_score`を`beats_previous_week(this_week_company_score,
  prev_week_company_score)`（既存`weekly_compare.py`をそのまま呼ぶ）で前週と比較する。
- **REQ-CEO-051（フィールド拡張、m5修正: rollback用フィールドを統合しcanonicalな単一行にする）**: THE
  SYSTEM SHALL 比較結果を `{ts, week_start, prev_week_company_score, this_week_company_score,
  beats_previous_week, allocation_change_ref, consecutive_miss_count, cooldown_weeks_remaining,
  rollback_fired, rolled_back_to_week}` として `~/.anicca-founder/state/ceo-verification.jsonl` に
  **1 pass につき1行**追記する（`rolled_back_to_week`は`rollback_fired==true`の場合のみ値を持ち、
  そうでなければ`null`）。**このREQ-CEO-051の1行が`ceo-verification.jsonl`への唯一のcanonical書込
  である** — REQ-CEO-053(b)が独立に別行を追記することはない（Phase 1c iteration-3 adversary指摘m5
  の直接反映: rollback発火passで2つの異なるschemaの行が入りうる曖昧さを、1行に統合することで解消）。
  実際の追記タイミング・値はREQ-CEO-058ステップ⑪で確定する。
- **REQ-CEO-052（B3修正 + m4反映: streak中はスナップショットを凍結、shapeを明示）**: THE SYSTEM SHALL
  `should_snapshot(consecutive_miss_count, cooldown_weeks_remaining) -> bool`（新設・純粋:
  `consecutive_miss_count == 0 and cooldown_weeks_remaining == 0` のときのみ true——REQ-CEO-058の
  ステップ順序により、この2引数は常に「このpassの START 時点の値（`cooldown_weeks_remaining_in`等）」
  を渡す）が true の場合**のみ**、`loop-registry.json`への実I/O書込（REQ-CEO-058ステップ⑨、
  `build_next_registry`によるこのpass唯一の書込）が起きる前に、現在（＝このpassでまだ
  一度も書き換えられていない、ディスク上の）allocation テーブル全体を `~/.anicca-founder/state/
  ceo-rollback.json` に atomic 書込でスナップ
  ショットする。**スナップショットの shape** は `{<loop>: {"allocation": {...}}}` ——
  `loop-registry.json`の各loopエントリのうち`"allocation"`サブキーのみを含む wrapper 付き dict
  （`loop-registry.json`のtop-level構造と同型、`"budget"`/`"consecutive_bad_weeks"`等の他サブキーは
  含まない、PROP-CEO-014bのfixture shapeと一致——Phase 1c iteration-2 adversary指摘m4の反映）。
  miss-streak が進行中（`consecutive_miss_count >= 1`）または rollback cooldown 中
  （`cooldown_weeks_remaining > 0`）は `ceo-rollback.json` を **上書きしない** — streak/cooldown が
  始まる直前の「最後に良好だった allocation」を保持し続ける（旧版の「毎週無条件スナップショット」
  だと、2週連続miss判定の直前に1週目の失敗済みallocation自身で上書きされてしまい、rollback先が
  既に悪化済みの状態になる——Phase 1c iteration-1 adversary指摘B3の直接修正）。
- **REQ-CEO-053（B3修正: rollback発火判定 + consecutive_miss_countリセットのみ、cooldown値の設定は
  REQ-CEO-058に一元化）**: THE SYSTEM SHALL `should_rollback(consecutive_miss_count,
  cooldown_weeks_remaining, threshold=2) -> bool`（新設・純粋: `cooldown_weeks_remaining == 0 and
  consecutive_miss_count >= threshold` のときのみ true——cooldown中は`cooldown_weeks_remaining`が
  0でないため構造的に必ずfalseになる、これがcooldown中の再発火防止の**直接の**メカニズムである。
  REQ-CEO-056参照）が、そのpassの START 時点の値（`consecutive_miss_count`はREQ-CEO-054適用後の
  今週分、`cooldown_weeks_remaining`は`cooldown_weeks_remaining_in`）に対して true の場合、
  `restore_from_rollback(rollback_snapshot) -> dict[str, dict]`（新設・純粋: `ceo-rollback.json`の
  スナップショット（`{<loop>: {"allocation": {...}}}`形）をそのまま恒等的に返すだけの橋渡し関数）を
  呼び、その出力を**この REQ 自身のローカルな戻り値** `rollback_restore`（B9修正: `registry_updates`
  への「queue」ではなく、REQ-CEO-025/040と同じ設計原則で完全にローカルな戻り値として扱う）とする
  （この REQ 自身は `loop-registry.json`への直接I/Oを一切行わない）。**`rollback_fired_this_pass`が
  false の場合、`rollback_restore`は`None`とする**（REQ-CEO-044の`build_next_registry()`が
  `rollback_restore is not None`で判定する）。**この`rollback_restore`は、REQ-CEO-058 ステップ⑨で
  `build_next_registry()`〔REQ-CEO-044〕へ名前付き引数としてそのまま渡される**（Phase 1c
  iteration-4 adversary指摘B7、iteration-5 adversary指摘B9の直接修正）。これによりREQ-CEO-052で
  保護された「既知良好」スナップショットが、このpassの`loop-registry.json`書込内容として確定する。
  この`ceo-rollback.json`は、REQ-CEO-052の凍結ポリシーにより streak開始前の状態のまま保たれている
  ため、直前に失敗した`A_bad1`ではなく実際に良好だった配分が復元される。rollback実行時、THE SYSTEM
  SHALL `consecutive_miss_count`を0にリセットする。**
  `ceo-verification.jsonl`への追記は、このREQでは行わない** — `rollback_fired`/`rolled_back_to_week`
  は REQ-CEO-051 の単一行スキーマのフィールドとして、REQ-CEO-058 ステップ⑪で他のフィールドと
  まとめて1回だけ書かれる（Phase 1c iteration-3 adversary指摘m5の直接反映: rollback発火時とpass終了時
  で別々にファイルへ書込む2アクションを持たない、書込は常にステップ⑪の1箇所のみ）。**
  `cooldown_weeks_remaining`の値そのものの設定（アーム）も、このREQではなく REQ-CEO-058 の
  `next_cooldown_weeks_remaining()`が同一pass内で唯一の場所として一元的に行う**（Phase 1c
  iteration-2 adversary指摘B4「REQ-CEO-053がcooldownを1に設定し、REQ-CEO-055が同一pass末尾で
  無条件decrementして0に戻す競合」の直接修正: cooldownの値の書き込み箇所を1箇所に集約し、
  「設定してから同じpass内で打ち消す」という順序依存のバグそのものを構造的に無くす）。
- **REQ-CEO-054（B5修正: miss count更新規則、cooldown中は「そのまま返す」——0への強制リセットではない）**:
  THE SYSTEM SHALL `update_miss_count(prev_count, beats_this_week, cooldown_weeks_remaining) -> int`
  （新設・純粋: `cooldown_weeks_remaining > 0`なら**`prev_count`をそのまま変更せず返す**（cooldown中は
  凍結——0への強制リセットではない。REQ-CEO-053のrollbackアクションが`consecutive_miss_count`を0に
  リセットするのはrollback発火**時点**の別のアクションであり、cooldown週に入った**後**の
  `update_miss_count`呼び出しはその0を維持するだけ、という関係。Phase 1c iteration-2 adversary
  指摘B5の直接修正: 旧版は本文が「0のまま据え置く」、PROP-CEO-014が`prev=1→1`とテストしており矛盾
  していた。この関数は任意の`prev_count`を受け付ける汎用純関数として「そのまま返す」の1ルールに
  統一する——`prev=0`でも`prev=1`でも、cooldown中は入力をそのまま返すという単一の契約）、そうで
  なければ`beats_this_week`がtrueなら`0`、falseなら`prev_count + 1`）を WEEKLYごとに1回、
  `cooldown_weeks_remaining_in`（そのpassのSTART時点の値、REQ-CEO-058参照）を渡して呼ぶ。結果は
  REQ-CEO-058のステップ順序に従って`~/.anicca-founder/state/ceo-miss-streak.json`へ永続化する。
- **REQ-CEO-055（B4修正: allocation決定skipの判定はSTART時点のcooldown値を使う、decrementは
  REQ-CEO-058に一元化。B7/B9反映: 「書込」ではなく「決定」をスキップする表現に統一、共有アキュム
  レータへのqueueという概念自体が廃止されたため）**: WHILE `cooldown_weeks_remaining_in > 0`（その
  passが START した時点で既にcooldown中だった場合——このpass自身がREQ-CEO-053でrollbackを発火させた
  場合は含まない、発火passはstartの時点では`cooldown_weeks_remaining_in == 0`だったのでこの条件には
  当てはまらず、REQ-CEO-058のステップ順序により発火pass自身の⑧-a〜⑧-e〔agentのallocation決定〕も
  別途skipされる）、THE SYSTEM SHALL ⑧-a〜⑧-e（REQ-CEO-022/011/030/031/032/034/060によるbudget-gate/
  guardrail/agent決定/pause/escalation）を**スキップ**し、`allocation_decisions = {}`（空dict）とする
  （rollbackで復元した、または前週から不変の既知良好状態をそのまま維持する——REQ-CEO-044の
  `build_next_registry()`が`allocation_decisions`に無いloopの`"allocation"`は`existing_registry`の
  値をそのまま使う）。REQ-CEO-058ステップ③（bandit/
  BudgetPacer/budget監視、REQ-CEO-010/011/014/023/024/025）と④（company_score算出・記録）と⑫
  （mail報告、REQ-CEO-080）はcooldown中も通常どおり実行する（配分は変えないが、観測と報告は
  止めない）。**`cooldown_weeks_remaining`の次passへの値の決定（decrement
  を含む）はこのREQでは行わない——REQ-CEO-058が唯一の場所として担う**（Phase 1c iteration-2
  adversary指摘B4の直接修正: 旧版は「各WEEKLY passの最後に無条件でdecrement_cooldownを呼ぶ」と
  書いており、REQ-CEO-053が同一pass内で直前にセットした値をそのまま打ち消してしまっていた）。
- **REQ-CEO-056（B3新設、B5修正で根拠を訂正: cooldown中のrollback再発火防止の直接メカニズム）**: WHILE
  `cooldown_weeks_remaining_in > 0`、`should_rollback`（REQ-CEO-053）は**その関数自身の条件式
  `cooldown_weeks_remaining == 0 and ...`**により構造的に必ずfalseを返す（REQ-CEO-054の
  `update_miss_count`がcooldown中に何を返すかとは無関係に、`should_rollback`自身の第2引数チェックが
  再発火を防ぐ——Phase 1c iteration-2 adversary指摘B5を踏まえ、根拠を「miss_countが0に凍結される
  から」ではなく「`should_rollback`自身のcooldown条件」に訂正）。cooldown終了後
  （`cooldown_weeks_remaining`が0に達した週）から通常のmiss-count更新・rollback判定が再開する。
  これにより「同じ既に悪い状態を繰り返し復元し続けるlivelock」（Phase 1c iteration-1 adversary
  指摘B3の懸念）は起きない——rollback先は常にREQ-CEO-052で保護された唯一の既知良好スナップショット
  であり、cooldown中は誰もそれを上書きしない。
- **REQ-CEO-057（B3新設: 状態の永続化場所の一元化）**: THE SYSTEM SHALL
  `consecutive_miss_count`/`cooldown_weeks_remaining`の読み書きを`~/.anicca-founder/state/
  ceo-miss-streak.json`の1ファイルに一元化する（REQ-CEO-052〜058すべてがこの1ファイルを読み書きする
  唯一の場所とし、複数ファイルへの分散書込による不整合を避ける）。ファイル不在時は
  `{consecutive_miss_count:0, cooldown_weeks_remaining:0}`として扱う（REQ-CEO-041と同型のbootstrap
  fail-safe）。
- **REQ-CEO-058（B4新設、B6/M5/B7/B8/B9修正: WEEKLY pass の実行順序を決定論的に1箇所で定義し、
  set-then-decrement競合・rollback-pass上書き・順序未配置REQ・loop-registry.json二重書込・アキュム
  レータ内部マージ順序未定義を構造的に無くす。全ての副作用REQの実行位置を漏れなく明示——INV-CEO-1/
  INV-CEO-2の実装）**: THE SYSTEM SHALL 各 WEEKLY pass を以下の**固定順序**で実行する（EARSの他REQ群
  はこの順序内の1ステップとして解釈する。順序自体をこのREQ1箇所に集約し、他REQの記述から実行順序を
  逆算させない。**B9修正: `registry_updates`という複数ステップが共有する可変アキュムレータは廃止した
  ——各ステップは自分自身のローカルな戻り値だけを返し、それらは全てステップ⑨の1関数だけが最後に
  受け取って組み立てる**、道A/team-lead指示2026-07-08）。

  **①** `ceo-miss-streak.json`から`consecutive_miss_count_in`/`cooldown_weeks_remaining_in`を読む
  （このpassでこれ以降変更されるまでの「START時点の値」として固定、REQ-CEO-057）。

  **②** roster snapshot読み取り（REQ-CEO-002〜004）。各loopについて`sum_earn_by_currency()`
  （REQ-CEO-002(c)）で`ledger_earn_entries`を得る。

  **③（M5新設、B7/B8修正: 毎pass無条件で走る「観測・学習」ステップ。budget系REQをここに配置）** 
  roster内の各loopについて次を**このpassの`cooldown_weeks_remaining_in`や後続の
  `rollback_fired_this_pass`の値に関わらず、rollback発火pass・cooldown中passを含む毎WEEKLY passで
  無条件に**実行する（実現ROI/spend/budget状況という「今週実際に起きた実測データの観測」は、今週
  allocationを変更するかどうかとは独立した別の関心事であるため——②のsnapshotが揃った時点でのみ
  依存し、③以降のどのステップの結果にも依存しない）:
    - **③-a** `realized_profit_usd(ledger_earn_entries, fx_config)`（REQ-CEO-050）でUSD換算後の
      実収益を算出し、`compute_reward(realized_earn_usdc=この値, weekly_spend_usd, lambda_)`
      （REQ-CEO-010、**`realized_earn_usdc`には必ずこのUSD換算後の値を渡す、生の`ledger_earn_entries`
      合計や`combined_score`を渡さない——INV-CEO-1、Phase 1c iteration-4 adversary指摘B8の直接修正**）
      → bandit `update(context, loop, reward)`（REQ-CEO-011）を呼ぶ。
    - **③-b** 会社全体の当該週spend合計を`BudgetPacer.update()`（REQ-CEO-014）に通す。
    - **③-c（B7新設: REQ-CEO-023/024/025の実行位置を明記。B9修正: ローカル戻り値を返すだけ）**
      `budget_for_loop`/`remaining_budget`/`is_hard_stopped`（agent-os copy+tweak）で当月budget状況を
      判定し、config/entry不在なら unlimited扱い+fail-openログを一度だけ記録（REQ-CEO-023）。
      soft-warn/hard-stop閾値到達なら`(month_key,loop,threshold_name)`ごと最大1回のmail送信
      （REQ-CEO-024、mail送信は別チャネルのためINV-CEO-2の書込一元化制約の対象外）。roster全loop分の
      `budget_snapshot_for_registry()`の出力をまとめた**このステップのローカルな戻り値**
      `budget_snapshot_by_loop: dict[str, dict]`を得る（実I/Oはしない、REQ-CEO-025。共有可変状態への
      書込も一切しない——他のどのステップの結果にも書き込まない、書き込まれもしない）。

  **④** `company_score`算出（③-aで各loop分計算済みの`realized_profit_usd()`値をloop横断で合算する
  だけ、二重計算しない）・`beats_previous_week`判定（REQ-CEO-050）。

  **⑤** `consecutive_miss_count_new = update_miss_count(consecutive_miss_count_in, beats_this_week,
  cooldown_weeks_remaining_in)`（REQ-CEO-054）。

  **⑥（B9修正: ローカル戻り値を返すだけ）** `rollback_fired_this_pass = should_rollback
  (consecutive_miss_count_new, cooldown_weeks_remaining_in, threshold=2)`（REQ-CEO-053）。true なら
  `restore_from_rollback(rollback_snapshot)`を呼び、その出力を**このステップのローカルな戻り値**
  `rollback_restore`とする（false の場合`rollback_restore = None`）+ `consecutive_miss_count`を0に
  リセット（REQ-CEO-053。**`ceo-verification.jsonl`への書込はここでは行わない**、REQ-CEO-051のとおり
  ステップ⑪で1回のみ。実I/Oはしない、共有可変状態への書込も一切しない）。

  **⑦** `cooldown_weeks_remaining_next = next_cooldown_weeks_remaining(cooldown_weeks_remaining_in,
  rollback_fired_this_pass, rollback_cooldown_weeks=1) -> int`（新設・純粋、この1関数が
  `cooldown_weeks_remaining`の次passへの値を**唯一**決定する: `rollback_fired_this_pass`が true
  なら`rollback_cooldown_weeks`（デフォルト1）をそのまま返す（この pass 自身では減算しない）。
  false かつ`cooldown_weeks_remaining_in > 0`なら`decrement_cooldown(cooldown_weeks_remaining_in) =
  max(0, cooldown_weeks_remaining_in - 1)`を返す。それ以外（false かつ
  `cooldown_weeks_remaining_in == 0`、通常運転）は`0`を返す）。

  **⑧（B6修正: 正式条件に`not rollback_fired_this_pass`を追加。B9修正: ローカル戻り値を返すだけ）**
  THE SYSTEM SHALL `cooldown_weeks_remaining_in == 0 and not rollback_fired_this_pass`（**この論理積
  そのものが正式条件——`cooldown_weeks_remaining_in == 0`だけでは不十分**: `should_rollback`自身の
  定義〔REQ-CEO-053〕により`rollback_fired_this_pass`が true になり得るのは必ず
  `cooldown_weeks_remaining_in == 0`の場合に限られるため、旧条件はrollback発火passを一切除外できず、
  ⑥で確定した`rollback_restore`をこの直後に⑧が今週のagent決定で上書きしてしまっていた——Phase 1c
  iteration-3 adversary指摘B6の直接修正。以下のサブステップ⑧-a〜⑧-eは、この論理積が true の場合
  **のみ**実行され、false の場合（cooldown中、またはこのpass自身がrollbackを発火させた場合の
  いずれか）は⑧全体を**丸ごとスキップ**し、`allocation_decisions = {}`（空dict）とする——rollback
  発火pass自身については⑥の`rollback_restore`が既にこのpassのallocationテーブル内容を兼ねており、
  ⑧の通常判断はしない/してはならない）なら次を順に実行する: **⑧-a**
  `filter_budget_compliant_loops`（REQ-CEO-022、③-cで判定済みのbudget状況を再利用）で当月hard-stop
  超過loopをdouble-down候補から除外。**⑧-b** bandit UCBスコア（または Thompson サンプル値）を算出し
  agent に提示（REQ-CEO-011、書込ではなく表示、REQ-CEO-012の「最終判断はagent」原則）。**⑧-c**
  agentがguardrail triad（REQ-CEO-031: `scale_eligible`/`cooldown_ok`/`fleet_at_capacity`）と
  capital gate（REQ-CEO-030(b)、`realized_profit_usd()`でUSD換算後の値を通す——INV-CEO-1）を踏まえて
  double-down/縮退を判断（REQ-CEO-030/032）し、決定した`allocation`と更新後の`consecutive_bad_weeks`
  を、行動した各loop分まとめた**このステップのローカルな戻り値**`allocation_decisions: dict[str,
  dict]`（REQ-CEO-040）とする（実I/Oはしない、共有可変状態への書込も一切しない）。**⑧-d** 縮退が
  pauseに達する場合は`status`を`allocation_decisions`へ含め + lessons記録（REQ-CEO-034、
  `ceo-lessons.jsonl`への実書込——`loop-registry.json`とは別ファイルのためINV-CEO-2の対象外）。
  **⑧-e** fleet増/tier引き上げのescalationがあれば`ceo-escalations.jsonl`へスキーマゲート付きで
  記録（REQ-CEO-060、該当する場合のみ、`ceo-escalations.jsonl`も別ファイルのためINV-CEO-2の対象外。
  記録するfield`weekly_realized_profit_usd`は③-aで計算済みの`realized_profit_usd()`値をそのまま使う
  ——INV-CEO-1、B10修正）。加えて`should_snapshot`判定（REQ-CEO-052、この判定に渡す2引数も①の
  START時点の値）が true なら`ceo-rollback.json`への実atomic書込（`loop-registry.json`ではなく
  専用の別ファイルのためINV-CEO-2の「単一書込」制約の対象外——スナップショット保存はallocation本体
  の書込とは別の関心事）。

  **⑨（B7新設、B9修正: アキュムレータではなく③/⑥/⑧の3つのローカル戻り値を直接受け取る単一組立
  関数、loop-registry.jsonへの単一書込点、INV-CEO-2の実装）** THE SYSTEM SHALL `build_next_registry
  (existing_registry, budget_snapshot_by_loop, rollback_restore, allocation_decisions)`
  （REQ-CEO-044、③-cの`budget_snapshot_by_loop`・⑥の`rollback_restore`・⑧の`allocation_decisions`
  という3つの**独立したローカル変数**を明示的な名前付き引数としてそのまま渡す——共有可変状態を
  経由しない、B9の直接反証）を1回呼び、結果を tmp書込→atomic rename で `loop-registry.json` に書く。
  **このステップが、`loop-registry.json`への1 WEEKLY passあたりの唯一のI/O書込である**（③-c/⑥/⑧の
  ローカル戻り値——budget/rollback復元後のallocation/agent決定後のallocationと
  consecutive_bad_weeks——が、すべてこの1回の書込にまとめて反映される）。

  **⑩** `ceo-miss-streak.json`へ`{consecutive_miss_count: (rollback_fired_this_passならば0、
  そうでなければconsecutive_miss_count_new), cooldown_weeks_remaining: cooldown_weeks_remaining_next,
  last_updated_week}`をatomic書込（この1回の書込がこのpassの状態変更の確定操作、REQ-CEO-057の
  一元化ファイルへの唯一の書込点）。

  **⑪** `ceo-verification.jsonl`へ REQ-CEO-051 の単一行を追記（`rollback_fired`/
  `rolled_back_to_week`は⑥の結果、`consecutive_miss_count`/`cooldown_weeks_remaining`は⑩で確定した
  値を記録——ステップ⑥では追記しない、m5修正）。

  **⑫** mail報告（REQ-CEO-080）。

  この順序でrollback発火 pass（week N、agentの今週の判断が仮に⑧-cまで走っていたら`A_good`とは
  異なる`A_bad3`を書いていたはずのケースを想定）を①→⑫の順に追跡すると: ⑥で
  `rollback_fired_this_pass=true`となり`rollback_restore = {A_good全loop分}`（ローカル変数）が確定
  する→⑦で`cooldown_weeks_remaining_next=1`が計算される（このpass内では未減算）→⑧の条件式
  `cooldown_weeks_remaining_in==0 and not rollback_fired_this_pass`は`True and not True = False`
  （このpassは`cooldown_weeks_remaining_in`単体は0だが`rollback_fired_this_pass`が true のため
  条件全体はfalse）となり、⑧-a〜⑧-eは**一切実行されない**、`allocation_decisions = {}`（空dict）の
  まま→`A_bad3`は計算すらされない（B6の直接反証: この振る舞いは⑧の正式条件そのものから導かれ、
  末尾の説明文に頼っていない）→⑨で`build_next_registry(existing_registry, budget_snapshot_by_loop,
  rollback_restore={A_good全loop分}, allocation_decisions={})`が呼ばれ、`rollback_restore`が非
  `None`のloopは全て`"allocation"`に`A_good`が優先的に採用され（`allocation_decisions`が空でも
  優先順位上、rollback側が最優先のため`A_bad3`が混入する余地が構造的にない）、`budget_snapshot_
  by_loop`の`"budget"`も**同じ1回の呼び出し**に含まれて`loop-registry.json`へ書き込まれる
  （B9の直接反証: `budget`が消えることも`A_bad3`が混ざることもない、単一関数の単一計算のため
  「後から来た書込が先の書込を上書きする」という順序依存の問い自体が発生しない）→⑩で
  `cooldown_weeks_remaining=1`が確定書込される。翌週（week N+1）: ①で`cooldown_weeks_remaining_in=1`
  を読む→⑥は`cooldown_weeks_remaining_in!=0`なので`should_rollback=false`（再発火しない、
  `rollback_restore=None`）→⑦で`decrement_cooldown(1)=0`が計算される→⑧の条件式は
  `False and ... = False`（`cooldown_weeks_remaining_in=1≠0`のため）なので引き続き⑧-a〜⑧-eは
  スキップされ`allocation_decisions={}`→⑨で`build_next_registry`が`rollback_restore=None`・
  `allocation_decisions={}`で呼ばれ、`"allocation"`は`existing_registry`（＝前週書き込まれた
  `A_good`）の値がそのまま維持され、`"budget"`のみ③-cの最新値に更新される→⑩で
  `cooldown_weeks_remaining=0`が確定書込される。週N+2では`cooldown_weeks_remaining_in=0`かつ
  `rollback_fired_this_pass=false`（通常、missが溜まっていなければ）なので⑧の条件式が true になり
  通常運転（allocation決定）が再開する。

### G. token guardrail（Anthropic 警告: 単純作業を高コスト multi-agent に流さない）

- **REQ-CEO-060（m2反映: スキーマゲートは承認ではないことを明記。B10修正: weekly_realized_profit_usd
  のUSD経由を明記）**: agent が loop の double-down 手段として「fleet 増（新規 core/instance 複製）」
  や「モデル tier 引き上げ」等の multi-agent/高コスト化を検討する場合、THE SYSTEM SHALL その決定を
  `~/.anicca-founder/state/ceo-escalations.jsonl` に `{ts, loop, escalation_type, justification,
  weekly_realized_profit_usd}` として記録する。**`weekly_realized_profit_usd`には、当該loopの
  `ledger_earn_entries`（REQ-CEO-002(c)）を REQ-CEO-050 の `realized_profit_usd(entries, fx_config)`
  に通した後のUSD換算済みの値を必ず渡す**（REQ-CEO-058ステップ③-aで既に計算済みの値をそのまま
  再利用するだけで新規計算は不要、INV-CEO-1の対象——Phase 1c iteration-5 adversary指摘B10の直接
  修正: `_usd`と名の付くこのjsonlフィールドがINV-CEO-1の列挙から漏れていた。`weekly_realized_
  profit_usd`が生のJPY値のまま記録されると、REQ-CEO-062のクロスチェックが参照する監査証跡が
  JPY建てloopで約`fx_config["jpy_usd_rate"]`倍狂う）。`justification` フィールドが空文字列の記録は
  スキーマ違反として reject する（決定論ゲート — 何を justification として書くかは agent の判断、
  「書かれていること」自体の強制のみコード化）。**このスキーマゲート自体は escalation を許可・
  実行するものではない** —
  fleet増/tier引き上げの実際の許可は REQ-CEO-031 の gate（`scale_eligible`/`cooldown_ok`/
  `fleet_at_capacity`）が担い、同じ意思決定パスから呼ばれる。`validate_escalation_schema() ==
  true` を「実行してよい」の十分条件と誤解しないこと（Phase 1c adversary指摘m2の反映）。
- **REQ-CEO-061**: THE SYSTEM SHALL `justification` の妥当性（内容が正しいか）を判定しない
  （LLM-as-judge も正規表現による内容判定も実装しない — 「理由を書く」というプロセスの強制のみが
  決定論の役割、内容の当否は agent 自身とその後の self-verification loop（REQ-CEO-050〜053）が
  実収益で事後検証する）。
- **REQ-CEO-062**: THE SYSTEM SHALL `weekly_realized_profit_usd` が 0 以下の loop に対する
  fleet増/tier引き上げの escalation record が REQ-CEO-031 の gate（scale_eligible 等）を素通り
  していないことを、`ceo-escalations.jsonl` と `loop-registry.json` の allocation 履歴を突き合わせる
  検証（Phase 3 adversary が確認）で担保する（コード側は REQ-CEO-031 の既存 gate を呼ぶのみ、
  二重実装しない）。

### H. 既存 founder-loop / ledger 不変条件の非破壊

- **REQ-CEO-070（B2修正: `exit "$RC"`より前に挿入、RC≠0でも実行される）**: THE SYSTEM SHALL
  `founder-loop.sh` の既存 money-wake ロジック（`record-earn.mjs` 呼び出し、`STATE.md` atomic 書込、
  `loop-report.sh founder ...` 呼び出し、INV-H1〜H6）を一切変更しない。CEO pass（`ceo/ceo-pass.sh`）
  呼び出しは、既存ロジックが完了した**後**、かつ **`founder-loop.sh`実ファイルの最終行`exit "$RC"`
  （現行73行目）より前**に挿入する——「末尾に追記」とは物理ファイルの最後の1バイトの後という意味
  ではなく、スクリプトの制御フローが`exit`する直前という意味である（Phase 1c adversary指摘B2の
  直接修正: `$RC`はrecord-earn.mjsの終了コードで、RPC失敗/ledger破損はINV-H6のコメントが明示する
  非稀パスであり、`exit "$RC"`の後にCEO pass呼び出しを置くとその度にCEO loop全体が無言でdead code
  になる）。CEO pass 自身の成否は既存の`exit "$RC"`が最終的に返す終了コードを一切変更しない
  （INV-H6「recorderのrcをcadenceへ伝播する」契約を保つ——CEO passはこの`exit`の直前に割り込む
  追加ステップであり、`RC`変数そのものを書き換えない）。既存の `RECORD`/`LEDGER` 変数・
  `record-earn.mjs` 呼び出し箇所は変更しない。
- **REQ-CEO-071（m1修正: private symbol import を避ける）**: THE SYSTEM SHALL CEO pass の WEEKLY
  処理（bandit更新・allocation書込・self-verification）を JST 週の月曜1回だけトリガーする
  （founder-loop.sh の wake がより高頻度でも重複実行しない）。判定は純関数
  `is_ceo_weekly_due(last_ceo_run_jst_date, today_jst_date) -> bool` とする。この関数は
  `weekly_report.py::_week_start`（module-private、アンダースコア始まりで他モジュールからの import
  を意図していない）を直接 import せず、同一の月曜起点ロジック（`date - timedelta(days=date.weekday())`）
  を `ceo/allocator.py` 内に**再導出**し、docstring に「`weekly_report.py::_week_start`と等価な週境界
  定義」であることをコメントで明記する（週境界定義を1箇所の決定論ロジックに保ちつつ、private symbolの
  cross-module importという壊れやすい依存を避ける——Phase 1c adversary指摘m1の反映）。
- **REQ-CEO-072**: THE SYSTEM SHALL `record-earn.mjs` を CEO pass から一切呼ばない・import しない
  （唯一のledger writerという既存契約、INV-H2 を CEO 側からも守る）。
- **REQ-CEO-073**: THE SYSTEM SHALL CEO pass が読む各 loop の metrics ledger／`-weekly.jsonl` を
  読み取り専用でオープンする（書込モードで開かない、既存 evaluator 群の「読み取り専用」契約と同一）。

### I. 報告（mail evidence）

- **REQ-CEO-080（grep確認: INV-CEO-1対象外の理由を明記）**: WEEKLY の CEO pass 完了後、THE SYSTEM
  SHALL `loop-report.sh ceo <summary> <result> <company_realized_profit_summary> <evidence>` を1回
  呼ぶ。`summary` には少なくとも「今週の会社全体 realized profit 合計」「double-down/縮退/pause した
  loop 一覧」「self-verification 結果（beats_previous_week / rollback有無）」を含める。
  **`company_realized_profit_summary`（`build_ceo_report_args`の`earned_usdc`相当、既存
  `report-args.mjs::founderReportArgs`と同型の`loop-report.sh`呼び出し引数）は、④で算出済みの
  `company_score`（REQ-CEO-050、既にUSD換算済み）をそのまま文字列化するだけであり、生の
  `ledger_earn_entries`から独自に再計算することは一切ない**（Phase 1c iteration-5 adversary指摘B10
  を受けたspec全文`_usd`/`_usdc` grepの一環として確認: この値はINV-CEO-1の列挙対象外——`realized_
  profit_usd()`を新たに呼ぶ入力口ではなく、既に安全な`company_score`を下流でそのまま使うだけの
  reporting stepであるため）。
- **REQ-CEO-081**: `evidence` 引数は `~/.anicca-founder/state/ceo-verification.jsonl` の当該週の
  行への具体的なポインタ（ファイルパス + 該当行の `week_start` 値）とする。roster が空（loop が
  1つも無い）場合のみ `"none: no loops registered yet"` を使う（既存 `lr_valid_evidence` gate、
  REQ-LV-003 を満たす）。
- **REQ-CEO-082**: DAILY 軽量点検（REQ-CEO-003）は mail を送らない（WEEKLY のみが報告対象、
  design spec の「週次＋日次の軽い点検」のうち mail 報告は週次のみという解釈を明示する）。

## Non-functional constraints

- No dry run（`~/.claude/CLAUDE.md`）: Phase 3 の E2E evidence は実際の mail 送信・実際の
  `loop-registry.json`／`ceo-verification.jsonl` 書込でなければならない。
- 判断のハードコード禁止: どの loop を倍賭けするか、何を「改善」とみなすか、justification の当否は
  全て agent が判断する。この spec がコード化するのは「bandit のスコア計算式」「budget hard-stop の
  フィルタ」「cadence/guardrail 純関数の呼び出し」「記帳・書込・mail 送信」のみ
  （`~/.claude/rules/building-effective-ai-agents.md` 準拠）。
- 既存の fail-closed / fail-open 契約を弱めない: `record-earn.mjs`/`loop-report.sh` の既存契約は
  無変更。budget config 未設定・fx-config 未設定（REQ-CEO-050）は fail-open（agent-os と同型、
  CLAUDE.md「稼ぐ動作を止めない」設計思想と一致）。allocation の異常値は fail-closed（REQ-CEO-042）。
  rollback の再武装（cooldown、REQ-CEO-055/056）は fail-closed 方向（配分を変えず観測に留める）。
- 車輪の再発明禁止: `cadence.py`/`weekly_compare.py`/`ledger_metrics.py`/`guardrails.py` を
  re-implement しない、必ず import して呼ぶ。Mahoraga/agent-os のロジックは copy+tweak し、
  出典コメントを新設ファイルの docstring に残す。
