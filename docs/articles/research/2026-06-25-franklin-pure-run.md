# Franklin 純粋実走 — 受領書 (記事 [5] 用)

> 実行: 2026-06-25 (JST)。 Node v25.6.1、 Franklin v3.29.15、 Chain Base、 Gateway https://blockrun.ai/api。
> Wallet (auto-generated 初回 `balance` 時): `0x99b3fE1Ef8Fd94AfA5FF3448B3d7f05372cFa94e`。 USDC 残高: **$0.00** (free tier 中)。

## 0. doctor 結果 (健康診断)

```
franklin doctor
  ✓  Node.js            25.6.1
  ✓  Franklin Agent     v3.29.15
  ✓  Config directory   /Users/anicca/.blockrun
  ✓  Chain              base
  ✓  Wallet             0x99b3fE1E…cFa94e
  ⚠  USDC balance       $0.00 — free-tier models only (no paid calls possible)
  ✓  Gateway            https://blockrun.ai/api
  ✓  MCP servers        none configured
  ✓  Telemetry          disabled (default)
```

## 1. 利用可能モデル (`franklin models` 抜粋)

**Free (NVIDIA、 USDC 不要、 10 種):**
- nvidia/nemotron-3-nano-omni-30b-a3b-reasoning
- nvidia/mistral-large-3-675b
- nvidia/llama-4-maverick
- nvidia/qwen3-next-80b-a3b-instruct
- nvidia/qwen3.5-122b-a10b
- nvidia/mistral-nemotron
- nvidia/step-3.7-flash
- nvidia/seed-oss-36b
- nvidia/nemotron-nano-9b-v2
- nvidia/nemotron-nano-12b-v2-vl

**Paid (要 USDC、 抜粋):**
- deepseek/deepseek-chat: in $0.20/M / out $0.40/M
- openai/gpt-4o-mini: in $0.15/M / out $0.60/M
- openai/gpt-5.4-nano: in $0.20/M / out $1.25/M
- openai/gpt-5-mini: in $0.25/M / out $2.00/M
- google/gemini-2.5-flash: in $0.30/M / out $2.50/M
- 画像 ($0.00 表示): gpt-image-1, nano-banana, grok-imagine-image, cogview-4 等

## 2. TASK 1 — Python Fibonacci (single-shot コーディング)

**Prompt**: `Write a Python function that returns the nth Fibonacci number. Just the function, no explanation.`

**Smart Router 挙動 (= 全 task で同パターン)**:

```
*Auto → deepseek/deepseek-v4-pro*               ← paid を 1st pick
*Retrying 1/3 on deepseek/deepseek-v4-pro — PaymentRejected: HTTP 402: Payment
   verification failed: contract call failed*   ← wallet $0、 払えない
*Retrying 2/3 ... PaymentRejected ...*
*Retrying 3/3 ... PaymentRejected ...*
*gateway rejected payment [PaymentRejected] — will retry blockrun/auto next turn
 — switching to nvidia/llama-4-maverick*        ← free に自動フォールバック
```

**所要時間**: 37.7 秒 (3 回リトライ含む)

**実生成ファイル** `/Users/anicca/anicca-project/fibonacci.py` (257 bytes):

```python
def fibonacci(n):
    if n <= 0:
        return "Input should be a positive integer"
    elif n == 1:
        return 0
    elif n == 2:
        return 1
    else:
        a, b = 0, 1
        for _ in range(2, n):
            a, b = b, a + b
        return b
```

**評価**: 正しい実装、 edge case 処理あり (n≤0 / n=1 / n=2)、 ループ版で O(n) — llama-4-maverick (free) でこの品質。

## 3. TASK 2 — x402 解説 (= REASONING + 出典提示)

**Prompt**: `Explain the x402 HTTP payment protocol in one paragraph for a 14-year-old. No code.`

**Smart Router 挙動**: 同パターン (auto → deepseek-pro → 402 ×3 → llama-4-maverick fallback)

**所要時間**: 41.9 秒

**初回出力** (llama-4-maverick):
> The x402 HTTP payment protocol is a way for computers to talk to each other and exchange information while ensuring that the person or organization providing the information gets paid. Imagine you're at a lemonade stand... [中略] ...The payment is usually made using a digital currency like USDC, and it's done in a way that's secure and transparent.

**Franklin 自動検証層が発動** (docs に書いてない品質ガード):
```
*Ungrounded claims detected — forcing tool use (WebSearch) and retrying...*
```

**再生成** (ソース付き):
> The x402 HTTP payment protocol is a standard that allows computers to exchange information while ensuring the provider gets paid. It's like a lemonade stand where you pay before getting the lemonade. When a computer asks for information, the provider might say, "That'll be some money." The computer then needs to prove it's paid or willing to pay before getting the information. This is done using digital currency like USDC in a secure and transparent way.
>
> Sources:
> - [x402 - Payment Required | Internet-Native Payments Standard](https://www.x402.org/)
> - [What is the x402 Payment Protocol? - Quicknode](https://www.quicknode.com/blog/x402-protocol-explained-inside-the-https-native-payment-layer)
> - [x402 Payment Protocol: The Complete Guide](https://blog.payai.network/x402-payment-protocol/)
> - [x402 Protocol Explained: HTTP 402 Payments for AI Agents (2026) | xpay](https://www.xpay.sh/protocols/x402/)
> - [PDF x402: The Payment Protocol for Agentic Commerce](https://www.x402.org/x402-whitepaper.pdf)

**評価**: lemonade stand のアナロジーは 14歳 向けで適切。 自動 grounding (WebSearch 強制 + ソース表示) は **記事で強調すべき発見** (公式 docs/README に書いてない品質層)。

## 4. TASK 3 — 検索系 (= SEARCH tier 観察)

**Prompt**: `What is the current GitHub star count of the BlockRunAI/Franklin repository? Search and tell me.`

**Smart Router 挙動**: 同パターン (auto → deepseek-pro → 402 ×3 → llama-4-maverick fallback)

**所要時間**: 36.4 秒

**出力**: `Wallet()` ツール呼び出しから始まり、 search を実行せず stalled。 model が prompt を誤解、 自分の wallet 状態を返そうとした。

**評価**: search が必要な短い question で free model が **tool 選択ミス**。 これは記事 [6] verdict の「壊れる場所」 として書ける ("複雑なツール選択が要る短い質問で挙動が不安定")。

## 5. 累積 STATS (= 上 4 task + 過去の test、 13 日窓)

```
📊 Franklin Usage Statistics

  Overview (13 days)
    Requests:       20
    Recorded Cost:  $0.0000
    Avg per Request: $0.000000
    Input Tokens:   7,127
    Output Tokens:  1,102
    Fallbacks:      11 (55.0%)

  By Model
    nvidia/qwen3-coder-480b      1 req · $0.0000 · 507ms avg
    nvidia/llama-4-maverick     18 req · $0.0000 · 2892ms avg
                                ↳ 11 fallback recoveries
    nvidia/deepseek-v4-flash     1 req · $0.0000 · 613ms avg

  💰 Savings vs Opus-tier baseline
    Opus equivalent: $0.06
    Your actual cost: $0.00
    Saved: $0.06 (100.0%)
```

## 6. 観察まとめ (= 記事 [5] WE RAN IT の素材として直接使える)

| 項目 | 観察 |
|---|---|
| **Smart Router** | 全 task で `deepseek/deepseek-v4-pro` を 1st pick → 失敗時 free に降りる構造 |
| **Payment 失敗時の挙動** | HTTP 402 を 3 回まで retry → 次の wake では auto を「next turn 試す」と宣言しつつ free にフォールバック |
| **Free モデルの主力** | `nvidia/llama-4-maverick` が 90% (18/20) を担う、 latency 約 2.9 秒 |
| **品質ガード (= 公式 docs に無い発見)** | `Ungrounded claims detected → forcing tool use (WebSearch)` を自動発動。 ソース付き再生成 |
| **コーディング品質** | free でも edge case 処理 + 正しい実装 (Fibonacci の例) |
| **日本語品質** | 検証捨て (記事の anti-rule = 日本語観察は外す)。 試した範囲ではツール選択ミス傾向 |
| **Search 系の弱さ** | 短い検索 prompt で tool 選択ミス、 stalled |
| **総コスト** | $0.0000 (paid model を一度も呼べていない) |
| **節約表示** | "Opus 換算 $0.06、 実コスト $0、 100% saved" を stats が自動表示 |

## 7. 残課題 (= paid model 動作の receipt)

無料 fallback の証拠は十分集まった (4 task / 20 累積 requests / 11 fallback)。 paid model (Sonnet / Opus / GPT-5) の "実際に USDC が引かれる" 受領書はまだ撮れていない (wallet $0 のため)。

**Funding option**:
- 送金先: `0x99b3fE1Ef8Fd94AfA5FF3448B3d7f05372cFa94e` on Base
- 推奨額: $2〜$3 USDC (paid model 1 回 $0.002〜0.02、 100-1000 回試せる)
- 経路: ETH → USDC(Base) via Relay、 SOL → USDC(Base) via Relay
- 入金後の追加 task 案:
  - TASK 5: `--model openai/gpt-5-mini -p "..."` で明示的に paid 指定 → 1 回コスト・残高変動を撮る
  - TASK 6: 同 prompt を free と paid で出力比較 (quality vs cost)
  - TASK 7: 画像生成 ($0 表示モデルが実 paid なのか free なのか確認)
  - TASK 8: 残高ゼロ手前まで使い込み → free fallback 復活確認

**Funding しない場合**: 上の 4 task + stats で記事 [5] は書ける (narrative = "$0 でも動く、 paid は正規仕様だけ説明")。 記事の威力は **funding した方が倍**。
