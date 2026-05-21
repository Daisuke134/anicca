# 1.5.0 DBスキーマ・APIコントラクト

> **関連Spec**: [main-spec.md](./main-spec.md)（本体）
>
> **最終更新**: 2026-01-28

---

## 1. 前提条件

**pgcrypto拡張が必要**（`gen_random_uuid()` 関数を使用）:
```sql
-- マイグレーション実行前に確認/有効化
CREATE EXTENSION IF NOT EXISTS pgcrypto;
```

※ メインDBはRailway PostgreSQL + Prisma。Supabaseは補助サービス（Slackトークン、Worker Memory等）であり、メインDBではない。Railway PostgreSQLではpgcryptoが未有効の場合があるため、マイグレーション前に上記コマンドで有効化すること。

### 1.1 マイグレーション実施手順

**Prismaの制約**: Prismaは以下をネイティブサポートしない:
- CHECK制約
- GENERATED ALWAYS AS（計算列）
- Partial Index / GIN Index

**運用方針**: SQL DDLを正とし、Prismaマイグレーションを手動拡張する。

```bash
# Step 1: Prismaマイグレーションを生成（適用しない）
cd apps/api && npx prisma migrate dev --create-only --name 1_5_0_cross_user_learning

# Step 2: 生成されたSQLファイルを編集
# 場所: prisma/migrations/<timestamp>_1_5_0_cross_user_learning/migration.sql
# 以下を手動追記:
#   - 全CHECK制約（本Spec Section 2のSQL定義を参照）
#   - type_stats の GENERATED ALWAYS AS カラム（tap_rate, thumbs_up_rate）
#   - Partial Index（hook_candidates.is_wisdom）
#   - GIN Index（hook_candidates.target_user_types, wisdom_patterns.target_user_types）
#   - 降順インデックス（tiktok_posts.posted_at DESC）

# Step 3: マイグレーションを適用
npx prisma migrate dev

# Step 4: 制約が正しく作成されたことを確認
npx prisma db execute --stdin <<< "SELECT conname FROM pg_constraint WHERE conname LIKE 'chk_%';"
```

**追記必須項目一覧**:

| テーブル | 追記項目 | 種別 |
|---------|----------|------|
| user_type_estimates | `REFERENCES profiles(id) ON DELETE CASCADE` FK、`CHECK (primary_type IN (...))`, `CHECK (confidence >= 0 AND confidence <= 1)` | FK, CHECK |
| type_stats | `CHECK (type_id IN (...))`, `CHECK (tone IN (...))`, `chk_sample_size_consistency`, `chk_thumbs_*` | CHECK |
| type_stats | `tap_rate GENERATED ALWAYS AS`, `thumbs_up_rate GENERATED ALWAYS AS` | 計算列 |
| hook_candidates | 全CHECK制約、`chk_hook_candidates_user_types`、`chk_hook_candidates_problem_types`、`UNIQUE(text, tone)`、`WHERE is_wisdom = true` Partial Index、`USING GIN(target_user_types)` | CHECK, Index, UNIQUE |
| tiktok_posts | `chk_metrics_consistency` | CHECK |
| wisdom_patterns | `CHECK (confidence ...)`、`chk_wisdom_patterns_user_types`、`USING GIN(target_user_types)` | CHECK, Index |

**注意**: Prismaモデルには計算列（tap_rate, thumbs_up_rate）を定義しない。読み取りは`prisma.$queryRaw`で直接SQLを実行する。

---

## 2. 新規テーブル（1.5.0）

### user_type_estimates

```sql
CREATE TABLE user_type_estimates (
  user_id UUID PRIMARY KEY REFERENCES profiles(id) ON DELETE CASCADE,
  primary_type VARCHAR(10) NOT NULL
    CHECK (primary_type IN ('T1', 'T2', 'T3', 'T4')),  -- 有効なタイプのみ
  type_scores JSONB NOT NULL DEFAULT '{}',
  confidence NUMERIC(5,4) NOT NULL DEFAULT 0
    CHECK (confidence >= 0 AND confidence <= 1),  -- 0..1制約
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_user_type_estimates_primary ON user_type_estimates(primary_type);
```

### type_stats

```sql
CREATE TABLE type_stats (
  type_id VARCHAR(10) NOT NULL
    CHECK (type_id IN ('T1', 'T2', 'T3', 'T4')),  -- 有効なタイプのみ
  tone VARCHAR(20) NOT NULL
    CHECK (tone IN ('strict', 'gentle', 'logical', 'provocative', 'philosophical')),  -- 5種のトーン
  tapped_count INT NOT NULL DEFAULT 0 CHECK (tapped_count >= 0),
  ignored_count INT NOT NULL DEFAULT 0 CHECK (ignored_count >= 0),
  thumbs_up_count INT NOT NULL DEFAULT 0 CHECK (thumbs_up_count >= 0),
  thumbs_down_count INT NOT NULL DEFAULT 0 CHECK (thumbs_down_count >= 0),
  sample_size INT NOT NULL DEFAULT 0 CHECK (sample_size >= 0),  -- 総Nudgeイベント数 = tapped_count + ignored_count
  tap_rate NUMERIC(5,4) GENERATED ALWAYS AS (
    CASE WHEN sample_size > 0 THEN tapped_count::NUMERIC / sample_size ELSE 0 END
  ) STORED,  -- 自動計算のため0..1制約は不要（式で保証）
  thumbs_up_rate NUMERIC(5,4) GENERATED ALWAYS AS (
    CASE WHEN tapped_count > 0 THEN thumbs_up_count::NUMERIC / tapped_count ELSE 0 END
  ) STORED,  -- 自動計算のため0..1制約は不要（式で保証）
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  PRIMARY KEY (type_id, tone),
  -- 集計整合性制約
  CONSTRAINT chk_sample_size_consistency CHECK (sample_size = tapped_count + ignored_count),
  CONSTRAINT chk_thumbs_up_le_tapped CHECK (thumbs_up_count <= tapped_count),
  CONSTRAINT chk_thumbs_down_le_tapped CHECK (thumbs_down_count <= tapped_count),
  CONSTRAINT chk_thumbs_total_le_tapped CHECK (thumbs_up_count + thumbs_down_count <= tapped_count)
);
-- 集計ルール: sample_size = tapped_count + ignored_count（イベント単位）
-- aggregateTypeStats.js で日次集計時に更新
--
-- ※ 集計対象: nudge_events.state->>'user_type' が保存されているイベントのみ
--   旧イベント（user_type未記録）は集計対象外
--
-- データソース定義（nudge_events LEFT JOIN nudge_outcomes で集計）:
--   tapped_count: nudge_outcomes.signals->>'outcome' = 'tapped' のイベント数
--   ignored_count: nudge_outcomes が NULL または outcome が 'tapped' 以外のイベント数
--   計算式: ignored_count = (全nudge_events数) - tapped_count
--   thumbs_up_count: tapped かつ nudge_outcomes.signals->>'thumbsUp' = 'true' のイベント数
--   thumbs_up_rate: thumbs_up_count / tapped_count（タップした人のうち👍した割合）
```

### hook_candidates

```sql
CREATE TABLE hook_candidates (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  text TEXT NOT NULL,
  tone VARCHAR(20) NOT NULL
    CHECK (tone IN ('strict', 'gentle', 'logical', 'provocative', 'philosophical')),  -- 5種のトーン
  UNIQUE (text, tone),  -- 同一Hook+Toneの重複防止
  target_problem_types TEXT[] NOT NULL DEFAULT '{}',
  target_user_types TEXT[] NOT NULL DEFAULT '{}',
  -- 配列要素の妥当性制約（許可リストのみ、NULLは型レベルで防止）
  -- ※ PostgreSQL TEXT[] は NOT NULL 制約で要素レベルのNULL禁止不可だが、
  --    アプリケーション層（API入力バリデーション）でNULL要素を拒否する
  -- ※ 空配列は許容（"全ProblemType/全UserType対象"を意味する。初期投入後に集計で更新される）
  CONSTRAINT chk_hook_candidates_user_types CHECK (
    target_user_types <@ ARRAY['T1','T2','T3','T4']::text[]
  ),
  CONSTRAINT chk_hook_candidates_problem_types CHECK (
    target_problem_types <@ ARRAY['self_loathing','procrastination','rumination','staying_up_late','porn_addiction','anxiety','cant_wake_up','lying','bad_mouthing','alcohol_dependency','anger','obsessive','loneliness']::text[]
  ),
  app_tap_rate NUMERIC(5,4) NOT NULL DEFAULT 0
    CHECK (app_tap_rate >= 0 AND app_tap_rate <= 1),
  app_thumbs_up_rate NUMERIC(5,4) NOT NULL DEFAULT 0
    CHECK (app_thumbs_up_rate >= 0 AND app_thumbs_up_rate <= 1),
  app_sample_size INT NOT NULL DEFAULT 0 CHECK (app_sample_size >= 0),
  tiktok_like_rate NUMERIC(5,4) NOT NULL DEFAULT 0
    CHECK (tiktok_like_rate >= 0 AND tiktok_like_rate <= 1),
  tiktok_share_rate NUMERIC(5,4) NOT NULL DEFAULT 0
    CHECK (tiktok_share_rate >= 0 AND tiktok_share_rate <= 1),
  tiktok_sample_size INT NOT NULL DEFAULT 0 CHECK (tiktok_sample_size >= 0),
  tiktok_high_performer BOOLEAN NOT NULL DEFAULT FALSE,  -- like率>10% AND share率>5%
  is_wisdom BOOLEAN NOT NULL DEFAULT FALSE,
  exploration_weight NUMERIC(3,2) NOT NULL DEFAULT 1.0 CHECK (exploration_weight >= 0),
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_hook_candidates_wisdom ON hook_candidates(is_wisdom) WHERE is_wisdom = TRUE;
CREATE INDEX idx_hook_candidates_high_performer ON hook_candidates(tiktok_high_performer) WHERE tiktok_high_performer = TRUE;
CREATE INDEX idx_hook_candidates_target_types ON hook_candidates USING GIN(target_user_types);
```

### tiktok_posts

```sql
CREATE TABLE tiktok_posts (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  hook_candidate_id UUID REFERENCES hook_candidates(id),
  tiktok_video_id VARCHAR(100) UNIQUE,  -- 重複投稿防止（fetch_metrics.py で照合後にUPDATE）
  blotato_post_id VARCHAR(100),
  caption TEXT,
  agent_reasoning TEXT,  -- エージェントの思考過程（なぜこのHook/トーンを選んだか）
  posted_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  metrics_fetched_at TIMESTAMPTZ,
  view_count BIGINT CHECK (view_count IS NULL OR view_count >= 0),  -- BIGINTで将来の大規模カウント対応
  like_count BIGINT CHECK (like_count IS NULL OR like_count >= 0),
  comment_count BIGINT CHECK (comment_count IS NULL OR comment_count >= 0),
  share_count BIGINT CHECK (share_count IS NULL OR share_count >= 0),
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  -- メトリクス整合性制約: 未取得時は全てNULL、取得後は全て非NULL
  CONSTRAINT chk_metrics_consistency CHECK (
    (metrics_fetched_at IS NULL AND view_count IS NULL AND like_count IS NULL AND comment_count IS NULL AND share_count IS NULL)
    OR (
      metrics_fetched_at IS NOT NULL AND view_count IS NOT NULL AND like_count IS NOT NULL AND comment_count IS NOT NULL AND share_count IS NOT NULL
    )
  )
);

CREATE INDEX idx_tiktok_posts_hook ON tiktok_posts(hook_candidate_id);
CREATE INDEX idx_tiktok_posts_posted_at ON tiktok_posts(posted_at DESC);
```

### wisdom_patterns

```sql
CREATE TABLE wisdom_patterns (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  pattern_name VARCHAR(100) NOT NULL,
  description TEXT,
  target_user_types TEXT[] NOT NULL DEFAULT '{}',
  -- 配列要素の妥当性制約（許可リストのみ、NULLは型レベルで防止）
  -- ※ PostgreSQL TEXT[] は NOT NULL 制約で要素レベルのNULL禁止不可だが、
  --    アプリケーション層（API入力バリデーション）でNULL要素を拒否する
  -- ※ 空配列は許容（"全UserType対象"を意味する）
  CONSTRAINT chk_wisdom_patterns_user_types CHECK (
    target_user_types <@ ARRAY['T1','T2','T3','T4']::text[]
  ),
  effective_tone VARCHAR(20)
    CHECK (effective_tone IS NULL OR effective_tone IN ('strict', 'gentle', 'logical', 'provocative', 'philosophical')),
  effective_hook_pattern TEXT,
  effective_content_length VARCHAR(20)
    CHECK (effective_content_length IS NULL OR effective_content_length IN ('short', 'medium', 'long')),
  app_evidence JSONB NOT NULL DEFAULT '{}',
  tiktok_evidence JSONB NOT NULL DEFAULT '{}',
  confidence NUMERIC(5,4) NOT NULL DEFAULT 0
    CHECK (confidence >= 0 AND confidence <= 1),  -- 0..1制約
  verified_at TIMESTAMPTZ,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_wisdom_patterns_types ON wisdom_patterns USING GIN(target_user_types);
```

---

## 3. Prisma schema追加

```prisma
model UserTypeEstimate {
  userId      String   @id @db.Uuid @map("user_id")
  primaryType String   @db.VarChar(10) @map("primary_type")
  typeScores  Json     @db.JsonB @default("{}") @map("type_scores")
  confidence  Decimal  @db.Decimal(5,4) @default(0)
  createdAt   DateTime @default(now()) @db.Timestamptz @map("created_at")
  updatedAt   DateTime @default(now()) @db.Timestamptz @map("updated_at")

  // FK: profiles(id) - 手動DDLで追加済み
  profile     Profile  @relation(fields: [userId], references: [id], onDelete: Cascade)

  @@index([primaryType])  // idx_user_type_estimates_primary
  @@map("user_type_estimates")
}

model TypeStats {
  typeId         String   @db.VarChar(10) @map("type_id")
  tone           String   @db.VarChar(20)
  tappedCount    Int      @default(0) @map("tapped_count")
  ignoredCount   Int      @default(0) @map("ignored_count")
  thumbsUpCount  Int      @default(0) @map("thumbs_up_count")
  thumbsDownCount Int     @default(0) @map("thumbs_down_count")
  sampleSize     Int      @default(0) @map("sample_size")
  updatedAt      DateTime @default(now()) @db.Timestamptz @map("updated_at")
  // NOTE: tap_rate, thumbs_up_rate はSQLの GENERATED ALWAYS AS カラム
  // Prismaでは @ignore 相当で定義せず、クエリ時に直接SQL参照する
  // 読み取りは prisma.$queryRaw で実行

  @@id([typeId, tone])
  @@map("type_stats")
}

// === Generated Columns 整合性方針 ===
// type_stats.tap_rate と thumbs_up_rate は PostgreSQL の GENERATED ALWAYS AS で定義
// Prisma はこれらを直接サポートしないため、以下の方針を採用:
// 1. Prismaモデルには計算カラムを定義しない
// 2. 読み取りは prisma.$queryRaw で直接SQLを実行
// 3. 書き込みは通常のPrisma updateで（計算カラム以外）
// 参照: https://github.com/prisma/prisma/issues/6368

model HookCandidate {
  id                 String    @id @db.Uuid @default(dbgenerated("gen_random_uuid()"))
  text               String    @db.Text
  tone               String    @db.VarChar(20)
  targetProblemTypes String[]  @default([]) @map("target_problem_types")
  targetUserTypes    String[]  @default([]) @map("target_user_types")
  appTapRate         Decimal   @db.Decimal(5,4) @default(0) @map("app_tap_rate")
  appThumbsUpRate    Decimal   @db.Decimal(5,4) @default(0) @map("app_thumbs_up_rate")
  appSampleSize      Int       @default(0) @map("app_sample_size")
  tiktokLikeRate     Decimal   @db.Decimal(5,4) @default(0) @map("tiktok_like_rate")
  tiktokShareRate    Decimal   @db.Decimal(5,4) @default(0) @map("tiktok_share_rate")
  tiktokSampleSize   Int       @default(0) @map("tiktok_sample_size")
  tiktokHighPerformer Boolean  @default(false) @map("tiktok_high_performer")
  isWisdom           Boolean   @default(false) @map("is_wisdom")
  explorationWeight  Decimal   @db.Decimal(3,2) @default(1.0) @map("exploration_weight")
  createdAt          DateTime  @default(now()) @db.Timestamptz @map("created_at")
  updatedAt          DateTime  @default(now()) @db.Timestamptz @map("updated_at")

  tiktokPosts TiktokPost[]

  @@unique([text, tone])  // 同一Hook+Toneの重複防止
  @@index([tone])  // Prisma対応インデックス
  // NOTE: GIN Index (target_user_types), Partial Index (is_wisdom) は手動SQLで追加
  @@map("hook_candidates")
}

model TiktokPost {
  id                String    @id @db.Uuid @default(dbgenerated("gen_random_uuid()"))
  // hookCandidateId は NULL 許容（テスト投稿や分類未確定の投稿を許可）
  hookCandidateId   String?   @db.Uuid @map("hook_candidate_id")
  tiktokVideoId     String?   @db.VarChar(100) @unique @map("tiktok_video_id")  // fetch_metrics.pyで照合後UPDATE
  blotatoPostId     String?   @db.VarChar(100) @map("blotato_post_id")
  caption           String?   @db.Text
  agentReasoning    String?   @db.Text @map("agent_reasoning")  // エージェントの思考過程
  postedAt          DateTime  @default(now()) @db.Timestamptz @map("posted_at")
  metricsFetchedAt  DateTime? @db.Timestamptz @map("metrics_fetched_at")
  viewCount         BigInt?   @map("view_count")  // BIGINTで将来の大規模カウント対応
  likeCount         BigInt?   @map("like_count")
  commentCount      BigInt?   @map("comment_count")
  shareCount        BigInt?   @map("share_count")
  createdAt         DateTime  @default(now()) @db.Timestamptz @map("created_at")

  hookCandidate HookCandidate? @relation(fields: [hookCandidateId], references: [id])

  @@index([hookCandidateId])
  @@index([postedAt(sort: Desc)])  // 最新投稿検索用
  @@map("tiktok_posts")
}

model WisdomPattern {
  id                   String    @id @db.Uuid @default(dbgenerated("gen_random_uuid()"))
  patternName          String    @db.VarChar(100) @map("pattern_name")
  description          String?   @db.Text
  targetUserTypes      String[]  @default([]) @map("target_user_types")
  effectiveTone        String?   @db.VarChar(20) @map("effective_tone")
  effectiveHookPattern String?   @db.Text @map("effective_hook_pattern")
  effectiveContentLength String? @db.VarChar(20) @map("effective_content_length")
  appEvidence          Json      @db.JsonB @default("{}") @map("app_evidence")
  tiktokEvidence       Json      @db.JsonB @default("{}") @map("tiktok_evidence")
  confidence           Decimal   @db.Decimal(5,4) @default(0)
  verifiedAt           DateTime? @db.Timestamptz @map("verified_at")
  createdAt            DateTime  @default(now()) @db.Timestamptz @map("created_at")
  updatedAt            DateTime  @default(now()) @db.Timestamptz @map("updated_at")

  // NOTE: GIN Index (target_user_types) は手動SQLで追加
  @@map("wisdom_patterns")
}
```

---

## 4. APIコントラクト

### 共通バリデーション要件

**配列フィールドのNULL要素禁止**（DB CHECK制約の補完）:

PostgreSQL CHECK制約では配列要素のNULL検知が困難なため、以下のフィールドは**API層で入力バリデーション**を行う:

| テーブル | フィールド | バリデーション |
|---------|-----------|---------------|
| hook_candidates | target_user_types | `arr.every(x => x !== null && ['T1','T2','T3','T4'].includes(x))` |
| hook_candidates | target_problem_types | `arr.every(x => x !== null && PROBLEM_TYPES.includes(x))` |
| wisdom_patterns | target_user_types | `arr.every(x => x !== null && ['T1','T2','T3','T4'].includes(x))` |

**実装箇所**: 各Admin API のリクエストボディバリデーション（Zod/Joi等）

---

### GET /api/mobile/user-type

**概要**: ユーザーのタイプ推定結果を取得

| 項目 | 内容 |
|------|------|
| **認証** | Bearer Token（Authorization header） |
| **レート制限** | 100 req/min/user |

**レスポンス（200 OK）**:
```json
{
  "success": true,
  "data": {
    "primaryType": "T1",
    "typeName": "完璧主義",
    "confidence": 0.75,
    "scores": {
      "T1": 8,
      "T2": 3,
      "T3": 1,
      "T4": 2
    },
    "lastUpdated": "2026-01-26T10:00:00Z"
  }
}
```

**エラーレスポンス**:
| コード | 条件 | レスポンス |
|--------|------|-----------|
| 401 | 認証なし/無効 | `{"success": false, "error": "Unauthorized"}` |
| 404 | プロフィール不存在 | `{"success": false, "error": "Profile not found"}` |
| 500 | 内部エラー | `{"success": false, "error": "Internal server error"}` |

**ログ方針**:
- 404: `warn`レベル、user_id含む（デバッグ用、通常発生しない）
- 500: `error`レベル、スタックトレース含む、アラート対象

**欠損時の挙動（エッジケース処理）**:

| ケース | Profile | user_type_estimates | Problems | 処理 | lastUpdated |
|--------|---------|---------------------|----------|------|-------------|
| 0. 不存在 | NULL | - | - | **404返却** | - |
| 1. 正常 | 存在 | 存在 | 任意 | DBから返却 | saved `updated_at` |
| 2. 未計算 | 存在 | 欠損 | 非空 | 即時計算→UPSERT→返却 | NOW() |
| 3. 空問題 | 存在 | 任意 | 空配列 | T4/0を返却（保存しない） | NOW() |

**ケース2の詳細（user_type_estimatesが存在しないがProblemsが非空）**:
- バックフィル未実行、オンボーディング後の初回アクセス等で発生
- Problems から `classifyUserType()` を即時計算
- confidence > 0 の場合のみ user_type_estimates に UPSERT
- `lastUpdated` は計算時刻（NOW()）を返却

```javascript
// 実装ロジック（userTypeService.js）

// タイプ名マッピング（API仕様用）
const TYPE_NAMES = {
  T1: '完璧主義',
  T2: '比較傾向',
  T3: '衝動型',
  T4: '不安型'
};

// DBフォーマット → API仕様フォーマット変換
function formatApiResponse(data, updatedAt) {
  return {
    primaryType: data.primaryType,
    typeName: TYPE_NAMES[data.primaryType],
    confidence: data.confidence,
    scores: data.typeScores || data.scores,  // DB: typeScores, 計算結果: scores
    lastUpdated: updatedAt
  };
}

async function getUserType(userId) {
  // 1. 既存データ確認
  const existing = await db.userTypeEstimates.findUnique({ where: { userId } });
  if (existing) {
    return formatApiResponse(existing, existing.updatedAt);
  }

  // 2. プロフィール確認
  const profile = await db.profiles.findUnique({ where: { id: userId } });

  // ケース0: プロフィール不存在 → 404
  if (!profile) {
    throw new NotFoundError('Profile not found');
  }

  const problems = profile.problems || [];

  if (problems.length === 0) {
    // ケース3: 空問題（プロフィール存在、problems空）→ 保存しない（デフォルト T4 を返却）
    const defaultData = { primaryType: 'T4', confidence: 0, scores: { T1: 0, T2: 0, T3: 0, T4: 0 } };
    return formatApiResponse(defaultData, new Date());
  }

  // ケース2: 即時計算→UPSERT
  const result = classifyUserType(problems);
  if (result.confidence > 0) {
    await db.userTypeEstimates.upsert({
      where: { userId },
      create: {
        userId,
        primaryType: result.primaryType,
        typeScores: result.scores,  // classifyUserType returns 'scores', Prisma model uses 'typeScores'
        confidence: result.confidence
      },
      update: {
        primaryType: result.primaryType,
        typeScores: result.scores,
        confidence: result.confidence
      }
    });
  }
  return formatApiResponse(result, new Date());
}
```

**Problem未設定時の挙動**:
- Problems が空配列の場合、デフォルトタイプ **T4（不安型）** を `confidence: 0` で返す
- **新規ユーザー**: user_type_estimates には保存しない（confidence > 0 の場合のみ保存）
- **既存ユーザーがProblemsをクリアした場合**: user_type_estimates の該当レコードを **DELETE** する
  - 理由: 古い推定値が残ると、タイプ別学習・Nudge生成で誤ったタイプが使われる
  - 実装場所: `apps/api/src/routes/mobile/profile.js` の Problems 更新ハンドラ
- テスト: `test_classifyUserType_empty_problems_returns_default`, `test_clearProblems_deletes_user_type_estimate`, `test_getUserType_calculates_on_missing` で検証

### 削除済み: POST /admin/tiktok/retention, POST /admin/tiktok/metrics

**理由**: メトリクス取得は Apify TikTok Scraper (`clockworks/tiktok-scraper`) で完全自動化。手動入力API不要。
`fetch_metrics.py` が24時間後に自動取得し、`tiktok_posts` と `hook_candidates` を更新する。

---

## 5. 実装判断メモ（2026-01-28 確定）

### Profile モデルへの逆方向 relation 追加（必須）

`UserTypeEstimate` が `Profile` を `@relation` で参照するため、`schema.prisma` の `Profile` モデルにも逆方向 relation を追加する:

```prisma
model Profile {
  id        String @id @db.Uuid
  email     String? @unique
  metadata  Json @db.JsonB @default("{}")
  createdAt DateTime @default(now()) @db.Timestamptz @map("created_at")
  updatedAt DateTime @default(now()) @db.Timestamptz @map("updated_at")

  settings         UserSetting?
  userTypeEstimate UserTypeEstimate?  // ← 1.5.0 Track A で追加

  @@map("profiles")
}
```

### Prisma vs Raw SQL 使い分け方針

Prisma Issue #6368 により GENERATED ALWAYS AS カラムは Prisma モデルに定義不可。DB ホスティング（Railway/Supabase）に依存しない Prisma の ORM 制限。

| 操作 | 方式 | 理由 |
|------|------|------|
| `userTypeService` UPSERT/DELETE | Prisma | 単純CRUD、型安全 |
| `GET /api/mobile/user-type` findUnique | Prisma | 単純読み取り |
| `aggregateTypeStats.js` 集計 | Raw SQL (`query()`) | 複雑なJOIN+GROUP BY |
| `type_stats` の `tap_rate`/`thumbs_up_rate` 読み取り | `prisma.$queryRaw` | GENERATED COLUMN |
| `generateNudges.js` タイプ別パターン取得 | Raw SQL | 既存パターンとの一貫性 |

---

## 6. PostgreSQL ベストプラクティスレビュー（2026-01-28）

Supabase Postgres Best Practices に基づくスキーマレビュー結果。

### 6.1 ブロッキング（マイグレーション前に必須修正）

#### CRITICAL: nudge_events JSONB パスのインデックス欠如

`aggregateTypeStats` ジョブと `initHookLibrary` が `nudge_events` を `state->>'user_type'` / `state->>'hook'` でフィルタする。インデックスなしでは全テーブルスキャンが発生し、データ増加に伴いパフォーマンスが劣化する。

**追加するインデックス（マイグレーションSQLに含める）**:

```sql
-- aggregateTypeStats用: domain + user_type存在フィルタ
CREATE INDEX idx_nudge_events_domain_user_type
  ON nudge_events(domain)
  WHERE (state->>'user_type') IS NOT NULL;

-- initHookLibrary用: domain + hook存在フィルタ
CREATE INDEX idx_nudge_events_domain_hook
  ON nudge_events(domain)
  WHERE (state->>'hook') IS NOT NULL;
```

#### HIGH: nudge_outcomes.nudge_event_id の FK インデックス欠如

PostgreSQL は外部キーカラムを自動インデックスしない。`nudge_events` と `nudge_outcomes` の JOIN（aggregateTypeStats、initHookLibrary、既存クエリ全て）がシーケンシャルスキャンになる。

**追加するインデックス（マイグレーションSQLに含める）**:

```sql
CREATE INDEX idx_nudge_outcomes_event_id ON nudge_outcomes(nudge_event_id);
```

#### HIGH: aggregateTypeStats の並行実行防止

日次 cron ジョブが重複実行された場合、集計カウントが不正になるか deadlock が発生する。

**実装方針: pg_try_advisory_lock を使用**:

```javascript
// aggregateTypeStats.js の冒頭
const LOCK_ID = 150001;
const [{ pg_try_advisory_lock: acquired }] = await query(
  'SELECT pg_try_advisory_lock($1)', [LOCK_ID]
);
if (!acquired) {
  console.log('aggregateTypeStats already running, skipping');
  return;
}
try {
  // ... 集計ロジック ...
} finally {
  await query('SELECT pg_advisory_unlock($1)', [LOCK_ID]);
}
```

同パターンを `backfill-user-types.js`（LOCK_ID=150002）にも適用する。

### 6.2 推奨改善（マイグレーション時に対応）

#### MEDIUM: type_stats カウントカラムを BIGINT に変更

`type_stats` は最大20行（4タイプ×5トーン）。集計カウントは全ユーザーのイベントを合算するため、年数経過で数百万に達する可能性がある。INT（21億）でも十分だが、20行テーブルでは BIGINT のストレージ増加は無視できる。

**変更**: `tapped_count`, `ignored_count`, `thumbs_up_count`, `thumbs_down_count`, `sample_size` → `BIGINT`

#### MEDIUM: hook_candidates.target_problem_types の GIN インデックス追加

`target_user_types` には GIN インデックスがあるが、`target_problem_types` にはない。`hookSelector.js` が問題タイプでフィルタする場合にシーケンシャルスキャンになる。

```sql
CREATE INDEX idx_hook_candidates_target_problems ON hook_candidates USING GIN(target_problem_types);
```

#### MEDIUM: updated_at 自動更新トリガー

Raw SQL で更新するテーブル（`type_stats`、バックフィル対象）は Prisma の `@updatedAt` が効かない。トリガーを作成するか、全 Raw SQL UPDATE に `updated_at = NOW()` を明示する。

**方針: Raw SQL UPDATE に `updated_at = NOW()` を明示する**（トリガーより明示的で予測可能）。

#### MEDIUM: バックフィルスクリプトのバッチ処理

1ユーザーずつ UPSERT ではなく、200件ずつカーソルベースでバッチ UPSERT を実行する。10-50倍高速。

### 6.3 受容する制限（変更不要）

| # | 項目 | 理由 |
|---|------|------|
| 1 | UUIDv4 PK（gen_random_uuid） | 既存スキーマと一貫。現規模（数千行）では断片化は問題にならない。1.6.0でUUIDv7を検討 |
| 2 | VARCHAR vs TEXT | CHECK制約が実質的な制約。VARCHAR は意図を明示する防御的設計 |
| 3 | NUMERIC(5,4) の精度 | 制約で [0,1] が保証されるため問題なし |
| 4 | hook_candidates.tone の B-tree インデックス | Prisma `@@index([tone])` がマイグレーション時に自動生成される |
