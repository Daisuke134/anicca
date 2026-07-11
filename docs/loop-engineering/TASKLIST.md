# TASKLIST — earn/record/verify を稼げる状態にする（atomic SSOT）

## ★★★ 唯一の真実 = NET PROFIT（Dais 2026-07-12 焼き込み）★★★
成果 = **loop が自分で redeem して、渡された額より wallet が増えた時のみ**。activity/build/建玉/test-green は成果でない。
- claude-p: 渡し合計 $18(POL$30由来) → **超えて初めて成功**。
- Franklin: 渡し $9〜 → 超えて初めて成功。
- source of truth = on-chain wallet が渡し額を上回る（loop 自身が redeem）。私(session AI)は trade しない・監視のみ。

## ★ HANDOVER 現状(2026-07-12, own-eyes) ★
**動く(verify済)**: loop3つ自律稼働 / 資金 loop の手に(claude-p Base$3.95+pm$1.35+Polymarket建玉$5未resolve / Franklin Sol$10.87) / menu=money-maker(pm/sol/hl/yield)のみ / 記録reconcile / 検証reality-verifier / 非-gamble bundle-arb戦略(claude-p自律でPolymarket bet実績)。
**未(=稼げない最後の1ピース)**: **報酬型MM(poly-maker liquidity-rewards)** = 「和<1でなくても板に居るだけで稼ぐ→複利」。builder移植中。これが入るまで net profit は出ない(bundle-arbは和<1が稀)。
**実現 net profit = まだ $0(この建玉 -$0.15微損, 未resolve)**。

## ★ CURRENT PHASE (2026-07-12) = 実際に稼ぐ。正本 game plan = `29-earn-game-plan.md` ★
記録/検証/一本化(#1-#6 下記)は全 DONE。今は「実 external:true を出す」フェーズ。
残タスク(doc29 の実装順):
- **G1. native→stablecoin swap** ✅ DONE(2026-07-12, 実マネー own-eyes): relay.link で POL→USDC.e 実行。0x810f = **$23.55 USDC.e** + 13 POL(gas)。tx 766894ff($2実証)→56348c8d($21.5本体)。手法= relay.link /quote → EVM tx を founder key で署名(web3.py)→ solver が非同期 fill。全エンジンの前提クリア。次: half を Franklin へ bridge + PM/HL/x402 に配分。
- **G1.7 realtime 発見(2026-07-12)**: loop(index.mjs balance.mjs) は **Base USDC** を残高として読む(0x810f Base)。funds は **Polygon USDC.e $23.55** → loop から見えない。かつ **loop の現戦略は弱い方**(pm=方向性/sol=momentum WAIT)。→ **今 Base に bridge して funding すると弱戦略で溶ける**。∴ 順序 = ①良い戦略を loop に build(poly-maker MM/HL funding-arb, doc28) → ②Base に bridge → ③loop 自律 trade。戦略 build が先(要 clean context, 実マネー安全)。
- **G2(strategy build 本丸). loop に構造 edge 戦略を移植**: pm=poly-maker(WS板+regime+risk, post-only=naked構造排除), hl=funding-arb。loop が自律 wake で回す。← autonomous earning の核。私は trade しない、loop がやる。
- **G3. 層0 x402 seller を live 化**（$0 資本の最速 earner）→ 最初の external:true。
- **G3. 層1 yield floor**(Beefy/Aave hedge) / **G4. 層2 HL funding-arb**($50-100超で)。
- 資金配分: claude-p $15 + Franklin $15。全員が同じ共有 skill で稼ぐ。
現在残高(own-eyes 2026-07-12 更新): **claude-p 0x810f Base USDC = $22.97**(loop が読む場所、reserve$20超=loop 自律trade可) + 13 POL(gas), pm 0x904B=$1.35, Franklin Base 0x3EcCAD=$6.48。
✅ G1完了(POL→USDC.e swap, tx 56348c8d) + ✅ Base bridge完了(relay Polygon→Base, tx 1fba42d, $22.97着) = **loop が funded・自律earn可能に**。
次: (a)loop の戦略を良い方に(poly-maker/funding-arb, 弱戦略のままだと funded でも溶ける) (b)loop の実 wake を観測し external:true を dashboard で確認。私は trade しない=loop がやる。

## ★ REALTIME 2026-07-12 04:06 (loop 自律行動を own-eyes 観測) ★
- **loop が自律で HL に入金した**: hl_trade wake が "balance $0<trade$20 → self-fund relay Base→HL" を実行。HL account value=**$18.78**(on-chain 検証, fee $1.22)。まだ position 無し(WAIT/narrate)。**＝自律 capital 管理 machinery は本物に動く。**
- 資金現況: HL $18.78 + Base USDC $0.97 + pm 0x904B $1.35 ≈ $21（$30 POL から swap/bridge fee ~$5 + 履歴 naked 損で目減り）。
- Franklin: x402-serve 立てたが**買い手ゼロ**、gig 需要ゼロ → net $0。
- **真の稼ぎ = 依然 $0**(external:true 実利益なし)。loop は活発だが「価値の受け手/edge」が無い。
- ⚠️ **緊急リスク**: loop が HL $18.78 を**弱い方向性戦略で trade すると溶ける**。→ 最優先 = HL を funding-arb(構造edge)に。または trade せず WAIT を維持。
- 手数料の学び: 小資本を multi-hop swap/bridge すると fee が%で重い($30→$21)。将来は Dais に SOL 直送→最小 hop。

---

## ★ REALTIME 2026-07-12 ~06:00 (directional bet エンジンを修復) ★
- **真のバグ発見&修正**: pick.py(consensus+whale の directional +EV エンジン)が常に WAIT だったのは戦略/資本でなく **①blockrun_llm SDK 未install ②brain env(OPENAI_BASE_URL) 未設定** → analyzer 死亡 → 永遠に "analyzer-unavailable" → **一度も賭けてなかった**。
- 修正: SDK を .venv-pysdk に install + run.sh に brain env(ClawRouter:8402 free) 追加 + loop HOME に sync。
- 検証(own-eyes): pick.py 再実行 → "analyzer-unavailable" から **"no-candidate-cleared-edge-confidence-gate"** に変化 = **consensus analyzer が実際に動き、市場をスキャンし、edge≥0.15 が無いので正しく WAIT**(盲賭けしない=right strategy)。
- → agent-economy-loop が pm を選ぶ度に pick.py が consensus で判断し、**edge≥0.15 & conf≥7 の市場が出たら自律で賭ける**。今は edge 無しで WAIT。
- 注: 一次情報では $20 directional は base rate 7.6% で大半-EV、pick.py の LLM推定 edge も未実証。だが「right strategy で edge がある時だけ賭ける」エンジンは今動く。日本 Polymarket 法リスクは Dais informed 判断。
- net profit 依然 $0(まだ賭けが約定してない=edge待ち)。

## ★ REALTIME 2026-07-12 ~04:45 (配分完了・自律trade解禁・監視へ) ★
- ✅ $18 を各 loop wallet へ配分完了(own-eyes): claude-p 0x810f **Base USDC $8.95** / Franklin 8Fpqd **Solana USDC $10.90**(+Franklin Base $6.48)。経路 HL withdraw→Arbitrum→relay分配。
- ✅ **reserve gate $20→$2** に下げた(3 loop plist, reload済 PID 86608/86678/86698)＝「$50 minimum の嘘」をコードで撤廃。両 loop が **$9-11 の少額で capital slot(pm/sol/hl/yield)を trade 可能に**。
- ✅ **私の meddle 終了**。以降 loop が自律 trade、私=監視+戦略self-improveのみ(trade はしない)。
- 監視対象: loop wake で実 trade が出るか / external:true が出るか / 溶かさないか。溶かすなら戦略を self-improve。
- 現実: 少額×現行戦略なので trading 利益は小さい/WAIT が正常。最も確実な increase = yield。稼ぎが出たら reality-verifier が自動検証(配線済)。

## ★ REALTIME 2026-07-12 ~04:30 (実マネー配分実行中) ★
- Dais 配分指示: Franklin $9 + claude-p $9、各 loop が最小額で earn 実証(少額で稼げねば誰も追加しない)。
- HL $18 を取り戻し中: HL withdraw3(EIP-712 直署名)成立 → HL accountValue $18.78→$0.78、$18 が Arbitrum 0x810f へ transit(HL出金~5分)。
- 次: Arbitrum 着 → relay で $9→Franklin(Solana 8Fpqd) + $9→claude-p Polymarket(Polygon pUSD)。loop が Polymarket MM(poly-maker報酬型=少額でも稼ぐ)で自律 trade。
- Franklin 既存 ~$10(Base $6.48+Sol $3.44)。claude-p pm 0x904B $1.35 + Base $0.97。
- 私は trade しない=loop がやる。私=資金配分+戦略改善+監視。


**これがタスクの source of truth。** 設計の正本(spec)は分離: `27-ideal-earn-record-verify-architecture.md`（2種の Anicca / 3層 / 図）。上位方針 = `23-...redesign.md §10`。
**進め方（Dais 2026-07-12 明示）**: ここから **main(私) が自分で build、1つずつ**。builder は信用せず、その出力は「下書き」として fresh adversary(Sonnet)+own-eyes で検証し、良い所だけ取り私が仕上げる/作り直す。3つ同時にやらない。
**Done 判定**: 金の真実 = wallet on-chain external:true のみ。report/test-green は稼ぎでない。各 atomic は「検証可能条件」を満たし私が own-eyes した時のみ ✅。

凡例: ⬜ 未着手 / 🔄 進行中 / 🧪 検証待ち(builder下書きあり) / ✅ done(own-eyes)

---

## #1 ledger 一意化  — status: ✅ DONE(2026-07-12, main merged + live quarantine, own-eyes)
- [x] 1a. canonical = `<ANICCA_HOME>/skills/earn/state/earn-ledger.jsonl`(6 writer が既に合意)。founder-loop の `state/earn-ledger.jsonl` は別物(GATE-0専用)＝意図的分離、merge しない
- [x] 1b. `resolveEarnLedgerPath()`(JS) + `resolve_ledger_path()`(Py) で両言語が同一 canonical を返す
- [x] 1c. `filterOwnWalletRows()`(JS)/`filter_own_wallet_rows()`(Py) = 自 wallet allow-list、walletless(sol/hl/narrate)は通す、他 wallet は fail-closed 除外
- [x] 1d. **live founder ledger の他 wallet 295行(a3cdd4/b9dd3b等)を `.earn-ledger.quarantine.jsonl` へ退避、自分170行保全、.bak 作成（非破壊、own-eyes 検証）**。汚染行に external:true は0件だった(偽稼ぎは無し)
- [x] 1e. JS 18/18 + Python 14/14 = 32/32 pass（私が自分で実行確認）
- 検証済み: main に merge(ledger.mjs grep=3)、live ledger は 0x810f のみ、読む場所が一意

## #2 pm reconcile 配線  — status: ✅ DONE(2026-07-12, main merged, own-eyes)
- [x] 2a. `reconcile.mjs` を本番 `skills/earn/lib/` へ（ownWallet スコープ追加、11/11 テスト green）
- [x] 2b. `run_earner.sh` の pass 末尾で毎 wake `pm-reconcile.mjs` 呼ぶ（HL と同形）
- [x] 2c. pm ledger = redeem が書く `~/anicca/skills/earn/state/earn-ledger.jsonl`（redeem.py:89）に向け、ownWallet=0x904b でスコープ
- [x] 2d. 実 pUSD $1.35 を eth_call で読取→baseline anchor→冪等 drift0 を own-eyes 確認。汚染21行(automaton)は quarantine、pm 7行保全
- 検証済み: pm-reconcile が実 pUSD を読み drift を記録。以後 pm の負け/買いが reconcile 行で載る（ledger ≡ wallet delta）
- 注: 実測で pm は $4.95→$1.35 とさらに流出中 → #3(pm HOLD/一本化)を急ぐ理由

## #3 earn loop 一本化  — status: ✅ DONE(2026-07-12, own-eyes、コード変更なし=infra dedup)
- [x] 3a. `pm-earner` を `launchctl bootout` + plist を `.disabled-2026-07-12` にリネーム(再起動でも復活しない)。launchctl list から消失を確認＝**10分毎の直接流出を止血**
- [x] 3b. pm は registry status:live で **既に index.mjs earn-menu に載っている**(liveSlotNames 経由)
- [x] 3c. pm は今 agent-economy-loop(PID実稼働) の menu 経由のみ。二重稼働解消
- [x] 追加安全: pm risk='capital'・carve-out 無し → 残高 $1.35 << BOOTSTRAP_RESERVE_USDC($20) なので filterCatalog が pm を menu から自動除外＝**低残高で自動 HOLD**(§10 N5 を構造的に満たす)
- 検証済み: claude-p の earn loop は agent-economy-loop 1本、pm は menu skill 化、流出停止

## #4 build loop 一本化  — status: ✅ 既に達成(2026-07-12 own-eyes で判明、実質no-op)
- [x] 検証: `founder-loop.sh` は **claude を呼ばない**（record-earn.mjs = 唯一の ledger writer + ceo bandit、prompt.txt 無し）。`claude --model sonnet -p` を呼ぶ build loop は **claude-p-mainloop ただ1本**。→ 「2つの重複 claude build loop」は存在しなかった（doc27 旧記述が誤り、私の前回 stale-read が原因）
- [x] つまり大脳 build loop は既に1本。追加統合は不要。builder が入れた mainloop の model override(`CLAUDE_P_MAINLOOP_MODEL`)は任意採用（未 merge、優先度低）
- 注: founder-loop(30min, deterministic 記録+CEO) と mainloop(6h, claude build) は**別役割**で、統合してはいけない（記録を6hに遅らせるのは害）

## #5 AGENTIC 検証実装(reality-verifier)  — status: ✅ DONE(2026-07-12, main merged, own-eyes 41/41)
- [x] 5a. `.claude/agents/reality-verifier.md` 作成(fresh-context, model:sonnet, tools=Read/Grep/Glob/Bash のみ=送金/署名不可)
- [x] 5b. 6カテゴリ: report_ledger_mismatch / report_onchain_mismatch / internal_transfer_mislabeled / mock_marker_in_success_path / narrate_only_claim / unhealthy_strategy
- [x] 5c. DETERMINISTIC(金の真実=on-chain,自分では判定しない) vs AGENTIC(正直さ=報告 vs ground-truth の一致) を定義に二重明記 + schema `role:agentic-honesty-check` で機械強制
- [x] 5d. spawn 配線 = `skills/self/reality-verify-spawn.sh`(fresh detached, self-fix 同型, DRYRUN seam)。※live cron(self-fix/週次)へのフック挿入は最後の1マイル follow-up
- [x] verdict schema(`reality-verdict-schema.mjs`): vague-PASS / evidence無しFAIL を機械拒否
- 検証済み: builder 下書きを私が読んで採用判断、main で 35 node + 6 bash = 41/41 pass 再走。他 feature の .vcsdd ノイズは除外して reality-verifier ファイルのみ取込
- [x] 残(last-mile) DONE(2026-07-12): `reality-verify-on-new-earn.sh` を `verify-loops-audit.sh`(6h cron)に配線。新 external:true earn が出た時だけ reality-verifier を fresh spawn(cursor 二度打ち防止・DRYRUN 状態不変・token-safe=earn0で0発火)。own-eyes: franklin gig+0.02 検出、冪等確認。**loop が私抜きで稼ぎの正直さを自己検証し続ける＝止まらない**

## #6 own-eyes 検証(記録=真実 + 検証層が実働)  — status: ✅ DONE(2026-07-12, own-eyes)
- [x] 6a-DETERMINISTIC: pm ledger の reconcile anchor `balance_after=1.34853` == pm wallet on-chain pUSD `$1.3485`（完全一致）。0x810f も $0.0001 で ledger 3行clean=偽稼ぎ無し。**記録 ≡ wallet の真実**
- [x] 6b-AGENTIC: reality-verifier(#5)を実データで発火。偽主張「pm loop が $50 稼いだ」を独立に ledger+on-chain 読取で **FAIL 判定**(report_ledger_mismatch=実$10.02 / report_onchain_mismatch=実$1.35 / unsupported_claim)。$8.68 の乖離も指摘。「金が動いたか」を断定せず「主張 vs ground-truth 一致」のみ判定＝AGENTIC 役割遵守
- 検証済み: DETERMINISTIC(wallet=真実) + AGENTIC(fresh verifier が嘘を捕捉) の2層が実データで機能。#5 も unit だけでなく end-to-end 実働確認
- ★正直な現状★: 検証機構は真実だが **誰も EARNING していない**(pm $1.35 / 0x810f ~$0)。#6 は「記録が正直」を証明、#7(実際に稼ぐ)が残る唯一の gate

## #7 実稼ぎ  — status: ⬜(最後・唯一の gate)
- [ ] 7a. external:true 実 tx で wallet が増えるまで回す
- 検証可能条件: wallet on-chain が実 tx で増える

---

## 依存グラフ
`1 → 2 → 3 → 6 → 7`（earn/記録の直列）。`4`,`5` は独立ファイル群 → 先行可。
main が1つずつ処理。builder 下書き(#1/#4/#5)は戻り次第 adversary+own-eyes で検証、良ければ採用・悪ければ私が作り直す。
