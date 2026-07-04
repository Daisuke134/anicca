# Feature: bet-research-predict (VCSDD, strict) — #25 BET-RESEARCH

## Goal (verifiable)
PM の directional 賭けを「research-driven」にして勝率を上げ、複利を加速する。franklin-bet の予測エンジン(web + prediction-market odds をリサーチして根拠付きで結果を pick)を、我々の PM earn に配線する。

## Context (grounded 2026-07-05, 実データ)
- 現状の PM = market_maker.py(両建て maker + LP報酬)+ bundle_arb.py(YES+NO<$1 裁定)。★research-driven な directional 選択は無い★。Morocco/Wimbledon の勝ちは market-making のフィルが結果的に有利に resolve しただけ(意図的な予測選択ではない)。
- franklin-bet(BlockRunAI/franklin-bet)の予測 = `franklin predict` モード(research-only toolset: web search/Exa/X/live prediction markets/market data)。
- ★grounding の重要発見★: installed `@blockrun/franklin` CLI に `predict` サブコマンドが★無い★(`franklin --help` = doctor/help のみ、`franklin predict` は一般 help に落ちる)。→ franklin-bet の予測は repo の `scripts/generate.mjs --agent`(内部 `scripts/lib/agent.mjs` が franklin prediction mode を driving)経由 = ★単純な CLI 呼び出しでなく、franklin-bet repo の engine を使う/または franklin を予測対応版に upgrade する必要★。
- コスト: franklin predict は有料 research(paid model + x402)。1予測あたり課金。self-funded なら OK だが claude-p(human-funded)で乱発は注意。

## Requirements (EARS)
- R1: PM の earn pass で、resolve 前の rewards/流動性のある市場に対し、research 予測(franklin-bet engine)で outcome + confidence を得る。
- R2: WHEN 予測の confidence が閾値超 かつ edge が手数料(fee schedule)を上回る THE system SHALL その side に directional 建玉を置く(size は Kelly 比 or 固定小額)。
- R3: 予測が弱い/edge が手数料未満なら建玉を置かない(WAIT が正しい)。
- R4: 勝った建玉は既存の自律 redeem(§44)で回収 → 複利。
- R5: 予測コストを ledger に記録(research コスト vs 期待値)。fail-closed。

## DONE (adversary が verify)
1. franklin-bet engine が我々の PM から呼べる(実装経路が確定、実行して予測が返る fresh evidence)。
2. 予測 confidence + edge の gate が閾値未満で WAIT、超過で建玉、を実データ or テストで確認。
3. 実際に1回 research-driven directional 建玉が置かれ、resolve→自律 redeem で realized に載る(no-mock、時間かかるので建玉までを実証、redeem は §44 の loop に任せる)。
4. コスト記録が ledger にある。

## Non-goals / OPEN(Dais 判断)
- ★franklin-bet engine の統合方法★: (a) franklin-bet repo を clone して generate --agent を叩く (b) @blockrun/franklin を予測対応版に upgrade (c) research-only toolset(web/odds)を自前で薄く実装。→ どれにするか + コストを許容するか = Dais 判断。
- 現状の複利コア(market-making + 自律 redeem)は既に動作。#25 は「勝率を上げる edge の追加」= 必須でなく enhancement。
