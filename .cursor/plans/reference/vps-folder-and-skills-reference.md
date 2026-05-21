# VPS フォルダ構成・スキル出力パス・削除リスト・スキル説明

**重要:** 修正を VPS に反映するには **必ず VPS に反映する**。ローカルだけの変更では意味がない。**エージェントが自分で SSH（`ssh anicca@46.225.70.241`）し、scp または VPS 上編集で反映する。ユーザーにコマンドを叩かせない。** 絶対禁止事項: `.cursor/rules/openclaw-vps-absolute.md`
- 反映例: ローカルで編集 → `scp` で VPS に送る。または SSH で VPS に接続し VPS 上で編集。
- スクリプト（任意）: `./scripts/openclaw-vps/sync-workspace-and-skills-to-vps.sh`
- 必要に応じて gateway 再起動: `./scripts/openclaw-vps/vps-ensure-env-and-restart-gateway.sh`

---

## 1. VPS のフォルダ構成（/home/anicca）

```
/home/anicca/
├── .openclaw/                    # OpenClaw の作業・メモリ・スキル置き場
│   ├── workspace/                # スキル実行結果の Single Source of Truth（JSON 等）
│   │   ├── AGENTS.md             # ← sync で送られる bootstrap 用（daily-memory が読む）
│   │   ├── hooks/                # trend-hunter 出力 → x-poster / tiktok-poster が読む
│   │   │   ├── 9am/YYYY-MM-DD.json
│   │   │   └── 9pm/YYYY-MM-DD.json
│   │   ├── trends/YYYY-MM-DD.json
│   │   ├── roundtable-standup/
│   │   ├── roundtable-memory-extract/
│   │   ├── roundtable-initiative-generate/
│   │   ├── hookpost-ttl-cleaner/
│   │   ├── sto-weekly-refresh/
│   │   ├── autonomy-check/
│   │   ├── suffering/
│   │   ├── nudges/
│   │   ├── trend-hunter/
│   │   └── anicca-auto-development/
│   ├── memory/anicca/            # エージェント「anicca」用メモリ（書き出し専用）
│   │   ├── lessons-learned.md    # daily-memory が追記
│   │   └── diary-YYYY-MM-DD.md   # daily-memory が作成
│   │   # ※ AGENTS.md はここに置かない。読むなら workspace/AGENTS.md のみ。
│   ├── workspace-anicca/        # 要確認: anicca-project の重複 clone なら削除候補
│   ├── skills/                  # 各スキル（sync で上書き）
│   ├── cron/                     # cron 設定等
│   └── agents/anicca/
├── .cache/                       # 2.5GB 級 — 削除候補（後述）
├── .npm/                         # 728MB 級 — キャッシュ削除候補
├── .npm-global/                  # 509MB 級
├── .local/                       # 518MB 級
├── .bun/                         # 107MB
├── openclaw-docker/              # 81MB
├── openclaw/                     # 24K（シンボリックリンク等）
└── openclaw-git/                 # 4K
```

**なぜ memory/anicca があるか**
- エージェント「anicca」専用の**永続メモリ**（lessons-learned、日記）を置くため。
- **AGENTS.md は sync で workspace にだけ置く。** memory/anicca に AGENTS.md を期待する指示は誤り（daily-memory は workspace/AGENTS.md を読むよう修正済み）。

---

## 2. スキル別・JSON/出力パス一覧

| スキル名 | 出力（保存）先 | cron / message に書くパス（VPS） |
|----------|----------------|----------------------------------|
| trend-hunter | `workspace/trends/YYYY-MM-DD.json`, `workspace/hooks/9am|9pm/YYYY-MM-DD.json`, `workspace/trend-hunter/metrics_YYYY-MM-DD.json` | 同上（~/.openclaw/workspace/...） |
| x-poster | 読むだけ: hooks/9am または 9pm | `~/.openclaw/workspace/hooks/9am|9pm/YYYY-MM-DD.json` |
| tiktok-poster | 読むだけ: hooks/9am または 9pm。FAL で imageUrl 生成後に Blotato で投稿 | 同上 |
| app-nudge-sender | `workspace/nudges/decisions_YYYY-MM-DD.json` | 同上 |
| suffering-detector | `workspace/suffering/findings_YYYY-MM-DD.json` | 同上 |
| roundtable-standup | `workspace/roundtable-standup/run_YYYY-MM-DD.json` | 同上 |
| roundtable-memory-extract | `workspace/roundtable-memory-extract/run_YYYY-MM-DD.json` | 同上 |
| roundtable-initiative-generate | `workspace/roundtable-initiative-generate/run_YYYY-MM-DD.json` | 同上 |
| hookpost-ttl-cleaner | `workspace/hookpost-ttl-cleaner/run_YYYY-MM-DD.json` | 同上 |
| sto-weekly-refresh | `workspace/sto-weekly-refresh/run_YYYY-MM-DD.json` | 同上 |
| autonomy-check | `workspace/autonomy-check/audit_YYYY-MM-DD.json` | 同上 |
| daily-memory | **読む:** `~/.openclaw/workspace/AGENTS.md`。**書く:** `~/.openclaw/memory/anicca/lessons-learned.md`, `~/.openclaw/memory/anicca/diary-YYYY-MM-DD.md` | message で上記を明記（memory/anicca/AGENTS.md は参照しない） |
| anicca-auto-development | `workspace/anicca-auto-development/survey_*.json`, `result_*.json` | 同上 |

結果はすべて **~/.openclaw/workspace/** 以下に集約されている（daily-memory の「書く」先だけ memory/anicca）。

---

## 3. 削除リスト（ディスク 89% 対策）

| 対象 | サイズ目安 | アクション |
|------|------------|------------|
| `~/.npm` キャッシュ | 728MB | `npm cache clean --force`（必要なら） |
| `~/.cache` | 2.5GB | 中身を確認し、不要なものだけ削除（pip/bun/ffmpeg 等）。全削除は危険なので部分削除推奨。 |
| `~/.openclaw/workspace-anicca` | 要確認 | anicca-project のフル clone なら VPS には不要。**確認後**削除可（sync で workspace に AGENTS.md 等だけ送っているため、このディレクトリが必須かどうかは gateway の仕様次第）。 |
| 古いログ・一時ファイル | 要確認 | `~/.openclaw/workspace/` 内の古い run_*.json を一定日数でアーカイブまたは削除する運用を検討。 |

**注意:** .openclaw 本体は約 13MB のため、89% の主因は .cache / .npm / .local / .npm-global。これらを削減すると空きが増える。

---

## 4. 各スキルの短い説明

| スキル | 何をするか | 主な出力 |
|--------|------------|----------|
| **roundtable-standup** | その日の cron 実行状況を集計し、成功/失敗/スキップ数・ブロッカー・X/TikTok/App Nudge の件数をまとめる「朝会」レポートを生成する。 | `workspace/roundtable-standup/run_YYYY-MM-DD.json`。Slack #metrics にサマリー投稿。 |
| **roundtable-memory-extract** | 直近の standup や実行結果から学び・事実を抽出し、メモリ用の構造化データにする。 | `workspace/roundtable-memory-extract/run_YYYY-MM-DD.json`。 |
| **roundtable-initiative-generate** | トレンド・支配テーマに基づき、App / X / TikTok / Moltbook 向けの「今週のイニシアチブ」を生成する。 | `workspace/roundtable-initiative-generate/run_YYYY-MM-DD.json`。トレンドベースの提案一覧。 |
| **hookpost-ttl-cleaner** | hooks の TTL 切れエントリをスキャンし、アーカイブまたは削除する。対象がなければ no-op。 | `workspace/hookpost-ttl-cleaner/run_YYYY-MM-DD.json`（スキャン数・削除数等）。 |
| **sto-weekly-refresh** | 今週の STO（Schedule / Top categories）を更新し、来週の推奨カテゴリ・パターンを出す。 | `workspace/sto-weekly-refresh/run_YYYY-MM-DD.json`。Schedule 維持・Top categories・Issues。 |
| **autonomy-check** | Cron の健全性・DLQ・ディスク・メモリ・負荷・X ポリシー・パイプライン・失敗率をチェックし、監査ログを出す。 | `workspace/autonomy-check/audit_YYYY-MM-DD.json`。PASS/WARN/FAIL と Slack 報告。 |
| **daily-memory** | **workspace/AGENTS.md** を読み（無ければセッション履歴から学びを抽出）、その日の学びを lessons-learned に追記し、日記ファイルを 1 本書く。 | `memory/anicca/lessons-learned.md`（追記）, `memory/anicca/diary-YYYY-MM-DD.md`（新規）。Slack #metrics に報告。 |
| **trend-hunter** | X / TikTok / Reddit からトレンドを収集し、trends と hooks（9am/9pm 用の X 用 postText・TikTok 用 caption と **imagePrompt**）を生成。**imageUrl は空でよい**（tiktok-poster が FAL で生成）。 | trends, hooks/9am|9pm, trend-hunter/metrics。 |
| **x-poster** | hooks の 9am または 9pm の X 用 postText を読んで X に 1 本投稿。 | 投稿 ID を output。Slack #metrics。 |
| **tiktok-poster** | hooks の 9am または 9pm の TikTok 用 caption・imageUrl を読む。**imageUrl が空なら imagePrompt で FAL を呼び画像を生成**し、その URL で Blotato に TikTok 投稿。 | 投稿 ID。Slack #metrics。 |
| **app-nudge-sender** | その slot で誰にどの Nudge を送るか決め、Railway API で App Nudge を配信。 | `workspace/nudges/decisions_YYYY-MM-DD.json`。 |
| **suffering-detector** | 苦しみ検知の実行結果を記録。 | `workspace/suffering/findings_YYYY-MM-DD.json`。 |

---

*最終更新: 2026-02-15*
