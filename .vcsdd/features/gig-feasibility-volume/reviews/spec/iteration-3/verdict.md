# gig-feasibility-volume — Spec Review Verdict (Phase 1c, iteration 3)

- **Reviewer**: fresh-context adversary（Builder 文脈なし、iteration-1/2 adversary 文脈なし、disk artifact + 実データのみで判定）
- **対象**: `specs/behavioral-spec.md`（REQ-GFV-001..024）+ `specs/verification-architecture.md`（PROP-001..036、required:true 31件）
- **判定日**: 2026-07-08
- **総合判定**: **FAIL**（blocking 0件、major 1件〔新規〕、minor 1件〔新規〕 — iteration-2 の blocking-1 は実データで独立検証し解消確認。次フェーズ進行は不可だが、収束まであと僅か）

## A. iteration-2 BLOCKING-1（cadence 源の信頼性）の解消確認 — ✅ 解消（実データ独立検証）

本セッションで `~/gig/applied.jsonl`（現在270行 — spec記載の269行から1行増加。loop が本レビュー中も稼働中のため想定内のドリフトであり、指摘事項としない）を Python で独立に再パースし、spec/PROP が主張する挙動をゼロから再現した。

| 検証項目 | 結果 |
|---|---|
| `cadence-contracts.json`の`gig`エントリ現状 | `kind:"row-exists"`, `source:"~/gig/gig-funnel.jsonl (REQ-LV-015)"` — spec の前提記述と一致（実ファイル確認） |
| `cadence.py`の`row-exists`分岐 | `today_jst_date in evidence.get("event_dates", [])` — spec が主張する「`cadence.py`自体は無変更で済む」という設計が正しいことを実コードで確認 |
| `cadence-evidence.py`の共有tuple | `gather_evidence()`内 `if loop in ("clip","affiliate","video","gig")` を実際に確認。`_event_dates_from_ts_rows`は`isinstance(ts,(int,float))`のみ処理（**文字列ts=無視**）— これが REQ-GFV-021 の「既存の数値epoch専用パーサーを流用できず新規パーサーが要る」という根拠を裏付ける実コード証拠 |
| ISO8601/epoch 両対応 parser の妥当性 | spec と同一ロジック（`Z`サフィックス→`+00:00`置換、`fromisoformat`、JST変換）を自分で実装し270行に適用 → **string 259 / numeric 1 / missing 10 / 文字列だが unparseable 2**。spec本文の「258/269がISO文字列、1が数値epoch、10がnull/missing、2がunparseable」とほぼ完全一致（差分は前述の1行増加のみ） |
| **housekeeping行の除外が正しいか（false-positive/false-negativeの両方向）** | 独立に日別集計した結果、**実測10個のJST日全て（2026-06-29〜2026-07-08）に厳密一致`applied`/`replied`行が最低1つ存在** — false-negativeゼロを確認。`applied_0`（1件）、`no_action`（37件）、`0_new_applications*`系（13件）等のhousekeeping行は正しく除外され、false-positiveも確認されず |
| PROP-036の主張 | **実データで独立再現し、真であることを確認**（10/10日で正しい判定） |
| 追加で発見した実データの異常系（`status`キー自体が存在しない行が13件、`applied_at`等の別スキーマ） | 13件全てのrequestIdは既存の正規`status:"applied"`行と重複せず、日付は2026-07-01(9件)/2026-07-03(4件)に集中。しかしこの2日とも**別途正規`applied`/`replied`行が既に存在**しており、event_datesの判定結果に影響なし。これはREQ-GFV-022の Edge Case（「非厳密一致statusは実作業でも意図的にunder-count、PROP-036がゼロ化しないことを実データで保証」）が既に想定・受容している種類のリスクと同一であり、独立検証でもその保証が成立することを確認した（新規のblocking/majorとしない）|
| `listings.jsonl`未実装との整合 | `ls ~/gig/listings.jsonl` で不在を確認。ただし`applied.jsonl`単独で10/10日をカバーできているため、`listings.jsonl`がゼロでも cadence 判定は現状壊れない |

**結論**: iteration-2 の BLOCKING-1（`increment`方式が本番実態でfalse-negativeになる懸念）は、Builder の再設計（`row-exists`維持 + 源を`applied.jsonl`+`listings.jsonl`に変更 + 厳密一致vocabulary）で構造的に解消しており、かつ本セッションの独立再検証（fixtureではなく実270行の再パース）でも false-negative/false-positive いずれも発生しないことを確認した。**PASS。**

## B. iteration-1 解消済み項目の regression spot-check

| iteration-1 finding | 状態 | 根拠 |
|---|---|---|
| BLOCKING-1（PROP-029/030ダングリング） | ✅ 退行なし | `grep -oE 'PROP-[0-9]+'`でPROP-001〜036を機械抽出し集合演算：定義済み36件と全参照が完全一致、ダングリング0、ギャップ0。§4の`required:true=31`/`required:false=5`もカウント一致 |
| MAJOR-3（gig-cli.sh壊れたパス2箇所） | ✅ 未修正のまま現存（spec通り） | 実ファイル`gig-cli.sh`を`grep -o`で確認：壊れたprefix`~/anicca/skills/human-funded/gig/`が**厳密に2箇所**（STEP0のpassprep.py呼び出し + APPLY_RUNBOOK読み込み）、正しいprefixは`funnel_report.py`呼び出しの1箇所のみで既に正しい。REQ-GFV-024のAcceptance Criteriaが要求する「両方修正」のスコープと完全一致 — 現状は「未修正」が正しい前提であり、spec/PROP-033はこの現状を正確に記述している |
| minor-2/3（fixture key数、78/91→68/91） | ✅ 退行なし（iteration-2で既に確認済み、再確認不要と判断） | — |
| MAJOR-1（design doc §6 cadence bar） | ✅ 上記§A参照、解消確認 | — |

## C. 新規発見（iteration-3、iteration-1/2は未検出）

### [MAJOR-1, NEW] REQ-GFV-010（`applied`行への`category`付与）に対応するPROPが `verification-architecture.md` に一つも存在しない

`grep -n "REQ-GFV-010" verification-architecture.md` は **ゼロヒット**。§2 Proof Obligationsテーブルの36行のうち、`REQ-GFV-010`をREQ列に持つ行は皆無。§1 Purity Boundary Mapにも§3 Verification Strategyにも登場しない。

一方、`REQ-GFV-006`(PROP-008)、`REQ-GFV-007`(PROP-009)、`REQ-GFV-016`(PROP-021/035)、`REQ-GFV-018`(PROP-024/025)、`REQ-GFV-020`(PROP-028/034) など、同じ「STARTUP prompt のテキスト変更で担保される振る舞い型REQ」は必ず最低1つの grep-presence PROP（Tier 0）を持ち、REQ-GFV-016/020 のように iteration-1 で欠陥指摘されたものは evidence-review PROP（PROP-034/035）まで追加済みである。REQ-GFV-010 だけがこのパターンから外れ、**grep-presence PROPすら存在しない**。

REQ-GFV-010自身のAcceptance Criteria文（behavioral-spec.md:118）は「`funnel_report.py`の`consumption`（`uncategorized`バケツへの集約）が間接的なacceptance signalになる」と書いているが、これは PROP-012/014（REQ-GFV-011/012 向け）のfixtureテストがたまたま`category`欠落ケースを扱っているというだけで、「STARTUP prompt が新規`applied`行に`category`を書けと指示しているか」も「実際に post-ship の新規行がcategoryを持つか」も、どのPROPも直接検証していない。

さらに、これは §5 Traceability の主張自体を裏切る：「Every REQ-GFV-001..024 in `behavioral-spec.md` maps to ≥1 PROP-XXX above ... every other REQ maps to a Tier-0/Tier-1 PROP as listed. No REQ is left without a verification method」— この一文は REQ-GFV-010 に関して事実と異なる（Consistency 次元にも波及する自己矛盾だが、根本原因は Testability の欠落なので二重計上せず Testability 側の1件として扱う）。

**修正提案**（軽微、1〜2行のPROP追加で閉じる）:
- Tier 0 grep-presence PROP を1つ追加：「`gig-cli.sh`のSTARTUP prompt textが、新規`status:"applied"`行書き込み時に必ず`category`フィールドを含めるよう指示する文言を含む」（PROP-021/028と同型）。
- 可能なら evidence-review PROP も1つ（PROP-034/035と同型）：post-ship の実`applied.jsonl`新規行のcategory充足率をサンプル確認。
- §5 Traceability の「every REQ maps to ≥1 PROP」の主張を、REQ-GFV-010 の追加後に再検算して更新。

### [minor-1, NEW] §0 Reality check の「FUNNEL REPORTはdo_improve分岐の外で無条件実行」という記述が、実際のgig-cli.sh STARTUP文言の構造と食い違う可能性

本セッションで `gig-cli.sh` のSTARTUP変数を直接読んだところ、"Before that, run FUNNEL REPORT ..." の一文は、テキスト上は "IF do_improve is true (from STEP 0): run IMPROVE STEP (B4): ... Also run BOT-TO-BOT SHARE (B5): ... **Before that, run FUNNEL REPORT** ... THEN report by mail: ..." という並びの中に現れ、B4/B5と同じ`do_improve`条件節の内側にあるように読める（少なくとも、「do_improve分岐の外側」と断定できるほど明確に外側にあるようには見えない）。

これは iteration-2 が導いた結論（`gig-funnel.jsonl`をcadence源として使うのをやめ`applied.jsonl`+`listings.jsonl`に切り替える）の正当性そのものには影響しない — どちらの読み方でも「本来の期待発火回数（218回 or 約54回）に対し実際は1回」という激しい未発火という実測事実は変わらず、その根本原因調査はこの feature の Non-goals で明示的にスコープ外とされている。ただし §0 の「outside the `do_improve` branch」という断定は、将来この Non-goal（「なぜfunnel_report.pyが発火しないか」）に着手する別featureが読む際に誤誘導する可能性があるため、記述の正確性として指摘する。ブロッキングではない。

## 1. Completeness — PASS

design doc §6 cadence bar は§Aの通り実データで解消確認。REQ-GFV-010自体は存在し内容も妥当（欠落しているのはPROPのみ、REQそのものの欠落ではない）ため、Completenessではなく次項Testabilityの問題として分類した。

## 2. Testability — FAIL

**[MAJOR-1, NEW]** 上記C参照。REQ-GFV-010がverification-architecture.md中に一つのPROPからも参照されていない。他は全て良好（PROP-001〜036は全REQに対しfixture/grep/evidence-reviewのいずれかで具体的な検証手法を伴う）。

## 3. Consistency — PASS（軽微な波及あり）

PROP番号の整合性（§Aの通り再検証済み、ダングリング0・ギャップ0）は良好。§5 Traceabilityの「every REQ maps to ≥1 PROP」という一文はREQ-GFV-010に関して事実誤りだが、これはTestability側のMAJOR-1の帰結として扱い、Consistency側で別枠のfindingとしては計上しない（二重計上回避）。MAJOR-1修正時に併せて§5の文言も更新すること。

## 4. Reality-grounding — PASS（軽微な指摘1件）

§Aで実データ独立再検証によりPROP-036の主張が真であることを確認。housekeeping行の除外ロジック（false-positive/false-negative双方向）も実データで健全と確認。[minor-1, NEW]（do_improve分岐の内外に関する記述の精度）を除き、他の実測値（22-key fixture、68/91→変わらず、broken path 2箇所、正しいpath 1箇所）も全て再照合し一致した。

## 5. Agent-vs-code boundary — PASS

REQ-GFV-021〜023の新規決定論コード（timestamp parser、exact-match status vocabulary、event_dates集計）は全て既存のBUILD AGENTS RIGHT除外規定（固定machine形式のパース = 判断ではない）に該当し、regex/keywordによるfeasibility/category判断は依然として導入されていない。実コード（`cadence-evidence.py`の`_event_dates_from_ts_rows`が数値epochのみ処理し文字列を無視する既存実装）を読んでもこの境界に反する箇所はない。

## 6. Dais 制約遵守 — PASS

`grep -ni "disclos\|AI-use\|開示"`で両spec文書を再検索し、AI使用申告/独自加工要件の文言が依然として存在しないことを再確認した（削除済みという記述のみ、要件としての再混入なし）。

## Summary

| 次元 | 判定 | blocking | major | minor |
|---|---|---|---|---|
| Completeness | PASS | 0 | 0 | 0 |
| Testability | FAIL | 0 | 1 | 0 |
| Consistency | PASS | 0 | 0 | 0 |
| Reality-grounding | PASS | 0 | 0 | 1 |
| Agent-vs-code boundary | PASS | 0 | 0 | 0 |
| Dais 制約遵守 | PASS | 0 | 0 | 0 |
| **合計** | **FAIL** | **0** | **1** | **1** |

**次アクション（Builder向け、iteration-4で収束見込み）**:
1. [MAJOR-1] `verification-architecture.md`にREQ-GFV-010向けのPROPを最低1つ（grep-presence、Tier 0）追加し、可能ならevidence-review PROPも追加。§4のrequired:true/false集計と§5 Traceabilityの主張を更新後の実カウントに合わせて修正。
2. [minor-1] §0 Reality checkの「FUNNEL REPORTはdo_improve分岐の外」という記述を、実際のgig-cli.sh STARTUP文言の構造（do_improve条件節内にB4/B5と並んで現れる）と照合し、正確な表現に修正するか、断定を避けた表現に弱める（任意、blocking/majorではない）。
3. iteration-2のBLOCKING-1、iteration-1の全7項目は本iterationで実データ独立検証済みであり、再度の実データ照合は不要 — 次回はMAJOR-1の修正差分のみのフォーカスレビューで収束可能と判断する。
