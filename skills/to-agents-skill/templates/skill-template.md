---
name: <SKILL_NAME>
description: "<DESCRIPTION>. Use when <USECASE>."
metadata: {"openclaw":{"emoji":"💡","os":["darwin","linux"]}}
---

# <SKILL_NAME>

## 目的
<DESCRIPTION>

## エンドポイント情報

| 項目 | 値 |
|------|-----|
| URL | `https://anicca-proxy-production.up.railway.app/api/x402/<SKILL_NAME>` |
| 価格 | $0.01 USDC per request |
| ネットワーク | Base mainnet (eip155:8453) |
| 認証 | x402 payment |

## awal コマンド

```bash
npx awal@2.0.3 x402 pay https://anicca-proxy-production.up.railway.app/api/x402/<SKILL_NAME> \
  -X POST \
  -d '<INPUT_JSON>'
```

## 入力スキーマ

```json
<INPUT_SCHEMA>
```

## 出力スキーマ

```json
<OUTPUT_SCHEMA>
```

## 使用例

```json
// Input
<EXAMPLE_INPUT>

// Output
<EXAMPLE_OUTPUT>
```

## SAFE-T
本スキルは苦しみや危機に関連するコンテキストを扱う可能性がある。severity >= 0.9 の場合は通常フローを停止し、緊急リソースを提示すること。
