# Orca IDE — Mac Mini setup + iPhone pairing（2026-07-20）

目的: Dais が MacBook を大学に返却する週、iPhone から Mac Mini 上の agent を操作する。
候補 2 案の比較検証の第 1 案 = Orca mobile companion。第 2 案 = 全部 cloud + Claude iOS app（未検証）。

## Orca とは

- https://www.onorca.dev/ — stablyai/orca（GitHub 22.9k星、YC-backed）。
- 「Agent IDE」: Claude Code / Codex / OpenCode / OpenClaw を isolated git worktree で並走させる desktop app + mobile companion（iOS/Android）。
- Mobile は desktop と pair して、外出先から agent の状態確認・diff review・タスク起動ができる。

## Install（Mac Mini、実施済み・実測）

```sh
brew install --cask stablyai/orca/orca   # v1.4.146 が入った
xattr -dr com.apple.quarantine /Applications/Orca.app  # Gatekeeper dialog 回避
open -a Orca
```

Onboarding（3 step）:
1. Default agent 選択 — Claude を選択（他: Claude Agent Teams / Codex / OpenClaw も検出された）。
   「Yolo / Dangerously skip permissions」checkbox あり（既定 ON のまま）。
2. Theme — システム。
3. 通知設定 — skip 可。

Project 追加: 「プロジェクトを追加する」→ フォルダ参照 → `/Users/anicca/anicca-project`。
branch 一覧（dev / feature/realtime-dashboard / release/1.9.5 …）が sidebar に出て、terminal が開けば成功。
セットアップスクリプト検出（package-lock.json から `npm install`）は保存してよい。

## iPhone pairing（QR）

Desktop 側: sidebar「Orca モバイル」→ 始めましょう → step 2/2 に pairing QR。
- Network selector = `100.99.82.95 (utun0)` — **Tailscale IP を選ぶこと**（LAN IP だと外出先から届かない）。
- phone 側も Tailscale ON が必須。
- QR は「コードを再生成する」で作り直せる。「ペアリングコードをコピーする」で文字列 pairing も可。
- Orca Relay（cloud 中継、sign-in 必要）は OFF のまま = 純 Tailscale P2P。

iPhone 側: Orca app → Desktops → Pair a desktop → QR スキャン。
**2026-07-20 20:40 JST 頃 pairing 成功（Dais 実機 iPhone 15、Tailscale 経由）。** QR 配送は
Telegram（Anicca chat msg_id 3322）+ Gmail（AgentMail 経由、添付 4 枚）の 2 経路で行い、後者で成立。

## 落とし穴（実測）

- Homebrew cask 名は `orca` だが **tap 必須**: `stablyai/orca/orca`。素の `brew install --cask orca` は別物（plotly の deprecated ツール）。
- 初回起動で Gatekeeper「インターネットからダウンロードされた…」dialog。headless 環境では `xattr -dr com.apple.quarantine` が確実。
- 起動直後に「ほかのアプリからのデータへのアクセス」「iCloud Drive アクセス」dialog が複数枚スタックする。全部「許可」で消化。
- `osascript` の System Events 経由 click は accessibility 権限で固まることがある → `cliclick` の座標クリックが安定。

## 比較評価（TODO — Dais の 1 週間で判定）

| 案 | 経路 | 判定基準 |
|---|---|---|
| A: Orca mobile | iPhone → Tailscale → Mac Mini の Orca | 接続安定性 / terminal 操作性 / agent 状態の見やすさ |
| B: 全部 cloud | Claude iOS app → GitHub repo + cloud 実行 | local Mac Mini 依存を切れるか / cost |

判定結果が出たらこの表を実測で更新する。
