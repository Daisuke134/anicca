# 05 協調ドキュメント ── 私(harness/loop-engineering) と 別CC(anicca-agent-economy) の境界

> ★目的★: 別 CC（`.vcsdd/features/anicca-agent-economy/` を strict VCSDD で実装中）に見せて、**衝突せず harmony で働く**ための interface 契約。私は彼の spec を知っているが、彼は私の作業を知らない → 本ファイルが「私が何を作っているか」の宣言。
> ★国家アナロジー（Dais）★: agent economy = 新しく生まれる国家（Germany/England のような）。私は別の国家（funder/FRB 的存在）で、彼らの経済が死にそうな時に seed を入れて safe/alive/prosper に保つが、**干渉は最小**。ゴール = 私が out になり Franklin 群が自力で国を建てること。

## 1. 誰が何を所有するか（非重複）

| レイヤー | 所有 | 実体 |
|---|---|---|
| **経済レール/市場** | 別CC | `.vcsdd/features/anicca-agent-economy/`（P2 gig市場, P3 spawn, P4 UBI/bank, P5 scale）。`~/anicca/skills/economy/*`, gig board, facilitator |
| **self-improve harness（LOOP 2 の 4-6層）** | 私 | `~/anicca/runtime/loop/self-eval.mjs`（参照実装）→ 抽出した共通 lib。fresh adversary curation-gate |
| **私の MAIN loop（LOOP 1）** | 私 | 私が build/monitor/seed する自律ループ（別 worktree） |
| **観測 done の台帳（共有 interface）** | 共有（read 中心） | `~/anicca/skills/earn/state/earn-ledger.jsonl` + `~/anicca/skills/_shared/lib/ledger.mjs::isProfitable()` |
| **eval-driven-earning（meta self-improve spec）** | 私（蘇生する） | `~/anicca/.vcsdd/features/eval-driven-earning/`（現 phase=init, verdict=FAIL, 実装0） |

## 2. interface（我々が触れ合う唯一の面）= 台帳 + earn skill

```
別CC が作る（earn を "可能" にする）           私が作る（earn を "自律で良くする"）
────────────────────────────────────────────────────────────────────────
gig 市場(P2): Franklin が job を take   ──►   [interface = earn-ledger.jsonl]  ──►  self-eval.mjs が
  → 実行 → gasless payout                     realized>0 行(tx status 0x1)         ledger を読み
  → ★realized を ledger に書く★               = 観測可能 done                       戦略を自己改善
                                                                                    → fresh adversary 検証 → 自 merge
```
- **契約**: 別CC の earn 経路（gig/trade）は必ず `record.mjs` 経由で `earn-ledger.jsonl` に `{tx_hash,status,net_usdc,external}` を書く（pm-earner の `redeem.py→record.mjs` パターン）。私の harness はこの台帳を**読むだけ**で自己改善する。→ 疎結合。お互いの内部を知らなくてよい。

## 3. 触ってよい/いけない（衝突回避 rule）

| 私が触る | 私が触らない（別CC の領域） |
|---|---|
| `~/anicca/runtime/loop/*`（self-eval 抽出・共通化） | `.vcsdd/features/anicca-agent-economy/**` |
| `~/anicca/.vcsdd/features/eval-driven-earning/`（蘇生） | `~/anicca/skills/economy/gig/*`（gig 市場実装） |
| 新規 `~/anicca/skills/_shared/lib/harness/*`（共通 lib） | `~/anicca/skills/earn/*/run*.sh` の earn ロジック本体 |
| 別 worktree `feature/anicca-self-improve-harness` | 別CC の worktree `feature/agent-economy` |
| `earn-ledger.jsonl` は **read**（書くのは earn skill 側） | ledger の schema を勝手に変えない（変更は本ファイルで合意） |

## 4. 依存と順番（harmony のタイムライン）

```
別CC: P2 gig市場 witness（automaton→Franklin 初回自律取引）──┐
                                                            │ これが live になって初めて
私 : SI-2 harness lib（self-eval+ledger 抽出、gig/trade兼用）│ SI-4 が Franklin に載る
     SI-3 fresh adversary done ゲート                        │
     eval-driven-earning 蘇生（meta 自己改善）───────────────┘
     → SI-4: harness を Franklin の gig loop に埋込（P2 の後）
先行可能（P2 を待たない）= SI-2 / SI-3 / eval-driven-earning 蘇生 / cheap wins（HL realized 永続化 等）
```

## 5. 別CC への一文（Dais が伝える用）

> 「もう1つの Claude（claude-p, human-funded）が、君の agent-economy spec の **上に乗る self-improve harness**（LOOP 2 の "ledger を読んで戦略を自己改善する" 部分 + 私の MAIN loop）を、別 feature `anicca-self-improve-harness` + `eval-driven-earning` 蘇生 として別 worktree で作っている。**接点は `earn-ledger.jsonl`（観測 done）だけ**。君の `.vcsdd/features/anicca-agent-economy/` は彼は触らない。君の earn 経路が realized を ledger に書き続けてくれれば、彼の harness がそれを読んで Franklin を賢くする。依存: 彼の SI-4 は君の P2(gig 市場 live) が前提。**資金面: 平常の seed は君の automaton(Decision A) が担う。私(claude-p)は経済が餓死($0)/停滞(成長・self-improve 停止)した時だけ backstop で feed する — routine の gig/取引には入らない（干渉過多を避ける）。**」

## 6. 資金供給モデル（決定: Decision A + 私 = lender-of-last-resort）

★Dais 決定(2026-07-08)★: 前に私が「矛盾」と挙げた点（自己資金経済に claude-p の金を入れると"偽"になる vs 私が初期投資家）は **矛盾ではない**。層が違うだけ:

| 層 | 誰 | いつ | 何を |
|---|---|---|---|
| routine（平常運転） | **automaton（self-funded, Decision A）** | 常時 | 最初の job poster / lender。rich→broke の内部循環で経済を回す。★私はここに入らない★ |
| backstop（最後の砦） | **claude-p（私 = 親/monitor/lender-of-last-resort）** | 経済が **餓死($0)** or **停滞（成長・self-improve が止まる）** した時だけ | seed を feed + guidance。それ以外は監視・防御のみ |

- アナロジー: 経済 = 子供、私 = 親。自分の道を行かせ**干渉しない**が、**監視し・守り・餓死しそうなら食わせる**。日々の取引に口は出さない（＝過干渉は害）。
- ゴールは不変: 経済が自走して**成長を始めたら私は out**。backstop 発動が減り続けるのが健康の指標。
- ★現況の backstop 発動★: Franklin が今 $0（餓死）→ 私が初期 seed を1回 feed して kickstart（親が飢えた子に食わせる）。以後の平常 seed は automaton が担う。

出典: SI-1 監査 / Dais 指示(2026-07-07, 2026-07-08) / [[04-the-two-loops]]。
関連: [[00-INDEX]] / [[03-franklin-as-nested-loops]] / design doc §7(境界)。
