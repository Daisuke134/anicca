# TikTok Nudgeカード自動投稿 Spec v3

## 開発環境

| 項目 | 値 |
|------|-----|
| **ワークツリーパス** | `/Users/cbns03/Downloads/anicca-tiktok-card-post` |
| **ブランチ** | `feature/tiktok-card-post` |
| **ベースブランチ** | `dev` |
| **作業状態** | 実装中（Blotato移行） |

---

## 1. 概要（What & Why）

### What
**実際のNudgeCardViewスクリーンショット**をTikTokに毎日自動投稿するシステム。

### Why
- **本物のカード** が広告として最も効果的（Pillow/AI生成より説得力がある）
- **毎日新しいカード** で飽きさせない（重複なし）
- **100%自動化** で手間ゼロ
- **EN/JA別アカウント運用**（各言語に最適化された投稿時間で配信）

### バージョン履歴

| バージョン | 変更点 |
|-----------|--------|
| v1 | Python/Pillow + Blotato API |
| v2 | SwiftUI ImageRenderer + TikTok Content Posting API |
| **v3（本Spec）** | **SwiftUI ImageRenderer + Blotato API（base64アップロード）** |

### v2→v3の変更点

| 項目 | v2 | v3（本Spec） |
|------|-----|-------------|
| アカウント構成 | 単一アカウント（EN/JA混在） | **2アカウント**（EN専用 + JA専用） |
| 投稿方式 | TikTok Content Posting API | **Blotato API**（base64アップロード） |
| 投稿頻度 | 1日2回（EN×1 + JA×1） | **1日4回**（EN×2 + JA×2） |
| 画像配信 | IMAGE_BASE_URL（CDNホスティング必須） | **base64→Blotato CDN**（外部ホスティング不要） |
| 認証 | TikTok OAuth 2.0（3 Secrets） | **Blotato API Key**（1 Secret、既存） |
| API審査 | TikTok Developer審査必要 | **不要**（Blotato経由） |

---

## 2. カード総数

| Problem Type | バリアント数 | 備考 |
|--------------|-------------|------|
| stayingUpLate | 21 | 5回/日 × 4.2日 |
| 他12種 | 14 × 12 = 168 | 3回/日 × 4.67日 |
| **合計/言語** | **189** | |
| **EN + JA** | **378** | |

**コンテンツ寿命:** 189枚 ÷ 2回/日/言語 = **約95日 ≈ 3ヶ月分/言語**

**全カード投稿済み時の動作:** `next_index >= 189`（全カード消化済み）の場合、reserveコマンドはexit 0 + GitHub Actions annotation warning（`All cards exhausted for {language}`）をログ出力してスキップする。Phase 4実装までの暫定動作。

---

## 3. 投稿スケジュール

### 時刻とその理由

| # | アカウント | 投稿時刻 (JST) | UTC (cron) | ターゲット時間帯 | 理由 |
|---|----------|--------------|------------|----------------|------|
| 1 | 🇯🇵 JA | **09:00** | `0 0 * * *` | 日本: 通勤・始業前 | 朝のスマホチェック時間。「今日を変えよう」系に最適 |
| 2 | 🇯🇵 JA | **19:00** | `0 10 * * *` | 日本: 帰宅・リラックス | 仕事終わり。瞑想・自己改善の需要が最も高い |
| 3 | 🇺🇸 EN | **23:00** | `0 14 * * *` | US 9AM EST / 10AM EDT | 米国朝。教育コンテンツは64%高エンゲージメント |
| 4 | 🇺🇸 EN | **10:00** (翌日) | `0 1 * * *` | US 8PM EST / 9PM EDT | 就寝前スクロール。マインドフルネスに最適 |

**出典:** Sprout Social 2025, Buffer 2025, Shopify 2026

**DST（夏時間）方針:** GitHub Actions cronはUTC固定のため、EN投稿はUTC固定運用とする。EDT期間（3月第2日曜〜11月第1日曜）は米国現地時刻が1時間ずれる（9AM→10AM, 8PM→9PM）。TikTokのエンゲージメントピークは±1時間の幅があるため、運用上許容する。JA投稿はJSTにDSTがないため影響なし。

### Blotatoアカウント設定

| アカウント | Blotato Account ID | 用途 |
|-----------|-------------------|------|
| EN | `XXX`（開発中placeholder） | 英語カード投稿 |
| JA | `XXX`（開発中placeholder） | 日本語カード投稿 |

**ID管理の単一責任:** GitHub Actions Variables（`BLOTATO_ACCOUNT_ID_EN`, `BLOTATO_ACCOUNT_ID_JA`）を唯一のsource of truthとする。コード内にハードコードしない。既存の`scripts/anicca-agent/config.py`のID（EN: 28152, JP: 27527）は別システム（daily TikTok agent）用であり、本システムとは独立。接続フェーズ完了条件: EN/JAの実IDがGitHub Variables に設定済みで、placeholder `XXX` が残っていないこと。

---

## 4. 受け入れ条件

| # | 条件 | テスト可能な形式 |
|---|------|-----------------|
| AC1 | 全189種類のカードが画像として生成される（EN/JA各） | `assets/card-screenshots/en/` と `ja/` に各189ファイル存在、全ファイルが有効なPNG |
| AC2 | 画像は実際のNudgeCardViewと同一のSwiftUI Viewから生成される | `ExportableNudgeCardView`が`NudgeCardView`と同一の`NudgeCardContent`を使用。レンダリング固定条件: `frame: 390x844`, `displayScale: 2.0`, `colorScheme: .light`, `locale: en_US / ja_JP` |
| AC3 | 1日4回投稿（EN×2 + JA×2）で重複なし | `posted_tracker.json`に記録。一意性キー: `{card_id}_{language}`。状態遷移は§6.2のstate machine定義に従う。**排他・原子性・回復戦略:** (1) Workflow `concurrency`で同時実行を排他、(2) **2段階方式:** Stage 1(reserve): `reserveNextCard`で`in_flight`予約→ローカル永続化→git push。Stage 2(post): `postPhoto`成功直後に`blotato_post_id`をtrackerにローカル永続化。ポーリング成功後`posted`に遷移→ローカル永続化。git pushはworkflowの`always()`ステップで一括実行（スクリプトクラッシュ時もblotato_post_idが永続化される）。(3) **失敗時の分岐:** (a) `blotato_post_id`未取得（postPhoto前のエラー）→ `in_flight`エントリ削除→rollback（確定未投稿のため安全）。(b) `blotato_post_id`取得済み（ポーリング中エラー等）→ `in_flight`のまま保持（次回runのTTL回復で照合）。(4) `in_flight`TTL超過回復: `blotato_post_id`で`GET /v2/posts/{id}`照合→`publicUrl`存在なら`posted`に補正、`failed`/未知ステータスなら`needs_manual_reconcile`、`blotato_post_id`未保存なら`needs_manual_reconcile`。(5) push競合は`git pull --rebase`→リトライ（最大3回）。(6) 全カード投稿済み(`next_index >= 189`)→exit 0 + warning annotation |
| AC4 | 通常運用時は完全自動。手動介入: (a) Blotato API key失効時（既存Secret更新）、(b) `needs_manual_reconcile`発生時 | `workflow_dispatch`で手動実行成功 + cronスケジュール4件設定済み |
| AC5 | ルールベース → LLM生成の順で投稿 | `card_order`配列でisAIGenerated=falseを先頭に配置 |

---

## 5. 決定事項（リサーチ結果）

### 5.1 画像生成方式

| 方式 | メリット | デメリット | **選定** |
|------|---------|-----------|----------|
| **A. SwiftUI ImageRenderer** | 実UIと完全一致、高速 | macOS限定 | ✅ **採用** |
| B. Python/Pillow | クロスプラットフォーム | デザイン再現が困難 | ❌ |

### 5.2 投稿方式

| 方式 | メリット | デメリット | **選定** |
|------|---------|-----------|----------|
| **A. Blotato API** | 既存連携あり、API審査不要、base64対応 | SLA未公開 | ✅ **採用** |
| B. TikTok Content Posting API | 公式、直接制御 | 審査必要、OAuth管理が複雑 | ❌ |

**v2でBlotatoを却下した理由と再評価:**

| v2の懸念 | v3での再評価 |
|---------|-------------|
| 画像投稿の信頼性不明 | 既存プロジェクトで毎日TikTok投稿に使用中。写真投稿はJPG形式でサポート確認済み |
| SLA未公開 | 4回/日の低頻度運用。レート制限: POST 30 req/min, Media 10 req/min。十分な余裕 |

**Blotato API仕様（調査済み）:**

| 項目 | 値 |
|------|-----|
| Base URL | `https://backend.blotato.com/v2` |
| 認証 | `blotato-api-key` ヘッダー |
| 投稿 | `POST /v2/posts` |
| メディアアップロード | `POST /v2/media`（URL or base64） |
| レスポンス | `{"postSubmissionId": "..."}` |
| ステータス確認 | `GET /v2/posts/{postSubmissionId}` → `status`, `publicUrl` |
| レート制限 | posts: 30/min, media: 10/min |
| TikTok写真形式 | **JPGのみ**（PNG→JPG変換が必要） |
| キャプション上限 | 2200文字 |

### 5.3 画像配信方式

| 方式 | 選定 | 理由 |
|------|------|------|
| **base64 → Blotato CDN** | ✅ | 外部ホスティング不要。ワークフロー内で完結 |
| IMAGE_BASE_URL（CDN） | ❌ | 外部依存が増える |

**画像配信フロー:**
```
GitHub Actions: ローカルPNGファイル読み込み
    → PNG→JPG変換（sharp）
    → base64エンコード
    → POST /v2/media（base64）
    → Blotato CDN URL取得
    → POST /v2/posts（mediaUrls: [CDN URL]）
```

### 5.4 投稿トラッカー

| 方式 | 選定 | 理由 |
|------|------|------|
| **JSON ファイル** | ✅ | シンプル、Git管理可、3ヶ月分で十分 |
| DB | ❌ | オーバーキル |

---

## 6. As-Is / To-Be

### As-Is（現状）

```
aniccaios/aniccaios/Views/NudgeCardView.swift  ← UI定義（既存）
aniccaios/aniccaios/Models/NudgeContent.swift  ← コンテンツモデル（既存）
aniccaios/aniccaios/Models/ProblemType.swift   ← 13問題タイプ（既存）
```

### To-Be（変更後）

#### 6.1 新規: CardScreenshotGenerator（v2と同一、変更なし）

```
aniccaios/
├── CardScreenshotGenerator/
│   └── Sources/
│       ├── main.swift
│       ├── CardRenderer.swift
│       ├── ExportableNudgeCardView.swift
│       └── LocalizationHelper.swift
```

#### 6.2 新規: 投稿トラッカー

```
assets/card-screenshots/
├── en/     (189 PNGファイル)
├── ja/     (189 PNGファイル)
└── posted_tracker.json
```

**posted_tracker.json スキーマ:**
```json
{
  "version": 1,
  "cards": {
    "staying_up_late_0": {
      "en": {
        "status": "posted",
        "reserved_at": "2026-02-07T08:59:50Z",
        "run_id": "12345678",
        "posted_at": "2026-02-07T09:00:00Z",
        "blotato_post_id": "abc-123-def"
      }
    }
  },
  "next_index": { "en": 2, "ja": 1 },
  "card_order": ["staying_up_late_0", "staying_up_late_1", ...]
}
```

**状態遷移（state machine）:**

| 状態 | 意味 | 遷移先 |
|------|------|--------|
| *(未登録)* | 未投稿 | → `in_flight` |
| `in_flight` | 予約済み・投稿処理中 | → `posted` / → `needs_manual_reconcile` / → *(削除)* |
| `posted` | 投稿完了 | 最終状態 |
| `needs_manual_reconcile` | TTL超過かつBlotato API照合不能 | → `posted` / → *(削除)* |

**各フィールド定義:**

| フィールド | 型 | 説明 |
|-----------|-----|------|
| `status` | `"in_flight" \| "posted" \| "needs_manual_reconcile"` | 現在の状態 |
| `reserved_at` | ISO 8601 string | `in_flight`予約時刻（TTL閾値: 1時間） |
| `run_id` | string | GitHub Actions run ID |
| `posted_at` | ISO 8601 string \| null | 投稿完了時刻 |
| `blotato_post_id` | string \| null | Blotato postSubmissionId（ステータス照合用） |

**`blotato_post_id`永続化タイミング:**
- `postPhoto()`成功直後（HTTP 200 + `postSubmissionId`取得時点）にtrackerへローカル保存（ファイル書き込み）
- ステータスポーリング（`checkPostStatus`）の前に必ず永続化する
- これにより、ポーリング中のクラッシュでも`blotato_post_id`経由で回復可能

**投稿失敗時の分岐:**
| 失敗タイミング | `blotato_post_id` | アクション |
|---------------|-------------------|-----------|
| `uploadMedia`/`postPhoto`前 | なし | `in_flight`削除 → rollback（確定未投稿） |
| `postPhoto`成功後、ポーリング中 | あり | `in_flight`保持（次回runのTTL回復で照合） |

**`in_flight` TTL超過回復（1時間）:**
1. `blotato_post_id`が保存済み → `GET /v2/posts/{blotato_post_id}` で照合
2. `status === "published"` かつ `publicUrl` あり → `posted`に補正
3. `status === "failed"` → `needs_manual_reconcile`
4. その他のステータス（`"pending"`, `"processing"` 等） → `needs_manual_reconcile`（in_flight永続化による全投稿停止を防ぐ）
5. `blotato_post_id`未保存（postPhoto前クラッシュ） → `needs_manual_reconcile`

#### 6.3 新規: 自動投稿スクリプト

```
scripts/tiktok-poster/
├── package.json
├── tsconfig.json
├── src/
│   ├── index.ts           # CLI エントリポイント
│   ├── blotato-client.ts  # Blotato API クライアント
│   ├── tracker.ts         # posted_tracker.json 操作
│   ├── tracker-io.ts      # ファイルI/O
│   ├── caption.ts         # キャプション生成
│   ├── image-loader.ts    # PNG読み込み→JPG変換→base64
│   ├── path-security.ts   # パストラバーサル防止
│   └── types.ts           # 型定義
```

**blotato-client.ts シグネチャ:**
```typescript
interface BlotatoClientOptions {
  dryRun?: boolean;
  apiKey?: string;
}

interface BlotatoPostResult {
  postSubmissionId: string;
}

interface BlotatoStatusResult {
  status: string;        // "published" | "failed" | "pending" | ...
  publicUrl: string | null;
}

class BlotatoClient {
  /** base64画像をBlotato CDNにアップロード */
  uploadMedia(base64Data: string): Promise<{ url: string }>;

  /** TikTokに写真投稿 */
  postPhoto(accountId: string, imageUrl: string, caption: string): Promise<BlotatoPostResult>;

  /** 投稿ステータス確認（recovery用） */
  checkPostStatus(postSubmissionId: string): Promise<BlotatoStatusResult | null>;
}
```

**image-loader.ts シグネチャ:**
```typescript
/** PNGファイルを読み込み、JPGに変換、base64エンコードして返す */
function loadImageAsBase64Jpg(pngPath: string): Promise<string>;
```

**キャプション要件:** すべてのキャプションに決定的キー `[card_key]`（`{card_id}_{language}`）を含める。

#### 6.4 新規: GitHub Actions

**.github/workflows/tiktok-card-post.yml:**
```yaml
name: TikTok Card Daily Post

on:
  schedule:
    # JA朝: 09:00 JST = 00:00 UTC
    - cron: '0 0 * * *'
    # JA夜: 19:00 JST = 10:00 UTC
    - cron: '0 10 * * *'
    # EN朝: 23:00 JST = 14:00 UTC固定（US 9AM EST / 10AM EDT）
    - cron: '0 14 * * *'
    # EN夜: 10:00 JST = 01:00 UTC固定（US 8PM EST / 9PM EDT）
    - cron: '0 1 * * *'
  workflow_dispatch:
    inputs:
      language:
        description: 'Language (en or ja)'
        required: true
        type: choice
        options: [en, ja]

permissions:
  contents: write

concurrency:
  group: tiktok-post
  cancel-in-progress: false

jobs:
  post:
    runs-on: ubuntu-latest
    timeout-minutes: 10
    steps:
      - uses: actions/checkout@<sha>
        with:
          ref: dev
          fetch-depth: 0
      - uses: actions/setup-node@<sha>
        with:
          node-version: '20'
      - name: Install dependencies
        run: cd scripts/tiktok-poster && npm ci
      - name: Build and test
        run: cd scripts/tiktok-poster && npm run build && npm test
      - name: Mask secrets
        run: echo "::add-mask::${{ secrets.BLOTATO_API_KEY }}"
      - name: Resolve language
        id: lang
        run: |
          if [ "${{ github.event_name }}" = "workflow_dispatch" ]; then
            echo "value=${{ github.event.inputs.language }}" >> "$GITHUB_OUTPUT"
          elif [ "${{ github.event.schedule }}" = "0 0 * * *" ] || \
               [ "${{ github.event.schedule }}" = "0 10 * * *" ]; then
            echo "value=ja" >> "$GITHUB_OUTPUT"
          else
            echo "value=en" >> "$GITHUB_OUTPUT"
          fi
      - name: Configure git
        run: |
          git config user.name "github-actions[bot]"
          git config user.email "github-actions[bot]@users.noreply.github.com"
      - name: "Stage 1: Reserve in_flight"
        run: cd scripts/tiktok-poster && npm run reserve -- --language ${{ steps.lang.outputs.value }}
        env:
          GITHUB_RUN_ID: ${{ github.run_id }}
          BLOTATO_API_KEY: ${{ secrets.BLOTATO_API_KEY }}
      - name: "Stage 1: Push reservation"
        run: |
          set -e
          git add assets/card-screenshots/posted_tracker.json
          git diff --cached --quiet && echo "No changes to commit" && exit 0
          git commit -m "chore: reserve in_flight for TikTok post"
          MAX_RETRIES=3; PUSHED=false
          for i in $(seq 1 $MAX_RETRIES); do
            git pull --rebase origin dev
            if git push; then PUSHED=true; break; fi
            echo "Push conflict, retry $i/$MAX_RETRIES"; sleep 5
          done
          [ "$PUSHED" = false ] && echo "ERROR: reservation push failed" && exit 1
      - name: "Stage 2: Post to TikTok via Blotato"
        id: post
        run: cd scripts/tiktok-poster && npm run post -- --language ${{ steps.lang.outputs.value }}
        env:
          BLOTATO_API_KEY: ${{ secrets.BLOTATO_API_KEY }}
          BLOTATO_ACCOUNT_ID_EN: ${{ vars.BLOTATO_ACCOUNT_ID_EN }}
          BLOTATO_ACCOUNT_ID_JA: ${{ vars.BLOTATO_ACCOUNT_ID_JA }}
      - name: "Stage 2: Push tracker update (success or rollback)"
        if: always() && steps.lang.outputs.value != ''
        run: |
          set -e
          git add assets/card-screenshots/posted_tracker.json
          git diff --cached --quiet && echo "No changes to commit" && exit 0
          git commit -m "chore: update TikTok post tracker"
          MAX_RETRIES=3; PUSHED=false
          for i in $(seq 1 $MAX_RETRIES); do
            git pull --rebase origin dev
            if git push; then PUSHED=true; break; fi
            echo "Push conflict, retry $i/$MAX_RETRIES"; sleep 5
          done
          [ "$PUSHED" = false ] && echo "ERROR: tracker push failed" && exit 1
```

---

## 7. テストマトリックス

| # | Phase | AC | テスト名 | カバー |
|---|-------|-----|----------|--------|
| 1 | 1 | AC1 | `testGenerateAllCards_EN_creates189Images` | OK |
| 2 | 1 | AC1 | `testGenerateAllCards_JA_creates189Images` | OK |
| 3 | 1 | AC1 | `testGeneratedImage_hasCorrectDimensions` | OK |
| 4 | 1 | AC2 | `test_exportable_view_matches_nudgecard_snapshot` | OK |
| 5 | 2 | AC3 | `test_getNextUnpostedCard_returnsCorrectCard` | OK |
| 6 | 2 | AC3 | `test_markAsPosted_updatesJSON` | OK |
| 7 | 2 | AC3 | `test_allCardsPosted_returnsTrue` | OK |
| 8 | 2 | AC3 | `test_no_duplicate_card_within_language` | OK |
| 9 | 2 | AC5 | `test_selector_prioritizes_rule_based` | OK |
| 10 | 2 | - | `test_blotato_postPhoto_dryRun_succeeds` | OK |
| 11 | 2 | - | `test_blotato_uploadMedia_base64` | OK |
| 12 | 2 | - | `test_blotato_checkPostStatus` | OK |
| 13 | 2 | - | `test_caption_includes_card_key` | OK |
| 14 | 2 | - | `test_image_loader_png_to_jpg_base64` | OK |
| 15 | 2 | AC3 | `test_reserveNextCard_sets_in_flight` | OK |
| 16 | 2 | AC3 | `test_in_flight_to_posted_transition` | OK |
| 17 | 2 | AC3 | `test_in_flight_post_failure_rolls_back` | OK |
| 18 | 2 | AC3 | `test_in_flight_rollback_decrements_next_index` | OK |
| 19 | 2 | AC3 | `test_ttl_recovery_via_blotato_status` | OK |
| 20 | 2 | AC3 | `test_reserve_blocked_when_manual_reconcile_exists` | OK |
| 21 | 2 | AC3 | `test_manual_reconcile_to_posted` | OK |
| 22 | 2 | AC3 | `test_manual_reconcile_to_unposted_rollback` | OK |
| 23 | 3 | AC4 | `test_workflow_has_four_cron_entries` | OK |
| 24 | 3 | AC4 | `test_language_resolution_four_crons_and_dispatch` | OK |
| 25 | 3 | AC3 | `test_workflow_two_stage_push` | OK |
| 26 | 3 | SEC | `test_workflow_masks_blotato_api_key` | OK |
| 27 | 3 | SEC | `test_workflow_actions_sha_pinning` | OK |
| 28 | 3 | AC3 | `test_workflow_concurrency_group` | OK |
| 29 | 3 | - | `test_accountId_routing_en_ja` | OK |
| 30 | 2 | AC3 | `test_multiple_in_flight_fail_fast` | OK |
| 31 | 2 | - | `test_path_security_traversal_prevention` | OK |
| 32 | 2 | AC3 | `test_ttl_recovery_unknown_status_to_manual_reconcile` | OK |
| 33 | 2 | AC3 | `test_all_cards_exhausted_exits_gracefully` | OK |
| 34 | 2 | - | `test_language_input_validation_rejects_invalid` | OK |

---

## 8. 境界

### 実装スコープ

| Phase | 実装 | 状態 |
|-------|------|------|
| **Phase 1** | CardScreenshotGenerator実装 + 全カード生成 | **v2で完了** |
| **Phase 2** | 投稿トラッカー + Blotatoクライアント実装 | **今回実装** |
| **Phase 3** | GitHub Actions設定 + 本番稼働 | **今回実装** |
| **Phase 4** | 既存Nudge DB再利用による無限投稿 | **将来実装** |

### やること
- Blotato APIクライアント（base64アップロード + 投稿）
- PNG→JPG変換（Blotato TikTok写真要件）
- 4 cronスケジュール（§3の時刻表）
- 2アカウント対応（EN/JA別accountId）
- placeholder ID（XXX）で開発→ユーザー接続後に差し替え

### やらないこと
- 画像ホスティング（base64アップロードで不要）
- TikTok Content Posting API連携（Blotato経由に変更）
- TikTok Developer App審査
- Phase 4（既存DB再利用）

### 触るファイル
- `scripts/tiktok-poster/src/` 内の全ファイル（大幅変更）
- `.github/workflows/tiktok-card-post.yml`

### 触らないファイル
- `aniccaios/CardScreenshotGenerator/`（v2で完成済み）
- `NudgeCardContent.swift`（参照のみ）
- `apps/api/`

---

## 9. 実行手順

### 9.1 スクリーンショット生成（初回）

```bash
cd aniccaios
swift run CardScreenshotGenerator --language en --output ../assets/card-screenshots/en
swift run CardScreenshotGenerator --language ja --output ../assets/card-screenshots/ja
```

### 9.2 自動投稿テスト

```bash
cd scripts/tiktok-poster
npm ci
npm run build && npm test           # テスト
npm run reserve -- --dry-run --language en   # ドライラン
npm run post -- --dry-run --language en      # ドライラン
```

---

## 10. セキュリティ設計

### 10.1 Blotatoトークン管理

| 項目 | 設計 |
|------|------|
| **認証方式** | API Key（HTTPヘッダー） |
| **保管するSecret** | `BLOTATO_API_KEY`（**既存**、GitHub Actions Secretsに設定済み） |
| **アカウントID** | `BLOTATO_ACCOUNT_ID_EN`, `BLOTATO_ACCOUNT_ID_JA`（GitHub Actions Variables） |
| **スコープ** | 投稿作成 + メディアアップロード + ステータス確認 |

### 10.2 入力バリデーション（多層防御）

| レイヤー | バリデーション |
|---------|--------------|
| **workflow_dispatch** | `type: choice` で `en`/`ja` に制限（GitHub UI） |
| **index.ts** | `parseLanguage()`で `'en'`/`'ja'` 以外は即 `exit 1`（GitHub API直接呼び出し対策） |
| **path-security.ts** | パストラバーサル防止（`..` 含むパスを拒否） |

### 10.3 v2からの簡素化

| v2（TikTok API） | v3（Blotato） |
|------------------|---------------|
| `TIKTOK_CLIENT_ID` | 不要 |
| `TIKTOK_CLIENT_SECRET` | 不要 |
| `TIKTOK_REFRESH_TOKEN` | 不要 |
| `IMAGE_BASE_URL` | 不要 |
| OAuth token refresh ロジック | 不要 |
| **合計: 4 Secrets + OAuth** | **合計: 1 Secret（既存）+ 2 Variables** |

### 10.4 GitHub Actions サプライチェーン対策

| 項目 | 方針 |
|------|------|
| Action参照 | commit SHA pinning |
| ログマスク | `::add-mask::` で BLOTATO_API_KEY をマスク |

---

## 11. E2E判定

| 項目 | 値 |
|------|-----|
| UI変更 | なし |
| 新画面 | なし |
| 結論 | Maestro E2Eシナリオ: **不要** |

---

## 12. ユーザー作業

### 実装前（不要）
Blotato API Keyは既にGitHub Secretsに設定済み。TikTok Developer App審査も不要。

### 実装後（接続フェーズ）

| # | タスク | 手順 | 取得するもの |
|---|--------|------|-------------|
| 1 | TikTokアカウント作成（EN用） | TikTokアプリで新規アカウント | アカウント |
| 2 | TikTokアカウント作成（JA用） | TikTokアプリで新規アカウント | アカウント |
| 3 | Blotatoに連携（EN） | Blotato → Connect Account → TikTok | Blotato Account ID |
| 4 | Blotatoに連携（JA） | Blotato → Connect Account → TikTok | Blotato Account ID |
| 5 | GitHub Varsに設定 | Repository → Settings → Variables | `BLOTATO_ACCOUNT_ID_EN`, `BLOTATO_ACCOUNT_ID_JA` |

---

## 13. 実装フェーズ

| Phase | 内容 | 状態 |
|-------|------|------|
| **1** | CardScreenshotGenerator実装 + 全カード生成 | **v2で完了（画像未生成、要実行）** |
| **2** | 投稿トラッカー + Blotatoクライアント実装 | **今回実装** |
| **3** | GitHub Actions設定 + 本番稼働 | **今回実装** |
| **4** | 既存Nudge DB再利用（95日後） | **将来実装** |

---

## 14. Phase 4: 既存Nudge DB再利用（将来実装）

> **⚠️ Phase 4は将来実装。今回のスコープ外。**

189枚の固定カード（約3ヶ月分/言語）を使い切った後、既存Nudge DBからコンテンツを再利用してTikTok投稿を継続する。

| 項目 | 値 |
|------|-----|
| トリガー | 全固定カードが投稿済み |
| コンテンツ元 | 既存Nudge DB |
| 期間 | 無限 |

---

## 15. 参考資料

- [Blotato API Reference](https://help.blotato.com/api/api-reference)
- [Blotato Publish Post](https://help.blotato.com/api/api-reference/publish-post)
- [Blotato Upload Media](https://help.blotato.com/api/api-reference/upload-media-v2-media)
- [Blotato TikTok Supported Posts](https://help.blotato.com/platforms/tiktok/supported-posts-and-media)
- [SwiftUI ImageRenderer](https://swiftwithmajid.com/2023/04/18/imagerenderer-in-swiftui/)
- [Sprout Social - Best Times to Post on TikTok 2025](https://sproutsocial.com/insights/best-times-to-post-on-tiktok/)
- [Buffer - Best Time to Post on TikTok 2025](https://buffer.com/resources/best-time-to-post-on-tiktok/)

---

**最終更新:** 2026-02-07
