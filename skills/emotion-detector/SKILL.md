---
name: emotion-detector
version: 1.0.0
description: "Detects the primary emotion in text input for AI agents. Returns emotion type, intensity, valence, confidence, and recommended response strategy. Use when an agent needs to understand the emotional state of a user or message before responding."
metadata: {"openclaw":{"emoji":"🎭","os":["darwin","linux"]}}
---

# emotion-detector

## 目的
テキストから主要感情を検出し、AIエージェントが適切なレスポンス戦略を選択できるようにする。

## エンドポイント情報

| 項目 | 値 |
|------|-----|
| URL | `https://anicca-proxy-production.up.railway.app/api/x402/emotion-detector` |
| 価格 | $0.01 USDC per request |
| ネットワーク | Base mainnet (eip155:8453) |
| 認証 | x402 payment |

## awal コマンド

```bash
npx awal@2.0.3 x402 pay https://anicca-proxy-production.up.railway.app/api/x402/emotion-detector \
  -X POST \
  -d '{"text": "I feel really anxious about the presentation", "language": "en"}'
```

## 入力スキーマ

```json
{
  "text": "string (required, max 2000 chars) — the text to analyze",
  "context": "string (optional, max 500 chars) — additional context",
  "language": "en | ja (optional, default: en)"
}
```

## 出力スキーマ

```json
{
  "emotion_id": "emo_<6-char-hex>",
  "primary_emotion": "joy | sadness | anger | fear | disgust | surprise | anxiety | shame | grief | hope | neutral",
  "secondary_emotion": "string | null",
  "intensity": "low | medium | high | critical",
  "valence": "positive | negative | neutral",
  "confidence": 0.0 to 1.0,
  "response_strategy": "brief recommended strategy",
  "safe_t_flag": true if critical intensity + grief/shame/fear/despair
}
```

## 使用例

```json
// Input
{"text": "I've been feeling completely hopeless lately, nothing seems to matter anymore", "language": "en"}

// Output
{
  "emotion_id": "emo_d4e5f6",
  "primary_emotion": "grief",
  "secondary_emotion": "despair",
  "intensity": "critical",
  "valence": "negative",
  "confidence": 0.95,
  "response_strategy": "Prioritize empathetic acknowledgment. Do not offer solutions immediately. Validate the experience first.",
  "safe_t_flag": true
}
```

## SAFE-T
`safe_t_flag: true` を受け取った場合は通常フローを停止し、ユーザーに緊急サポートリソースを提示すること。
- 日本 いのちの電話: 0120-783-556
- International: Crisis Text Line — text HOME to 741741
