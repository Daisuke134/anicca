# EVOLVE: earnings-gated 自己改善ハーネス — design spec (#19)

**日付**: 2026-07-05
**status**: build
**repo**: `~/anicca`（skills/earn + runtime）

## 0. なぜ / 原則（HARD）

Dais の中核方針: 「俺は harness を作る。**戦略(alpha)は書かない**。instance が自分で試し、勝った戦略が swarm に伝播して、賢くなる」。realized>0 への本丸は「勝率を上げる」= alpha の質。だが俺が手でチューニングするのは禁止（`harness or cook = harness`）。→ **instance が自分の knob を変異させ、chain-verified な realized P&L で勝った変異だけが baseline になり全個体へ伝播する** ハーネスを作る。

**HARD #0**: どの market/side を賭けるかは MODEL が決める（不変）。EVOLVE が変えるのは「探索の knob（genome）」だけ。genome も市場・side を hardcode しない。

## 1. Goal（検証可能な完了条件）

**DONE** =
1. **genome**: 各 instance の earn 探索 knob（`MIN_EDGE / MIN_CONF / RESOLVE_HORIZON_DAYS / MAX_CANDIDATES / EARN_CONSENSUS_MODELS`）を1ファイル `genome.json`（instance body の state）に集約。earn 経路（run.sh→pick.py）はこの genome を env として読む（既存 env override をそのまま使う＝再発明なし）。
2. **mutation（探索）**: instance が周期的に genome の**安全範囲内**の小変異を試す（次 N pass だけ）。money-safety cap（`MAX_BET_SIZE / MAX_PASS_SPEND`）は genome の外で不変、変異で無効化できない。fail-closed。
3. **attribution**: 各 genome 世代の **chain-verified realized P&L** を earn-ledger（redeem 行 = on-chain tx 付き）から集計。genome id を bet 時に記録し、resolve/redeem 時に紐付ける。
4. **earnings-gated merge**: ある変異 genome の realized P&L が現 baseline を **chain-verified で上回った**時だけ、その genome を新 baseline に採用（`~/anicca` の canonical baseline genome を更新）。**人間ゼロ・盛りゼロ**（paper/simulated P&L では merge しない、on-chain redeem のみ）。負けは破棄。
5. **propagation（mother-sync）**: baseline genome は canonical repo に置き、daemon の既存 rsync（`~/anicca/skills → body`）で全 instance に伝播。

## 2. 作業（MUST）

### 2.1 genome ハーネス（`skills/earn/lib/genome.mjs` or `.py`, 新規）
- MUST: `load_genome(instance_home)` → baseline genome（canonical）+ その instance の現世代 override をマージして返す。無ければ安全な default（今の env default 値）。
- MUST: `mutate(genome)` → 安全範囲内で1〜2 knob を小変異（例: MIN_EDGE ±0.03, RESOLVE_HORIZON_DAYS ±7, MAX_CANDIDATES ±2、範囲は clamp）。MAX_BET_SIZE/MAX_PASS_SPEND は変異対象外。
- MUST: `genome_id(genome)` = 内容の短 hash（P&L 紐付け用）。

### 2.2 earn への配線（既存 pick.py/run.sh の env を genome から供給）
- MUST: run.sh が pass 開始時に `load_genome`（+ 探索周期なら `mutate`）を呼び、その値を `MIN_EDGE` 等の env に export してから pick.py を実行。現在の genome_id を trace に記録。
- MUST: 変異は「探索窓」でのみ（例: M pass に1回 mutate、他は baseline）。money-safety cap は常に固定 env で上書き（genome より優先）。

### 2.3 attribution + gate（`skills/earn/lib/evolve.mjs`, 新規）
- MUST: earn-ledger の redeem 行（realized, on-chain tx）を genome_id 別に集計 → 各世代の realized P&L と bet 数。
- MUST GATE: 変異世代の realized P&L が baseline を上回り、かつ **on-chain redeem が最低 K 件**（統計的に無意味な1発を除く、K は env）で確認された時のみ「昇格候補」。
- MUST: 昇格 = canonical baseline genome を更新（`~/anicca/.../baseline-genome.json`）+ git commit（自動、no human）。simulated/paper は絶対に昇格させない（HARD 0.24）。

### 2.4 propagation
- MUST: baseline genome は `~/anicca/skills/earn/` 下の canonical file。daemon rsync が body へ配る（既存機構、追加配線不要）。

## 3. money-safety invariants
- MUST: mutation は安全範囲に clamp、`MAX_BET_SIZE/MAX_PASS_SPEND/POLY_MIN_ORDER` は genome 外で常に固定・変異不可。
- MUST: 昇格は **on-chain-verified realized P&L のみ**（redeem tx）。ledger に paper/simulated が混ざったら昇格させない。
- MUST: identity(#27) / clean-stdout(#25) / free-mode(#31) は不変。genome は市場・side を決めない（MODEL の領分）。

## 4. 検証（VCSDD）
1. build（Sonnet）: 2.1–2.4 実装。genome load/mutate/id の単体、gate が chain-verified redeem のみで昇格することの単体。
2. **simulated-ledger E2E**（realized は数日かかるので、合成 ledger で gate を検証）: baseline genome_id=A（realized $1）と 変異 genome_id=B（realized $3, redeem K件）を仕込んだ合成 earn-ledger を食わせ、**B が昇格 → baseline が B に更新 → git commit** されることを実測。逆に B が paper のみ/redeem<K なら**昇格しない**ことも実測。
3. fresh Sonnet adversary（disk + read-only）: mutation が cap を破れないか、昇格が on-chain redeem のみか（paper 混入で昇格しないか）、HARD#0（市場/side 非決定）非退行、identity/free/stdout 非侵襲。PASS まで fix。
4. 俺: 合成 ledger で昇格/非昇格の両方を実測して close。real propagation は bet resolution に伴い継続（数日スケール、loop が回す）。

## 5. 触るファイル（境界）
- 新規: `skills/earn/lib/genome.*`, `skills/earn/lib/evolve.*`, `skills/earn/baseline-genome.json`
- 編集: `skills/earn/polymarket-trade/run.sh`（genome → env の配線 + genome_id trace）
- 変更しない: pick.py の判断ロジック / place_order / fund_via_bridge / redeem / identity block / money-safety cap

## 6. 検証ログ（GLVS Verify — 実施記録）

| 段 | 結果 |
|---|---|
| Build(Sonnet) `df16d92` | genome.mjs(load/mutate/id, FORBIDDEN_CAP 除去)+ evolve.mjs(attribution/gate/promote/CLI)+ baseline-genome.json + run.sh 配線。51/51 test、合成 E2E 昇格/非昇格 実測 |
| Adversary(fresh Sonnet) | **FAIL → 2 must-fix**: ①C.5 money-safety=「損が少ないだけ」の genome を昇格（baseline -$5→challenger -$2 で昇格）＝net-losing 戦略の自動採用 ②promote() の git commit が path-scoped でなく無関係ファイル巻き込み。cap 変異不可/eval 注入安全/on-chain のみ昇格/HARD#0/非退行 は PASS |
| Fix `3fa5578` | net-positive floor(`mutant.realized>0 && >max(baseline,0)`)+ MIN_EDGE floor 0.05 3層 + path-scoped commit + MAX_PASS_SPEND hard override 対称化 + injection 回帰テスト（実 bash eval で metachar payload 無害化を実測）。合成: -$5 vs -$2→非昇格、$1 vs $3→昇格 |
| 俺の独立検証 | **60/60 test green**（再実行）+ net-positive floor eyeball + commit push 確認 |

**DONE(2026-07-06): 自己改善ハーネス完成+検証** — genome 変異は run.sh に per-pass 配線済み、昇格は「on-chain-verified かつ net-positive の genome のみ」を保証（money-safety adversary-hardened）。**残(実配線の最後の1手)**: `node evolve.mjs` の周期起動（daily 相当）。ただし昇格には複数 genome 世代 × K件以上の redeem データが必要で、現状 baseline のみ・bet 未解決なので**今は promote 対象ゼロ**（数週間の変異+resolution データ蓄積後に有効化）。→ 周期 trigger は trivial follow-up。
