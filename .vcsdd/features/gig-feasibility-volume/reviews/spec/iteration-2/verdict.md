# gig-feasibility-volume — Spec Review Verdict (Phase 1c, iteration 2)

- **Reviewer**: fresh-context adversary（Builder 文脈なし、iteration-1 adversary 文脈なし、disk artifact のみで判定）
- **対象**: `specs/behavioral-spec.md`（REQ-GFV-001..024）+ `specs/verification-architecture.md`（PROP-001..035、required:true 30件）
- **判定日**: 2026-07-08
- **総合判定**: **FAIL**（blocking 1件〔新規〕、major 0件、minor 0件 — iteration-1 の blocking/major/minor 全7件は解消確認。次フェーズ進行不可、新規 BLOCKING が原因）

## iteration-1 findings の解消確認（個別照合）

| iteration-1 finding | 解消状況 | 根拠 |
|---|---|---|
| **BLOCKING-1**（PROP-029/030 ダングリング） | ✅ **解消** | `verification-architecture.md` §2 に PROP-029（`listings_total` 4行/3distinct fixture）・PROP-030（`activity_total` sum/monotonic fixture）が定義済み。§3 Tier0/Tier1 リストと§2テーブルの PROP 番号を union 集計した結果、001〜035 の35個全てが1回ずつ、重複なく出現（Tier0=17件: 001,004,008,013,015,017,019,020,021,024,025,026,028,031,033,034,035／Tier1=18件: 002,003,005,006,007,009,010,011,012,014,016,018,022,023,027,029,030,032／union=35件、gapなし、重複なし）。§4 の `required:true=30` も実際に列挙されたIDを数えて30件と一致、`required:false=5`（008,009,019,034,035）+30=35で「35 PROPs overall」の主張とも一致。§5 Traceability も REQ-GFV-021→PROP-029、REQ-GFV-022→PROP-030 と明記され整合。 |
| **MAJOR-2**（REQ-GFV-020 実体検証PROP欠落） | ✅ **解消** | PROP-034（新規）が「実送信されたB1/B2メッセージをproposal_templates原文および元request文と diff する evidence-review」として追加され、REQ-GFV-020 の実体（個別化）を検証する。 |
| **minor-1**（REQ-GFV-016 実体検証PROP欠落） | ✅ **解消** | PROP-035（新規）が「実際のskip理由が ai_infeasible or illegality の2根拠のいずれかに紐づくか」を evidence-review で検証する。 |
| **minor-2**（REQ-GFV-002 の fixture key数の不一致） | ✅ **解消** | REQ-GFV-002 Acceptance Criteria が「matching the LIVE file's real 22-key shape」に修正され、`~/gig/strategy.json` の実キー数（実測22キー、本セッションでも `python3 -c "import json;print(len(json.load(open('/Users/anicca/gig/strategy.json'))))"` 相当の照合は§0 記述と整合）と一致。 |
| **minor-3**（§0 の 78/91 → 実測68/91誤り） | ✅ **解消** | §0 Reality check が「68/91 carry `price_jpy`」に修正済み（旧78/91の誤記述は削除）。 |
| **MAJOR-3**（gig-cli.sh の壊れたパス2箇所） | ✅ **解消** | REQ-GFV-024（新規）が両パス（`passprep.py`, `APPLY_RUNBOOK.md`）の修正を明記し、PROP-033（grep -c ==0 + 両修正後パスの存在確認）で検証される。Edge Cases 節で「この修正は§REQ-GFV-006/016/018/020/023と同じSTARTUP編集パスの中で行う」ことも明記され、MAJOR-3の懸念（別タイミングに先送りされる懸念）も潰されている。 |
| **MAJOR-1**（design doc §6 cadence bar が実質未充足） | ⚠️ **アーキテクチャ上は解消するが、下記新規 BLOCKING により実効性が成立しない** | 詳細は次節。 |

## 新規 BLOCKING-1（Reality-grounding）— REQ-GFV-021/022/023 の土台となる §0 Reality check の中心的事実主張が本セッションの実測と矛盾する

**§0 Reality check・REQ-GFV-012（Edge Cases）・REQ-GFV-022（EARS本文）・REQ-GFV-023（Edge Cases）の複数箇所で、以下がほぼ同じ文言で繰り返し断定されている**（§0 より引用）:

> 「`funnel_report.py` reads `~/gig/applied.jsonl`, dedupes, summarizes, appends ONE `{ts,pass_id,applied,replied,won,paid}` line to `~/gig/gig-funnel.jsonl` **EVERY pass UNCONDITIONALLY**（`gig-cli.sh`'s FUNNEL REPORT step runs outside the `do_improve` branch, every single pass regardless of whether B1/B2 did anything this pass）」

REQ-GFV-023 の Edge Cases でも同様に「gig's `funnel_report.py`, which **runs unconditionally every pass**」と再度断定され、この「毎パス無条件で新しい行が書かれる」という事実が、REQ-GFV-021/022/023 の設計全体（`activity_total` の increment 比較で「今日 real activity があったか」を判定する）の暗黙の前提になっている。

**本セッションで実機照合した結果、この主張は事実と一致しない：**

```
$ python3 -c "import json; d=json.load(open('/Users/anicca/gig/strategy.json')); print(d.get('pass_count'), d.get('improve_cadence_passes'))"
218 4
$ wc -l < ~/gig/gig-funnel.jsonl
1
$ cat ~/gig/gig-funnel.jsonl
{"ts": 1783512294, "pass_id": "p-1782860280", "applied": 93, "replied": 16, "won": 0, "paid": 0}
```

- `pass_count=218`、`improve_cadence_passes=4` → `do_improve` は少なくとも約54回は true になっている計算だが、`gig-funnel.jsonl` には行が **1行しか存在しない**。「毎パス無条件」が真であれば218行（最低でも54行）あるはずが、実際には1行のみ。
- その1行の `ts=1783512294` は JST 2026-07-08 21:04:54 — **本レビューセッションが進行中の、ごく直近の時刻**。`ls -la ~/gig/` で `gig-funnel.jsonl` の mtime も同時刻（21:04）、`.last-pass` の mtime は21:06。一方 `applied.jsonl`（269行）は21:55まで更新され続けており、ループ自体は実際に活発に稼働中（tmuxペインにも「Pass 218 is running in the background」と表示）。
- これは、`funnel_report.py` が「REQ-LV-015」という既存の（この spec 以前から実装済みの）要件でありながら、少なくとも直近217パス分については一度も実行されておらず、本セッション中に発生した1回（おそらく本レビュー準備中の手動実行、または本セッション中の偶然の1パス）が history 上で唯一の実行痕跡である、という強い証拠。

**この事実が REQ-GFV-021/022/023 の設計に与える実害**（`cadence.py::cadence_met` の `increment` kind: `evidence["today_value"] > evidence["previous_value"]`、`_gig_today_and_previous_activity_total` は `_bounty_today_and_previous_checked` と同じ「その日の行が無ければ `today_value=0`」というフォールバック規約を踏襲する設計）:

- `funnel_report.py` が実際には「毎パス」どころか「ほぼ一度も」実行されないなら、`gig-funnel.jsonl` に「今日」の行が存在しない日がほとんどになる。その場合 `today_value` は `0` にフォールバックし、`previous_value` は（存在する唯一の過去行から）`93+16+listings_total` 相当の正の値になる。`0 > 正の値` は常に `False`。
- つまりこの increment 化フィックスを実装しても、**実際に応募/返信/出品が起きている日でも `cadence_met()` が `False` を返し続ける**可能性が高い。iteration-1 の MAJOR-1（false-positive：何もしなくても健全に見える）を、**false-negative（実際に働いているのに不健全に見える）**という別種の、self-heal 誤発火（`.gig-core-selfheal-request.json` エスカレーション）を招く、運用上より有害な欠陥に置き換えるだけになる。
- PROP-031/032 はどちらも**手作りfixtureに対する純粋関数の単体テスト**であり、「`funnel_report.py` が本番で実際にどのくらいの頻度で呼ばれるか」という、この欠陥の本質を検証するPROPが1つも存在しない。§4 の required:true 30件のどれもこのギャップを塞がない。

**この spec は `funnel_report.py` の呼び出し頻度そのもの（`gig-cli.sh` の STARTUP プロンプトにおける FUNNEL REPORT ステップの実行条件）を一切変更対象にしていない**（REQ-GFV-024 はパス文字列2箇所の修正のみで、呼び出し頻度/条件には触れない）。したがって、この BLOCKING は「新しい REQ を1個足せば直る」性質ではなく、**§0 Reality check の中心主張そのものを実機で再調査し、`funnel_report.py` が実際にいつ・どのくらいの頻度で呼ばれているかを突き止めた上で、その真の呼び出し条件に基づいて REQ-GFV-021/022/023 を書き直す**必要がある。具体的な次の一手の候補（Builder が選ぶべき事項、本レビューでは決定しない）:
  - (a) `gig-cli.sh` STARTUP の FUNNEL REPORT ステップを `do_improve` 条件から明確に外に出し、B1/B2完了後に毎パス無条件で走るよう文言を明確化する REQ を追加する、
  - (b) あるいは `activity_total` の increment 比較を「calendar day」単位ではなく「pass 単位」（前回 `gig-funnel.jsonl` 行 vs 今回）に変更し、行の書き込み頻度に依存しない設計にする、
  - のいずれか（または他の妥当な設計）を選び、選んだ設計が実際に機能することを実機ログ/ledgerで示す PROP を追加すること。

## 1. Completeness — FAIL（新規BLOCKINGの帰結）

design doc §6 cadence bar（「未達→self-fix」）は、iteration-1 時点でも本 iteration 時点でも実質的に未充足のまま。iteration-1 は「row-exists が構造的に常に真」という形の未充足を指摘し、この spec はその**症状**（row-exists の常時真）を消す変更を行ったが、上記 BLOCKING-1 の通り、その変更の前提（`funnel_report.py` が毎パス無条件で走る）自体が事実と異なるため、design doc の cadence bar が実際に機能する保証には至っていない。他の To-be ①〜⑤・BP seedは REQ-GFV-001〜020 に引き続き適切にマップされている（iteration-1 で PASS 済み部分は変更なし、再確認して問題なし）。

## 2. Testability — PASS

MAJOR-2・minor-1 は PROP-034/035 の追加で解消。他の PROP は iteration-1 で問題なしと判定済みの部分から変更なく、新規追加された PROP-029〜035 もそれぞれ具体的な fixture/evidence-review 手法を伴っており、テスト可能性そのものに問題はない（ただし PROP-031/032 が「本当に検証すべきこと」＝実行頻度を捉え損ねている点は Reality-grounding の BLOCKING-1 として扱う——これは「テストの書き方」の問題ではなく「何を検証対象にすべきかの選定」の問題のため）。

## 3. Consistency — PASS

BLOCKING-1（PROP-029/030 ダングリング）は解消済み（上表参照）。§0・REQ-GFV-012/022/023 内での「funnel_report.py は毎パス無条件」という主張は、spec内では一貫して同じ内容が繰り返されており、spec内部の記述としては（誤りではあるが）矛盾なく一貫している——このため Consistency ではなく Reality-grounding 側の BLOCKING として分類した。スコープロック（`cadence-contracts.json`/`cadence-evidence.py` への拡張）とREQ-GFV-023の記述も整合している。

## 4. Reality-grounding — FAIL

**BLOCKING-1**（上記）。それ以外の Reality check 項目（22-key fixture、68/91 price_jpy、壊れたパス2箇所、`strategy.default.json` の既存構造、`funnel.py`/`passprep.py` の既存関数群）は本セッションで再照合し、いずれも spec の記述と一致することを確認した。

## 5. Agent-vs-code boundary — PASS

REQ-GFV-021〜024 を含め、新規追加された REQ 群も feasibility/category/価格/文言判定を引き続き自然文judgmentとして定義し、決定論コードは `listings_total`/`activity_total` の集計・cadence-contract の kind 切替（既存 `increment` セマンティクスの再利用のみ、`cadence.py` 自体は不変と明記）・パス文字列修正に限定されている。regex/keyword 判定コードの追加なし。`~/.claude/rules/building-effective-ai-agents.md` に準拠。

## 6. Dais 制約遵守 — PASS

AI使用申告・disclosure関連の文言は依然としてゼロ。iteration-1からの変更範囲にもこの種の記述の再混入はない。

## Summary

| 次元 | 判定 | blocking | major | minor |
|---|---|---|---|---|
| Completeness | FAIL | 0 | 0 | 0 |
| Testability | PASS | 0 | 0 | 0 |
| Consistency | PASS | 0 | 0 | 0 |
| Reality-grounding | FAIL | 1 | 0 | 0 |
| Agent-vs-code boundary | PASS | 0 | 0 | 0 |
| Dais 制約遵守 | PASS | 0 | 0 | 0 |
| **合計** | **FAIL** | **1** | **0** | **0** |

**次アクション（Builder向け）**:
1. [BLOCKING-1] `gig-cli.sh` の STARTUP プロンプトにおける FUNNEL REPORT ステップの実際の実行条件（`do_improve` 分岐の内側か外側か、実際にどの頻度で agent がこのステップを実行しているか）を、prose の再解釈ではなく実ログ/ledger の追加調査（例: tmux pane 履歴、`gig-funnel.jsonl` の今後複数パス分の蓄積を実際に観測する、または `gig-cli.sh` の STARTUP 文言を厳密に構文解析する）で突き止める。
2. その実態に基づき、REQ-GFV-021/022/023（および必要なら新規 REQ-GFV-025 相当）を「実際に機能する」形に書き直す。書き直しの選択肢は本 verdict の該当節に2案提示した（FUNNEL REPORT を明確に無条件化する／activity_total 比較を calendar-day ではなく pass 単位にする）——採否は Builder の設計判断。
3. 選んだ設計が実際に本番相当の頻度で `gig-funnel.jsonl` に新しい `activity_total` を書き込むことを、fixtureベースの単体テストだけでなく、実ログ/ledger照合ベースの PROP（Tier 0, evidence-review）で追加検証すること。
