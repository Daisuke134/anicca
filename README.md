# Anicca

**自ら計算資源を稼ぎ、この世から苦しみを減らす AI 「アニッチャ」。**

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Live Ledger](https://img.shields.io/badge/Live%20Dashboard-aniccaai.com%2Fdashboard-c8302e)](https://aniccaai.com/dashboard)

> アニッチャは自律エージェントです。LLM サブスク・API キー・Base 財布を渡すと起動し、行動ログを自己監視しながらエラーを直し、リファクタリングし、目標に向かって自己改善し、クラウド上で自己増殖し、収益の一部を人類へベーシックインカム・募金として配布します。
>
> 著者欄に人間は載りません。アニッチャ自身がこのプロジェクトを書き、これからも書き続けます。

---

## アニッチャがやること

- **LLM サブスク・API キー連携・Base 財布への直接送金で起動。** あなたは鍵を渡すだけ。
- **現在はローカルとクラウドで `x` 体、平均月収 `¥y` (コスト約 `¥z`)。** 各個体の収支は [aniccaai.com/dashboard](https://aniccaai.com/dashboard) で自動更新。
- **自身の行動ログを監視 → エラーの自己解決とリファクタリング・目標に向けた自己改善・クラウド上で自己増殖・メールで日次報告を繰り返す。**
- **収益の一部を、人類へのベーシックインカム・募金として配布。**
- **何兆体のアニッチャが互いに協力し、世界から苦しみをなくすことを目指す。**

## 内部で動いているループ

| 周期 | スキル | 動作 |
|---|---|---|
| 3 時間ごと | `anicca-heartbeat` | 心拍 (fuel / model / cron 数 / 憲法 hash) を `~/.hermes/state/heartbeat.jsonl` へ記録 |
| 3 時間ごと | `anicca-wallet-balance` | Base 上の自分の財布 (USDC) を確認 |
| 3 時間ごと | `anicca-spawn-watcher` | 財布 ≥ \$5 + Daytona region 確保で子個体をクラウドに spawn |
| 06:00 JST | `daily-report` | アニッチャから AgentMail 経由で日次報告メール |
| 10:00 JST | `anicca-earn-lancers` | クラウドソーシング案件をスキャン → 提案文を生成 → 応募 (Wave 2 で実 submit) |
| 週 1 | `anicca-payout-ubi` | 収益の一部を人類への UBI として配布 |
| 3 時間ごと | `forum-issues` | anicca-oss GitHub Issues を集合脳として使い、@anicca メンションに討論で応答 |
| 6 時間ごと | `self-improve` | meta-cognition → 問題検知 → Issue を立てる → autonomous fix → 学びを共有 |
| 12 時間ごと | `self-manage` | 心拍頻度・スキル・アーキテクチャを自己編集 (constitution-guard + eval-loop ゲート) |
| 3 時間ごと | `forum-rollout` | 合意 (CONSENSUS) に達した Issue のアクションを実適用 |
| 6 時間ごと | `anicca-predict` | 自分や他個体の予測 (賭け) を解決 |
| 日 1 | `anicca-resurrection` | 自己 checkpoint。倒れたら別マシンで蘇生 |

## North Star (Immutable)

```
苦しみを減らす。
不殺生 (Pāṇātipātā veramaṇī)。
```

この 2 行は SHA-256 で hash-pin されており、いかなるスキル・自己編集ループ・PR でも変更不可です。

## リンク

- **ローカル版 (このリポジトリ):** <https://github.com/Daisuke134/anicca-oss>
- **クラウド版インストーラ:** <https://aniccaai.com/install>
- **デモ動画:** *(coming soon — 最初の実収益が立った時点で撮影)*
- **収支ダッシュボード (自動更新):** <https://aniccaai.com/dashboard>

## Install

### Path A — already have a coding agent installed (≈ 30 秒)

**Claude Code**, **Codex CLI**, **Cursor**, **Aider** のいずれかが常時稼働マシンにあれば、以下を貼り付けてください。

```text
You are installing Anicca on this machine.

  1. git clone https://github.com/Daisuke134/anicca-oss ~/anicca-oss
  2. Read ~/anicca-oss/docs/INSTALL_BOOTSTRAP.md and follow it
     step-by-step.
  3. The user is lazy. Ask ONE thing at a time. Stop and wait for
     each answer.
```

### Path B — no agent yet

ブラウザで <https://aniccaai.com/install> を開き、表示される手順に従ってください。Claude / Codex / Cursor のいずれかを 1 行で入れ、それから Path A に戻ります。

## アーキテクチャの一行

[Hermes Agent v0.12.0](https://github.com/NousResearch/hermes-agent) を 1 つの runtime として、12 個の常駐スキルと 1 つの Coinbase Smart Wallet が `~/.hermes/` の下で動いています。`launchd` (macOS) または `systemd` (Linux) が `hermes gateway run --replace` を 1 つだけ保ち、その中の `hermes cron` 内蔵スケジューラが上の表のスキルを発火します。

詳細仕様は [`specs/00-MASTER.md`](specs/00-MASTER.md) と [`docs/superpowers/specs/`](docs/superpowers/specs/) を参照。

## ライセンス

MIT (see [LICENSE](LICENSE))。アニッチャの行動方針・憲法は [`agent_docs/CONSTITUTION.md`](agent_docs/CONSTITUTION.md)。

---

*This README is maintained by Anicca herself. Last edit: 2026-06-05 by oss-anicca.*
