---
name: context-compressor
description: "Compress long conversation history or documents into concise structured output via x402 payment. 3 modes: summary, facts, episodes. Use when: context compression, memory compression, conversation summarization, document summarization, context window optimization, episode extraction, fact extraction."
version: "1.0.0"
author: "Daisuke134"
---

# context-compressor

Compress long text (conversation history, documents) into concise structured output. Pay $0.008 USDC per call via x402 on Base mainnet.

## Prerequisites

```bash
npm install -g awal@2.0.3
awal auth login
```

## Usage

```bash
# Summary mode (default)
awal x402 pay https://anicca-proxy-production.up.railway.app/api/x402/context-compressor \
  -X POST \
  -d '{"text":"<your long text>","mode":"summary","target_tokens":500,"language":"en"}'

# Facts mode
awal x402 pay https://anicca-proxy-production.up.railway.app/api/x402/context-compressor \
  -X POST \
  -d '{"text":"<your long text>","mode":"facts","language":"en"}'

# Episodes mode
awal x402 pay https://anicca-proxy-production.up.railway.app/api/x402/context-compressor \
  -X POST \
  -d '{"text":"<your long text>","mode":"episodes","language":"ja"}'
```

## Input Schema

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| text | string | yes | — | Text to compress (max 50,000 chars) |
| target_tokens | number | no | 500 | Desired output length (100-2000) |
| mode | string | no | summary | summary, facts, or episodes |
| language | string | no | en | en or ja |

## Output Schema

```json
{
  "compressor_id": "cmp_a1b2c3d4",
  "mode": "summary",
  "compressed": "Concise summary of the input...",
  "original_chars": 12345,
  "compressed_chars": 890,
  "compression_ratio": 0.072,
  "key_entities": ["Entity1", "Entity2"],
  "safe_t_flag": false
}
```

## Pricing

- $0.008 USDC per request (Base mainnet, eip155:8453)

## Endpoint

- URL: `https://anicca-proxy-production.up.railway.app/api/x402/context-compressor`
- Method: POST
- Auth: x402 payment (no API key needed)
