# OpenClaw 移行で抜けていた「根本」— ワークスペース bootstrap

OpenClaw リポジトリ（https://github.com/openclaw/openclaw）をクローンしてオンボーディングとワークスペース作成の流れを追った結果。

---

## 問題（根本）

**VPS 上で `openclaw onboard` を一度も実行していない。**

OpenClaw の設計では、**ワークスペースと「初期に用意されるべきファイル」は `openclaw onboard` が作成する**。

- コード: `src/commands/onboard-non-interactive/local.ts` → `ensureWorkspaceAndSessions(workspaceDir, runtime, { skipBootstrap })`
- `src/commands/onboard-helpers.ts` の `ensureWorkspaceAndSessions` は `ensureAgentWorkspace({ ensureBootstrapFiles: true })` を呼ぶ（`skipBootstrap` でない限り）
- `src/agents/workspace.ts` の `ensureAgentWorkspace` が次を**バンドルされたテンプレート**（`docs/reference/templates/`）から作成する:
  - **AGENTS.md**
  - **SOUL.md**
  - **TOOLS.md**
  - **IDENTITY.md**
  - **USER.md**
  - **HEARTBEAT.md**
  - **BOOTSTRAP.md**（新規ワークスペースのみ）

Anicca では **AGENTS.md だけ** を repo から sync して VPS の `~/.openclaw/workspace/` に置いている。**SOUL.md, TOOLS.md, IDENTITY.md, USER.md, HEARTBEAT.md, BOOTSTRAP.md は OpenClaw の onboard が作るもので、VPS で onboard を実行していないため存在しない。** これが「移行で抜けていた根本」＝**最初に用意されるべきファイル（bootstrap 一式）が未作成**という状態。

---

## 解決（やること 1 つ）

**VPS で一度だけ `openclaw onboard` を実行し、ワークスペースと bootstrap ファイルを作成する。**

```bash
ssh anicca@46.225.70.241 'openclaw onboard --non-interactive --accept-risk --skip-health'
```

- これで `~/.openclaw/workspace/` が作られ、AGENTS.md, SOUL.md, TOOLS.md, IDENTITY.md, USER.md, HEARTBEAT.md, BOOTSTRAP.md が OpenClaw のテンプレートから書き出される（既存ファイルは上書きしない `wx` フラグ）。
- 実行後、Anicca の sync スクリプトで **AGENTS.md を上書き** すればよい:
  - `./scripts/openclaw-vps/sync-workspace-and-skills-to-vps.sh`
- 必要なら `openclaw.json` や credential は既存のまま使う（onboard が上書きする場合は事前にバックアップし、必要な設定だけ戻す）。

---

## 参照

| 項目 | パス（OpenClaw リポジトリ） |
|------|-----------------------------|
| ワークスペース作成 | `src/agents/workspace.ts` — `ensureAgentWorkspace`, `writeFileIfMissing` |
| テンプレート配置 | `docs/reference/templates/` — AGENTS.md, SOUL.md, TOOLS.md, IDENTITY.md, USER.md, HEARTBEAT.md, BOOTSTRAP.md |
| オンボーディング呼び出し | `src/commands/onboard-non-interactive/local.ts` — `ensureWorkspaceAndSessions(workspaceDir, runtime, { skipBootstrap })` |
