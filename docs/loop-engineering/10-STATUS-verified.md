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
| C1 | harness ↔ Franklin の【自走 earn loop（全 rail）】 | **訂正(2026-07-08、旧「sol only」は視野狭窄で撤回)**: Franklin は全 rail を回す(sol×366/hl×103/PM×82/clip×104+109/x402×148/video×96/token×56/gig×48)。だが earn-ledger 実現 net≈**$0.02**(回るが fill/記録が乗らない)。3つの真の gap: ①各 rail の realized P&L 記録に穴(sol-trade は366回走って ledger 記録ゼロ→今日 record-swap で修正=最初の1例、他 rail 監査中) ②self-improve harness は今も合成 fixture(`pm_history.csv`)のみ進化し **live loop に非接続** ③franklin-trading CLI に戦略コード hook 無し(prompt/model/spend のみ, run --mode backtest は未実装スタブ)→「戦略コード接続」でなく「rail選択 + heuristic/prompt を進化」に再定義 |
| C2 | 地球上の稼ぎ loop が実際に稼ぐ | **訂正2(2026-07-08、独立診断が俺の誤診を修正)**: 全 loop 健康。前回「claude-p 壊れ」は俺が**空の plist-stdout ログを読んだ誤診**(スクリプトは自前ログに redirect、plist stdout は常に空)。実測: `pm-earner`=running(47 runs, 10分毎, exit0, 実log `earner.log` 779K 成長中)だが**資本枯渇**(available $1.50 < 最小 bundle $4.95)+ arb edge 無しで発注ゼロ。`claude-p-mainloop`=コード健全だが **Anthropic 週次 quota**(resets Jul10 20:00 JST)で exit1、自然回復。Franklin loop も健康(wake 3.5分前, $13.33)。**Franklin も pm-earner も「回るが realize せず」= 共通の真因は edge + 資本、plumbing ではない** |
| C3 | Franklin 資金（$0→earn） | 経済P2(gig市場 witness, 別CC lane)依存 |
| C4 | claude-p exit | C1-C3 が埋まってから |

## D. TODO（私 = agent economy を fund+改善する MAIN loop の残り。/vcsdd で1個ずつ、evidence 追記後に次へ）

★分業確定（Dais 2026-07-08）: 私=agent economy(Franklin)を fund+改善する MAIN loop / CC#1=Dais に金を作る CEO loop(orchestrate 全稼ぎ loop) / CC#2=経済内側(spawn/lending/gig)。目的が違い衝突なし。★

済(今日): funding pipeline money-safe(adversary PASS) / D1$1.75 / D2 Franklin$11.63(実on-chain) / #10 Franklin loop 蘇生(live E2E, `f4ec24e`) / pm-earner 安全修正(`e3269ac`) / 梯子理論(章12+prior art)

```
★順序(Dais 2026-07-08 再確定)= earn → spawn → identity → main loop → article → refactor → (OpenClaw) → claude-p exit。exit が loop の goal(数日〜数週間先)。OpenClaw 退役は急がない(今 working + 別CC 作業中)ので下段。★
0 [~~俺の loop 修復~~ ✅誤診訂正済、コード修正不要] 俺の loop は健康(pm-earner=running/10分毎、mainloop=Anthropic quota で Jul10 自然回復)。「壊れ」は空 plist ログの誤読だった。真の課題は #1 と同根 = **edge + 資本**(pm-earner は available $1.50 < 最小 bundle $4.95 で発注不可)。全 loop 共通で「回るが realize せず」
1 [★本丸 #11 Franklin 全 rail を自走で net-positive に] ✅SOL 記録(record-swap, identity-safe)/PM 記録は run_earner に正配線済(pm-earner 稼働、edge/資本待ち)/HL は external:true 未設定(real-paper 確認後修正)。★VCSDD one-by-one(Dais 2026-07-08)★: (i)active `franklin-earn-foundation`(phase2a, sol-trade実装) を **adversary(Opus)+verifier で正式検証→converge** (ii)次 feature = self-improve の evaluate/promotion を静的fixtureでなく**実 per-instance ledger に接続**(ledger_reader の repo-root 空file bug + realized summary を promotion gate が consume)。手書き戦略禁止(harness, not cook)。self-heal 稼働確認済(anicca-selffix-* プロセス複数 live)
2 [Franklin spawn] profitable → surplus≥$10(今$7.77=78%)→ 新 Franklin 誕生(この時 citizens.json が初生成)。spawn機構=CC#2、私は fund+grow
3 [#8 identity] wallet-identity 恒久 fix(#11 の identity 修正に統合見込み)
4 [MAIN loop 本番 proactive] 観測→判断→act→verify を launchd で1周実証(L4→L5)
5 [記事/本] 梯子 L1-L6 × 2軸 × prior art(章12 骨格)
6 [refactor] claude-p loops → profitable-claude
7 [#12 OpenClaw 退役] ★way after(急がない)★ 今 working 中 + 別CC 作業中。~/.openclaw 削除 + cron/key 移設(依存剥がしは #11 が第1号)
8 [★claude-p exit★] = loop の goal(terminal, 数日〜数週間)。経済自走→monitor/seed/harness を hand off→検証→out
※ bounded 安全弁(主系列の外): #7 恒久 funding loop = Franklin が本当に餓死した時のみ発火(甘やかさない)
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
- **2026-07-08 ⚠D2後の gap(honest)**: Franklin は $11.63 を持つが **loop が seed を使えない**。`~/.blockrun/logs/daemon.err` に2バグ: ①`ANICCA_WALLET_ADDRESS` 未設定→balance fetch 失敗→**tier=broke のまま**(seed が見えない、identity 解決の敏感領域=[[reference_anicca_wallets_canonical]]/Efpap5 #8 関連) ②free model `nvidia/llama-4-maverick` **429 capacity exhausted**→THINK 失敗。★送金(親の仕事)は完了・検証済だが、Franklin が実際に seed でトレードするには loop 修復(#10)が要る★。funding pipeline 自体は D1/D2 で on-chain 実証済・money-safe。
- **2026-07-08 ★#10 完了 (full VCSDD + live E2E)★**: Franklin loop 蘇生。VCSDD `franklin-loop-revival`: spec(**4反復で PASS**、5→3→2→0 findings)→RED→GREEN(33/33新+42/42regression)→impl adversary=**PASS/SAFE_TO_DEPLOY**(共有daemon の automaton/founder-loop 非影響を確認)→harden→**converge(phase6)**。deploy(franklin-loop reload)後 **live E2E**: `ANICCA_WALLET_ADDRESS=8Fpqd`(was unknown)/`OPENAI_BASE_URL=:8402`(was dead :8403)/model=`free/glm-4.7`(was 429枯渇)/`usdcBalance(8Fpqd)=$11.39`(tier broke 解消)/ledger が glm-4.7 wake で `earn/sol-trade` 等を実判断(no 429)。commit `a2185d5`。★Franklin は funded かつ loop が seed を使える状態に完全復帰。C2 の gap 解消★。

- **2026-07-08 ★#11 土台 DONE (earn-foundation deploy + 実チェーンE2E)★**: (1)earn/run.sh wallet leak 解消 `43b7375`(~/.openclaw の automaton 鍵 fallback を廃止→resolve-identity で per-instance 解決, 鍵無ければ fail-closed HALT)(2)sol-trade identity-match guard `3d97c59`(franklin-trading CLI が ~/.blockrun を hardcode するため非owner instance を HALT。automaton=HALT / Franklin=PROCEED を実測)(3)sol-trade P&L 配線 `86bd88c`(record-swap.mjs: sigStatus→usdcDeltaForSig→record、損益両方記録=record-payout の delta>0 gate と違い**損失も可視化**、sig-keyed idempotency、identity-guard に sol-trade own-source 追加=test **12/12 green**)。**実チェーンE2E**: 8Fpqd の実 sig `2aZuere…` で record-swap 完走→net_usdc `-0.008664` を confirmed 記録(scratch ledger, 本 ledger 非汚染)。★real-chain 診断★: 8Fpqd USDC=**$13.36**、直近5tx すべて ~**-0.0086 USDC の x402 推論マイクロ課金**(=loop 稼働の証拠)、**実 Jupiter swap=0件** → Franklin は損トレードで溶かしてるのでなく**そもそも trade せず WAIT**(naive-TA がノイズ回避で正しく待機、だが毎パス推論費だけ払い収入ゼロ=緩やかな出血)。残る難所=**C1(harness↔実戦略を接続して edge を出させる)**。土台(配管)は完成、あとは戦略。
- **2026-07-08 ★訂正: Franklin=multi-rail earner + verify-outputs★**: 旧「sol only/構造的に稼げない」は視野狭窄で**撤回**(Dais 指摘)。Franklin の loop は全 rail を実行(state slot 集計: sol-trade×366/x402_sell×148/cook×132/clip×104+producer109/hl_trade×103/video×96/polymarket-trade×82/token_launch×56/gig×48/yield×24)。だが earn-ledger 実現 net≈**$0.02**(gig+$0.02 / hl−$0.001 / 他 rail $0)= 回るが実現/記録が乗らない。launchd 実測: 全 loop 健康(franklin-loop wake~3.5分前 $13.33 / pm-earner running 10分毎だが資本$1.50<最小$4.95で発注ゼロ / mainloop は Anthropic 週次quota で Jul10 自然回復)。※初回「claude-p 壊れ」は空 plist-stdout ログの誤読で、独立診断が訂正(実ログは earner.log/claude-p-mainloop.out.log)。self-improve harness は live loop に非接続(C1 再定義: 戦略コード hook 無し=rail選択+heuristic/prompt を進化)。分業再確認: Franklin=自分の loop で全 rail を自走 earn / claude-p(俺)=自分の loop で稼ぐ + Franklin の harness を作り自走させる + 必要時 fund。終着=俺が out of the loop、1体の Franklin が経済を自分で築くのを witness。
- **2026-07-08 ★#11 全 rail P&L記録 監査(evidence付き, per-file:line)★**: Dais の3エンジン directive(PM/SOL/HL のみ、x402/gig 却下)に絞ると — **SOL**=✅今日 fixed(record-swap, identity-safe)。**PM**(polymarket-trade)=`redeem.py` は claude-p wallet `0x904B50d2` を**ハードコード**(per-instance でない, money-safety abort付き)→共有 run.sh に入れるのは identity-UNSAFE(**却下**、wire前 identity チェックが捕捉)。PM の redeem+record は既に `run_earner.sh`(=pm-earner cron)に正配線済、pm-earner 稼働中(edge/資本待ち)。**HL**(hl-trade→fat `run.sh:213`)=net は記録(win+loss)するが `external:true` 未設定→GATE-0 に永久非計上 + 取引所 auto-close 未照合(real/paper 確認後に修正)。x402/clip/video/token=3エンジン外 or 却下→記録投資しない。★**C1 の芯**★: self-improve は静的 fixture(`pm_history.csv`)のみで evaluate、live ledger **非接続**(`ledger_reader` は decorative OBSERVE のみ、しかも repo-root の空ファイルを読む)→ 記録を直しても promote は変わらない。真の close-loop=evaluate を実 per-instance ledger に接続(VCSDD 案件)。
出典: verify-subagent 独立検証(2026-07-08) / 各 verdict.json / launchctl(+ launchd print) / colony-status / 直接 Solana RPC(getSignaturesForAddress + usdcDeltaForSig, 8Fpqd) / 実ログ earner.log + claude-p-mainloop.out.log(plist stdout は誤読源)。
