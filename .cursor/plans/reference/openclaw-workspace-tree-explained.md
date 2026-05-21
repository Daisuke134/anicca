# OpenClaw フォルダツリー詳細説明

最終更新: 2026-02-15

## 1. skills と workspace/skills の役割（2026-02-15 統一）

| 場所 | 中身 | 同期元・インストール方法 |
|------|------|--------------------------|
| `~/.openclaw/skills/` | 全スキル（SKILL.md + 実行コード） | **repo の openclaw-skills/** を rsync。**x-research, reddit-cli** は `install-full-skills-on-vps.sh` で完全版を追加。 |
| `~/.openclaw/workspace/skills/` | **moltbook-interact のみ**（jobs.json が参照） | **VPS 上で** `clawhub install moltbook-interact --workdir ~/.openclaw/workspace --dir skills` |

- **trend-hunter, x-poster など** → `~/.openclaw/skills/` に SKILL.md（repo から rsync）。エージェントが指示に従ってツールで実行。
- **x-research** → `~/.openclaw/skills/x-research` に rohunvora リポを clone。trend-hunter がこのパスを参照。
- **reddit-cli** → `~/.openclaw/skills/reddit-cli` に ClawHub でインストール。
- **moltbook-interact** → `~/.openclaw/workspace/skills/moltbook-interact` に ClawHub でインストール。moltbook-monitor / moltbook-poster が scripts/moltbook.sh を実行。

---

## 2. GOG・Google Calendar・Gmail はどこにあるか？

### 2.1 現在の openclaw.json の状態（VPS 用）

| 連携 | 場所 | 状態 |
|------|------|------|
| **GOG** | `skills.entries.gog` | ✅ 有効。openclaw.json に記載あり（418行付近）。 |
| **Google Calendar** | plugins.entries / plugins.installs | ❌ なし。現在の openclaw.json に未登録。 |
| **Google Gmail** | plugins.entries / plugins.installs | ❌ なし。同上。 |

### 2.2 想定される所在

- **GOG**  
  OpenClaw の公式バンドルスキル。`openclaw onboard` や `skills add gog` で skills.entries に追加される。すでに openclaw.json にある。

- **Google Calendar / Gmail**  
  以下のどれかである可能性が高い：
  1. **Cursor / Codex の Agent Skills**（`.cursor/skills/google-calendar-automation/`, `.codex/skills/google-drive-automation/` 等）  
     → ローカルの Cursor/Codex 上で「このエージェントが Google を使う」用。VPS の OpenClaw には関係しない。
  2. **Composio / Rube MCP 経由**  
     → `docs/backup-composio-implementation.md` に Composio による Google Calendar 統合の設計がある。VPS の openclaw.json には現状プラグイン登録なし。
  3. **openclaw-gmail 等のプラグイン**  
     → いったんインストールしたが、VPS リセット後に openclaw.json が初期化され、設定が消えた可能性。

VPS 上で Google Calendar / Gmail を使いたい場合は、onboard の設定やプラグインの再導入が必要。

---

## 3. フォルダツリー各項目の説明

```
/home/anicca/.openclaw/workspace/
├── ops/                                    # キュー・heartbeat・提案
│   ├── steps.json                          # mission-worker が読む未実行 step キュー
│   ├── heartbeat_state.json                # ops-heartbeat の状態
│   ├── proposals.json                      # 提案一覧
│   └── completed/                          # 完了した step の記録
│       └── YYYY-MM-DD.json
│
├── trends/                                 # trend-hunter のトレンドのみ
│   └── YYYY-MM-DD.json
│
├── hooks/                                  # 投稿用 1 本（X / TikTok 用）
│   └── YYYY-MM-DD.json
│
├── trend-hunter/                           # trend-hunter のメトリクス・学習メモ
│   └── metrics_YYYY-MM-DD.json
│
├── nudges/                                 # app-nudge-sender 用（誰に何を送るか）
│   └── decisions_YYYY-MM-DD.json
│
├── suffering/                              # suffering-detector の検知結果
│   └── findings_YYYY-MM-DD.json
│
├── autonomy-check/                         # autonomy-check の監査ログ
│   └── audit_YYYY-MM-DD.json
│
├── hookpost-ttl-cleaner/                   # hookpost-ttl-cleaner の実行結果
│   └── run_YYYY-MM-DD.json
│
├── moltbook-monitor/                       # moltbook-monitor の監視結果
│   └── run_YYYY-MM-DD.json
│
├── moltbook-poster/                        # moltbook-poster の投稿結果
│   └── run_YYYY-MM-DD.json
│
├── roundtable-standup/                     # roundtable-standup の朝会出力
│   └── run_YYYY-MM-DD.json
│
├── roundtable-memory-extract/              # roundtable-memory-extract の出力
│   └── run_YYYY-MM-DD.json
│
├── roundtable-initiative-generate/         # roundtable-initiative-generate の出力
│   └── run_YYYY-MM-DD.json
│
├── sto-weekly-refresh/                     # sto-weekly-refresh の実行結果
│   └── run_YYYY-MM-DD.json
│
└── skills/                                 # moltbook-interact のみ（ClawHub 完全版）
    └── moltbook-interact/                  # scripts/moltbook.sh を moltbook-monitor/poster が使用
```

---

## 4. 各フォルダの役割（一覧）

| フォルダ | 役割 | 誰が書く/読む |
|----------|------|----------------|
| **ops/** | キュー、heartbeat、提案の状態管理 | ops-heartbeat（書く）、mission-worker（読む・更新） |
| **trends/** | 日次のトレンド候補 | trend-hunter |
| **hooks/** | 当日 X/TikTok 用の投稿 1 本 | trend-hunter（書く）、x-poster / tiktok-poster（読む） |
| **trend-hunter/** | メトリクスと学習メモ | trend-hunter |
| **nudges/** | 誰に何を送るかの決定 | app-nudge-sender |
| **suffering/** | 苦しみ・危機の検知結果 | suffering-detector |
| **autonomy-check/** | 規約違反・監査ログ | autonomy-check |
| **hookpost-ttl-cleaner/** | 古い hook の TTL 掃除 | hookpost-ttl-cleaner |
| **moltbook-monitor/** | Moltbook 監視結果 | moltbook-monitor |
| **moltbook-poster/** | Moltbook 投稿結果 | moltbook-poster |
| **roundtable-standup/** | 朝会の出力 | roundtable-standup |
| **roundtable-memory-extract/** | メモリ抽出の出力 | roundtable-memory-extract |
| **roundtable-initiative-generate/** | イニシアチブ生成の出力 | roundtable-initiative-generate |
| **sto-weekly-refresh/** | 週次の投稿時間最適化結果 | sto-weekly-refresh |
| **skills/** | moltbook-interact の完全版（ClawHub） | moltbook-monitor, moltbook-poster |

---

## 5. Cursor/Codex の skills との違い

| 種別 | 場所 | 用途 |
|------|------|------|
| **OpenClaw VPS skills** | `~/.openclaw/skills/` または `workspace/skills/` | VPS 上で動く Anicca エージェントが使う |
| **Cursor Agent Skills** | `.cursor/skills/`（例: google-calendar-automation） | Cursor IDE の AI がローカルタスクで使う |
| **Codex Skills** | `.codex/skills/` | Codex CLI のエージェントが使う |

Google Calendar / Gmail を「接続した」と言っている場合、Cursor や Codex のスキルとして追加した可能性があり、その場合は VPS の OpenClaw には含まれない。
