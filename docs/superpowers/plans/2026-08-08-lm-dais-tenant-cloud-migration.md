# LM Dais テナント・クラウド移行 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Dais テナントの LM internal-worker をローカル colima から Railway に移し、ローカル実行体（colima 6.2G + launchd 2 plist）を撤去する。

**Architecture:** Railway に `Dockerfile.runtime` ベースの worker サービスを新設 → Telegram token を1手順で切替 → E2E PASS 後にローカル撤去。コード変更はほぼゼロ、作業の本体は配線・env 移植・実測検証。

**Tech Stack:** Railway CLI / Docker (colima) / launchctl / mr-bot repo (`scripts/runtime-up.js`)

**Spec:** `docs/superpowers/specs/2026-08-08-lm-dais-tenant-cloud-migration-design.md`

**鉄則:** クラウドで動いた証拠を見てからローカルを止める。Task 順序の入替禁止。

---

### Task 1: image バックアップ（rebuild 不能の保険）

**Files:** なし（ローカル FS のみ）

- [ ] **Step 1: ディスク空きを確認（tar は数 GB になりうる）**

Run: `df -h /System/Volumes/Data | tail -1`
Expected: Avail が 8Gi 以上。8Gi 未満なら STOP して報告。

- [ ] **Step 2: image を save**

```bash
docker save mr-bot-local-runtime:dev -o /Users/operator/lm-runtime-image-backup.tar
```

- [ ] **Step 3: tar の実在と中身を検証**

Run: `ls -lh /Users/operator/lm-runtime-image-backup.tar && tar -tf /Users/operator/lm-runtime-image-backup.tar | head -3`
Expected: ファイルサイズ > 100M、manifest.json 等のエントリが出る。0 byte や tar エラーなら Task 1 からやり直し。

### Task 2: env 退避（file 直結・stdout 禁止）

**Files:**
- Create: `/Users/operator/.lm-migration/worker.env`（chmod 600、git 管理外）
- Create: `/Users/operator/.lm-migration/api.env`（chmod 600、git 管理外）

- [ ] **Step 1: 退避先を作る**

```bash
mkdir -p /Users/operator/.lm-migration && chmod 700 /Users/operator/.lm-migration
```

- [ ] **Step 2: env を file 直結で書き出す（値を画面に出さない）**

```bash
docker inspect mr-bot-local-worker-1 --format '{{range .Config.Env}}{{println .}}{{end}}' > /Users/operator/.lm-migration/worker.env
docker inspect mr-bot-local-api-1 --format '{{range .Config.Env}}{{println .}}{{end}}' > /Users/operator/.lm-migration/api.env
chmod 600 /Users/operator/.lm-migration/*.env
```

- [ ] **Step 3: 件数だけで検証（中身を表示しない）**

Run: `wc -l /Users/operator/.lm-migration/*.env`
Expected: worker.env が 20 行以上。0 行なら inspect からやり直し。
★ このファイルの中身を cat / echo / ログ出力するの禁止。漏れたら該当 key を即 rotate。

### Task 3: Railway 現状調査

**Files:**
- Create: `/Users/operator/.lm-migration/railway-recon.md`（調査メモ、secrets 書き込み禁止）

- [ ] **Step 1: CLI 認証確認**

Run: `railway whoami`
Expected: アカウント名が返る。未認証なら STOP して報告（対話 login が要るため）。

- [ ] **Step 2: 既存プロジェクト/サービスを列挙**

```bash
railway list
```

Expected: LM の既存プロジェクトが見える。プロジェクト名・既存サービス名・環境名を `railway-recon.md` に記録。

- [ ] **Step 3: LM リポジトリと Railway の接続方式を確認**

`railway-recon.md` に以下を記録:
- 既存 web app サービスのビルド方式（GitHub 連携 or CLI up）
- どの環境（production/staging）に足すか → production
- `Dockerfile.runtime` がプロジェクト root にあること: `ls /Users/operator/Projects/mr-bot-main/Dockerfile.runtime`

### Task 4: worker ジョブ種の監査（browser 依存ゲート）

**Files:** なし（読み取りのみ）

- [ ] **Step 1: worker の capabilities を確認（key 名のみ）**

```bash
grep -o '^LM_WORKER_CAPABILITIES=.*' /Users/operator/.lm-migration/worker.env | cut -d= -f2
```

- [ ] **Step 2: internal-worker の実装でローカル依存を探す**

```bash
grep -rn "cloak\|CDP\|9222\|playwright\|puppeteer\|localhost\|127.0.0.1" /Users/operator/Projects/mr-bot-main/apps/mr-bot/scripts/runtime-up.js | head -20
grep -rln "cloak\|launch_persistent_context\|:9222" /Users/operator/Projects/mr-bot-main/apps/mr-bot/lib/ | head -10
```

Expected: ヒットゼロ、または health/自ポート系のみ。
**GATE: ローカルブラウザ（CloakBrowser/CDP）必須のジョブが見つかったら Task 5 に進まず報告**（spec §4.4 のとおり spec 改訂が必要）。

### Task 5: Railway internal-worker サービス新設（Phase 1）

**Files:**
- Modify: Railway 側設定のみ（repo コード変更なし想定）

- [ ] **Step 1: サービス作成**

```bash
cd /Users/operator/Projects/mr-bot-main
railway add --service lm-internal-worker
```

（CLI 版によりサブコマンド差異あり。失敗したら `railway add --help` を読んで同等操作。ダッシュボード操作が必要なら手順を報告。）

- [ ] **Step 2: ビルド設定**

- Builder: Dockerfile、path = `Dockerfile.runtime`
- Start command: `node scripts/runtime-up.js internal-worker`
- Restart policy: ON_FAILURE（Railway 既定で可）

- [ ] **Step 3: env 移植（Telegram token を除く）**

`/Users/operator/.lm-migration/worker.env` から **`LM_TELEGRAM_BOT_TOKEN` 以外**を設定する。値を画面に出さないため、1 key ずつ:

```bash
# 例（値は env ファイルから直接 shell 変数に読む。echo しない）
set -a; source /Users/operator/.lm-migration/worker.env; set +a
railway variables --service lm-internal-worker \
  --set "LM_DEPLOYMENT_ROLE=$LM_DEPLOYMENT_ROLE" \
  --set "LM_RUNTIME_TENANT_ID=$LM_RUNTIME_TENANT_ID" \
  --set "SUPABASE_URL=$SUPABASE_URL"
# …worker.env の全 key を同様に（LM_TELEGRAM_BOT_TOKEN だけ除外）
```

注意: `LM_WORKER_HEALTH_PORT` は Railway の PORT 慣習に合わせる（`PORT` を尊重する実装か runtime-up.js で確認。違うなら `LM_WORKER_HEALTH_PORT=$PORT` 相当を設定）。
ローカル専用 key（`MINIO_*` がローカル MinIO を指す場合等）は移植前に endpoint がクラウドから届くか確認。届かない host（localhost/host.docker.internal）を指す key は報告してから判断。

- [ ] **Step 4: デプロイ**

```bash
railway up --service lm-internal-worker --detach
```

- [ ] **Step 5: health 検証（Telegram なしの疎通）**

```bash
railway logs --service lm-internal-worker | tail -30
```

Expected: worker 起動ログ、クラッシュループなし。health endpoint が公開されているなら `curl -fsS <railway-domain>/health` で 200。
**PASS するまで Task 6 に進まない。**

### Task 6: 切替 + E2E（Phase 2）

- [ ] **Step 1: 切替（1 手順・並走ゼロ）**

```bash
set -a; source /Users/operator/.lm-migration/worker.env; set +a
railway variables --service lm-internal-worker --set "LM_TELEGRAM_BOT_TOKEN=$LM_TELEGRAM_BOT_TOKEN" && \
docker stop mr-bot-local-worker-1 mr-bot-local-api-1
```

（Railway は変数変更で自動再デプロイ。local stop を同一コマンド行で直結し、token の二重消費時間を最小化する。）

- [ ] **Step 2: E2E — Telegram 往復**

Dais の Telegram bot に実メッセージを送り、cloud worker からの応答を実観測。
Run: `railway logs --service lm-internal-worker | grep -i telegram | tail -5`
Expected: 受信 + 送信のログ。Dais 側にも実着信。

- [ ] **Step 3: E2E — daily loop 1 周**

worker のジョブを 1 回実走させ（スケジュール待ちでなく即時トリガー手段があればそれを使う）、Supabase に新規行が書かれたことを実観測。
Expected: ログに loop 完走 + Supabase の対象テーブルに新 timestamp 行。

- [ ] **Step 4: 失敗時 rollback（3 分）**

```bash
railway variables --service lm-internal-worker --set "LM_TELEGRAM_BOT_TOKEN=" && \
docker start mr-bot-local-api-1 mr-bot-local-worker-1
```

rollback したら原因を直してから Step 1 に戻る。

- [ ] **Step 5: PASS evidence を記録**

`/Users/operator/.lm-migration/e2e-pass.md` に、観測した Telegram messageId・Supabase 行・ログ行(秘密なし)を記録。

### Task 7: ローカル撤去（Phase 3・E2E PASS 後のみ）

- [ ] **Step 1: PASS evidence 確認**

Run: `ls /Users/operator/.lm-migration/e2e-pass.md`
Expected: 存在する。無ければ Task 6 未完 = STOP。

- [ ] **Step 2: launchd 2 plist を撤去**

```bash
launchctl bootout gui/$(id -u)/ai.anicca.colima-autostart
launchctl bootout gui/$(id -u)/ai.anicca.outbound-runtime-healthcheck
rm /Users/operator/Library/LaunchAgents/ai.anicca.colima-autostart.plist
rm /Users/operator/Library/LaunchAgents/ai.anicca.outbound-runtime-healthcheck.plist
```

- [ ] **Step 3: コンテナと VM を削除**

```bash
docker rm -f mr-bot-local-worker-1 mr-bot-local-api-1
colima stop && colima delete -f
```

- [ ] **Step 4: 回収を実測**

Run: `df -h /System/Volumes/Data | tail -1 && du -sh /Users/operator/.colima 2>/dev/null || echo ".colima gone"`
Expected: Avail が Task 実行前より +5G 以上。`.colima` が消えている。

- [ ] **Step 5: 復活しないことを検証（launchd 残骸ゼロ）**

Run: `launchctl list | grep -iE "colima|outbound-runtime" || echo "clean"`
Expected: `clean`。10 分後に `pgrep -fl colima || echo "no colima"` → `no colima`。

- [ ] **Step 6: 24h 生存確認の予約**

翌日、cloud worker の daily loop 継続 + Telegram 着信を確認（spec §4.3 の 24h テスト）。確認後 `/Users/operator/lm-runtime-image-backup.tar` は 30 日保持後に削除可。

---

## Self-Review 済みチェック

- Spec coverage: Phase 0→Task 1-4 / Phase 1→Task 5 / Phase 2→Task 6 / Phase 3→Task 7。spec §4.3 の E2E 4 項目は Task 6 Step 2-3 + Task 7 Step 5-6 でカバー。
- Placeholder: なし（Railway CLI のサブコマンド差異のみ「--help を読んで同等操作」と明示）。
- 順序依存: Task N は Task N-1 の PASS evidence が前提。入替禁止。
