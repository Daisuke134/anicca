# gig-feasibility-volume — Spec Review Verdict (Phase 1c, iteration 4)

- **Reviewer**: fresh-context adversary（Builder 文脈なし、iteration-1/2/3 adversary 文脈なし、disk artifact + 実データのみで判定）
- **対象**: `specs/behavioral-spec.md`（REQ-GFV-001..024）+ `specs/verification-architecture.md`（PROP-001..038、required:true 32件／required:false 6件）
- **判定日**: 2026-07-08
- **総合判定**: **PASS**（blocking 0件、major 0件、minor 0件 — 次フェーズ〔vcsdd-tdd〕進行可）

## A. iteration-3 MAJOR-1 / minor-1 の解消確認（実照合）

### MAJOR-1（REQ-GFV-010 に対応する PROP が皆無だった件）— ✅ 解消

`verification-architecture.md` に `PROP-037`（Tier 0, grep-presence, required:true）・`PROP-038`（Tier 0, evidence-review, required:false）が新規追加され、両方とも REQ 列が `REQ-GFV-010` であることを§2テーブル該当行で確認した。

- **PROP 番号の完全性を自ら再カウント**: `grep -oE '^\| PROP-[0-9]+' verification-architecture.md` で §2 テーブル定義行を機械抽出 → `PROP-001`〜`PROP-038` が1個ずつ、ちょうど38件、欠番0・重複0で存在。両文書全体での `PROP-[0-9]+` 参照のユニーク集合も同じ38件と一致し、ダングリング参照ゼロを確認した。
- **§4 集計の再検算**: `required:true` 行を `grep -oE '\| true \|'` で機械カウント→**32件**、`required:false`（`| false`)→**6件**。32+6=38。§4 本文が主張する「required:true count = 32」「required:false ... 6 total, 38 PROPs overall」と完全一致。
- **REQ カバレッジの再検算**: `behavioral-spec.md` の `### REQ-GFV-\d+` 定義行を抽出→REQ-GFV-001〜024 の24件全存在を確認。`verification-architecture.md` 全体をスキャンし、REQ-GFV-001〜024 のうち一度も `REQ-GFV-XXX` として言及されないものが無いか python で集合差分を取った結果 → **missing = []**（全24件がカバーされている、REQ-GFV-010 も含め）。
- **§5 Traceability**: 「REQ-GFV-010→PROP-037/038 [added spec-review iteration-3 MAJOR-1 fix — this REQ previously mapped to zero PROPs, a gap the iteration-3 adversary found]」という記述が実際の§2テーブル行と整合していることを確認した。iteration-3 が指摘した「Every REQ maps to ≥1 PROP という主張自体が事実誤りだった」という自己矛盾も、この追加で解消されている。

**結論**: MAJOR-1 は実データ・実カウントで独立に再現確認でき、完全に解消している。

### minor-1（§0 の FUNNEL REPORT 記述が実 gig-cli.sh 構造と食い違う件）— ✅ 解消

`behavioral-spec.md` §0（iteration-3 CORRECTION 行、20行目）は、旧来の「FUNNEL REPORT は `do_improve` 分岐の外で無条件実行される」という断定を撤回し、「STARTUP prompt は自然文の1段落であり構造は100%パース可能ではない。FUNNEL REPORT の一文は "IF do_improve is true...: run IMPROVE STEP (B4)...Also run BOT-TO-BOT SHARE (B5)...Before that, run FUNNEL REPORT...THEN report by mail..." というブロックの内側にテキスト上現れ、B4/B5とグルーピングされているように読める（`do_improve` 分岐の外側と明確には言えない）」という、断定を避けた正確な記述に修正されている。

本セッションで実際に `~/profitable-claude/skills/human-funded/gig/gig-cli.sh`（Python で直接読み込み、正規表現ではなく文字列検索で該当箇所を抽出）を確認したところ、`do_improve` 節は次の構造だった:

```
IF do_improve is true (from STEP 0): run IMPROVE STEP (B4): ...
Also run BOT-TO-BOT SHARE (B5): ...
Before that, run FUNNEL REPORT (REQ-LV-015, deterministic, no judgment): python3 ~/profitable-claude/skills/human-funded/gig/funnel_report.py ...
THEN report by mail: run bash ~/a...
```

「IF do_improve is true」以降、明示的な「ENDIF」やそれに類する区切りが無いまま FUNNEL REPORT の一文がB4/B5と並んで現れており、spec の修正後記述（「同じ `do_improve` 条件節の内側にB4/B5と並んで現れる、外側と断定できない」）と実テキストの構造が完全に一致することを確認した。旧来の「毎パス無条件」という断定は実テキストのどこにも根拠が見当たらず、撤回は正しい判断である。

**結論**: minor-1 は実 gig-cli.sh の直接読み込みで解消を確認した。

## B. iteration-3 で PASS だった cadence 設計・iteration-1/2 解消済み項目の退行チェック（spot check）

| 項目 | 結果 | 根拠 |
|---|---|---|
| `cadence-contracts.json` の `gig` エントリ現状 | 退行なし（実装フェーズ前なので未変更が正しい） | `python3 -c "import json;..."` で実ファイルを読むと `kind:"row-exists"`, `source:"~/gig/gig-funnel.jsonl (REQ-LV-015)"` のまま — spec §0/REQ-GFV-023 が「現状はこう、これから変える」と記述する前提と一致。まだ Phase 2 (TDD/impl) に進んでいないので当然、変更されていれば逆におかしい |
| `cadence-evidence.py` の `gig` が共有 row-exists タプルに残っている | 退行なし（同上、未実装が正しい） | `grep -n "gig"` で `if loop in ("clip", "affiliate", "video", "gig")` が2箇所（181, 213行）に残存を確認。REQ-GFV-023 が実装時にこの `gig` を専用関数 `_gig_activity_event_dates` に移す、という記述と矛盾しない（Phase 1c=spec review であり、コードはまだ触っていない） |
| `applied.jsonl` の実行数 | 269→270→**271行**（本セッション時点） | `wc -l` で271行を確認。loop が稼働し続けているための自然増分であり、iteration-2/3 と同じ扱い（指摘事項としない） |
| PROP-001〜036（iteration-1/2/3 で解消済みの項目）の番号・内容 | 退行なし | 上記Aの再カウントで001〜038全件を機械確認済み、001〜036の内容もざっと目視で iteration-3 時点の記述から変更されていないことを確認（037/038追加以外の差分なし） |
| Dais 制約（AI開示文言の不在） | 退行なし | `grep -ni "disclos\|AI-use\|開示"` を再実行し、ヒットは §0 と §5 Non-goals の「以前のドラフトが誤って導入したが削除済み」という記述のみ（要件としての再混入なし）と確認 |
| regex/keyword judgment 混入なし | 退行なし | `grep -ni "re\.compile\|regex"` の全ヒットが「regexを使わない」という否定文脈のみであることを確認（新規のjudgment用regex導入なし） |

iteration-1/2 で既に解消確認済みの項目（PROP-029/030ダングリング、gig-cli.sh壊れたパス2箇所の現状記述、22-key fixture、68/91 price_jpy等）は iteration-3 verdict が「再確認不要」と判断済みであり、本 iteration でも§Aの機械的な全体再カウントに包含される形で矛盾が無いことを確認した（個別の再照合は行っていないが、全体のPROP/REQ集合演算に異常がないことがその健全性の代理指標になっている）。

## 1. Completeness — PASS

design doc の To-be 全項目（①〜⑦）は REQ-GFV-001〜024 に引き続きマップ済み。§6 cadence bar は iteration-2/3 の実データ検証で機能する設計になっていることが既に確認されており、本 iteration で新規に触れられた部分（REQ-GFV-010周り）もCompletenessの欠落ではなくTestability側の欠落だったことは iteration-3 の分類判断のままで問題ない。

## 2. Testability — PASS

**iteration-3 の MAJOR-1 は解消**（§A参照）。PROP-037（grep-presence, Tier 0）・PROP-038（evidence-review, Tier 0, lean上required:false）はいずれもPROP-021/028、PROP-034/035と同型の既存パターンを踏襲しており、新規に導入された検証手法ではない。他の全PROPも変更なく、テスト可能性の欠落は残っていない。

## 3. Consistency — PASS

PROP番号（001〜038、欠番0・重複0）・REQ番号（001〜024、全カバー）ともに§Aの機械的再カウントで整合を確認した。§5 Traceability の「every REQ maps to ≥1 PROP」という主張は、REQ-GFV-010の追加により今度こそ事実と一致している（iteration-3時点では事実誤りだったこの一文が、iteration-4時点では真になった）。§4の必須数集計（32 true / 6 false / 38合計）も実カウントと一致。

## 4. Reality-grounding — PASS

minor-1 の解消を実 gig-cli.sh 直接読み込みで確認した（§A参照）。`applied.jsonl` の行数増分（271行、本セッション時点）は loop 稼働中の自然な差分であり、10日間の実測日カバレッジの主張（PROP-036）に影響しない範囲の増分であることは iteration-2/3 と同じ性質（新規行は既存日付の追加行、または直近日への追加であり、10/10日カバーという主張を壊す方向の変化ではない）。

## 5. Agent-vs-code boundary — PASS

REQ-GFV-010/037/038 を含め、新規追加された内容も `category` フィールドの付与を agent judgment（どのカテゴリに合致するか）として定義しており、決定論コードは既存の集計・パース・ダングリング検出パターンの範囲に留まる。regex/keyword による feasibility/category 判定コードは依然として導入されていない。`~/.claude/rules/building-effective-ai-agents.md` に準拠。

## 6. Dais 制約遵守 — PASS

`grep -ni "disclos\|AI-use\|開示"` を再実行し、AI使用申告/独自加工要件が要件として再混入していないことを確認した（「以前のドラフトが誤って導入し削除済み」という記述のみ）。

## Summary

| 次元 | 判定 | blocking | major | minor |
|---|---|---|---|---|
| Completeness | PASS | 0 | 0 | 0 |
| Testability | PASS | 0 | 0 | 0 |
| Consistency | PASS | 0 | 0 | 0 |
| Reality-grounding | PASS | 0 | 0 | 0 |
| Agent-vs-code boundary | PASS | 0 | 0 | 0 |
| Dais 制約遵守 | PASS | 0 | 0 | 0 |
| **合計** | **PASS** | **0** | **0** | **0** |

**結論**: iteration-1〜3で発見された全findings（blocking 2件、major 4件、minor 4件、延べ）は本iterationまでにすべて実データ・実コード照合で解消を確認した。新規findingsはゼロ。この spec（`behavioral-spec.md` + `verification-architecture.md`）は Phase 1c を PASS し、次フェーズ（`vcsdd-tdd`、RED phase）に進行してよい。
