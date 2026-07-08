# gig-feasibility-volume — Spec Review Verdict (Phase 1c, iteration 1)

- **Reviewer**: fresh-context adversary（Builder 文脈なし、disk artifact のみで判定）
- **対象**: `specs/behavioral-spec.md`（REQ-GFV-001..020）+ `specs/verification-architecture.md`（PROP-001..028、required:true 25件）
- **判定日**: 2026-07-08
- **総合判定**: **FAIL**（blocking 1件、major 4件、minor 2件 — 次フェーズ進行不可）

## 1. Completeness — FAIL

設計正本 To-be の①〜⑥はおおむね REQ にマップされている（①REQ-GFV-001/002/016、②REQ-GFV-004/005/006/012、③REQ-GFV-007、④REQ-GFV-003、⑤REQ-GFV-016、BP seed=REQ-GFV-018/019）。⑦は明示的に非スコープ（design doc §7 = task #20 別トラック、妥当）。

**[MAJOR-1] 設計正本⑥ EDD の「cadence（self-heal の bar）: 毎日『N件出品 or 応募したか』+ 全メッセージ確認したか。未達→self-fix」が実質未充足。**
根拠（本セッションで実ファイル確認）: `~/anicca/skills/self/cadence-contracts.json` の `gig` entry は `kind:row-exists`、`source: ~/gig/gig-funnel.jsonl` のみ。ところが `funnel_report.py::run()` は `~/gig/applied.jsonl` の**全履歴**を毎回 dedupe→summarize して `gig-funnel.jsonl` に1行追記する処理であり、かつ `gig-cli.sh` STARTUP は「FUNNEL REPORT」ステップを **do_improve 分岐の外・毎パス無条件**で実行する（`gig-cli.sh:21` 該当箇所: "Before that, run FUNNEL REPORT ... THEN report by mail"）。したがって「今日 実際に出品/応募が1件もなくても」行は必ず追記され、row-exists チェックは構造的に常に true になる（当日の活動有無を判定できない）。REQ-GFV-005/006（listings_due gate）・REQ-GFV-012（listings_live 追加）はこの cadence gate に一切接続されておらず、`§5. Non-goals` は「cadence-contracts.json の gig entry の row-exists check は REQ-GFV-012 で additive に満たされる」とだけ書いて、上記の「そもそも row-exists が無意味な当日判定である」事実を検証・言及していない。設計正本が明示的に要求する「未達→self-fix」の cadence bar を、この REQ 群は実質的に閉じていない。

## 2. Testability — FAIL

**[MAJOR-2] REQ-GFV-020（品質・自然さ = テンプレ未加工送信の禁止）に対応する PROP が grep 存在確認（PROP-028）のみで、要件の実体（個別化が実際に行われたか）を検証する PROP が皆無。**
verification-architecture.md §1 のテーブル自体は「verified by grep (clause presence) + real pass evidence (no verbatim-template sends observed)」と書いているが、この "real pass evidence" 部分に対応する PROP エントリが §2 のテーブルに存在しない（PROP-028 は grep のみ）。REQ-GFV-006（PROP-008）・REQ-GFV-007（PROP-009）・REQ-GFV-014（PROP-019）は同種の「振る舞い検証」を required:false の evidence-review PROP として明示的に用意しているのに、REQ-GFV-020 だけ実体検証の PROP が欠落している。design doc が「成約率とアカウント健全性のため」と明記する重要要件であるにもかかわらず、この REQ の受け入れ基準は事実上「プロンプト文言があるか」しか保証しない。

**[minor-1]** REQ-GFV-016（never-refuse）も PROP-021（grep のみ）で、実パスでの拒否理由の適合性を追う evidence-review PROP が無い（REQ-GFV-007 の PROP-009 で間接的に応募率トレンドはカバーされるが、「拒否理由が feasibility/違法以外でないか」を直接見る手段ではない）。MAJOR-2 ほどではないが同根の欠落。

**[minor-2]** REQ-GFV-002 の Acceptance Criteria 例示（「20 keys の fixture → 21 keys」）は、実在する `~/gig/strategy.json`（LIVE、pass_count=217）の実キー数と食い違う（実測 22 keys、下記 §4 参照）。fixture の一般化された "N keys" 自体は正しい書き方だが、§0 Reality check の説明文脈で使われる具体例が実データと不一致で紛らわしい。ブロッキングではない。

## 3. Consistency — FAIL

**[BLOCKING-1] verification-architecture.md §3「Verification Strategy」の Tier 0 リストが `PROP-029`, `PROP-030` を参照しているが、この2つは §2「Proof Obligations」テーブル（PROP-001〜PROP-028 のみ）に存在しない。**
該当箇所（§3）: 「Tier 0（...）: PROP-001, 004, 008 (partially — E2E), 013, 015, 017, 019 (evidence, not gate), 020, 021, 024, 025, 026, 028, **029, 030**.」— PROP-029/030 に対応する行が §2 テーブルにも §5 Traceability にも存在しない。ダングリング参照であり、§4「lean-mode required-obligation summary」が主張する「28 PROPs overall」という総数（PROP-001..028）とも矛盾する（Tier 0 リストは29件目・30件目の存在を前提にしている）。§5 Traceability は「no PROP references a REQ that does not exist」と主張するが、実際に起きている不整合はその逆（PROP番号が参照されているのに定義が存在しない）であり、この主張自体が誤り。この文書だけで実装・adversary フェーズに進むと、未定義の PROP-029/030 が何を指すか誰も判断できない。**要修正: §3 から PROP-029/030 を削除するか、意図された内容を §2 に PROP-029/030 として追加し §4/§5 の集計を再計算すること。**

他の整合性は良好: seed（`strategy.default.json`）と live（`~/gig/strategy.json`）の二重管理は REQ-GFV-002/003/009/019 + Non-goals で一貫して定義されており矛盾なし（seed のみ変更、live は fill-forward の追加キーのみ、既存の自己改善済み値=`max_applicants:12` 等は不可侵と明記）。`max_apply_per_pass=5` と「応募数最大化（1件絞り廃止）」も矛盾なし — REQ-GFV-007 が要求するのは「viable な request を cap まで全部埋める」ことであり cap 自体の引き上げではない。過保守スクリーニング（設計文書の診断）を feasibility 明確化（REQ-GFV-001）+ never-refuse（REQ-GFV-016）で解消する設計であり、cap 撤廃を主張していないため整合。

## 4. Reality-grounding — FAIL

**[MAJOR-3] スコープロック対象ファイル `gig-cli.sh` の STARTUP prompt 文字列自体に、実在しないパス参照が2箇所ある。この spec が同じ STARTUP 文字列を複数箇所（REQ-GFV-006/016/018/020）で編集する対象でありながら、この既存欠陥に一切触れていない。**
実機確認（本セッション、`ls`/`find` で検証）:
- `gig-cli.sh:21` STARTUP 内: `python3 ~/anicca/skills/human-funded/gig/passprep.py` — このパスは存在しない（`~/anicca/skills/human-funded/` ディレクトリ自体が無い）。実体は `~/profitable-claude/skills/human-funded/gig/passprep.py`。
- 同 STARTUP 内: `~/anicca/skills/human-funded/gig/scripts/coconala/APPLY_RUNBOOK.md` — 同様に存在しない。実体は `~/profitable-claude/skills/human-funded/gig/scripts/coconala/APPLY_RUNBOOK.md`。
`strategy.json` の mtime は本日（2026-07-08 20:30）で pass_count は増え続けており、LLM agent が実行時に自己修正して正しいパスを探し当てている可能性が高い（ハードコードされた決定論スクリプトではなく agent 実行のため）。ただし REQ-GFV-005（listings_due）・REQ-GFV-017（cold_start）・REQ-GFV-018（B4 の search+metrics 両輪）は全て「STEP 0（passprep.py）が吐く JSON を agent が正しく読む」ことに強く依存しており、STARTUP 文字列自身が指す passprep.py の呼び出しパスが壊れている事実を spec の §0 Reality check（`gig-cli.sh:21` を引用済みと主張）が見落としている。self-correction に頼る現状は保証ではなく、この spec が STARTUP を編集するタイミングで一緒に直すのが筋。

**[minor-3]** §0 Reality check の統計値に誤り: 「78/91 carry `price_jpy`」と記載されているが、本セッションで `~/gig/applied.jsonl` を実測した結果 `status:"applied"` 91行中 `price_jpy` を持つのは **68行**（`in` チェックでも truthy チェックでも同じ）。ブロッキングではないが、「verified this session, Read/grep」と明記されたテーブルの数値精度に疑問が残る。

以下は Reality-grounding として正しく確認できた（PASS 項目）: `strategy.default.json`／`passprep.py`／`funnel.py`／`funnel_report.py`／`run.sh` の `SETTLED`/`jnum()`／`~/anicca/skills/self/self-improve/gig/evaluator.py`／`~/anicca/skills/self/self-improve/lib/weekly_compare.py`／`~/anicca/skills/self/cadence-contracts.json`／`agent-reach` skill は全て実在し、spec が引用する挙動（skip-floor、`dedupe_latest_status`、`evaluate_stage1` のフォールバック分岐、sandbox-boundary コメント文言等）と一致。`~/gig/listings.jsonl` が未実装である点、および出品作成フローがコード上どこにも存在しない点も spec の記述通り正確（「1行変更」という誤認は見られない — Non-goals で「新規 `listings.py` モジュールは作らない、browser 駆動の agent 判断のまま」と明記されており、正しく new-implementation として扱われている）。

## 5. Agent-vs-code boundary — PASS

feasibility 判定（`ai_doable`/`ai_infeasible`）・カテゴリ選定・出品価格/tier・提案文言はすべて自然文の judgment input としてのみ定義され（§1「Judgment vs determinism boundary」に明記）、決定論コードは bootstrap/repair（`passprep.py`）・skip-floor・`listings_due`/`cold_start` の cadence boolean・funnel 集計（`funnel.py`）・evidence-ledger 存在確認・週次集計（`evaluator.py`）に限定されている。regex/keyword 配列で feasibility やカテゴリ適合を判定するコードパスは REQ 群のどこにも導入されておらず、`~/.claude/rules/building-effective-ai-agents.md`（BUILD AGENTS RIGHT）に準拠。findings なし。

## 6. Dais 制約遵守 — PASS

AI 使用の申告・AI 生成物への独自加工/disclosure に関する REQ・文言は両ドキュメントのどこにも存在しない。behavioral-spec.md §0 最終行および §5 Non-goals 最終項目に「以前のドラフトが誤ってこの種の要件を導入していたが、Dais の 2026-07-08 指示により削除済み」と明記されており、意図通り除去が確認できる。「違法/scam は skip」という文言（REQ-GFV-016）は許容範囲内。findings なし。

## Summary

| 次元 | 判定 | blocking | major | minor |
|---|---|---|---|---|
| Completeness | FAIL | 0 | 1 | 0 |
| Testability | FAIL | 0 | 1 | 2 |
| Consistency | FAIL | 1 | 0 | 0 |
| Reality-grounding | FAIL | 0 | 1 | 1 |
| Agent-vs-code boundary | PASS | 0 | 0 | 0 |
| Dais 制約遵守 | PASS | 0 | 0 | 0 |
| **合計** | **FAIL** | **1** | **3** | **3** |

**次アクション（Builder向け）**:
1. [BLOCKING-1] verification-architecture.md の PROP-029/030 ダングリング参照を解消（削除 or 定義追加＋§4/§5 再計算）。
2. [MAJOR-1] cadence gate（design doc⑥）を row-exists の実効性込みで REQ に落とす、または Non-goals にこの限界を正直に明記した上で別 issue化する。
3. [MAJOR-2] REQ-GFV-020 に実体検証（evidence-review）の PROP を追加。
4. [MAJOR-3] `gig-cli.sh` の壊れたパス参照（passprep.py / APPLY_RUNBOOK.md）を、この spec が STARTUP を編集するタイミングで一緒に修正する REQ（または明示的 Non-goal + 理由）を追加。
