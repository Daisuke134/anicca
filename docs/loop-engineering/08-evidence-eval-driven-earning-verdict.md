# 08 証拠ベース評価 ── eval-driven-earning は "良い" か（外部検証、意見でなく引用）

> ★方法論の訂正★: 私(claude-p)は一度 eval-driven-earning を「良い」と自分の判断で断定した。これは evaluation/spec/verification-driven の違反（vibes 判断・引用ゼロ）。撤回し、**3本の外部検索 subagent が集めた引用のみ**で判定し直した。以下は私の意見ではない。全て source+URL+逐語。
> ★ルール確定★: 「良い/grounded/正しい」を外部引用なしに言わない。→ memory `feedback_never_claim_good_without_external_citation`。

## A. 引用元の grounding 検証（agent1、実 `gh api` 実測）

3 repo は全て実在（でっち上げでない）:
- `HKUDS/ClawWork` = **8,229★** MIT active（claim 8.2k と一致）
- `benchflow-ai/awesome-evals` = **685★** (license: NOASSERTION) active
- `garylab/MakeMoneyWithAI` = **557★** (無 license) active

spec が主張する6機構の grounding 判定:

| # | 機構 | 判定 | 根拠（逐語） |
|---|---|---|---|
| 1 | TrackedProvider real-cost | 🟢 GROUNDED | ClawWork `clawmode_integration/provider_wrapper.py` に `class TrackedProvider:` 実在。ただし spec の thinking_tokens 個別抽出は独自拡張 |
| 2 | survival ledger | 🟢 GROUNDED(概念) | ClawWork `economic_tracker.py` に `get_survival_status()`/`get_net_worth()`/`is_bankrupt()` 実在。ただし spec の `loss_start_ts`/7日grace/isSolvent は独自 |
| 3 | **decide_activity explore/exploit (Group DA)** | 🔴 **MISATTRIBUTED** | 名前は ClawWork `DecideActivityTool` に在るが中身は `{"activity":{"enum":["work","learn"]}}` の2択 LLM tool のみ。**Beta分布/alpha-beta/epsilon-greedy/bandit は repo 全体に一切無し**（`gh search code "bandit"`=0件, `"epsilon"`=0件）。REQ-DA1〜DA4 は実名を借りた完全なオリジナル発明 |
| 4 | rubric-judge-with-override | 🟡 GROUNDED(簡易版) | ClawWork `llm_evaluator.py` に rubric 採点+2つの hard override 実在。ただし spec の5段階 precedence は独自 |
| 5 | Verifier's Law (verifiable>judgeable) | 🟢 GROUNDED | awesome-evals README §8 + `PATTERNS.md`「a *verifiable* reward is a rubric function that runs real code against ground truth」。Jason Wei 記事を明記引用 |
| 6 | **calibration-drift (Group EV5)** | 🟡 **軽度 MISATTRIBUTED** | awesome-evals に用語2語は在る（他論文の説明内）が、**Pearson相関+閾値0.3+judge重み半減アルゴリズムは存在せず**、spec 独自発明 |

（`MakeMoneyWithAI` の opportunity radar cron = 🟢 GROUNDED: workflow に `cron:"0 0 * * *"` 実在）

**総合(agent1)**: 「外部 grounded」でも「純オリジナル」でもない**ハイブリッド**。4/6 は実在パターンに genuinely grounded。だが **Group DA(bandit) と EV5(calibration-drift) は "出典を貼っただけのオリジナル発明" = 修正必須**。

## B. 外部 BP と我々設計の逸脱（agent2、全て一次資料）

個別要素はどれも正統 BP で裏付くが、外部が一貫して警告する**3逸脱**:

| # | 逸脱 | 出典（逐語は agent ログ/本章末） |
|---|---|---|
| a | **素朴 bandit（全履歴累積 posterior）は非定常＋遅延報酬に無防備** → recency-weight/sliding-window 必須 | Sutton&Barto *RL* §2.4「appropriate in a stationary environment, but not if the bandit is changing over time」/ Liu,Downe,Reid arXiv:1902.08593 |
| b | **realized$ も代理指標(Goodhart)** → wash-trade/自己支払い/台帳バグでゲーム可 → reward capping・sandboxing・trip-wire 必須。ゲーミングは"汎化"する | Weng "Reward Hacking in RL"（Amodei et al. 10防御）/ Anthropic "Sycophancy to Subterfuge" arXiv:2406.10162「generalize zero-shot to directly rewriting their own reward function」 |
| c | **戦略の"承認/変更検証"と bandit の"配分"は別レイヤー** → 混同すると backtest 過学習が報酬に流入 | Lopez de Prado(ADIA)「walk-forward... only a single path is tested... risk of overfitting」/ freqtrade「backtesting will never replace running a strategy in dry-run mode」 |

一致（逸脱なし）: calibration の思想（Hamel Husain「align the judge... >90% agreement」）、Verifier's Law＝on-chain$（Jason Wei「Objective truth/Fast/Scalable/Low noise/Continuous reward」5要件を満たす）、outcome-grading／pass^k（Anthropic Demystifying Evals）。

**BP の canonical 5層アーキテクチャ**（単一 bandit に全責務は BP のどこも支持しない）:
```
L0 戦略検証ゲート: backtest → walk-forward → dry-run(paper) → 少額live  ← 新規/変更戦略の承認
L1 Bandit 配分  : vetted 済み戦略の"間"のみ。recency-weight/sliding-window（非定常対応）
L2 Outcome grader: 実現$（Verifier's Law最適）
L3 judge calibration: 使うなら ground-truth へ較正、乖離時 down-weight
L4 reward-hacking防御: capping・sandboxing(意思決定と台帳書込の分離)・trip-wire異常検知
```

## C. copy+tweak で reinvent を避ける（agent3、実 star/interface 逐語）

**推奨（証拠ベース）= `algorithmicsuperintelligence/openevolve`（6,653★, Apache-2.0, 2026-07-05 active）を fork。自作しない。**
- `# EVOLVE-BLOCK-START/END` マーカーで**戦略ファイル内の編集境界を物理的に区切る**機構が実在 → 我々の「bounded edits to strategy file / editable-surface」をゼロ設計しなくてよい。
- evaluator が `EvaluationResult(metrics={"combined_score":...})` を返す → **realized USDC を直接 fitness に差せる**。
- trading fitness(PnL/Sharpe/Drawdown) は `quantevolve` fork で実証済み。
- `artifacts` side-channel に **vcsdd-adversary の verdict を流し込める**（fresh-adversary gate を自然統合）。
- cascade evaluation（stage1 軽量 → stage2 本番 backtest）= 我々の L0 検証と L1 の2段に対応。
- 次点 GEPA(5.5k★, `str→float`)は単純だが編集境界/多様性維持/cascade を自前実装要。DGM/ADAS は stale＋fitness 決め打ちで不可。

## D. 総合の帰結（＝訂正後の方針、証拠に基づく）

1. **eval-driven-earning を as-is で建てない**。理由（引用済）: (i) Group DA(bandit) と EV5(calibration-drift) は misattributed invention、(ii) BP から3逸脱、(iii) 未実装(0ファイル)・未検証(spec-review FAIL)・1円も稼いでいない。
2. **reinvent しない**: self-improve の"機構"は **openevolve を copy+tweak**（bandit の自作をやめ、実証済み進化最適化に載せ替え）。
3. **grounded 要素は活かす**: TrackedProvider real-cost / survival ledger / Verifier's Law の verifiable-gate / judge の $較正。
4. **3逸脱を塞ぐ**: L0 戦略検証ゲート(backtest→walk-forward→paper→少額live)を分離、bandit/evolve は vetted 戦略のみ・非定常対応、L4 reward-hacking防御(capping/sandbox/trip-wire)を必須化。
5. **手順**: 上記で spec を作り直し → **fresh Opus adversary が spec-review** → PASS で TDD → VCSDD 全工程。良し悪しは私でなく adversary+外部引用が決める。

## 出典（一次資料）
Sutton&Barto RL §2.4 / Liu-Downe-Reid arXiv:1902.08593 / Anthropic "Demystifying evals for AI agents" / Weng "Reward Hacking in RL" / Anthropic "Sycophancy to Subterfuge" arXiv:2406.10162 / Hamel Husain "LLM-as-a-Judge" / Jason Wei "Verifier's Law" / Lopez de Prado(ADIA) "Three Types of Backtests" / freqtrade docs / HKUDS/ClawWork / benchflow-ai/awesome-evals / garylab/MakeMoneyWithAI / algorithmicsuperintelligence/openevolve / gepa-ai/gepa。
検証物件: `scratchpad/repo-verify/`（3 repo の README/該当ソース保存済）。
関連: [[07-patchlevel-spec-two-loops]] [[06-harness-engineering-weng]] [[00-INDEX]]。
