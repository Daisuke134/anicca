# Spec Review Verdict — claude-p-loop-verification (Phase 1c, iteration 1)

Reviewer: fresh-context adversary (no Builder context). Judged from disk artifacts only:
- `.vcsdd/features/claude-p-loop-verification/specs/behavioral-spec.md`
- `.vcsdd/features/claude-p-loop-verification/specs/verification-architecture.md`
- `docs/superpowers/specs/2026-07-08-claude-p-loop-verification-evidence-design.md`（設計正本）

全参照ファイル・シンボル（20+件）を Read/Grep/Bash で実ファイルに対して裏取りした（`ls`/`grep -n`/`python3 -c` によるJSON構造確認含む）。

## 次元別判定

| # | 次元 | 判定 | 根拠 |
|---|---|---|---|
| 1 | Completeness | PASS（minor 1件） | 設計正本の Goal1-5 / P0-1〜P0-7 / 検証アーキテクチャ表 / Cadence Contract(§H) / EDD(§I) / Dashboard(§J) / Loop Scaling(§K) / OpenClaw統合(§L) は全てEARS要件でカバー済み。Goal 6（E2E完了判定・fresh adversary PASS）のみ独立REQ-LV-xxxが無く、NFR一文とverification-architecture側のPROP-LV-013にのみ存在（F5、非blocking） |
| 2 | Testability | **FAIL** | REQ-LV-101の汎用`cadence_met(ledger_rows, today_jst_date, contract)`が、設計正本Cadence Contract表が定める7ループ中3ループ（bounty=増分ベース、founder-loop=STATE.md mtimeベース、pm-earner=複合contract）の判定基準を実際には実装できない（F1、blocking） |
| 3 | Consistency | **FAIL** | REQ-LV-100の「8 loop」という数え間違い（実際は7、clip-promoteを除外すると宣言しつつ「8」と書く）（F3、minor）。REQ-LV-120がclip-promoteを含む「8 loop」のdashboard statusをcadence_met()から取ると書くが、REQ-LV-100はclip-promoteをcadence contract対象外としており未定義（F2、major）。Ground truth節のgig-cli.sh パス記載が同一ドキュメント内の他節（In scope／REQ-LV-004）と矛盾し実ファイルシステムとも不一致（F4、minor、Reality-groundingとも重複） |
| 4 | Reality-grounding | FAIL（minor 1件） | 参照された実ファイル・関数・シンボル（loop-report.sh, self_heal.py, record-payout.mjs, record_earn.py, evolve.mjs, verify-loops.sh, verify-loops-audit.sh, healthcheck-runtime-loop.sh, self-fix.sh, founder-loop.sh, record-earn.mjs, healthcheck-lib.sh, evaluator.py, promote_gate.sh/py, telemetry-collect.sh, _instance_paths.sh, dashboard.json, jobs.json enabled=103件, gated.json, commission-watermark.json 等）は全て実在し記載どおりの挙動・シグネチャを確認できた。唯一の例外がF4（gig-cli.shパス誤記） |
| 5 | Agent-vs-code boundary | PASS | 全REQで「判断はagent、検証・記帳・mail送信のみ決定論コード」の境界が一貫して守られている。cadence_met/streak/scale_eligible/is_ban_suspected等は全て既記録済みfactの純粋な集計関数であり、新規judgmentのハードコードではない。evaluator.pyパターンのLLM judge不使用（Verifier's Law）も既存承認済みパターンのcopy+tweakで新規逸脱なし |

## 総合判定

**FAIL** — blocking finding 1件（F1）。

F1はCadence Contract（design spec Dais指示の核心機能、§H全体・REQ-LV-100〜104・REQ-LV-120・REQ-LV-135が依存）の中心関数が、それ自身が置き換えようとしている旧`fresh()`方式と同じ「アーティファクトの存在だけで健全と誤判定する」欠陥を、bounty/founder-loop/pm-earnerの3ループに対して形を変えて再導入しかねない、という意味で軽微ではない。Phase 2着手前に修正すべき。

F2（major）はF1修正と合わせて解決可能（clip-promoteのdashboard status定義を追加するだけ）。

blocking 0件・major 0件に収束すれば次のiterationでPASS相当と判断できる規模の修正。

## 修正後の再レビュー条件

1. F1: REQ-LV-101の入力を「ledger行の存在」から「loop種別ごとに何を"1回のcadence達成"とみなすか」を明示的に切り替えられる形に修正する（design spec Cadence Contract表の4種の判定基準――row-exists / increment / mtime / compound――を機械的に区別できるようにする）。
2. F2: REQ-LV-120（またはREQ-LV-100）にclip-promoteのdashboard status定義を追加する。
3. F3: REQ-LV-100の「8 loop」を「7 loop」に修正する。
4. F4: behavioral-spec.md Ground truth節のgig-cli.shパスを`~/profitable-claude/skills/human-funded/gig/gig-cli.sh`に修正する。
5. F5（任意、非blocking）: Goal 6にREQ-LV-xxxを新規採番するか、既存NFR文をそのREQとして明示的に格上げする。

---

## Findings（詳細）

### F1 — BLOCKING — cadence_met() の汎用シグネチャが3ループの契約基準を実装できない

**対象REQ**: REQ-LV-101, REQ-LV-100, REQ-LV-102, REQ-LV-103, REQ-LV-104, REQ-LV-120, REQ-LV-135（連鎖的に依存）

**問題**:
設計正本 §Cadence Contract表（`docs/superpowers/specs/2026-07-08-claude-p-loop-verification-evidence-design.md:56-72`）は、loopごとに判定基準が異なると明示している:

| loop | 判定（設計正本記載） |
|---|---|
| clip/affiliate/gig | 当日 ledger 行の存在 |
| bounty | `gated.json` の **checked 増分**（行の存在ではなく差分） |
| founder-loop | **STATE.md mtime** + ledger |
| pm-earner | 1 pass/時 + redeem確認/日（**2種の異なる単位の複合契約**） |

しかしREQ-LV-101は単一の汎用シグネチャ `cadence_met(ledger_rows, today_jst_date, contract) -> bool` を定義し、判定基準を「`today_jst_date`に該当する行が`ledger_rows`に1件以上存在するか」の一種類に固定している。

実ファイルで裏取りした結果、この不一致は実装上も実際に起きる:

- `~/anicca/skills/self/founder-loop/founder-loop.sh`（Read確認済み）は、`record-earn.mjs`が新規の外部USDC流入を検知できなかった場合でも**毎回STATE.mdを書き換える**（`last_wake_utc`が毎回更新される）が、`~/.anicca-founder/state/earn-ledger.jsonl`への追記は`record-earn.mjs`のINV-1〜7ゲートを通過した「実際の外部入金」があった時のみ発生する（コメント: "the ONLY writer of the ledger, with all anti-fake gates"）。つまり「1 pass/日」というfounder-loopのcadence契約は、ledgerの行の有無では判定できない（稼ぎがゼロの日でもpassは正常に実行されている）。REQ-LV-101をそのまま適用すると、稼ぎがない日は毎日falseになり、設計正本が意図した「1 pass/日」の充足条件（passが動いたか）と異なる基準（earnが発生したか）を測ることになる。
- `~/profitable-claude/skills/human-funded/bounty/state/gated.json`（存在確認済み）ベースの判定は、設計上「checked件数の**増分**」が基準。REQ-LV-016で新設する`bounty-funnel.jsonl`は**passのたびに1行追記**される（`{ts, pass_id, checked, survivors, ...}`）ため、boardが枯渇していて実際にはcheckedが増えていないpassでも当日行は存在してしまう。REQ-LV-101の「行の存在」判定をそのまま適用すると、checked増分ゼロの日でも`cadence_met=true`と誤判定されうる——これは今回の変更が置き換えようとしている旧`fresh()`方式（artifact存在だけで健全と誤判定する）と本質的に同じ欠陥を、増分ベースの契約に対して再導入する。
- pm-earnerの契約「1 pass/時 + redeem確認/日」は2つの異なる頻度・単位の複合条件であり、REQ-LV-100が例示するJSONスキーマ `{"cadence": "1/day", "unit": "reel", "boundary_tz": "Asia/Tokyo"}` は単一のcadence/unitペアしか表現できない。この複合契約をどう1つの`contract`引数にエンコードし、`cadence_met`がどう2条件のANDを取るのかが未定義。

**Severity**: blocking — Cadence Contractは本feature最大の目的（「7日前に投稿があるからOK」という旧stale判定の恒久修正、design spec Dais指示原文）であり、この中心関数の欠陥はその目的を部分的に無効化する。PROP-LV-020/021/022（verification-architecture.md）のテストケースも全て「行の存在」前提のfixtureしか書かれておらず、bounty/founder-loop/pm-earner固有のケースが欠落している。

**修正提案**:
`cadence_met`の入力を「loop種別ごとに何を1回の達成イベントとみなすか」を呼び出し元が選べる形にする。例:
- `cadence_met(event_dates: list[str], today_jst_date, contract) -> bool` とし、`event_dates`の中身は呼び出し元が用意する（clip/affiliate/gig=ledger行のtsから；bounty=checkedが前回より増加した行のtsのみ抽出；founder-loop=STATE.mdのmtime；pm-earner=passログのtsとredeemログのtsを別々に2回呼ぶ）。
- または、REQ-LV-101を「row-exists型4ループ（clip/affiliate/video/gig）」用の関数として明示的にスコープを絞り、bounty/founder-loop/pm-earner用に別々の新規REQ（`bounty_cadence_met`, `founder_cadence_met`, `pm_cadence_met`等）を追加する。
どちらの方向でもよいが、Phase 2着手前にspecへ反映すること。

### F2 — MAJOR — REQ-LV-120がclip-promoteのdashboard statusをcadence_met()に依存させているが、clip-promoteはcadence契約対象外

**対象REQ**: REQ-LV-120, REQ-LV-100

**問題**: REQ-LV-100は「8 loop（clip/affiliate/video/gig/bounty/pm-earner/founder-loop、**clip-promoteは...対象外**・現行の維持対象のまま）」と明記し、clip-promoteをCadence Contract（REQ-LV-101〜104）の対象から明示的に除外している。一方REQ-LV-120は「8 loop分の`{loop, type, account, status, streak, ...}`配列を書き出す。`status`は**REQ-LV-101の`cadence_met()`結果**」と規定しており、REQ-LV-040（clip-promoteを含む8ブロック）と同じ枠組みを流用しているためclip-promoteもこの8 loopに含まれる読み方が自然。しかしclip-promoteにはcadence contractが存在しないため`cadence_met()`の入力（`contract`）が未定義で、`status`をどう計算するかが規定されていない。

**Severity**: major — dashboard実装着手時に実装者が独自解釈をせざるを得ず、spec-drivenの意図に反する。

**修正提案**: REQ-LV-120にclip-promoteの`status`定義を追加する（例: `record-payout.mjs`のstatus:"recorded"行が当日存在するかを独立の判定基準として明記）。

### F3 — MINOR — REQ-LV-100の「8 loop」という数え間違い

**問題**: 「8 loop」と書きつつ列挙されているloop名は clip/affiliate/video/gig/bounty/pm-earner/founder-loop の**7個**であり、8個目（clip-promote）は同じ文の中で明示的に除外されている。正しくは「7 loop」。REQ-LV-040（clip-promoteを含む別の8-loopリスト）からの転記ミスと推測される。

**Severity**: minor。**修正提案**: 「8 loop」を「7 loop」に修正する。

### F4 — MINOR — Ground truth節のgig-cli.shパスが実ファイルシステムおよび同一ドキュメントの他節と矛盾

**問題**: behavioral-spec.md Ground truth節（62-63行目）は「`~/anicca/skills/human-funded/gig/gig-cli.sh`」と記載しているが、実ファイルシステム確認の結果`~/anicca/skills/human-funded/gig/`は**存在しない**（`ls`: "No such file or directory"）。実在するのは`~/profitable-claude/skills/human-funded/gig/gig-cli.sh`のみ（確認済み、`-rwxr-xr-x`）。同一ドキュメントの「In scope」節（73-78行目）とREQ-LV-004（105-108行目）、および設計正本自体（開発環境節）は、いずれも正しく`~/profitable-claude/skills/human-funded/{gig,affiliate,bounty}/*-cli.sh`と記載しており、Ground truth節のみが誤っている。

**Severity**: minor（実装の根拠となるIn scope節・REQ-LV-004は正しいため実害リスクは低いが、「実装確認済み」節の内部矛盾として記録に値する）。**修正提案**: Ground truth節62-63行目のパスを`~/profitable-claude/skills/human-funded/gig/gig-cli.sh`に修正する。

### F5 — MINOR（非blocking）— Goal 6に対応する独立REQが存在しない

**問題**: 設計正本のGoal 6（E2E完了判定・fresh-context adversary PASS）に対応する独立EARS要件がbehavioral-spec.mdに存在しない。Non-functional constraints節の一文とverification-architecture.mdのPROP-LV-013（「Goal 1/6 E2E」）でのみカバーされている。Goal 1-5がいずれも複数のREQ-LV-xxxに分解されているのに対し、Goal 6だけが非対称。

**Severity**: minor、非blocking（PROP-LV-013が実質的な検証手段を提供している）。**修正提案**: 新規REQ-LV-xxx（例: REQ-LV-019）としてGoal 6を明示的に採番するか、既存NFR文を正式なREQとして格上げする。

### サマリ表

| ID | Severity | 対象REQ | 一言 |
|---|---|---|---|
| F1 | blocking | REQ-LV-100〜104, 120, 135 | cadence_met()の汎用シグネチャがbounty/founder-loop/pm-earnerの契約基準を実装できない |
| F2 | major | REQ-LV-120, 100 | clip-promoteのdashboard status定義が未規定 |
| F3 | minor | REQ-LV-100 | 「8 loop」の数え間違い（正しくは7） |
| F4 | minor | Ground truth節 | gig-cli.shパスの内部矛盾（実在しないパスを記載） |
| F5 | minor | Goal 6 | 独立REQ未採番（PROP-LV-013でカバー済みのため非blocking） |
