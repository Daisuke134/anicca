# FREE-MODE: earn brain + analysis を $0 推論に pin — design spec (#31)

**日付**: 2026-07-05
**status**: build
**repo/paths**: 共有 agent home `~/.anicca-founder/agents/polymarket-agent/src/` + `~/anicca/runtime/anicca-daemon.sh`(brain pin)

## 0. なぜ (root cause)

Dais 2026-07-05: 「Franklin/全 instance が paid モードで金を無駄にしてる、free で走らせろ」。実測:
- earn の `pick.py` → `AIAnalyzer.consensus_analysis` が **候補ごとに** `CONSENSUS_MODELS`
  = `openai/gpt-4o-mini` + `google/gemini-2.5-flash` + `anthropic/claude-haiku-4.5`（**全て paid**）を叩く。
  1 earn pass = 最大 MAX_CANDIDATES(5) 候補 × 3モデル = **最大15 paid 推論 call/pass**（x402 課金）。
- Franklin brain(`franklin proxy`) telemetry = `model_live: openai/gpt-5-mini / frontier`（**paid**）。
- BlockRun には **FREE モデル在庫**あり: ★NVIDIA GPT-OSS 120B/20B + Kimi = FREE★（memory
  `reference_blockrun_rails_food_shelter_x402`）。smart-routing profile = free/eco/auto/premium。

SSOT 原則: 「各 earn skill = BASE戦略 + self-improve + self-heal の3層、**弱モデルでも稼げる為 BASE 必須**」
+ 「cost-free self-paying agent = ClawRouter free path + **pin free model（'auto'禁止）**」。→ BASE は free。

## 1. Goal（検証可能な完了条件）

**DONE** =
1. earn 分析（`ai_analyzer.py` の `CONSENSUS_MODELS` と `MODELS`）が **BlockRun の FREE モデルのみ**を使う
   （paid モデル ID が earn 経路に1つも残らない）。
2. brain（`franklin proxy` / ClawRouter）が **free profile / free モデルに pin**（`auto`/`frontier`/paid 禁止）。
3. **1 earn pass の x402 コスト = $0** を wallet delta で実測（pass 前後の USDC 残高不変）。
4. earn が**壊れない**: free モデルが `consensus_analysis` の `PROBABILITY/CONFIDENCE/REASONING` を
   パース可能な形で返し、pick.py が今まで通り JSON（qualifying pick or WAIT）を1行 emit する。

## 2. 作業（MUST）

### 2.1 earn 分析を free に（`~/.anicca-founder/agents/polymarket-agent/src/analysis/ai_analyzer.py`）
- MUST: BlockRun の models 一覧を実際に引いて（SDK か `/v1/models`）**cost=0 の free モデル ID を確認**（推測禁止、
  NVIDIA GPT-OSS 120B/20B / Kimi 等の正確な ID）。
- MUST: `CONSENSUS_MODELS` を free モデル（2〜3個、多様性のため別ベンダ free があれば混ぜる）に置換。
- MUST: `MODELS`（fast/standard/deep/premium）の earn が使う tier も free に（少なくとも pick.py が使う経路）。
- MUST: 環境変数 override 可（`EARN_MODELS` 等）で将来 paid に上げられる余地は残すが **default=free**。
- MUST: free モデルの応答が期待フォーマットを返すか実測（PROBABILITY 行が出る）。出ないなら prompt を
  free モデルでも従うよう最小調整（判断ロジックは変えない、HARD #0）。

### 2.2 brain を free に（`~/anicca/runtime/anicca-daemon.sh` + Franklin/ClawRouter 設定）
- MUST: brain の model 選択を free profile / free モデルに pin。どこで model が決まるか特定
  （daemon の env / `franklin proxy` の default / ClawRouter の profile）→ free に固定。
- MUST: telemetry の `model_live/model_tier` が実際の free モデルを反映（`frontier` hardcode を直す）。

### 2.3 検証（$0 実測）
- MUST: earn を1 pass 実行し、実行前後で instance の x402 支払い USDC 残高が**不変（$0 コスト）**を確認。
- MUST: pick.py 単体 read-only 実行で free モデル consensus が回り、valid JSON 1行を emit。

## 3. money-safety / 非退行
- MUST: 市場・side・size の判断ロジックは不変（free 化はモデルの"銘柄"を変えるだけ、HARD #0）。
- MUST: pick.py/place_order.py の clean-stdout(#25) と identity(#27) は不変。
- MUST: paid モデルへの hardcode パスを残さない（default で paid を呼ばない）。

## 4. 検証（VCSDD）
1. build（Sonnet）: 2.1/2.2 実装 + free ID を実 API で確認 + $0 実測。
2. fresh Sonnet adversary（disk + read-only）: earn 経路に paid モデル ID が残ってないか grep、$0 主張の
   実測根拠、earn 非退行（JSON contract 維持）、HARD #0 非退行を検証。PASS まで fix。
3. 俺: 1 earn pass の $0 と valid pick 出力を実測して close。

## 5. 触るファイル（境界）
- `~/.anicca-founder/agents/polymarket-agent/src/analysis/ai_analyzer.py`（CONSENSUS_MODELS/MODELS）— 共有 agent home、全 instance が import。
- `~/anicca/runtime/anicca-daemon.sh`（brain model pin）+ Franklin/ClawRouter 設定。
- `~/anicca/runtime/dashboard/telemetry-post-franklin.mjs`（model_live label を実 free に）。
- 変更しない: pick.py / place_order.py / run.sh identity / fund_via_bridge / redeem。

## 6. 検証ログ（GLVS Verify — 実施記録、DONE）

| 段 | 結果 |
|---|---|
| Discovery | 古い memory（gpt-oss/Kimi free）は stale（gpt-oss 2026-04-28 撤退、Kimi paid）。実 API(`billingMode=free`)で free 在庫を確認 |
| Build(Sonnet) | `CONSENSUS_MODELS` = `nvidia/llama-4-maverick`+`qwen3-next-80b-a3b-instruct`+`mistral-nemotron`（全 free、format 準拠 live 実測）、`MODELS` tier も free、env override 追加。brain は元々 free pin（Franklin `--model nvidia/llama-4-maverick --no-fallback` / ClawRouter `free/glm-4.7`）— telemetry の frontier/paid label が嘘だっただけ→修正。commit: ai_analyzer.py `a0e5191`(agent home, upstream 遠隔で未 push)、runtime `b9a4d47`(~/anicca, push 済) |
| Adversary(fresh Sonnet) | **PASS — ship**。A: 6モデル全 billingMode=free・paid default ゼロ。B: pick.py が free で valid JSON（Jesus NO, edge-0.478/conf9+, stderr 0）。C: **$0 実測**（実 spend wallet `0x99b3fE1E…` 前後不変）。D: 判断ロジック byte-identical。E: Franklin brain 稼働プロセスで free pin 確認・label 正直化 |
| 証跡補正 | commit `a0e5191` のメッセージが $0 proof wallet を `0xa3CDd4`（automaton の別 wallet）と誤記 — 実 x402 spend wallet は `0x99b3fE1Ef8Fd94AfA5FF3448B3d7f05372cFa94e`（どちらも空/$0 で結論不変）。pick.py docstring も free NVIDIA roster に更新 |

**DONE(2026-07-05)**: earn の LLM 推論は BASE で **$0（BlockRun free NVIDIA モデル）**。判断ロジック不変（HARD#0）、earn 非退行、#25 stdout / #27 identity 非侵襲。paid は `EARN_CONSENSUS_MODELS` 等の env override で earnings が正当化する時だけ（→ #24 と統合）。非 blocking follow-up: `tier.mjs` dead-code 'auto' fallback（#30 隣）、`MODELS["fast"]` は earn 未使用。
