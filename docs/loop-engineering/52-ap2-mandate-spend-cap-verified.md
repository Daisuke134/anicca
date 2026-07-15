# 52 — AP2 (Agent Payments Protocol): 支出上限マンデートを自分で壊してみた実測記録

2026-07-16, article-daily loop実行時の研究記録。

## 何を調べたか

Google が2025年9月に公開した AP2 (Agent Payments Protocol) — 人間がエージェントに委任する支出上限を
暗号署名つきの Mandate として渡す規格。v0.2 は2026年4月にFIDOアライアンスへ運営移管。
x402(その場の少額決済)・ERC-8004(身元/評判)と並ぶ、AIエージェント決済まわり3規格の一角。

## 実際にやったこと(receipts)

```
git clone https://github.com/google-agentic-commerce/AP2.git
cd AP2 && python3 -m venv .venv && source .venv/bin/activate
pip install -e .
python -m pytest code/sdk/python/ap2/tests/ -q
# => 29 passed
```

自作の spend-cap 実験スクリプト(`/tmp/ap2-research/spend_cap_experiment.py`、セッション一時領域):
人間役が上限$50のOpen Payment Mandateをエージェント役の鍵に対して署名 → エージェント役が3パターンで
支払い伝票(Payment Mandate)を作り検証にかける。

```
OPEN MANDATE (signed by human, cap=$50): eyJhbGciOiAiRVMyNTYi...
[under-cap $30] ALLOWED: agent spent $30.00, within cap.
[over-cap $80] BLOCKED by constraint check: ['Amount 8000 exceeds maximum 5000']
[tampered-token $30] SIGNATURE VERIFY FAILED: Malformed KB-JWT: expected header.payload.signature
```

## 結論

- 暗号層(SD-JWTベースのMandateチェーン)は仕様通りに動作。上限超過・署名改ざんはどちらも機械的に拒否された。
- 限界: エージェントの身元は保証しない(Blue Headline/Everest Group指摘)。実運用カード決済量では未検証。
  誤送金時の責任所在は仕様の外。

## 出典

- https://github.com/google-agentic-commerce/AP2
- https://cloud.google.com/blog/products/ai-machine-learning/announcing-agents-to-payments-ap2-protocol
- https://ap2-protocol.org/
- https://blueheadline.com/software-dev/ap2-security-2026-ai-agent-payments/
- https://www.everestgrp.com/googles-agent-payments-protocol-ap2-a-new-chapter-in-agentic-commerce-blog/

## 出力

記事: JP(note/Zenn/Substack-ja/X)+ EN(X) を draft 化。dev.to/Substack-en は de-slop gate 非収束のため
このパスでは未staging(詳細は `state/articles.jsonl` 2026-07-15T21:49 台のエントリ参照)。
