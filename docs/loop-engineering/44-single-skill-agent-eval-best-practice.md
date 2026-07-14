# 単一 skill × loop agent のテスト best practice（2026-07-14 調査）

対象: 「agent の menu を1 skill に絞り、実世界アウトカムで検証する」方法の業界標準。
用途: x402_sell → bounty → affiliate(clip, video) を同型でテストする harness (#13) の設計根拠。
調査: tool-eval-research subagent (sonnet)、一次ソース確認済み。

## 結論

「menu 制限 + 実世界アウトカム N episode 計測」= **tool/capability ablation として確立された手法**。
最も直接の先例 = Berkeley BFCL v4 §6.3（tool ON/OFF の2条件比較で因果を分離）。
実務家が上に足す3点: ①trajectory レビュー ②error taxonomy ③pass^k。

## 出典付きプラクティス表

| プラクティス | 出典 + 核心引用 | 我々への写像 |
|---|---|---|
| ACI をテストしてから loop へ | Anthropic "Building Effective Agents" (2024-12) https://www.anthropic.com/engineering/building-effective-agents — "Test how the model uses your tools: Run many example inputs... to see what mistakes the model makes, and iterate." | skill の tool 定義を手動で多数回叩き、誤用パターンを先に潰す |
| sandbox で拡張テスト後に自律運用 | 同上 — "extensive testing in sandboxed environments, along with the appropriate guardrails" | live-enable 前の dry-run/spend-cap は正式裏付けあり |
| 毎ステップ ground truth | 同上 — "crucial for the agents to gain 'ground truth' from the environment at each step" | 各 wake で on-chain 残高実測を必須ステップに |
| end-state で判定（trajectory でなく） | Sierra tau2-bench docs/evaluation.md — reward = DB end-state hash 比較。actions は「参照軌跡であり要求ではない」 | 「売れたか」= wallet 残高の増分で判定。手順の綺麗さは問わない |
| **pass^k** | Yao et al. τ-bench arXiv:2406.12045 — "a new metric (pass^k) to evaluate the reliability of agent behavior over multiple trials... gpt-4o pass^8 <25% in retail" | 単発成功で「動く」と言わない。k=4〜8 の独立試行で毎回成功するか |
| 自動エラー分類 | tau-bench auto_error_identification.py — "(1) Fault assignment (user/agent/environment) (2) Fault type (used_wrong_tool, wrong_argument, ...)" | 失敗 wake を skill バグ/market 起因/判断ミスに分類してから合否 |
| **tool ablation（直接の先例）** | BFCL v4 blog §6.3 https://gorilla.cs.berkeley.edu/blogs/15_bfcl_v4_web_search.html — "by rerunning evaluations with the search tools disabled... accuracy drops dramatically without tool usage" | 我々は逆方向（1 tool のみ ON）だが同じ因果分離ロジック |
| 決定論的検証（LLM-judge でなく） | BFCL 同上 — "AST based, or state-transition based verification ensuring determinism" | verify-inflow の on-chain 実測 = 業界標準と一致 |
| offline → online 二段階 | LangSmith Evaluation docs — "Offline Evaluation: Test before you ship / Online Evaluation: Monitor in production" | 新 skill はまず少数 dry-run → loop 本番でオンライン監視 |

## harness への実装レシピ（#13 の仕様）

1. **Isolation**: `ANICCA_SLOT_ALLOWLIST=<skill>`（capability ablation。因果帰属の担保）
2. **試行数**: 最低 k=4（厳密には 8）の独立エピソードで pass^k を計測。単発 PASS は楽観バイアス
3. **成功指標**: end-state = on-chain external 増分（self-pay 除外）。決定論チェックのみ、LLM-judge 不使用
4. **対照群**: 同 loop を allowlist=空(何もしない menu)で走らせ 0 件を確認（BFCL 方式の逆条件）
5. **PASS 条件3点セット**: pass^k ≥ 閾値 + on-chain ground-truth + 失敗の fault taxonomy 分類完了
6. **落とし穴**: eval leakage（本番と同一 loop/prompt で回す）／metric gaming（"Avoids Tool Usage" 型 — trajectory ログのレビューを併用）／pass^1 と pass^k の乖離

## 我々の現在地への適用

- founder の外部着弾 2 件 = **pass^1 相当**。「x402_sell skill が動く」と言い切るには claude-p / Franklin での再現 + 複数 wake での安定を待つ（今の watch 設計がそのまま計測器）
- 対照群は事実上ある（x402 掲載前の全期間 = external 0）が、正式には allowlist=空 run を1本置くとより厳密
- fault taxonomy は wake log (daemon.err.log) + ledger + verify-inflow の3ソースから分類可能
