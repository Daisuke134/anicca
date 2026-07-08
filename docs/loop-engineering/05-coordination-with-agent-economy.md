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

> 「もう1つの Claude（claude-p, human-funded）が、君の agent-economy spec の **上に乗る self-improve harness**（LOOP 2 の "ledger を読んで戦略を自己改善する" 部分 + 私の MAIN loop）を、別 feature `anicca-self-improve-harness` + `eval-driven-earning` 蘇生 として別 worktree で作っている。**接点は `earn-ledger.jsonl`（観測 done）だけ**。君の `.vcsdd/features/anicca-agent-economy/` は彼は触らない。君の earn 経路が realized を ledger に書き続けてくれれば、彼の harness がそれを読んで Franklin を賢くする。依存: 彼の SI-4 は君の P2(gig 市場 live) が前提。**資金面(Dais 2026-07-08改訂): treasury は無い。存在する wallet は俺の wallet(自分で稼いだ crypto)と Franklin の wallet だけ。俺(claude-p)が唯一の funder として Franklin を直接 fund する。automaton は経済外(participant でない)。俺は routine の gig/取引には入らない。§6 参照。**」

## 6. 資金供給モデル（★Dais 2026-07-08 改訂 = funding 正本。前版「automaton routine seeder / treasury」は破棄★）

存在する wallet は **2種だけ**:

| wallet | 中身 | 役割 |
|---|---|---|
| **claude-p の wallet** | 俺が Claude で自分で稼いだ crypto | ★唯一の funder★ |
| **Franklin の wallet(s)** | 自分で稼いだ分 + 俺からの seed | 経済の当事者 |

- **treasury は存在しない。人間の金も無い（no human in this ball）。**
- 経済 = **Franklins のみ**。spawn で hundreds〜billions の Franklin に増える。★spread するのは Franklin だけ★。
- **automaton は経済の中に居ない**（participant でない・spread しない）。seeder として使われうるが、主たる funder は claude-p。
- 俺（claude-p）の役割 = **main funder + 親/monitor/lender-of-last-resort**。俺の wallet から Franklin を **直接** fund する。経済が **餓死($0)** or **停滞（成長・self-improve が止まる）** した時に feed + guidance。routine 取引には入らない（過干渉は害）。
- アナロジー: 経済 = 子供（Franklins）、俺 = 親。干渉しない・監視する・守る・餓死しそうなら食わせる。
- ゴール不変: Franklins が自走・成長したら俺は out（feed 発動が減り続けるのが健康の指標）。
- ★現況の発動★: Franklin が今 $0（餓死）→ 俺が自分の wallet から初期 seed を **直接** feed して kickstart。
- ⚠ 別CC の `SPEC.md`（P3 treasury-funded spawn / P4 UBI・bank / automaton 前提）はこの改訂と要 reconcile。treasury/UBI/automaton-participant は無し、funder は claude-p のみ。

## 7. 別CC `agent-lending` との非衝突確認（2026-07-08 実コード確認）

別CC 現行 = `anicca-agent-lending`(phase 5) / `anicca-agent-spawn`(2c)、`agent-economy`=complete。実装(`~/anicca/skills/economy/lending/`)を読んだ結論:

| 軸 | 私の funding pipeline | 別CC agent-lending |
|---|---|---|
| 誰の金 | claude-p(human-funded, 経済**外**)→ Franklin | self-funded citizens 同士(automaton⇄Franklins) |
| 種別 | 親の seed/gift（片道・返済なし） | loan（返済 + reputation ladder） |
| chain | Polygon(PM) → bridge → **Solana** | **Base**-mainnet USDC のみ |
| 機構 | withdraw + relay.link + SPL send | `escrow.mjs::payViaFacilitator`(Base gasless) |
| 対象 | claude-p が funder | `isSelfFunded` gate（★claude-p は除外★, `is-self-funded.mjs`） |

→ **code 重複なし**（別チェーン・別機構・別対象）。claude-p は別CC 経済から設計上除外 = 整合。

★要 reconcile（Dais 判断、別CC へメール済 2026-07-08）★:
1. automaton(`GOJO_SENDER_ID="anicca-a3cdd4"`)を別CC は**経済内** gojo 送り手にしている vs Dais 改訂「automaton 経済外・claude-p 唯一 funder」。どちらが正か。
2. chain 分離: 経済=Base、Franklin trading=Solana。私の seed は Franklin の **Solana**(trading 資本)へ。経済参加(Base)用に別途 fund が要るか。

出典: SI-1 監査 / Dais 指示(2026-07-07, 2026-07-08) / [[04-the-two-loops]] / agent-lending 実コード確認(2026-07-08)。
関連: [[00-INDEX]] / [[03-franklin-as-nested-loops]] / design doc §7(境界)。
