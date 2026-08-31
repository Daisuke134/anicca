# Mr.bot: Dais テナントのクラウド移行（ローカル colima worker 撤去）

日付: 2026-08-08
状態: DESIGN
実装 executor: Sonnet 5 subagent（Dais 2026-08-08 指示）
レビュー: superpowers code-review（Opus 5 fresh one-shot）

## 1. 問題（実測済みの現状）

Dais 個人の Mr.bot テナントだけが、この Mac mini 上のローカル Docker
（colima VM 6.2G）で動いている。他ユーザーは Railway のクラウドで動く。

実測した構成（2026-08-08）:

| 要素 | 実測値 |
|---|---|
| コンテナ | `mr-bot-local-worker-1` / `mr-bot-local-api-1`（image: `mr-bot-local-runtime:dev`、Up 5 days、healthy） |
| worker の役割 | `node scripts/runtime-up.js internal-worker`。env に `LM_TELEGRAM_BOT_TOKEN` / `LM_INSTAGRAM_*` / `LM_TIKTOK_*` / `LM_POSTIZ_API_KEY` / `SUPABASE_URL` / `LM_RUNTIME_TENANT_ID` |
| 蘇生装置 | `ai.anicca.colima-autostart.plist`（launchd、RunAtLoad + 300s、`~/scripts/colima-autostart.sh` が `colima start`）+ コンテナ側 `restart=unless-stopped` |
| 監視 | `ai.anicca.outbound-runtime-healthcheck.plist`（2分ごと、`http://127.0.0.1:18790/health`、実体は `outbound-guardian.js`） |
| 起動元 compose | `~/anicca-project/.worktrees/openclaw-mr-bot-daily-task6b-20260729/deploy/local` — **既に削除済み**。コンテナは image の慣性だけで生きているゾンビ構成（rebuild 定義がディスク上に無い） |

### 何が悪いか

1. **dogfood になっていない**: Dais が web ユーザーと同じ経路を通らないため、ユーザーが踏むエラーに Dais が最初に気づけない。
2. **Mac が単一障害点**: 再起動・ディスク死で Dais の daily loop（Telegram 送信・SNS 連携）が止まる。
3. **再現不能**: compose 元が消えており、image が死んだら復旧手順が存在しない。
4. **ディスク 6.2G**: colima VM が常時ディスクを占有（このスペックの Mac は空き 3GB を切って CRITICAL になった実績あり）。

## 2. ゴール

- Dais のテナントの internal-worker を Railway（既存 LM クラウド環境）で動かす。
- Dais は以後 web ユーザー #1 として、他ユーザーと**完全に同一の経路**で LM を使う。
- ローカルの colima / コンテナ / launchd 2 plist を撤去し、この Mac から LM 実行体依存をゼロにする。
- **移行中に Dais の daily loop を止めない**（切替瞬間の数分を除く）。

### 非ゴール

- local self-host 形態（製品の3形態の1つ）のコード削除はしない。`deploy/local` の**コードパス**は OSS ユーザー向け機能として残す。撤去するのは「Dais のテナントがそれで動いている状態」だけ。
- Railway web app / Supabase 本体の変更はしない。

## 3. 検討した代替案

| 案 | 却下理由 |
|---|---|
| A. 現状維持（ローカル継続） | dogfood 不成立・単一障害点・ゾンビ構成が直らない |
| B. ローカルを「正規の再現可能構成」に作り直す | 再現性は直るが dogfood 不成立と障害点は残る。Dais の「web と同じ体験をする」要求を満たさない |
| **C. Railway に internal-worker を追加し Dais テナントを移す（採用）** | repo に `Dockerfile.runtime` + `nixpacks.toml` が既にあり部品が揃っている。書く量最小、Dais の要求と一致 |

## 4. 設計

### 4.1 アーキテクチャ（after）

```
Railway
├── web app（既存・他ユーザー）──→ Supabase
└── internal-worker（新設・全テナント、Dais 含む）──→ Supabase
                                   └→ Telegram / IG / TikTok / Postiz

Mac mini: LM 実行体なし（colima 削除・plist 削除）
```

### 4.2 フェーズ（順序厳守）

**鉄則: クラウドで動いた証拠を見てから、ローカルを止める。逆順は禁止。**

#### Phase 0 — 保全と調査（読み取りのみ + 保険）
1. `docker save mr-bot-local-runtime:dev -o /Users/operator/lm-runtime-image-backup.tar` — rebuild 不能なので撤去前の唯一の復元手段を確保する（Phase 3 完了 + 30 日後に削除してよい）。
2. worker / api コンテナの env を **file 直結**で退避（stdout に通さない。secrets を含む）。
3. Railway 既存プロジェクトのサービス構成・env・デプロイ方法を確認。
4. Supabase 側の Dais テナント（`LM_RUNTIME_TENANT_ID`）設定を確認。

#### Phase 1 — Railway に internal-worker を立てる
1. Railway に新サービス追加。ビルドは repo の `Dockerfile.runtime`。
2. 起動コマンド = `node scripts/runtime-up.js internal-worker`（ローカルと同一）。
3. env を Phase 0 の退避分から移植。**ただし `LM_TELEGRAM_BOT_TOKEN` はこの時点では未設定**（切替まで両立させない）。
4. 完了条件: health endpoint が 200 を返す（Telegram 以外の機能で疎通確認）。

#### Phase 2 — 切替 + E2E
1. 1手順で: cloud worker に `LM_TELEGRAM_BOT_TOKEN` を設定して再起動 → 直後に `docker stop mr-bot-local-worker-1 mr-bot-local-api-1`。
   - 根拠: Telegram bot token は 1 トークンにつき消費者 1 つ（getUpdates/webhook の排他）。並走させると取り合いで両方壊れる。
2. E2E 検証（全部 PASS するまで Phase 3 に進まない）:
   - Telegram: 実メッセージ送信 → LM からの応答受信を実観測
   - daily loop: 1 周実走 → Supabase への書き込みを実観測
   - health: cloud の health endpoint 200
3. **rollback**: 失敗したら cloud worker から token を外し `docker start` で local 復帰（3 分）。

#### Phase 3 — ローカル撤去（Phase 2 PASS 後のみ・宣言して実行）
1. `launchctl bootout gui/$UID/ai.anicca.colima-autostart` + plist 削除
2. `launchctl bootout gui/$UID/ai.anicca.outbound-runtime-healthcheck` + plist 削除
3. コンテナ削除 → `colima stop && colima delete`
4. `df -h` で回収を実測（期待 +6.2G）
5. healthcheck の後継: cloud worker の死活監視は Railway の restart policy（クラッシュ時自動再起動）に委ねる。ローカル launchd による監視は残さない（Mac 依存を戻さないため）。加えて Dais 自身が web ユーザーとして毎日使う = 異常は dogfood で即日発覚する、がこの移行の主目的そのもの。

### 4.3 E2E 判定（GATE 3）

| テスト | PASS 条件 |
|---|---|
| Telegram 往復 | Dais の Telegram に実メッセージが cloud worker から届く（送信元 ID 確認） |
| daily loop 1 周 | cloud worker のログに loop 完走 + Supabase に新規行 |
| local 撤去後の生存 | 撤去 24h 後に daily loop が継続していること（launchd が消えても何も再起動しないこと） |
| Mac 非依存 | （撤去後）colima プロセス 0、port 18788/18790 LISTEN 0 |

### 4.4 エラーハンドリング / リスク

| リスク | 対策 |
|---|---|
| Telegram token 取り合い | Phase 2 の 1 手順切替。並走ゼロ |
| image 再現不能のまま撤去 | Phase 0 の `docker save` が済むまで一切の停止操作禁止 |
| secrets 漏洩 | env 退避は file 直結。stdout に出したら即 rotate |
| Railway 課金増 | worker 1 サービス分（月数ドル規模）。ローカル 6.2G + 単一障害点解消と引き換え |
| cloud worker が IG/TikTok の browser 系操作を必要とする場合 | Phase 0 で worker の実ジョブ種を確認。ローカルブラウザ（CloakBrowser）必須のジョブが見つかったら、そのジョブだけの扱いを spec 改訂で決める（発見時点で Phase 1 を止めて報告） |

## 5. 変更ファイル見積り（Plan size）

| 要素 | ファイル | 推定 LOC |
|---|---|---|
| Railway サービス定義（必要なら） | `deploy/railway/` 新設 or Railway UI のみ | 0–40 |
| worker の cloud 用 env 差分（必要なら） | `config/` or Railway env | 0–10 |
| 撤去スクリプト（手順書で足りるなら書かない） | なし | 0 |

コード変更はほぼゼロの見込み。主作業は配線・env 移植・検証。3 files / 100 LOC 以内 → slice 分割不要。

## 6. TODO（実行順）

| # | タスク | 状態 |
|---|---|---|
| 1 | 本 spec 書き + commit | in_progress |
| 2 | Phase 0: 保全と調査 | pending |
| 3 | Phase 1: Railway internal-worker デプロイ | pending (blocked by 2) |
| 4 | Phase 2: 切替 + E2E | pending (blocked by 3) |
| 5 | Phase 3: ローカル撤去 + 6.2G 回収実測 | pending (blocked by 4) |
