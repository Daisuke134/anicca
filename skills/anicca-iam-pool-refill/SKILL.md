---
name: anicca-iam-pool-refill
description: 月1回 fal.ai で 10 枚の IAM photo 背景を生成し、anicca-iam-photo-en/ja の pool ディレクトリに保存する。日次 cron はこの pool から rotation して fal を呼ばない (cost -90%)。
metadata:
  tags: cost-saver, image-pool, fal, monthly
  requires:
    bins: [bash, python3]
    env: [FAL_API_KEY]
---

# anicca-iam-pool-refill

## Why

`anicca-iam-photo-en` と `anicca-iam-photo-ja` の日次 cron は毎日 fal.ai で 1080×1350 画像生成 = $0.025/run × 2 lang × 30 day = **$1.50/月**。

**Pool 化:** 月 1 回 10 枚生成 → 日次 cron は pool から rotation = fal call は **月 20 回** (10×2 lang) = $0.50/月 = **-67% コスト**。

## Run

```bash
bash ~/.openclaw/skills/anicca-iam-pool-refill/scripts/refill.sh
```

## What it does

1. en pool に bg_1..bg_10.jpg を fal 生成 (各 BG_PROMPT[i] を使用)
2. ja pool に同じく bg_1..bg_10.jpg
3. 既存 pool は backup/<timestamp> に退避してから上書き
4. Slack #metrics 報告

## Cron

`1 0 1 * *` JST = 毎月 1 日 00:01 (月初)
