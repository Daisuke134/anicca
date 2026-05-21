# OpenClaw VPS 用スクリプト

## 完全版スキルの初回インストール（VPS 上で実行）

trend-hunter / moltbook-monitor / moltbook-poster が動くには、x-research, reddit-cli, moltbook-interact の**実行コード**が必要。sync で送る SKILL.md だけでは不足。

```bash
# スクリプトを VPS に送って実行
scp scripts/openclaw-vps/install-full-skills-on-vps.sh anicca@46.225.70.241:~/
ssh anicca@46.225.70.241 'bash ~/install-full-skills-on-vps.sh'
```

- x-research: `~/.openclaw/skills/x-research` に rohunvora/x-research-skill を clone + bun install
- reddit-cli: ClawHub で `~/.openclaw/skills` にインストール
- moltbook-interact: ClawHub で `~/.openclaw/workspace/skills` にインストール

実行後、ローカルで `sync-workspace-and-skills-to-vps.sh` を再実行して Anicca 用 SKILL.md を反映する。

## スキル＋bootstrap の同期（ローカル → VPS）

**「スキルを実行できるスクリプトが見つからない」と Anicca が返す場合:**  
スキルは「SKILL.md を読んで手順をツールで実行する」仕様であり、起動用スクリプトは存在しない。以下で AGENTS.md（スキル実行ルール）と全 SKILL.md を VPS に反映する。

```bash
./scripts/openclaw-vps/sync-workspace-and-skills-to-vps.sh
ssh anicca@46.225.70.241 'systemctl --user restart openclaw-gateway.service'
```

- 反映先: `~/.openclaw/skills/`（スキル）, `~/.openclaw/cron/jobs.json`（cron 定義）, `~/.openclaw/workspace/AGENTS.md`（bootstrap）
- 同一スクリプトで jobs.json も `~/.openclaw/cron/` に scp する（移行で抜けていた根本対応）

## workspace 19 項目検証（VPS 上で実行）

`.cursor/plans/reference/openclaw-workspace-folder-tree-and-todo.md` の #13–#19 が VPS で満たされているか確認する。

```bash
scp scripts/openclaw-vps/verify-vps-workspace.sh anicca@46.225.70.241:~/
ssh anicca@46.225.70.241 'bash ~/verify-vps-workspace.sh'
```

---

## GPT-5.3 Codex への切替（運用化）

VPS 上の Anicca を `openai-codex/gpt-5.3-codex` で動かすための手順。

### 前提

- Slack に繋ぐ gateway は **VPS 1台のみ**。ローカルでは gateway を止めてあること。
- 詳細 Runbook: `.cursor/plans/reference/openclaw-anicca.md`

### クイック手順

| 順 | 作業 | 実行場所 |
|----|------|----------|
| 0 | ローカルで gateway が動いていないことを確認 | ローカル Mac |
| 1 | VPS で gateway を止める（OAuth 中 OOM 防止） | VPS |
| 2 | **openai-codex OAuth**（ブラウザで許可 → redirect URL を VPS に貼り付け） | ローカルから `ssh -tt` |
| 3 | 本スクリプトを VPS に送って実行（allowlist + primary 設定 + gateway 再起動） | VPS |
| 4 | Slack で 1 メンション = 1 返信・モデル表示を確認 | Slack |

### コマンド例（ローカルから）

```bash
# 0) ローカルで gateway が止まっていること
pgrep -fl openclaw-gateway || echo "OK"

# 1) VPS で gateway 停止
ssh anicca@46.225.70.241 'systemctl --user stop openclaw-gateway.service'

# 2) OAuth（TTY 必須。表示された URL をブラウザで開き、リダイレクト先 URL をターミナルに貼り付ける）
ssh -tt anicca@46.225.70.241 'openclaw models auth login --provider openai-codex'

# 3) スクリプトを送って実行
scp scripts/openclaw-vps/switch-to-gpt53codex.sh anicca@46.225.70.241:~/
ssh anicca@46.225.70.241 'bash ~/switch-to-gpt53codex.sh'
```

### Unknown model が出た場合

- **原因**: OAuth 未完了、または primary を切り替えたが gateway 再起動前／再起動失敗。
- **対応**:
  1. VPS で `openclaw models status --agent anicca` を実行し、`openai-codex/gpt-5.3-codex` が一覧に出るか確認。
  2. 出ない場合は OAuth をやり直し（上記 2）、その後 3 のスクリプトを再実行。
  3. 出るのに Unknown model のときは、gateway を再起動: `systemctl --user restart openclaw-gateway.service` し、ログで `agent model: openai-codex/gpt-5.3-codex` を確認。
