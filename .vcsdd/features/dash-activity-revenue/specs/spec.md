# Feature: dash-activity-revenue (VCSDD, strict) — #18 DASH

## Goal
claude-p と Franklin の per-agent dashboard が「revenue ~$0 / waiting for next wake」なのを直す。両 poster に ★log(直近の実 ledger 活動)★ と ★revenue_by_source(実 realized を per-source)★ を追加し、実際の稼ぎと活動を dashboard に流す。

## Context (grounded 2026-07-05)
- 真因: telemetry-post-claude-p.mjs / telemetry-post-franklin.mjs は stripped-down = payload に net_worth_usd + revenue_mo_usd(★未実現 upnl★)だけ。log も revenue_by_source も送っていない。→ dashboard は活動0("waiting for next wake") + revenue 未反映("no measurable revenue")。
- 汎用 telemetry-poster.mjs(automaton)は正しい: 直近20 ledger 行 + revenue_by_source(revenue.mjs)を送る。payload = {net_worth_usd, daily_revenue_usd, monthly_revenue_usd, revenue_by_source, log}。
- 実データは存在する: claude-p の realized = ~/anicca/skills/earn/state/earn-ledger.jsonl(source:polymarket-redeem の $5.99)。Franklin の活動 = ~/.blockrun/state/ledger.jsonl(hl_trade/sol-trade wake)。
- claude-p は proxy body(~/.anicca-founder)でなく pm-earner の earn-ledger(mother path)を読むべき。

## Requirements (EARS)
- R1: telemetry-post-claude-p.mjs の payload に ★log★(claude-p の実活動の直近~20行: earn-ledger の redeem/trade + wake)を含める。
- R2: 同 payload に ★revenue_by_source★(realized per-source、~/anicca/skills/earn/state/earn-ledger.jsonl を claude-p wallet 0x904b… でフィルタ、revenue.mjs 再利用)。monthly_revenue = Σ by_source。
- R3: telemetry-post-franklin.mjs にも log(~/.blockrun/state/ledger.jsonl 直近~20) + revenue_by_source(Franklin の realized)。
- R4: 偽の数字を作らない(実 ledger のみ、無ければ空/0、fail-closed)。既存の net_worth/署名は壊さない。
- R5: 未実現 upnl を realized revenue として偽装しない(revenue_mo は realized ベース、未実現は別扱い or 0)。

## DONE (adversary が verify)
1. telemetry-post-claude-p.mjs / franklin.mjs の payload に log[] と revenue_by_source が含まれる(コード確認)。
2. ★live 検証★: 両 poster を実走 → dashboard-sync の claude-p/Franklin 行に log entries>0 + revenue_by_source が実 ledger と一致(claude-p は redeem $5.99 が source:polymarket-redeem として出る)。
3. 偽の数字ゼロ(realized のみ、未実現を revenue と偽らない)。署名 POST が 202 継続。

## Non-goals
- dashboard フロント(page.tsx)の描画変更(既存が log/revenue_by_source を表示する前提)。family tree / self率(別: #26)。
