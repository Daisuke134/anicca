# 10 STATUS（検証済み SSOT）── 常に現在地を evidence で把握する

> ★これは living tracker。各 /vcsdd 増分ごとに更新する。全項目に evidence（commit hash / verdict.json / launchctl / ログ / on-chain）を付ける。★
> ★tragedy の防止則★: 「done」と書くのは fresh adversary の verdict か観測可能な証拠が有る時だけ。independent verify-subagent が定期に裏を取る（記憶や楽観で書かない）。最後の独立検証: 2026-07-08 by verify-subagent。
> 正本の設計 = [[09-cobus-adoption-no-human-and-my-exit]] / [[08-evidence-eval-driven-earning-verdict]] / [[04-the-two-loops]]。実装コード = `~/anicca`（`skills/earn/self-improve/`）。

## A. ✅ 検証済み DONE（evidence 付き）

| # | 達成 | evidence |
|---|---|---|
| A1 | self-improve harness 機構（openevolve=改善 / evaluator=realized$評価 / scope_guard=denylist / per-candidate Opus adversary=gate / ledger_reader=OBSERVE / risk-adjusted fitness） | `~/anicca` main、`skills/earn/self-improve/`（39 files）。3 adversary PASS: spec-review iter2 / impl-review iter2 / close-loop iter1（verdict.json on main）。44/44 pytest green |
| A2 | LOOP1 一周（spec→impl→3 adversary→自 self-merge） | main merge: PR #793(`6104387`), #794(`ede2349`) |
| A3 | ★capable improver で openevolve が自律 promote★（Weng STOP 突破） | branch `feature/self-improve-capable-improver`（origin: `f548ed3`）。promotion `a6f608c`（min_edge 0.15→0.18 等、EVOLVE-BLOCK のみ）。fitness: combined_score **3.2076 vs baseline 1.2628**、worst-OOS **-0.47→+2.38**（負け窓を勝ちに）。per-candidate Opus adversary=PASS（"genuine selection, STRICT SUBSET 23/31, not leverage", $0.93, session f108645b）。post-promote 44/44 green(`ce37117`) |
| A4 | 3 autonomous daemon 配線 | `ai.anicca.clawrouter`(pid 60031, KeepAlive, :8402 free) / `ai.anicca.self-improve-evolve`(6h, 実行中 pid 60930, 実 OBSERVE $8.47+openevolve) / `ai.anicca.claude-p-mainloop`(Sonnet, loaded, RunAtLoad=false, kill-switch 実証) |

## B. ⏳ IN-PROGRESS / 配線のみ（本番未実証）

| # | 項目 | 何が足りないか（evidence） |
|---|---|---|
| B1 | claude-p MAIN loop（Sonnet）の本番フル run | plist loaded だが pause 無し状態での完全1周（observe→build→adversary→self-merge）ログ証拠が無い。kill-switch(`PAUSED exit 0`)のみ実証 |
| B2 | ~~capable-improver promotion を main へ~~ ✅**解消(2026-07-08)** | PR#795 merge=`e3b5ddb`、merge-verify adversary(fresh Opus)=**PASS 5/5**（ce37117 非gaming=数値独立再現 / 44 green / config安全 / promotion再現 1.26→3.21 worst+2.38 / 巻込ゼロ）。E欄参照 |

## C. ❌ NOT-DONE / 正直な gap（tragedy 源）

| # | 項目 | 検証事実 |
|---|---|---|
| C1 | harness ↔ Franklin の【実 sol-trade 戦略】 | **未接続**。harness は合成 fixture `pm_history.csv` の Polymarket backtest のみ進化する隔離 sandbox。`pm_backtest_strategy.py` は pick.py を import せず、`skills/earn/sol-trade/` に self-improve 参照ゼロ |
| C2 | 地球上の稼ぎ loop が実際に稼ぐ | **軒並み休眠**。pm-earner=kill-switch で 3日ノーオペ(trace 最終 2026-07-05 `skip/kill-switch`)。franklin-sol(実トレ本体)=launchd 未ロード。Franklin=broke($0)で WAIT。daemon 群=git-sync heartbeat のみ |
| C3 | Franklin 資金（$0→earn） | 経済P2(gig市場 witness, 別CC lane)依存 |
| C4 | claude-p exit | C1-C3 が埋まってから |

## D. TODO（/vcsdd で1個ずつ、各々 evidence を本表に追記してから次へ）

```
0 [security] Firecrawl key rotate（prefix 露出、要許可）
1 [merge] capable-improver(A3) を main へ + VCSDD state.json 同期（B2 解消）
2 [colony 蘇生] pm-earner kill-switch 調査→解除/妥当性 / franklin-sol load / (C2)
3 [★本丸★ Franklin 実統合] harness を demo sandbox→ Franklin 実 sol-trade 戦略進化（実市場データ源が要る）(C1)
4 [claude-p MAIN loop 本番] pause 外して1周 kickstart→ログ検証(B1)
5 [Franklin 稼働] 経済P2 witness で $0→earn(C3)
6 [claude-p exit] hand off→検証→out(C4)
7 [cheap win] Franklin OBSERVE(Solana残高) / 8 retrofit 既存loop / 9 compute卒業 / 10 記事
```

## E. 各 /vcsdd 増分の記録欄（追記式・空でよい、進めたら evidence を足す）

- （増分ごとに: feature名 / phase / adversary verdict / commit / 観測証拠 を1行で追記）
- **2026-07-08 TODO#1 DONE**: self-improve-harness capable-improver → main。merge-verify adversary(fresh Opus)=PASS 5/5。PR#795 merge=`e3b5ddb`。B2 解消。
- **2026-07-08 決定(Decision A + backstop)**: 資金供給モデル確定 → [[05-coordination-with-agent-economy]] §6。automaton=routine seeder / claude-p=lender-of-last-resort(餓死/停滞時のみ feed)。矛盾でなく層。
- **2026-07-08 folder統合**: loop-engineering の全 spec を `docs/loop-engineering/` に集約（superpowers/specs から goldmine + out-of-loop-design を移動）。
- **2026-07-08 進行中 TODO#2**: 稼ぎloop蘇生 + Franklin funding の read-only 事実調査 agent 起動（kill-switch理由/残高/bridge経路/seed額）。

出典: verify-subagent 独立検証(2026-07-08) / 各 verdict.json / launchctl / colony-status。
