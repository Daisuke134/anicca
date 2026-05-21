# VPS Gateway: .env と Control UI アクセス（公式ドキュメント準拠）

**参照:** [OpenClaw Docs](https://docs.openclaw.ai/)

---

## 1) 公式ドキュメントの要点

| ドキュメント | URL | 要点 |
|-------------|-----|------|
| **Getting Started** | https://docs.openclaw.ai/start/getting-started | Control UI: `openclaw dashboard` または `http://127.0.0.1:18789/`。Gateway: `openclaw gateway status`。 |
| **Environment Variables** | https://docs.openclaw.ai/help/environment | OpenClaw は **`~/.openclaw/.env`**（＝`$OPENCLAW_STATE_DIR/.env`）を読みにいく。優先順: プロセス環境 → CWD の .env → **~/.openclaw/.env** → config env → shell import。 |
| **Linux App** | https://docs.openclaw.ai/platforms/linux | VPS クイックパス: Node 22+ → `openclaw onboard --install-daemon` → ローカルで `ssh -N -L 18789:127.0.0.1:18789 user@host` → `http://127.0.0.1:18789/` を開いてトークン貼る。systemd の**最小例**には EnvironmentFile は書いていない（`ExecStart=openclaw gateway --port 18789` のみ）。 |
| **Gateway Runbook** | https://docs.openclaw.ai/gateway | リモートアクセス: `ssh -N -L 18789:127.0.0.1:18789 user@host`。Linux: `openclaw gateway install` → `systemctl --user enable --now openclaw-gateway.service`。linger: `sudo loginctl enable-linger <user>`。 |
| **Setup (Linux systemd)** | https://docs.openclaw.ai/start/setup | Linux は systemd **user** service。ログアウトで止まるので `sudo loginctl enable-linger $USER` を推奨。 |

---

## 2) 当プロジェクトの VPS で起きていた問題

- **症状:** `http://127.0.0.1:18789/chat?session=...` にアクセスできない（接続リセット）。
- **原因:** VPS の systemd unit が `EnvironmentFile=/home/anicca/.env` を参照しているが、そのファイルが存在せず、**Failed to load environment files: No such file or directory** で Gateway が起動していなかった。
- **公式の読み方:** Environment のドキュメントでは「OpenClaw は ~/.openclaw/.env を読む」とある。systemd の **install** が unit に `EnvironmentFile=~/.env` を書くため、そのファイルがないと systemd が起動を拒否する。

---

## 3) 対処（公式＋当プロジェクトの運用）

| やること | 根拠 |
|----------|------|
| **VPS に `/home/anicca/.env` を用意する** | systemd unit が `EnvironmentFile=/home/anicca/.env` を参照しているため。中身は `~/.openclaw/.env` と同一でよい。 |
| **2 箇所を同期して使う** | OpenClaw は `~/.openclaw/.env` を読む。systemd は `~/.env` を読む。両方同じ内容に保つ。 |
| **同期コマンド** | プロジェクトルートで `./scripts/openclaw-vps/sync-env-to-vps.sh`。これで両方に書き込む。 |
| **Gateway 再起動** | `.env` を直したあと: `ssh anicca@46.225.70.241 'export XDG_RUNTIME_DIR=/run/user/$(id -u); systemctl --user restart openclaw-gateway.service'` |

---

## 4) Control UI にアクセスする手順（公式どおり）

1. **VPS で Gateway が動いていること**  
   `ssh anicca@46.225.70.241 'systemctl --user status openclaw-gateway'` で `Active: active (running)` を確認。

2. **ローカルで SSH トンネル**  
   `ssh -N -L 18789:127.0.0.1:18789 anicca@46.225.70.241`（バックグラウンドでも可。例: `ssh -f -N -L ...`）。

3. **ブラウザで開く**  
   `http://127.0.0.1:18789/` または `openclaw dashboard`。必要ならトークンを貼る。

4. **Slack チャンネルセッション**  
   `http://127.0.0.1:18789/chat?session=agent%3Aanicca%3Aslack%3Achannel%3A<CHANNEL_ID>` でそのセッションを開ける。

---

## 4.5) TUI を VPS の Gateway に繋いで「VPS で動かす」

**現象:** `openclaw tui` だけ実行するとデフォルトで **Mac の** gateway (`ws://127.0.0.1:18789`) に接続する。そのためランタイムは Mac（host: CBNS03のMacBook Pro, repo: /Users/cbns03/.openclaw/workspace）になる。

**やりたいこと:** TUI から **VPS の** Anicca に接続し、VPS 上で会話する（host: VPS, repo: /home/anicca/.openclaw/workspace）。

| 順番 | やること |
|------|----------|
| 1 | **Mac の gateway を止める** — ポート 18789 を空ける。`openclaw gateway` や LaunchAgent で動いていたら停止する。 |
| 2 | **SSH トンネルを張る** — `./scripts/openclaw-vps/tunnel-control-ui.sh` を実行してそのままにしておく（別ターミナルでフォアグラウンド）、または `ssh -f -N -L 18789:127.0.0.1:18789 anicca@46.225.70.241` でバックグラウンド。 |
| 3 | **TUI を起動する** — `openclaw tui`（デフォルトで `ws://127.0.0.1:18789` に接続）。このとき 18789 はトンネル経由で VPS の gateway につながるので、**VPS 上で**動く。 |

トークンが必要な場合は VPS の `~/.openclaw/openclaw.json` の `gateway.auth.token` を Control UI の設定に貼る。事前に `ssh anicca@46.225.70.241 'systemctl --user status openclaw-gateway'` で VPS の gateway が `active (running)` であることを確認すること。

**TUI をワンショットで VPS に繋ぐ:** トンネルが張ってある状態で `./scripts/openclaw-vps/tui-vps.sh` を実行すると、VPS から token を取得して `openclaw tui` を起動する（token を手で貼る不要）。

---

## 5) Gateway が起動しないときの確認

```bash
# VPS で
journalctl --user -u openclaw-gateway -n 30 --no-pager
```

- **Failed to load environment files: No such file or directory** → `/home/anicca/.env` を作成し、`~/.openclaw/.env` をコピー。その後 `systemctl --user restart openclaw-gateway.service`。
- **Failed to spawn 'start' task** → 上記に加え、`ExecStart` のパス（`/usr/bin/node` や `openclaw`）が存在するか確認。

---

*最終更新: 2026-02-14（公式 docs.openclaw.ai に基づく）*
