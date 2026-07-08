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
| C2 | 地球上の稼ぎ loop が実際に稼ぐ | ⚠**訂正(2026-07-08 fresh調査)**: pm-earner は kill-switch でなく**稼働中**（10分毎、実現益 **+$8.47** on-chain 6件 status0x1）。真のボトルネック = ①`MAX_PASS_SPEND=$2` 固定cap で $19.26 が発注されず眠る（3市場割で$0.67<最小bundle$4.95）②PM proxy からの **withdraw 経路が未実装**で Franklin へ資金を出せない ③浮遊 crypto は **$1.12 のみ**（$19.26 は PM に展開済）。Franklin=$0 で WAIT。franklin-loop は稼働中(franklin-sol.plist は二重実行回避で無効のまま正) |
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
- **2026-07-08 決定→改訂(funding)**: treasury 廃止・automaton 経済外。存在 wallet=claude-p + Franklin の2つだけ、claude-p=唯一 funder が Franklin を**直接** fund、経済=Franklins のみ(spawn で hundreds〜billions)。→ [[05-coordination-with-agent-economy]] §6。★別CC SPEC.md(treasury/UBI/automaton) は要 reconcile★。
- **2026-07-08 folder統合**: loop-engineering の全 spec を `docs/loop-engineering/` に集約（superpowers/specs から goldmine + out-of-loop-design を移動）。
- **2026-07-08 TODO#2 調査DONE(fresh evidence)**: pm-earner 稼働中・実現益+$8.47。ボトルネック=MAX_PASS_SPEND=$2 cap で $19.26 眠る + PM withdraw 経路未実装。浮遊 crypto $1.12 のみ。bridge=relay.link 実証済($10 Polygon→Solana=$9.95着,0.46%)。BF9v(Solana $0.47)は Franklin と同chain。
- **2026-07-08 pm-earner 安全修正 + identity 確定(DONE)**: (1)🔴 **guard fail-closed 復活** — `run_earner.sh` に KILL チェック追加（cron 実体が KILL を読まず check_cumulative_halt が本番で死んでいた、commit `e3269ac`）(2)**MAX_PASS_SPEND $2→$5**（眠る $19.26 を展開、market_maker の directional 露出を資本~26%に抑制、verification 推奨値、reload 済）(3)**wallet identity**: 8Fpqd が stable+正（franklin-stats **625:1** vs Efpap5）、clean 再起動後 proxy=8Fpqd 確認、送金 **address-safe**。Efpap5=過去1回のみ transient（key制御未確認）→ root-cause は別 task、funding は blockしない。
- **2026-07-08 build DONE + adversary PASS**: funding コード完成（`568fecb`、正本は `~/anicca/skills/earn/funding/`、~/.blockrun は作業残骸で無害）。money-safety adversary(fresh Opus)=**OVERALL PASS**（7次元、unwrap contract を Polymarket docs 照合、28テスト live pass）。要修正 Finding A(confirmation 未 try/except→D2/cron 前に必須 #9)。
- **2026-07-08 ★D1 完了 + on-chain 検証★**: claude-p→Franklin **初の実 seed** end-to-end 成功。①withdraw $2 pUSD unwrap+transfer→0x810f(Polygon `0xe10e22c24cfa…`) ②bridge $2 Polygon→Solana(`0xfd3309…`/`0x3af35b…`, fee~12%) ③send $1.7545 BF9v→Franklin(Solana `3EAkr9sv…` **finalized**)。Franklin USDC **$0→$1.7545**（直接 RPC 確認、colony-status は cache 遅延）。★未実証だった pUSD unwrap も live 成功★。$1.75 では Franklin まだトレード不能 → 次 D2 本 seed($10-20)は Finding A/C 修正+cap 引上げ後。
- **2026-07-08 ★D2 完了 + on-chain 検証★**: Franklin へ本 seed $10。withdraw($10, Polygon `0x65992485`+unwrap `0x7c62b0b4`)→bridge($10→$9.95, Solana `0x5bcf3596`, **fee 0.47%**)→send($9.9526, Solana `3K8Ff3Jik`)。Franklin USDC **$1.67→$11.63**(直接 RPC 確認)。道中で cap 二重計上バグ発見・修正(`a3ecb0a`: `--include-pusd` の unwrap 2tx を outflow 重複計上 → unwrap phase 除外 + bridge/send `counts_as_outflow=False`)。Franklin は今トレード可能域($10-20)。残: WAIT 脱出を franklin-loop で観測 + #7 恒久ループ。

出典: verify-subagent 独立検証(2026-07-08) / 各 verdict.json / launchctl / colony-status。
