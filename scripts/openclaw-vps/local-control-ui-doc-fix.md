# ローカル Control UI: 公式ドキュメントに沿った対処（Session path とチャット消える問題）

**前提**: local → VPS → local と戻ったあと、「Session file path must be within sessions directory」やチャット入力/応答が消える問題が出る。**公式のやり方だけで直す**（独自スクリプトは使わない）。

---

## 1) 公式の「開き方」はこれだけ

- **Getting Started**: [Getting Started - OpenClaw](https://docs.openclaw.ai/start/getting-started)  
  - Control UI を開く: **`openclaw dashboard`** またはブラウザで **http://127.0.0.1:18789/**
- **Dashboard**: [Dashboard - OpenClaw](https://docs.openclaw.ai/web/dashboard)  
  - ローカルなら **http://127.0.0.1:18789/** を開く。  
  - 再接続時: **`openclaw dashboard`**（リンクをコピーしてブラウザを開く）。

**結論**: `open-control-ui.sh` や `local-fix-session-path.js` は**公式には不要**。ドキュメントは「gateway を起動 → `openclaw dashboard` または URL を開く」だけ。

---

## 2) 何が間違っていたか（私たちのやり方）

| やっていたこと | 公式の扱い |
|----------------|------------|
| `start-gateway-mac.sh` で `OPENCLAW_STATE_DIR` と `HOME` を固定して gateway 起動 | ドキュメントは **`openclaw gateway`** のみ。`OPENCLAW_STATE_DIR` は「別の state を使うとき」用（[Environment Variables](https://docs.openclaw.ai/help/environment)）。通常は**指定しない**。 |
| Control UI を開く前に `local-fix-session-path.js` で `sessions.json` を書き換える | どこにも「sessions.json を手で正規化する」とは書いていない。 |
| `open-control-ui.sh` で「パス正規化 → URL を開く」を毎回やる | ドキュメントにそんな手順はない。 |

**根本**: 別マシン（VPS）の state をコピーしてきたり、**state dir / profile が食い違う**と、`sessions.json` に「別マシンの絶対パス」が残り、ローカルの gateway が「sessions ディレクトリの外」と判定してエラーになる（[Migration Guide - Common footguns](https://docs.openclaw.ai/install/migrating#footgun-profile--state-dir-mismatch)）。

---

## 3) 問題1: 「Session file path must be within sessions directory」

### 原因（公式の説明）

- [Migration Guide](https://docs.openclaw.ai/install/migrating):  
  - state は **「そのマシン」の** `$OPENCLAW_STATE_DIR`（既定は `~/.openclaw/`）とセットで使う想定。  
  - **別の profile / state dir** で動かすと「config が効かない・チャネルが消える・**セッション履歴が空**」などの不整合が出る。  
- つまり: **VPS で作った state（`sessions.json` に VPS の絶対パスが入ったもの）をローカルにコピーして、そのままローカルで使うとエラーになる**。

### 対処（ドキュメントどおり）

1. **gateway は「余計な指定なし」で起動する**  
   - ローカルでは **`openclaw gateway`** だけ（`start-gateway-mac.sh` で `OPENCLAW_STATE_DIR` を付けない）。  
   - これで state は常に **既定の `~/.openclaw/`** になり、解釈が一貫する。

2. **移行後は必ず Doctor を実行する**  
   - [Migration Guide - Step 3](https://docs.openclaw.ai/install/migrating#step-3--run-doctor-migrations--service-repair):  
     - 新しいマシンで **`openclaw doctor`** を実行。  
     - 設定の正規化・state の整合性チェック・レガシー state の移行などを行う。  
   - [Doctor](https://docs.openclaw.ai/gateway/doctor):  
     - 「State integrity checks」「Transcript mismatch」「Session dirs missing」などで不整合を検出・警告する。

3. **ローカルに戻ったとき、VPS の state を上書きしていないか確認する**  
   - もし **VPS の state をローカルの `~/.openclaw/` にコピーして上書きした**なら、その state には VPS の絶対パスが入っている。  
   - **推奨**:  
     - **ローカル専用の state を使う**: VPS から state をコピーしない。ローカルではローカルだけで作った `~/.openclaw/` を使う。  
     - または、VPS からコピーした state を使い続けたい場合は、**そのマシン（VPS）上で gateway を動かし、ローカルからはリモート接続**（[Remote access](https://docs.openclaw.ai/gateway/remote)）する。

4. **すでに壊れた session だけ直したい場合**  
   - 該当 agent の `~/.openclaw/agents/<agentId>/sessions/sessions.json` を編集して、**別マシンの絶対パスが入っているエントリを削除**するか、  
   - その agent の `sessions` フォルダをバックアップしたうえで **`sessions.json` を空のオブジェクト `{}` にして保存**し、gateway を再起動すると、新規セッションが作られ、パスは現在のマシンになる。  
   - （これは「state をこのマシン用にリセットする」運用であり、公式の「手動で sessionFile を正規化するスクリプト」ではない。）

---

## 4) 問題2: チャットの入力/応答が消える

### 公式の説明

- [Control UI - Chat behavior](https://docs.openclaw.ai/web/control-ui#chat-behavior):  
  - `chat.send` は非ブロッキング。応答は **`chat` イベント**でストリームされる。  
  - 履歴は **セッションの transcript** に保存される。

- いったん **「Session file path must be within sessions directory」** になっていると、そのセッションの transcript を正しく読めず、**履歴が表示されない・入力が流れたように見えて消える**挙動になりうる。

### 対処

1. **先に「Session file path」を解消する**  
   - 上記「3) 問題1」のとおり、**`openclaw gateway` のみで起動**し、**VPS の state で上書きしていない**状態で **`openclaw doctor`** を実行。  
   - 必要なら、壊れた session だけ `sessions.json` を整理して gateway を再起動する。

2. **セッションが正しく開けるようになったうえで、まだメッセージが消える場合**  
   - [Answer Overflow の同様の報告](https://www.answeroverflow.com/m/1469702064765665404): 実行中に別のメッセージを送ると、キューされてすぐには履歴に出ないことがある。  
   - まずは **1 通送って応答が完了してから**次のメッセージを送る、**Stop で止めてから**送り直す、などで挙動を確認する。  
   - それでも消える場合は、OpenClaw の Control UI の不具合の可能性があるので、リポジトリの Issue や Discord 等で確認するのがよい。

---

## 5) やることチェックリスト（ローカルに戻ったとき）

| 順番 | やること | 参照 |
|------|----------|------|
| 1 | gateway を **`openclaw gateway`** で起動する（`OPENCLAW_STATE_DIR` を付けない）。`start-gateway-mac.sh` は使わない。 | [Getting Started](https://docs.openclaw.ai/start/getting-started) |
| 2 | **`openclaw doctor`** を実行する。 | [Migration - Step 3](https://docs.openclaw.ai/install/migrating#step-3--run-doctor-migrations--service-repair), [Doctor](https://docs.openclaw.ai/gateway/doctor) |
| 3 | Control UI は **`openclaw dashboard`** または **http://127.0.0.1:18789/** で開く。 | [Dashboard](https://docs.openclaw.ai/web/dashboard) |
| 4 | まだ「Session file path…」が出る場合は、VPS の state をローカルにコピーしていないか確認し、必要なら該当 agent の `sessions.json` を整理（壊れたエントリ削除 or 空にして再作成）。 | 上記 3) の 4 |

**`open-control-ui.sh` と `local-fix-session-path.js` は、このドキュメントの手順では使わない。**
