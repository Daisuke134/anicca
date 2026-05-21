# Anicca OpenClaw Implementation Specification

> **目的**: Anicca を OpenClaw エージェントとして実装し、24/7 自律運用を実現する
> **RFC 2119 準拠**: MUST, SHOULD, MAY を使用
> **最終更新**: 2026-02-05 (Round 3)
> **ベース**: 1.6.2-ultimate-spec.md + OpenClaw Framework Research

**運用現状（どこで動いているか）:** `.cursor/plans/reference/openclaw-anicca.md` を参照。現時点では **ローカル**で gateway 運用中・VPS gateway は停止済み。

---

## 0. Executive Summary

| 項目 | 決定 |
|------|------|
| **Anicca の定義** | 単一 OpenClaw エージェント。全プラットフォームを統合管理 |
| **ホスティング** | Hetzner VPS (Ashburn) + Tailscale + Docker |
| **iOS アプリ連携** | Railway API 経由。Nudge は Railway Cron → API → APNs（変更なし） |
| **自律レベル** | 承認フロー付き（重要アクションは Slack 確認） |
| **初期スコープ** | x-poster, tiktok-poster, suffering-detector のみ |

### スケーリング決定（CRITICAL）

| Skill | 実行場所 | 理由 |
|-------|---------|------|
| x-poster | OpenClaw VPS | 1日2回、軽量 |
| tiktok-poster | OpenClaw VPS | 1日1回、軽量 |
| suffering-detector | OpenClaw VPS (isolated session) | Heartbeat、軽量、race condition回避 |
| **app-nudge-sender** | **Railway Cron のみ（OpenClawには実装しない）** | 毎時、高負荷、既に動作中、二重実行防止 |
| trend-hunter | **1.7.0へ延期** | 優先度低 |
| feedback-fetch | **1.7.0へ延期** | 優先度低 |

**重要**: app-nudge-sender は Railway Cron に残す。OpenClaw の cron entries には追加しない。
これにより二重実行（duplicate notifications）を防止する。

---

## 0.1 レビュー対応（2026-02-05 Round 3）

### Critical Issues 修正

| # | Issue | 対応 | Status |
|---|-------|------|--------|
| 1 | Token timing attack | 定数時間比較に修正（Section 4.2） | ✅ |
| 2 | Secret管理 | `.env.example` 追加、rotation policy 文書化（Section 2.3） | ✅ |
| 3 | Input validation | Zod でリクエスト検証（Section 4.2） | ✅ |
| 4 | Race condition (hook_statistics) | 楽観的ロック（version column）**必須**（Section 4.1, 4.3） | ✅ |
| 5 | Circuit breaker | 外部 API に circuit breaker 追加（Section 3 各 Skill） | ✅ |
| 6 | FAL optional 明確化 | tiktok-poster は FAL 必須、x-poster は任意（Section 3.2） | ✅ |
| 7 | app-nudge-sender 二重実行 | OpenClaw cron から削除、Railway Cron のみ | ✅ |
| 8 | trend-hunter/feedback-fetch 未定義 | 1.7.0へ延期、cron から削除 | ✅ |
| 9 | suffering-detector race condition | isolated session に変更 | ✅ |
| 10 | Thompson Sampling 詳細なし | アルゴリズム追加（Section 3.5） | ✅ |
| 11 | DB スキーマなし | agent_posts, hook_statistics スキーマ追加（Section 4.3） | ✅ |
| 12 | Docker root 実行 | non-root user 指定（Section 5.3） | ✅ |
| 13 | 全 Skill に DLQ なし | DLQ 設定追加（Section 4.6） | ✅ |
| 14 | FeedbackSchema 未定義 | Section 4.2 に追加 | ✅ |
| 15 | PostRecordSchema.imageUrl 欠落 | Section 4.2 で追加 | ✅ |
| 16 | OpenAI/Slack circuit breaker 未定義 | Section 4.5 に追加 | ✅ |

---

## 1. アーキテクチャ

### 1.1 全体図

```
┌─────────────────────────────────────────────────────────────────────────┐
│                      ANICCA OPENCLAW AGENT                               │
│                                                                         │
│  ┌────────────────────────────────────────────────────────────────────┐ │
│  │                    Hetzner VPS (Ashburn)                           │ │
│  │                                                                    │ │
│  │  ┌──────────────────────────────────────────────────────────────┐  │ │
│  │  │                  OpenClaw Gateway                             │  │ │
│  │  │                  ws://127.0.0.1:18789                         │  │ │
│  │  │                                                               │  │ │
│  │  │  Sessions:                                                    │  │ │
│  │  │  ├─ main → DM対話、承認フロー                                │  │ │
│  │  │  ├─ cron:x-poster → X投稿（isolated）                        │  │ │
│  │  │  ├─ cron:tiktok-poster → TikTok投稿（isolated）              │  │ │
│  │  │  └─ heartbeat:suffering-detector → 苦しみ検出（isolated）    │  │ │
│  │  │                                                               │  │ │
│  │  │  NOTE: app-nudge-sender は Railway Cron で実行（OpenClaw外）  │  │ │
│  │  └──────────────────────────────────────────────────────────────┘  │ │
│  │                           │                                        │ │
│  │  ┌────────────────────────┴────────────────────────────────────┐  │ │
│  │  │                     Skills                                   │  │ │
│  │  │  ├─ x-poster                                                 │  │ │
│  │  │  ├─ tiktok-poster                                            │  │ │
│  │  │  ├─ suffering-detector                                       │  │ │
│  │  │  ├─ hook-selector (helper)                                   │  │ │
│  │  │  ├─ content-verifier (helper)                                │  │ │
│  │  │  ├─ memu-manager (helper)                                    │  │ │
│  │  │  └─ steipete/slack (clawhub)                                 │  │ │
│  │  │                                                              │  │ │
│  │  │  NOT included: app-nudge-sender (Railway Cron only)          │  │ │
│  │  └─────────────────────────────────────────────────────────────┘  │ │
│  │                                                                    │ │
│  │  External Connections:                                             │ │
│  │  ├─ Railway API (anicca-proxy-production.up.railway.app)          │ │
│  │  ├─ Blotato API (X/TikTok posting)                                │ │
│  │  ├─ FAL API (image generation)                                    │ │
│  │  ├─ OpenAI API (LLM)                                              │ │
│  │  └─ Slack Webhook (notifications)                                  │ │
│  │                                                                    │ │
│  └────────────────────────────────────────────────────────────────────┘ │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                       RAILWAY (Production)                               │
│  ├─ API Service (anicca-proxy-production.up.railway.app)                │
│  ├─ PostgreSQL (Railway Internal)                                       │
│  └─ Cron Service (nudge-cronp) → 継続稼働（app-nudge-sender 担当）      │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                          iOS App                                         │
│  ├─ Push通知受信（APNs）                                                │
│  ├─ API 通信（/api/mobile/*）                                           │
│  └─ Nudge フィードバック送信                                            │
└─────────────────────────────────────────────────────────────────────────┘
```

### 1.2 ディレクトリ構成

```
~/.openclaw/
├─ openclaw.json                 # メイン設定
├─ credentials/                  # OAuth/API キー
├─ workspaces/
│  └─ anicca/
│     ├─ AGENTS.md               # エージェント指示
│     ├─ SOUL.md                 # Anicca のパーソナリティ
│     ├─ skills/
│     │  ├─ x-poster/
│     │  │  ├─ SKILL.md
│     │  │  ├─ main.py
│     │  │  ├─ hook_selector.py
│     │  │  ├─ verifier.py
│     │  │  └─ error_handler.py
│     │  ├─ tiktok-poster/
│     │  │  ├─ SKILL.md
│     │  │  ├─ main.py
│     │  │  └─ error_handler.py
│     │  ├─ suffering-detector/
│     │  │  ├─ SKILL.md
│     │  │  ├─ detector.py
│     │  │  ├─ error_handler.py
│     │  │  └─ responders/
│     │  ├─ hook-selector/
│     │  │  └─ SKILL.md
│     │  ├─ content-verifier/
│     │  │  └─ SKILL.md
│     │  └─ memu-manager/
│     │     └─ SKILL.md
│     └─ memory/
│        └─ sessions/
├─ dlq/                          # Dead Letter Queue (OpenClaw Skills only)
│  ├─ x-poster.jsonl
│  ├─ tiktok-poster.jsonl
│  └─ suffering-detector.jsonl
└─ logs/
   └─ anicca.log
```

---

## 2. 設定ファイル

### 2.1 openclaw.json

```json5
{
  // Gateway 設定
  gateway: {
    bind: "loopback",           // 127.0.0.1 のみ
    port: 18789,
    auth: {
      mode: "password",
      password: "${ANICCA_AGENT_TOKEN}"
    },
    tailscale: {
      mode: "serve",            // Tailnet 内のみアクセス可
      resetOnExit: true
    }
  },

  // エージェント設定
  agents: {
    defaults: {
      model: "anthropic/claude-opus-4-5",
      workspace: "~/.openclaw/workspaces/anicca"
    },
    list: [
      {
        id: "anicca-main",
        workspace: "~/.openclaw/workspaces/anicca"
      }
    ]
  },

  // Skills 設定
  skills: {
    load: {
      watch: true,
      watchDebounceMs: 250
    },
    entries: {
      // === 自作 Skills ===
      "x-poster": {
        enabled: true,
        env: {
          ANICCA_PROXY_BASE_URL: "https://anicca-proxy-production.up.railway.app",
          ANICCA_AGENT_TOKEN: "${ANICCA_AGENT_TOKEN}",
          BLOTATO_API_KEY: "${BLOTATO_API_KEY}",
          X_ACCOUNT_ID: "${X_ACCOUNT_ID}",
          OPENAI_API_KEY: "${OPENAI_API_KEY}",
          FAL_API_KEY: "${FAL_API_KEY}",
          SLACK_WEBHOOK_AGENTS: "${SLACK_WEBHOOK_AGENTS}"
        }
      },
      "tiktok-poster": {
        enabled: true,
        env: {
          ANICCA_PROXY_BASE_URL: "https://anicca-proxy-production.up.railway.app",
          ANICCA_AGENT_TOKEN: "${ANICCA_AGENT_TOKEN}",
          BLOTATO_API_KEY: "${BLOTATO_API_KEY}",
          TIKTOK_ACCOUNT_ID: "${TIKTOK_ACCOUNT_ID}",
          FAL_API_KEY: "${FAL_API_KEY}",
          SLACK_WEBHOOK_AGENTS: "${SLACK_WEBHOOK_AGENTS}"
        }
      },
      // NOTE: app-nudge-sender は OpenClaw に含めない（Railway Cron で継続）
      "suffering-detector": {
        enabled: true,
        env: {
          ANICCA_PROXY_BASE_URL: "https://anicca-proxy-production.up.railway.app",
          ANICCA_AGENT_TOKEN: "${ANICCA_AGENT_TOKEN}",
          MOLTBOOK_API_KEY: "${MOLTBOOK_API_KEY}",
          SLACK_WEBHOOK_AGENTS: "${SLACK_WEBHOOK_AGENTS}"
        }
      },

      // === clawhub Skills ===
      "steipete-slack": {
        enabled: true,
        env: {
          SLACK_WEBHOOK_URL: "${SLACK_WEBHOOK_AGENTS}"
        }
      }
    }
  },

  // Cron スケジュール
  cron: {
    entries: [
      // X 投稿: 09:00, 21:00 JST
      {
        id: "x-poster-morning",
        schedule: "0 0 * * *",   // 00:00 UTC = 09:00 JST
        timezone: "Asia/Tokyo",
        action: "skill",
        skill: "x-poster",
        message: "Post morning wisdom to X"
      },
      {
        id: "x-poster-evening",
        schedule: "0 12 * * *",  // 12:00 UTC = 21:00 JST
        timezone: "Asia/Tokyo",
        action: "skill",
        skill: "x-poster",
        message: "Post evening wisdom to X"
      },
      // TikTok 投稿: 20:00 JST
      {
        id: "tiktok-poster",
        schedule: "0 11 * * *",  // 11:00 UTC = 20:00 JST
        timezone: "Asia/Tokyo",
        action: "skill",
        skill: "tiktok-poster",
        message: "Post wisdom image to TikTok"
      }
      // NOTE: 以下は OpenClaw に含めない
      // - app-nudge-sender: Railway Cron で継続（二重実行防止）
      // - trend-hunter: 1.7.0 へ延期
      // - feedback-fetch: 1.7.0 へ延期
    ]
  },

  // Heartbeat (isolated session で実行)
  heartbeat: {
    entries: [
      {
        id: "suffering-detector",
        interval: "5m",
        action: "skill",
        skill: "suffering-detector",
        message: "Check for suffering posts on Moltbook",
        session: "isolated"  // main session と分離して race condition 回避
      }
    ]
  }
}
```

### 2.2 環境変数一覧

| 変数名 | 用途 | 必須 |
|--------|------|------|
| `ANICCA_AGENT_TOKEN` | Railway API 認証トークン | ✅ |
| `BLOTATO_API_KEY` | X/TikTok 投稿 API | ✅ |
| `X_ACCOUNT_ID` | Blotato X アカウント ID | ✅ |
| `TIKTOK_ACCOUNT_ID` | Blotato TikTok アカウント ID | ✅ |
| `OPENAI_API_KEY` | LLM（GPT-4o-mini） | ✅ |
| `FAL_API_KEY` | 画像生成 | ⬜ |
| `SLACK_WEBHOOK_AGENTS` | Slack 通知 | ⬜ |
| `MOLTBOOK_API_KEY` | Moltbook API | ⬜ |

### 2.3 Secret 管理（追加）

**.env.example:**

```bash
# === REQUIRED ===
ANICCA_AGENT_TOKEN=your-secure-token-here
BLOTATO_API_KEY=your-blotato-key
X_ACCOUNT_ID=your-x-account-id
TIKTOK_ACCOUNT_ID=your-tiktok-account-id
OPENAI_API_KEY=sk-your-openai-key

# === OPTIONAL ===
FAL_API_KEY=your-fal-key
SLACK_WEBHOOK_AGENTS=https://hooks.slack.com/services/xxx
MOLTBOOK_API_KEY=your-moltbook-key
```

**Secret Rotation Policy:**

| Secret | Rotation 頻度 | 手順 |
|--------|--------------|------|
| `ANICCA_AGENT_TOKEN` | 四半期 | 1. Railway + VPS 同時更新 2. Gateway 再起動 |
| `BLOTATO_API_KEY` | 年1回 | Blotato ダッシュボードで regenerate |
| `OPENAI_API_KEY` | 年1回 | OpenAI ダッシュボードで regenerate |
| `SLACK_WEBHOOK_AGENTS` | 不要（漏洩時のみ） | Slack App 設定で新規作成 |

**Security Best Practices:**

1. `.env` は **絶対に git commit しない**（.gitignore に追加済み）
2. VPS では `chmod 600 ~/.openclaw/.env`
3. Docker では `docker secret` を使用（docker-compose.yml 更新済み）
4. 漏洩検知: GitHub Secret Scanning enabled
5. **ログに Secret を出力しない**（console.log 禁止）

---

## 3. Skills 詳細

### 3.1 x-poster Skill

**SKILL.md:**

```markdown
---
name: x-poster
description: Post wisdom content to X/Twitter with Thompson Sampling hook selection and quality verification
version: 1.0.0
user-invocable: true
metadata: {"openclaw":{"emoji":"🐦","requires":{"env":["ANICCA_AGENT_TOKEN","BLOTATO_API_KEY","OPENAI_API_KEY"]},"primaryEnv":"BLOTATO_API_KEY"}}
---

# X Poster Skill

Automatically post wisdom content to X/Twitter.

## Flow
1. Select hook via Thompson Sampling
2. Generate content via Railway API
3. Verify quality (score >= 3/5)
4. Generate image via FAL (optional)
5. Post via Blotato API
6. Save to agent_posts DB
7. Update hook statistics
8. Notify Slack

## Triggers
- Cron: 09:00, 21:00 JST
- Manual: `openclaw skill x-poster`

## Error Handling
- 429: Exponential backoff + Equal Jitter
- 5xx: Retry 3 times, then DLQ
- 4xx: Abort, notify Slack
```

**実装:** 1.6.2-ultimate-spec2.md の main.py, hook_selector.py, verifier.py, error_handler.py をそのまま使用

### 3.2 tiktok-poster Skill

**SKILL.md:**

```markdown
---
name: tiktok-poster
description: Post wisdom images to TikTok (static images only, no video)
version: 1.0.0
user-invocable: true
metadata: {"openclaw":{"emoji":"🎵","requires":{"env":["ANICCA_AGENT_TOKEN","BLOTATO_API_KEY","FAL_API_KEY"]},"primaryEnv":"BLOTATO_API_KEY"}}
---

# TikTok Poster Skill

Post wisdom content as static images to TikTok.

## Constraints
- Images only (no video generation in 1.6.2)
- Image MUST include text overlay
- 1 post per day (20:00 JST)

## Flow
1. Select hook via Thompson Sampling
2. Generate image with text via FAL
3. Verify image quality (score >= 3/5)
4. Post via Blotato API
5. Save to agent_posts DB
6. Notify Slack
```

### 3.3 app-nudge-sender（Railway Cron で継続 - OpenClaw 外）

> **IMPORTANT**: このスキルは OpenClaw に含めない。Railway Cron (`nudge-cronp`) で継続稼働。
> 二重実行（duplicate notifications）を防止するため、OpenClaw には実装しない。

**現行アーキテクチャ（変更なし）:**
```
Railway Cron (nudge-cronp)
    ↓ 毎時 00分
POST /api/cron/nudge
    ↓
Railway API
    ↓
APNs → iOS App
```

**Fatigue Prevention（現行ロジック維持）:**

| パラメータ | 値 |
|-----------|-----|
| daily_limit_per_type | 5 |
| daily_limit_total | 10 |
| cooloff_hours_after_negative | 24 |
| min_hours_between_same_hook | 48 |

### 3.4 suffering-detector Skill

**SKILL.md:**

```markdown
---
name: suffering-detector
description: Detect user suffering and respond appropriately (Moltbook reply, X → App Nudge)
version: 1.0.0
user-invocable: false
disable-model-invocation: false
metadata: {"openclaw":{"emoji":"💜","requires":{"env":["ANICCA_AGENT_TOKEN","MOLTBOOK_API_KEY"]},"primaryEnv":"MOLTBOOK_API_KEY","session":"isolated"}}
---

# Suffering Detector Skill

Detect user suffering across platforms and respond appropriately.

## Session Isolation

**CRITICAL**: This skill runs in an ISOLATED session, not the main session.
- Prevents race conditions with approval flows in main session
- Each heartbeat execution gets its own context
- No state pollution between runs

## Platform Behavior
| Platform | Detection | Response |
|----------|-----------|----------|
| Moltbook | ✅ Keywords + Sentiment | ✅ Reply directly |
| X | ✅ Keywords + Sentiment | ❌ No reply → App Nudge instead |

## Detection Signals
- Keywords: 「つらい」「死にたい」「もう無理」etc.
- Time: 0-5 AM posts
- Pattern: Consecutive posts
- History: Previous negative feedback

## Response Priority
1. HIGH (死にたい, 消えたい): Immediate compassionate response + alert
2. MEDIUM (つらい, しんどい): Compassionate response within 5 min
3. LOW (やる気でない): Regular Nudge queue

## Error Handling
- All failures → DLQ (`~/.openclaw/dlq/suffering-detector.jsonl`)
- Slack alert on HIGH priority detection failure
- Circuit breaker on Moltbook API (3 failures → 1 min cooldown)
```

---

## 4. Railway API 拡張

### 4.1 新規エンドポイント

| Method | Path | 用途 |
|--------|------|------|
| GET | `/api/agent/hooks` | フック一覧取得（Thompson Sampling 用統計付き） |
| POST | `/api/agent/hooks` | 新規フック追加 |
| POST | `/api/agent/hooks/stats` | フック統計更新 |
| GET | `/api/agent/wisdom` | Wisdom 一覧取得 |
| POST | `/api/agent/content` | コンテンツ生成 |
| POST | `/api/agent/posts` | 投稿記録保存 |
| POST | `/api/agent/feedback` | フィードバック記録 |

### 4.2 認証（Timing-Safe + Input Validation）

```javascript
// middleware/agentAuth.js
const crypto = require('crypto');
const { z } = require('zod');

/**
 * Timing-safe token comparison to prevent timing attacks.
 *
 * CRITICAL SECURITY NOTES:
 * 1. Do NOT use `===` or `!==` for token comparison (leaks length via timing)
 * 2. Do NOT check length before timingSafeEqual (leaks length via timing)
 * 3. MUST use HMAC to normalize length before comparison
 */
const verifyAgentToken = (req, res, next) => {
  const authHeader = req.headers.authorization;
  if (!authHeader || !authHeader.startsWith('Bearer ')) {
    return res.status(401).json({ error: 'Missing or malformed Authorization header' });
  }

  const token = authHeader.slice(7); // Remove 'Bearer '
  const expectedToken = process.env.ANICCA_AGENT_TOKEN;

  if (!expectedToken) {
    // Log to monitoring, not console (ANICCA_AGENT_TOKEN missing is critical)
    return res.status(500).json({ error: 'Server configuration error' });
  }

  // Constant-time comparison using HMAC
  // HMAC normalizes both inputs to same length (32 bytes for sha256)
  // This prevents length leakage via timing attacks
  const hmacKey = crypto.randomBytes(32); // Ephemeral key per request
  const tokenHmac = crypto.createHmac('sha256', hmacKey).update(token).digest();
  const expectedHmac = crypto.createHmac('sha256', hmacKey).update(expectedToken).digest();

  // Now both are 32 bytes, safe to use timingSafeEqual
  if (!crypto.timingSafeEqual(tokenHmac, expectedHmac)) {
    return res.status(401).json({ error: 'Unauthorized' });
  }

  next();
};

// Usage
router.use('/api/agent/*', verifyAgentToken);

/**
 * Input validation schemas (Zod)
 */
const PostContentSchema = z.object({
  topic: z.string().min(1).max(500),
  problemType: z.enum([
    'staying_up_late', 'cant_wake_up', 'self_loathing', 'rumination',
    'procrastination', 'anxiety', 'lying', 'bad_mouthing', 'porn_addiction',
    'alcohol_dependency', 'anger', 'obsessive', 'loneliness'
  ]),
  tone: z.enum(['gentle', 'firm', 'playful']).default('gentle'),
  language: z.enum(['ja', 'en']).default('ja'),
  feedback: z.string().max(1000).optional(),
});

const PostRecordSchema = z.object({
  platform: z.enum(['x', 'tiktok', 'moltbook']),
  content: z.string().min(1).max(5000),
  hook: z.string().min(1).max(500),
  hookId: z.string().uuid().optional(),
  externalPostId: z.string().max(100),
  reasoning: z.string().max(2000).optional(),
  imageUrl: z.string().url().optional(), // DB スキーマと整合
});

const HookStatsSchema = z.object({
  hookId: z.string().uuid(),
  outcome: z.enum(['success', 'failure', 'neutral', 'posted']),
  timestamp: z.string().datetime().optional(),
  version: z.number().int().min(0), // REQUIRED: Optimistic locking (P2025 if stale)
});

const FeedbackSchema = z.object({
  userId: z.string().uuid(),
  postId: z.string().uuid().optional(),
  platform: z.enum(['x', 'tiktok', 'moltbook', 'nudge']),
  feedbackType: z.enum(['positive', 'negative', 'neutral']),
  comment: z.string().max(1000).optional(),
});

// Validation middleware
const validate = (schema) => (req, res, next) => {
  try {
    req.body = schema.parse(req.body);
    next();
  } catch (error) {
    return res.status(400).json({
      error: 'Validation failed',
      details: error.errors
    });
  }
};

// Usage
router.post('/api/agent/content', validate(PostContentSchema), contentHandler);
router.post('/api/agent/posts', validate(PostRecordSchema), postHandler);
router.post('/api/agent/hooks/stats', validate(HookStatsSchema), statsHandler);
router.post('/api/agent/feedback', validate(FeedbackSchema), feedbackHandler);
```

### 4.3 データベーススキーマ

```sql
-- Prisma migration: 20260205_agent_tables

-- Hook統計（Thompson Sampling用）
CREATE TABLE hook_statistics (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  hook_id UUID NOT NULL REFERENCES hooks(id) ON DELETE CASCADE,
  platform VARCHAR(20) NOT NULL CHECK (platform IN ('x', 'tiktok', 'moltbook', 'nudge')),
  successes INTEGER NOT NULL DEFAULT 0 CHECK (successes >= 0),
  failures INTEGER NOT NULL DEFAULT 0 CHECK (failures >= 0),
  version INTEGER NOT NULL DEFAULT 0, -- Optimistic locking（必須）
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  UNIQUE(hook_id, platform)
);

-- Agent投稿記録
CREATE TABLE agent_posts (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  platform VARCHAR(20) NOT NULL CHECK (platform IN ('x', 'tiktok', 'moltbook')),
  external_post_id VARCHAR(100) NOT NULL,
  hook_id UUID REFERENCES hooks(id),
  content TEXT NOT NULL,
  reasoning TEXT,
  image_url TEXT,
  engagement_score INTEGER DEFAULT 0,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  UNIQUE(platform, external_post_id)
);

-- DLQエントリ（永続化用、通常はファイルベース）
CREATE TABLE dlq_entries (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  skill VARCHAR(50) NOT NULL,
  payload JSONB NOT NULL,
  error_message TEXT NOT NULL,
  retry_count INTEGER NOT NULL DEFAULT 0,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  resolved_at TIMESTAMPTZ
);

-- Index for Thompson Sampling queries
CREATE INDEX idx_hook_statistics_platform ON hook_statistics(platform);
CREATE INDEX idx_agent_posts_platform_created ON agent_posts(platform, created_at DESC);
CREATE INDEX idx_dlq_entries_skill_resolved ON dlq_entries(skill, resolved_at) WHERE resolved_at IS NULL;
```

**Prisma Schema（抜粋）:**

```prisma
model HookStatistics {
  id        String   @id @default(uuid())
  hookId    String   @map("hook_id")
  platform  String
  successes Int      @default(0)
  failures  Int      @default(0)
  version   Int      @default(0) // REQUIRED for optimistic locking
  createdAt DateTime @default(now()) @map("created_at")
  updatedAt DateTime @updatedAt @map("updated_at")

  hook Hook @relation(fields: [hookId], references: [id], onDelete: Cascade)

  @@unique([hookId, platform])
  @@map("hook_statistics")
}

model AgentPost {
  id             String   @id @default(uuid())
  platform       String
  externalPostId String   @map("external_post_id")
  hookId         String?  @map("hook_id")
  content        String
  reasoning      String?
  imageUrl       String?  @map("image_url")
  engagementScore Int     @default(0) @map("engagement_score")
  createdAt      DateTime @default(now()) @map("created_at")

  hook Hook? @relation(fields: [hookId], references: [id])

  @@unique([platform, externalPostId])
  @@map("agent_posts")
}
```

### 4.4 Thompson Sampling アルゴリズム

```python
# skills/hook-selector/thompson_sampling.py
import numpy as np
from dataclasses import dataclass
from typing import List, Optional

@dataclass
class HookStats:
    hook_id: str
    hook_text: str
    successes: int  # Alpha - 1 (engagement/conversion)
    failures: int   # Beta - 1 (no engagement)
    version: int    # Optimistic lock

def select_hook_thompson(hooks: List[HookStats], seed: Optional[int] = None) -> HookStats:
    """
    Thompson Sampling for hook selection.

    Algorithm:
    1. For each hook, sample from Beta(α, β) where:
       - α = successes + 1 (prior = 1)
       - β = failures + 1 (prior = 1)
    2. Select the hook with the highest sampled value

    Why Beta distribution:
    - Conjugate prior for Bernoulli likelihood
    - Models uncertainty in success probability
    - Naturally balances exploration (new hooks) vs exploitation (proven hooks)

    Pseudocode:
    ```
    for each hook h in hooks:
        α_h = h.successes + 1
        β_h = h.failures + 1
        θ_h ~ Beta(α_h, β_h)  # Sample success probability
    return argmax(θ)
    ```

    Args:
        hooks: List of HookStats with success/failure counts
        seed: Optional random seed for reproducibility in tests

    Returns:
        Selected HookStats object
    """
    if not hooks:
        raise ValueError("hooks list cannot be empty")

    if seed is not None:
        np.random.seed(seed)

    samples = []
    for hook in hooks:
        # Beta distribution parameters (add 1 for uniform prior)
        alpha = hook.successes + 1
        beta = hook.failures + 1

        # Sample from Beta distribution
        sample = np.random.beta(alpha, beta)
        samples.append((sample, hook))

    # Select hook with highest sampled value
    _, selected = max(samples, key=lambda x: x[0])
    return selected

def update_hook_stats(
    hook_id: str,
    outcome: str,  # 'success' | 'failure' | 'neutral'
    current_version: int,
    db_client
) -> bool:
    """
    Update hook statistics with optimistic locking.

    Returns:
        True if update succeeded, False if version conflict (retry needed)
    """
    increment_field = None
    if outcome == 'success':
        increment_field = 'successes'
    elif outcome == 'failure':
        increment_field = 'failures'
    # 'neutral' and 'posted' don't update stats

    if increment_field is None:
        return True

    try:
        result = db_client.hook_statistics.update_many(
            where={
                'hookId': hook_id,
                'version': current_version  # Optimistic lock check
            },
            data={
                increment_field: {'increment': 1},
                'version': {'increment': 1}
            }
        )
        return result.count > 0  # False if version mismatch
    except Exception as e:
        raise RuntimeError(f"Failed to update hook stats: {e}")
```

**Quality Scoring Algorithm (Verifier):**

```python
# skills/content-verifier/scoring.py
from dataclasses import dataclass
from typing import List
import re

@dataclass
class QualityScore:
    total: float  # 0-5 scale
    breakdown: dict
    passed: bool  # total >= 3.0

def score_content(content: str, platform: str) -> QualityScore:
    """
    Score content quality on 0-5 scale.

    Scoring criteria (each 0-1, summed to 5):
    1. Length appropriateness (platform-specific)
    2. Tone alignment (gentle/compassionate)
    3. No forbidden words (spam, aggressive)
    4. Call-to-action presence (soft, not salesy)
    5. Originality (not duplicate of recent posts)

    Args:
        content: The text content to score
        platform: 'x', 'tiktok', or 'moltbook'

    Returns:
        QualityScore with total, breakdown, and passed flag
    """
    scores = {}

    # 1. Length check
    char_count = len(content)
    length_ranges = {
        'x': (100, 280),
        'tiktok': (50, 150),
        'moltbook': (100, 500)
    }
    min_len, max_len = length_ranges.get(platform, (50, 300))
    if min_len <= char_count <= max_len:
        scores['length'] = 1.0
    elif char_count < min_len:
        scores['length'] = char_count / min_len
    else:
        scores['length'] = max(0, 1 - (char_count - max_len) / max_len)

    # 2. Tone check (gentle keywords)
    gentle_words = ['やさしく', '大丈夫', '一緒に', 'ゆっくり', '少しずつ']
    tone_score = min(1.0, sum(1 for w in gentle_words if w in content) / 2)
    scores['tone'] = tone_score

    # 3. Forbidden words check
    forbidden = ['今すぐ', '必ず', '絶対', '限定', '無料']
    forbidden_count = sum(1 for w in forbidden if w in content)
    scores['forbidden'] = max(0, 1 - forbidden_count * 0.5)

    # 4. Soft CTA check
    soft_cta = ['考えてみて', 'どうかな', '試してみない？', 'かもしれない']
    cta_present = any(c in content for c in soft_cta)
    scores['cta'] = 1.0 if cta_present else 0.5

    # 5. Originality (placeholder - would check against recent posts DB)
    scores['originality'] = 1.0  # TODO: implement duplicate check

    total = sum(scores.values())
    return QualityScore(
        total=total,
        breakdown=scores,
        passed=total >= 3.0
    )
```

### 4.5 Circuit Breaker パターン

```javascript
// utils/circuitBreaker.js
class CircuitBreaker {
  constructor(options = {}) {
    this.failureThreshold = options.failureThreshold || 5;
    this.resetTimeoutMs = options.resetTimeoutMs || 60000; // 1 minute
    this.state = 'CLOSED'; // CLOSED | OPEN | HALF_OPEN
    this.failures = 0;
    this.lastFailureTime = null;
    this.name = options.name || 'unknown';
  }

  async execute(fn) {
    if (this.state === 'OPEN') {
      if (Date.now() - this.lastFailureTime >= this.resetTimeoutMs) {
        this.state = 'HALF_OPEN';
      } else {
        throw new Error(`Circuit breaker ${this.name} is OPEN`);
      }
    }

    try {
      const result = await fn();
      this.onSuccess();
      return result;
    } catch (error) {
      this.onFailure();
      throw error;
    }
  }

  onSuccess() {
    this.failures = 0;
    this.state = 'CLOSED';
  }

  onFailure() {
    this.failures++;
    this.lastFailureTime = Date.now();
    if (this.failures >= this.failureThreshold) {
      this.state = 'OPEN';
      console.warn(`Circuit breaker ${this.name} opened after ${this.failures} failures`);
    }
  }
}

// Usage in skills - ALL external APIs MUST have circuit breakers
const blotatoBreaker = new CircuitBreaker({ name: 'blotato', failureThreshold: 3 });
const falBreaker = new CircuitBreaker({ name: 'fal', failureThreshold: 3 });
const railwayBreaker = new CircuitBreaker({ name: 'railway', failureThreshold: 5 });
const openaiBreaker = new CircuitBreaker({ name: 'openai', failureThreshold: 5, resetTimeoutMs: 120000 });
const slackBreaker = new CircuitBreaker({ name: 'slack', failureThreshold: 10, resetTimeoutMs: 300000 }); // Higher threshold - non-critical
const moltbookBreaker = new CircuitBreaker({ name: 'moltbook', failureThreshold: 3 });
```

### 4.6 DLQ (Dead Letter Queue) 設定

```javascript
// utils/dlq.js
const fs = require('fs').promises;
const path = require('path');

const DLQ_DIR = process.env.DLQ_DIR || path.join(process.env.HOME, '.openclaw/dlq');

async function writeToDLQ(skill, payload, error) {
  const entry = {
    timestamp: new Date().toISOString(),
    skill,
    payload,
    error: error.message,
    stack: error.stack,
    retryCount: 0
  };

  const filePath = path.join(DLQ_DIR, `${skill}.jsonl`);
  await fs.appendFile(filePath, JSON.stringify(entry) + '\n');

  // Alert via Slack
  if (process.env.SLACK_WEBHOOK_AGENTS) {
    await fetch(process.env.SLACK_WEBHOOK_AGENTS, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        text: `⚠️ DLQ Entry: ${skill}\nError: ${error.message}`
      })
    });
  }
}

// Each skill MUST have DLQ handling
const SKILL_DLQ_CONFIG = {
  'x-poster': { maxRetries: 3, retryDelayMs: 60000 },
  'tiktok-poster': { maxRetries: 3, retryDelayMs: 60000 },
  'suffering-detector': { maxRetries: 2, retryDelayMs: 30000 }
};
```

---

## 5. VPS セットアップ

### 5.1 Hetzner VPS スペック

| 項目 | 値 |
|------|-----|
| プラン | CPX11 (2 vCPU, 2GB RAM, 40GB SSD) |
| リージョン | Ashburn (ash) |
| OS | Ubuntu 24.04 LTS |
| コスト | ~$5/月 |

### 5.2 初期セットアップスクリプト

```bash
#!/bin/bash
# /home/anicca/scripts/setup.sh

set -euo pipefail

echo "=== Anicca VPS Setup ==="

# 1. Update system
apt-get update && apt-get upgrade -y

# 2. Install dependencies
apt-get install -y \
  curl \
  git \
  docker.io \
  docker-compose \
  ufw \
  fail2ban \
  unattended-upgrades

# 3. Security setup
ufw default deny incoming
ufw default allow outgoing
ufw allow 22/tcp
ufw --force enable
systemctl enable fail2ban
systemctl start fail2ban

# 4. SSH hardening
sed -i 's/#PasswordAuthentication yes/PasswordAuthentication no/' /etc/ssh/sshd_config
sed -i 's/#PermitRootLogin prohibit-password/PermitRootLogin no/' /etc/ssh/sshd_config
systemctl restart sshd

# 5. Install Tailscale
curl -fsSL https://tailscale.com/install.sh | sh
tailscale up

# 6. Install Node.js (for OpenClaw)
curl -fsSL https://deb.nodesource.com/setup_20.x | bash -
apt-get install -y nodejs

# 7. Install OpenClaw
npm install -g openclaw@latest

# 8. Create anicca user
useradd -m -s /bin/bash anicca
usermod -aG docker anicca

# 9. Setup OpenClaw
su - anicca << 'EOF'
openclaw onboard --install-daemon
mkdir -p ~/.openclaw/workspaces/anicca/skills
EOF

echo "=== Setup complete ==="
echo "Next: Configure ~/.openclaw/openclaw.json and skills"
```

### 5.3 Docker Compose

```yaml
# /home/anicca/docker-compose.yml
version: '3.8'

services:
  openclaw:
    image: openclaw/openclaw:latest
    container_name: anicca-openclaw
    restart: unless-stopped
    # SECURITY: Run as non-root user
    user: "1000:1000"  # anicca user UID:GID
    ports:
      - "127.0.0.1:18789:18789"
    volumes:
      - /home/anicca/.openclaw:/home/node/.openclaw
      - /home/anicca/workspaces/anicca:/home/node/.openclaw/workspaces/anicca
    environment:
      - ANICCA_AGENT_TOKEN=${ANICCA_AGENT_TOKEN}
      - BLOTATO_API_KEY=${BLOTATO_API_KEY}
      - X_ACCOUNT_ID=${X_ACCOUNT_ID}
      - TIKTOK_ACCOUNT_ID=${TIKTOK_ACCOUNT_ID}
      - OPENAI_API_KEY=${OPENAI_API_KEY}
      - FAL_API_KEY=${FAL_API_KEY}
      - SLACK_WEBHOOK_AGENTS=${SLACK_WEBHOOK_AGENTS}
      - MOLTBOOK_API_KEY=${MOLTBOOK_API_KEY}
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:18789/health"]
      interval: 30s
      timeout: 10s
      retries: 3
    # SECURITY: Drop all capabilities, add only what's needed
    cap_drop:
      - ALL
    # SECURITY: Read-only root filesystem where possible
    read_only: true
    tmpfs:
      - /tmp
    # SECURITY: No new privileges
    security_opt:
      - no-new-privileges:true
```

**Security Notes:**
- `user: "1000:1000"`: anicca ユーザーで実行（root禁止）
- `cap_drop: ALL`: 全 Linux capabilities を削除
- `read_only: true`: ルートファイルシステムを読み取り専用に
- `no-new-privileges`: 権限昇格を防止

---

## 6. 実装チェックリスト

### Phase 1: インフラ（Day 1）

| # | タスク | AC | 状態 |
|---|--------|-----|------|
| 1.1 | Hetzner VPS 作成 | SSH 接続成功 | ⬜ |
| 1.2 | セキュリティ設定 | UFW + fail2ban 動作 | ⬜ |
| 1.3 | Tailscale 設定 | `tailscale status` 接続確認 | ⬜ |
| 1.4 | OpenClaw インストール | `openclaw --version` 表示 | ⬜ |
| 1.5 | Docker 設定 | `docker-compose up` 成功 | ⬜ |

### Phase 2: Gateway 設定（Day 1）

| # | タスク | AC | 状態 |
|---|--------|-----|------|
| 2.1 | openclaw.json 作成 | 設定ファイル完成 | ⬜ |
| 2.2 | 環境変数設定 | `.env` ファイル作成 | ⬜ |
| 2.3 | Gateway 起動 | `openclaw gateway` 動作 | ⬜ |
| 2.4 | 認証確認 | Token 認証成功 | ⬜ |

### Phase 3: x-poster Skill（Day 1-2）

| # | タスク | AC | 状態 |
|---|--------|-----|------|
| 3.1 | SKILL.md 作成 | ファイル完成 | ⬜ |
| 3.2 | main.py 実装 | 手動実行で投稿成功 | ⬜ |
| 3.3 | hook_selector.py | ユニットテスト通過 | ⬜ |
| 3.4 | verifier.py | テキスト検証動作 | ⬜ |
| 3.5 | error_handler.py | DLQ 書き込み確認 | ⬜ |
| 3.6 | Cron 動作確認 | 09:00 JST に自動実行 | ⬜ |

### Phase 4: tiktok-poster Skill（Day 2）

| # | タスク | AC | 状態 |
|---|--------|-----|------|
| 4.1 | SKILL.md 作成 | ファイル完成 | ⬜ |
| 4.2 | main.py 実装 | 手動実行で投稿成功 | ⬜ |
| 4.3 | Cron 動作確認 | 20:00 JST に自動実行 | ⬜ |

### Phase 5: suffering-detector Skill（Day 2-3）

| # | タスク | AC | 状態 |
|---|--------|-----|------|
| 5.1 | SKILL.md 作成 | ファイル完成 | ⬜ |
| 5.2 | detector.py 実装 | キーワード検出動作 | ⬜ |
| 5.3 | error_handler.py 実装 | DLQ 書き込み確認 | ⬜ |
| 5.4 | Moltbook 連携 | 返信投稿成功 | ⬜ |
| 5.5 | Heartbeat 動作確認 | 5分ごと（isolated session） | ⬜ |

### Phase 6: Railway API 拡張（Day 2-3）

| # | タスク | AC | 状態 |
|---|--------|-----|------|
| 6.1 | agent 認証ミドルウェア | Token 検証動作（HMAC方式） | ⬜ |
| 6.2 | DB マイグレーション | hook_statistics, agent_posts 作成 | ⬜ |
| 6.3 | GET /api/agent/hooks | フック一覧取得（統計付き） | ⬜ |
| 6.4 | POST /api/agent/posts | 投稿記録保存 | ⬜ |
| 6.5 | POST /api/agent/content | コンテンツ生成 | ⬜ |
| 6.6 | POST /api/agent/hooks/stats | 統計更新（楽観的ロック） | ⬜ |

### Phase 7: Slack 統合（Day 3）

| # | タスク | AC | 状態 |
|---|--------|-----|------|
| 7.1 | steipete/slack インストール | `clawhub list` で表示 | ⬜ |
| 7.2 | 通知動作確認 | 投稿完了通知が届く | ⬜ |
| 7.3 | エラー通知確認 | 失敗時に通知が届く | ⬜ |
| 7.4 | DLQ アラート確認 | DLQ 追加時に通知が届く | ⬜ |

### Phase 8: E2E テスト（Day 3）

| # | タスク | AC | 状態 |
|---|--------|-----|------|
| 8.1 | x-poster E2E | 手動実行 → X 投稿成功 | ⬜ |
| 8.2 | tiktok-poster E2E | 手動実行 → TikTok 投稿成功 | ⬜ |
| 8.3 | suffering-detector E2E | Moltbook 投稿 → 返信届く | ⬜ |
| 8.4 | Circuit Breaker 確認 | 連続失敗 → OPEN 状態確認 | ⬜ |
| 8.5 | DLQ 確認 | 失敗 → DLQ ファイル追記確認 | ⬜ |
| 8.6 | 24時間稼働確認 | VPS 再起動後も自動復旧 | ⬜ |

> **NOTE**: app-nudge-sender は Railway Cron で継続稼働のため、OpenClaw E2E テスト対象外

---

## 7. 成功メトリクス

| メトリクス | ベースライン | 目標 | 測定方法 |
|-----------|-------------|------|---------|
| **X 投稿品質** | N/A | >= 3/5 全投稿 | verifier.py |
| **X フォロワー** | 0 | 100（1ヶ月後） | X API |
| **TikTok フォロワー** | 0 | 100（1ヶ月後） | TikTok API |
| **App Nudge 開封率** | 10% | 15% | Firebase Analytics |
| **システム稼働率** | N/A | 99.5% | Health check |
| **DLQ エントリ数** | N/A | < 5/週 | DLQ 監視 |

---

## 8. 将来拡張（1.7.0+）

| 機能 | Phase | 説明 |
|------|-------|------|
| **trend-hunter Skill** | 1.7.0 | トレンドトピック収集（4時間ごと） |
| **feedback-fetch Skill** | 1.7.0 | エンゲージメント指標取得（4時間ごと） |
| **app-nudge-sender 移行** | 1.7.0+ | Railway Cron → OpenClaw（スケーリング検証後） |
| Gmail 自動返信 | 1.7.0 | ルーティンメール自動返信 |
| Calendar 管理 | 1.7.0 | 予定の自動作成・調整 |
| TikTok 広告運用 | 1.7.0 | 自動入札・クリエイティブ最適化 |
| ASA 運用 | 1.7.0 | キーワード・入札自動最適化 |
| 動画生成 | 1.8.0 | Remotion / Sora での動画作成 |
| 自己進化 | 2.0.0 | コード自動改善 |
| 寄付メカニズム | 2.0.0 | 収益の自動寄付 |

---

## 更新履歴

| 日付 | 内容 |
|------|------|
| 2026-02-05 | 初版作成（OpenClaw Research + 1.6.2 Spec 統合） |
| 2026-02-05 | Round 2: Secret管理、Zod検証、楽観的ロック追加 |
| 2026-02-06 | Round 3: 全 CRITICAL issues 修正（13項目） |

---

**END OF SPECIFICATION**
