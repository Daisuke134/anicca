# 14 — Cold-start escape: how self-improving trading agents actually get an edge (evidence + copy-able BP)

> 2026-07-10。Dais「search-first: self-improvement leap は未解決、web+gh で BP を探し clone してコードを読め」への回答。全項 clone 済 repo の file:line 出典付き。記事⑤「self-improvement をどう本当に効かせるか」の核 + Franklin cold-start 修正の設計正本。

## 我々の trap（精密診断、自コード file:line）
- `~/anicca/skills/earn/lib/evolve.mjs:27,132-137` — `DEFAULT_MIN_REDEEMS=3`(K)。`evaluatePromotion` は `redeem_count < K` で promotion 拒否。genome が一度も trade しない → redeem_count 永久 0 → **gate は永遠に開かない**。
- `sol-genome.mjs` の mutation = **対称 coin-flip**（`direction = rng()<0.5 ? -1 : 1`）を baseline+override から毎 cadence 引き直し。∴ 存在する探索機構すら ~50% で gate を締め、一方向に複数歩進まない → starvation から出られない。
- `sol-gate.mjs::decideEngagement` は毎 pass `conviction/wouldEngage` を**既に計算**し `sol-gate-cli.mjs:121` が**無条件 trace**（REQ-011）。near-miss シグナルは trace に在るが、evolve/promotion pipeline は realized ledger P&L しか読まず**死にデータ**。

## clone して読んだ repo（scratchpad/research/）
| repo | 何 | cold-start を破る key code | copy 可 |
|---|---|---|---|
| `algorithmicsuperintelligence/openevolve`(6.6k★, OSS AlphaEvolve) | LLM 進化的プログラム合成、MAP-Elites+island | 失敗/0点プログラムを**捨てず** `{error:0.0}` で population に残す(`evaluator.py:265`)、prompt に**best でなく diverse sample を注入**(`prompt/sampler.py:385-457`) | ○ near-miss を data 化 |
| `tarsyang/quantevolve`(OpenEvolve fork, quant) | Binance backtest で戦略進化 | `if num_trades<2: combined_score=min(_, -50.0)`(`quant_evaluator.py:284-287`)= 殆ど trade しない戦略を**hard penalty**→「never trade」から離れる fitness 勾配。seed は SMA-crossover で**積極的に trade**、選択で規律を足す（保守 seed + 変異頼みの逆） | ○（連続 fitness 要） |
| **`mq545/polyevolve`（prediction-market、Franklin と最も近い）** | 解決済み歴史 Polymarket/Kalshi で genome(prompt+data重み+sizing)を進化、live 資本ゼロ | **exploration/confirmation の水平分割**(`ARCHITECTURE.md:1-40`): 「EXPLORATION(上)=無制限・$0・信じない / CONFIRMATION(下)=forward paper-bet の実績を rubric で通ったものだけ信じる」。abstain-all は fitness ~0(neutral、punish せず)だが**これは探索が offline 歴史 corpus 上で走るから**成立(`fitness.py:94-98`)。mutate は mu+lambda・train選択/val報告・Gaussian jitter=**我々の mutate() と構造同型**(`optimizer.py`) | ◎ **最適合** |
| `jennyzzt/dgm`(Darwin Gödel Machine, Sakana) | 自己改変 coding agent、diff を benchmark で実証 | 親選択が**greedy-best でない**: `prob ∝ sigmoid(10(score-.5))×(1+children)`(`DGM_outer.py:83-100`)= 低スコア親も非ゼロ確率で選び diversity を枯らさない | △ population 化時 |

## Franklin cold-start への copy+tweak（ランク付き、VCSDD で harness-not-cook）
1. **【最優先】PolyEvolve の exploration/confirmation split を sol-evolve に mirror**: promotion を live `redeem_count≥K`(構造的にデータ枯渇)だけに gate せず、**歴史 SOL 価格/liquidity を backtest replay**（offline・$0・無制限）し、同じ `decideEngagement`/conviction 式で各 candidate genome の「would-have-traded 回数 + simulated P&L」を生成、rubric(十分な would-engage 数・非退化)を通った genome を**live baseline に promote**。live wake は discovery でなく confirmation/monitoring に。出典 `polyevolve/ARCHITECTURE.md:1-40`。
2. **【次】QuantEvolve の非対称探索を既存 mutate() に**: starvation signal（N 連続 skip / redeem_count が M pass 0 のまま）検知時、mutation direction を **loosen 方向に強制**（MIN_MOMENTUM/MIN_CONVICTION を下げる）し、最低1回 trade が出たら対称 random に戻す。= 決定論的 bookkeeping（starvation counter を読み RNG 分岐を bias）で judgment でない → `rules/building-effective-ai-agents.md` の「hardcode judgment 禁止・tool/算術のみ」に適合。出典 `quantevolve/quant_evaluator.py:284-287`(penalize→bias に適応、gate が binary K ゆえ)。
3. **【安価・#2 と同時】既 trace の near-miss conviction を evolve へ供給**: `sol-gate-cli.mjs` が REQ-011 で既に `wouldEngage/conviction` を無条件 log = evolve にとって死にデータ。OpenEvolve の「0点 attempt を population data 化」(`evaluator.py:265`+diverse sample)を mirror し、#2 の starvation 検知が同 trace log を読む。

## 正直（hype vs real）
- OpenEvolve/AlphaEvolve は**安価・高速・決定論的な evaluator を持つ領域**（kernel 速度・packing・backtest Sharpe）では genuinely 新規改善を出す。live trading が hard な理由はまさに evaluator(実 fill・実時間)が遅く高価だから → だから真面目な repo は全部**まず backtest/歴史 replay で進化**し forward confirmation 後にだけ「信じる」。**live wake-cycle 結果のみから backtest bootstrap 無しで genome を進化させる repo は皆無** = Franklin が今嵌っている、最もデータ枯渇した最難経路。
- DGM/Voyager 型「自己改変 harness」は dense reward の code/skill 領域では real。だが **self-modify + live capital + rare-event reward** を閉じた repo は見つからず = 現状 genuinely 未解決の最前線。PolyEvolve も README で明言「Paper predictions only – no live trading」。
- bandit の forced-exploration（epsilon-greedy/optimistic-init/UCB）は教科書標準で #2 に直接対応するが、「skip-gated trading agent の epsilon-greedy threshold 緩和」の既製 repo は無い = 小さく既知の primitive を自作（低リスク）。durable live edge を進化させる困難な主張には既製解無し。

→ 記事⑤の実 BP = この3機構 + 「backtest bootstrap してから live」。Franklin 修正 = #1(backtest bootstrap) + #2(非対称探索) を VCSDD で sol-evolve/sol-genome に copy+tweak（次 context）。関連 [[08-evidence-eval-driven-earning-verdict]] [[06-harness-engineering-weng]] [[03-franklin-as-nested-loops]]。
