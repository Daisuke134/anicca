# SPEC — メインループの GOAL 再設計（goal engineering）＋ 私の役割 = monitor

> 2026-07-12。**忘れないためにここに焼く**。evidence 正本 = [[../loop-engineering/27-long-horizon-goal-engineering-BP]]（web裏取り済BP）+ [[../loop-engineering/17-agent-economy-deep-research-2026-07-10]] §10(理想10部品)/§11。VCSDD feature 名 = `mainloop-goal-northstar`。

## 0. 何が壊れているか（今回の脱線から学んだ罪）
- ★**手作業で機能を建てるのは罪**。建てるのは"ループ"。claude-p(対話中の私)が手でVCSDDを回した時点で、無人ループの意味を殺し、Dais に babysit させた＝二重の human loop＝全部無駄。★
- 今の GOAL（`~/anicca/skills/self/claude-p-mainloop-prompt.txt`）= 「Franklin を self-heal / もっと稼がせる親」＝**看護師型**。理想（10部品の agent 経済）を北極星に持たないので「もっと稼ぐ」に収束し、経済を**建てない**。

## 1. 実機の事実（2026-07-12 確認）
| 項目 | 値 |
|---|---|
| daemon | `~/Library/LaunchAgents/ai.anicca.claude-p-mainloop.plist`（load 済・稼働中・pause 無し） |
| 周期 | StartInterval **21600s = 6h** |
| script | `~/anicca/skills/self/claude-p-mainloop.sh`（`claude --model sonnet -p "$(cat prompt.txt)"`、timeout 3600） |
| **GOAL（頭脳）** | `~/anicca/skills/self/claude-p-mainloop-prompt.txt` ← **ここを書き換えるのが全て** |
| 停止 | `~/.anicca/claude-p-loop.pause` を置く |
| 最終実行 | 2026-07-11T16:10Z exit0「EXIT-CHECK 未達→継続」 |

## 2. TODO（全て VCSDD で実施。手作業で"それっぽく"直さない）
- [ ] **T1. GOAL 書き換え（最重要）** — prompt.txt を「看護師型」→「建築家型」に。焼く内容:
  - **北極星**: 「**自立市民の数**（自 wallet で自 compute を賄える net-positive な AI の頭数）を増やせ」。数字＝検証可能、無限＝終わらない（[[27]] §1 Anthropic right-altitude / Stanley objective-paradox）。
  - **地図**: 毎 wake に理想（[[17]]§10 の10部品）と循環マネー/検証の核心を読ませる。
  - **差分ループ**: 「理想 vs 今 を測る → 一番デカい**欠けを1つ**選ぶ → VCSDD で建てる → ground-truth 検証 → self-merge → 繰り返す」。**何を建てるかは agent が毎回発見**（人が具体タスクを指定しない＝1回で終わらない）。
  - **反 Goodhart**: 単一 KPI に縮約しない。「tx 件数」「wake が走った」を成果と呼ぶの禁止。実 external USDC / 実自立のみ（[[27]]§2 DeepMind spec-gaming）。
  - **bound**: 各反復に終端条件（max_turns / timeout / fresh adversary の done 判定）（[[27]]§5）。
  - **報告**: 毎サイクル「北極星の数字・選んだ欠け・建てた物・証拠」を MAINLOOP-LOG に。
- [ ] **T2. verifier を本物に** — done 判定が self-report でなく **on-chain tx / ledger 実増 / 実 URL** の独立再検証か（[[../loop-engineering/23-anicca-loop-architecture-redesign]] §0 の3原則）。
- [ ] **T3. 私（claude-p 対話）の役割を monitor に固定** — ログ / on-chain / ledger を見て「ゴールへ進んでいるか・嘘をついていないか」だけ確認。**手を出さない**。
- [ ] **T4. 1サイクル無人実行を観測** — 迷走 or 嘘があれば **GOAL 文 か verifier を直す**（ループ自体は止めない・手で肩代わりしない）。

## 3. done 条件（検証可能）
- T1: prompt.txt に北極星＋差分ループ＋反Goodhart＋bound＋報告が入り、次 wake のログで「理想 vs 今 の差分から欠けを1つ選んだ」痕跡が出る。
- T2: done 判定のコードが report テキストでなく決定的チェックを読む。
- T3/T4: 私が手で build した形跡がゼロで、ループのログに自律の1サイクルが残る。

## 4. 禁止
- 私（対話 claude-p）が feature を手で VCSDD 実装すること。ループの仕事を奪わない。
- ゴールを「具体タスク1個」にすること（1回で終わり human 復活）。曖昧な精神論にすること（迷走）。→ right altitude を守る。
