# TikTok Agent ロバスト化 & リリース仕様

## 概要

TikTok Agent（`scripts/anicca-agent/`）のコード監査で発見された10件の問題を修正し、毎日確実にTikTok投稿が行われるようにする。修正後、ローカルフルフローテスト → dev検証 → mainマージ → 1.5.0リリース。

## 現在の実装状況（2026-01-28）

| Track | 内容 | 状態 |
|-------|------|------|
| Track A | Cross-User Learning バックエンド | ✅ dev マージ済み |
| Track B | TikTok Agent 基本実装 | ✅ dev マージ済み |
| Track C | Learning Loop（Wisdom + Thompson Sampling） | ✅ dev マージ済み、Staging検証済み |
| Agent ロバスト化 | 本スペック | ❌ 未実装 |

### Staging検証済み項目

- Thompson Sampling: 3回呼び出し、exploit/explore両方確認済み
- refresh-tiktok-stats + wisdom extraction: 正常動作確認済み
- 全28ユニットテスト PASS
- Staging URL: `https://anicca-proxy-staging.up.railway.app`

---

## 問題一覧（コード監査結果）

### CRITICAL（4件）

#### C-1: save_post_record が呼ばれない可能性がある

| 項目 | 内容 |
|------|------|
| ファイル | `anicca_tiktok_agent.py:86-89` |
| 問題 | Agent が `finish_reason == "stop"` で終了した場合、save_post_record を呼ばずに終了する。System Prompt で「ALWAYS call save_post_record」と書いてあるが、コードレベルの強制がない |
| 影響 | 投稿しても記録が残らない → 翌日の学習が機能しない → Learning Loop 崩壊 |

**修正方針**: Agent ループ終了後にポスト追跡変数をチェックし、save_post_record が呼ばれていなければ強制呼び出し。

**修正コード** (`anicca_tiktok_agent.py`):

```python
# ループ前に追跡変数を定義
post_record_saved = False
last_blotato_post_id = None
last_caption = None
last_hook_candidate_id = None

# ループ内: tool_call 実行時に追跡
for tool_call in message.tool_calls:
    fn_name = tool_call.function.name
    fn_args = json.loads(tool_call.function.arguments)
    # ... 既存の実行コード ...

    # 追跡
    if fn_name == "save_post_record":
        post_record_saved = True
    elif fn_name == "post_to_tiktok":
        result_data = json.loads(result)
        if result_data.get("success"):
            last_blotato_post_id = result_data.get("blotato_post_id")
            last_caption = fn_args.get("caption", "")

# ループ後: save_post_record が呼ばれていなければ強制呼び出し
if not post_record_saved and last_blotato_post_id:
    print("⚠️ [Anicca Agent] save_post_record was not called. Forcing save...")
    try:
        forced_result = save_post_record(
            blotato_post_id=last_blotato_post_id,
            caption=last_caption or "auto-saved",
            hook_candidate_id=last_hook_candidate_id or "",
            agent_reasoning="[FORCED] Agent did not call save_post_record",
        )
        print(f"  → Forced save result: {forced_result}")
    except Exception as e:
        print(f"  ❌ Forced save failed: {e}")
```

#### C-2: Thompson Sampling strategy パラメータが tool 定義に欠如

| 項目 | 内容 |
|------|------|
| ファイル | `tools.py:42-52` |
| 問題 | `get_hook_candidates` のパラメータに `strategy` がない。API側には `?strategy=thompson` が実装済みだが、Agent が呼べない |
| 影響 | Agent は常にデフォルトのリストモードで取得 → Thompson Sampling が使われない |

**修正コード** (`tools.py` - TOOL_DEFINITIONS の get_hook_candidates):

```python
"parameters": {
    "type": "object",
    "properties": {
        "strategy": {
            "type": "string",
            "enum": ["list", "thompson"],
            "default": "thompson",
            "description": "Selection strategy. 'thompson' returns a single hook selected by Thompson Sampling (recommended). 'list' returns multiple hooks sorted by metric."
        },
        "limit": {"type": "integer", "default": 20, "description": "Number of hooks to return (only used with 'list' strategy)"},
        "sort_by": {
            "type": "string",
            "enum": ["app_tap_rate", "tiktok_like_rate", "exploration_weight"],
            "default": "app_tap_rate",
        },
    },
    "required": [],
},
```

**修正コード** (`tools.py` - get_hook_candidates 実装):

```python
def get_hook_candidates(**kwargs):
    strategy = kwargs.get("strategy", "thompson")
    limit = kwargs.get("limit", 20)
    sort_by = kwargs.get("sort_by", "app_tap_rate")
    try:
        result = api.get_hook_candidates(limit=limit, sort_by=sort_by, strategy=strategy)
        return json.dumps(result)
    except Exception as e:
        return json.dumps({"error": str(e), "candidates": []})
```

**修正コード** (`api_client.py` - get_hook_candidates):

```python
def get_hook_candidates(self, limit=20, sort_by="app_tap_rate", strategy=None):
    params = {"limit": limit, "sort_by": sort_by}
    if strategy:
        params["strategy"] = strategy
    return self._get("/hook-candidates", params=params)
```

#### C-3: 空の blotato_post_id が検証されていない

| 項目 | 内容 |
|------|------|
| ファイル | `tools.py:320, 323-330` |
| 問題 | `post_to_tiktok` が失敗すると `blotato_post_id: ""` を返す。この空文字列がそのまま `save_post_record` に渡されDB保存される |
| 影響 | 空IDのレコードが作られ、メトリクス取得 (`fetch_metrics.py`) がエラーになる |

**修正コード** (`tools.py` - save_post_record):

```python
def save_post_record(**kwargs):
    blotato_post_id = kwargs["blotato_post_id"]
    if not blotato_post_id or blotato_post_id.strip() == "":
        return json.dumps({"error": "blotato_post_id is empty. Post may have failed.", "saved": False})
    try:
        result = api.save_post_record(
            blotato_post_id=blotato_post_id,
            caption=kwargs["caption"],
            hook_candidate_id=kwargs.get("hook_candidate_id"),
            agent_reasoning=kwargs.get("agent_reasoning"),
        )
        return json.dumps(result)
    except Exception as e:
        return json.dumps({"error": str(e), "saved": False})
```

#### C-4: 空の image_url が後続ツールに伝搬する

| 項目 | 内容 |
|------|------|
| ファイル | `tools.py:237-244` |
| 問題 | `generate_image` が失敗すると `image_url: ""` を返す。Agent がこれをそのまま `evaluate_image` → `post_to_tiktok` に渡す |
| 影響 | Blotato API に空URLを送信 → 投稿失敗 → 無駄なAPI呼び出し |

**修正コード** (`tools.py` - generate_image の戻り値):

```python
# 既存の空URL返却箇所を全て修正:
# 空の場合はerrorフラグを明確にする

# Line 221
url = images[0].get("url", "") if images else ""
if not url:
    return json.dumps({"error": "No image URL returned", "image_url": ""})
return json.dumps({"image_url": url})

# Line 237-238
url = images[0].get("url", "") if images else ""
if not url:
    return json.dumps({"error": "No image URL in result", "image_url": ""})
return json.dumps({"image_url": url})
```

**修正コード** (`tools.py` - evaluate_image):

```python
def evaluate_image(**kwargs):
    image_url = kwargs["image_url"]
    if not image_url or image_url.strip() == "":
        return json.dumps({"quality_score": 0, "issues": ["No image URL provided"], "recommendation": "regenerate"})
    # ... 既存コード ...
```

---

### HIGH（2件）

#### H-1: 3つのツールに try/except がない

| 項目 | 内容 |
|------|------|
| ファイル | `tools.py:146-155 (get_yesterday_performance, get_hook_candidates, save_post_record)` |
| 問題 | API呼び出しが例外を投げるとAgent全体がクラッシュ（`anicca_tiktok_agent.py:102-105` のtry/exceptでキャッチされるが、エラーメッセージが不親切） |
| 影響 | Agent上位のcatchで処理されるため即死はしないが、ツール固有のフォールバック値が返せない |

**修正**: 各ツールにtry/exceptを追加し、構造化されたエラーJSONを返す。

```python
def get_yesterday_performance(**kwargs):
    try:
        result = api.get_recent_posts(days=1)
        return json.dumps(result)
    except Exception as e:
        return json.dumps({"error": str(e), "posts": []})
```

（get_hook_candidates, save_post_record も同様 — C-2, C-3 の修正に含まれる）

#### H-2: evaluate_image のリトライがコード実装されていない

| 項目 | 内容 |
|------|------|
| ファイル | `anicca_tiktok_agent.py:37`, `tools.py:247-282` |
| 問題 | System Prompt に「If score < 6, regenerate (max 2 retries)」と書いてあるが、コードレベルのリトライロジックがない。Agent の判断に完全依存 |
| 影響 | Agent が低品質画像をそのまま投稿する可能性がある |

**修正方針**: Agent の判断に任せる（OpenAI function callingの設計原則に従う）。ただし System Prompt をより明確にし、evaluate_image の戻り値にリトライカウントのヒントを含める。

**修正コード** (`tools.py` - evaluate_image の JSON パースエラー時):

```python
except (json.JSONDecodeError, IndexError):
    # score=5, recommendation="post" は矛盾 → "regenerate" に修正
    return json.dumps({"quality_score": 5, "issues": ["Failed to parse evaluation"], "recommendation": "regenerate"})
```

---

### MEDIUM（4件）

#### M-1: evaluate_image のデフォルト score=5 と recommendation="post" が矛盾

| 項目 | 内容 |
|------|------|
| ファイル | `tools.py:282` |
| 問題 | JSONパース失敗時に `score=5, recommendation="post"` を返す。threshold=6 なのに score=5 で "post" は矛盾 |

**修正**: H-2 に含まれる（`recommendation: "regenerate"` に変更）

#### M-2: search_trends がオプション（mandatory にすべき）

| 項目 | 内容 |
|------|------|
| ファイル | `anicca_tiktok_agent.py:32` |
| 問題 | System Prompt に「Optionally call search_trends」と書いてある。ユーザーの要望で mandatory にする |

**修正**: System Prompt の Step 3 を修正

```
変更前: "3. Optionally call search_trends for current content inspiration"
変更後: "3. Call search_trends to research current trends (MANDATORY - always do this)"
```

#### M-3: agent_reasoning が save_post_record でオプション

| 項目 | 内容 |
|------|------|
| ファイル | `tools.py:136` |
| 問題 | `agent_reasoning` が required に入っていない。学習ループに重要なデータ |

**修正**: required に追加

```python
"required": ["blotato_post_id", "caption", "agent_reasoning"],
```

#### M-4: System Prompt が構造化されていない

| 項目 | 内容 |
|------|------|
| ファイル | `anicca_tiktok_agent.py:24-54` |
| 問題 | 自由度が高すぎ、毎日のワークフローが安定しない。NVIDIA Agent Framework Level 2（構造化ワークフロー）のベストプラクティスに従い、出力フォーマットを強制すべき |

**修正**: System Prompt 全体を構造化ワークフロー形式に書き換え。

```python
SYSTEM_PROMPT = """You are Anicca's TikTok content agent. You create ONE TikTok post per day.

## MANDATORY WORKFLOW (follow this exact order)

### STEP 1: Review Yesterday
Call get_yesterday_performance.
- If posts exist: note what worked/didn't (like_rate, share_rate)
- If empty (Day 1): proceed to Step 2

### STEP 2: Get Hook Candidates
Call get_hook_candidates with strategy="thompson".
- The API uses Thompson Sampling: 80% exploit (top performers) / 20% explore (new hooks)
- Use the returned hook as your primary content

### STEP 3: Research Trends (MANDATORY)
Call search_trends with a query related to the selected hook's theme.
- Query examples: "self-improvement TikTok 2025", "habit change viral content"
- Use trend insights to enhance your caption and image prompt

### STEP 4: Generate Image
Call generate_image with a detailed prompt.
- Format: 9:16 portrait (TikTok standard)
- Must include readable text overlay with the hook
- Style: emotional, relatable, clean design

### STEP 5: Evaluate Image Quality
Call evaluate_image with the generated image URL and hook text.
- If score < 6 or recommendation is "regenerate": go back to Step 4 (max 2 retries total)
- If score >= 6: proceed to Step 6
- After 2 failed retries: post the best image anyway

### STEP 6: Post to TikTok
Call post_to_tiktok with the image URL and caption.
- Caption: hook text + brief context + hashtags
- Hashtags: #anicca #習慣化 #自己改善 #マインドフルネス #仏教 #行動変容
- Max caption length: 2200 chars

### STEP 7: Save Record (MANDATORY - NEVER SKIP)
Call save_post_record with ALL fields:
- blotato_post_id: from Step 6 result
- caption: the posted caption
- hook_candidate_id: from Step 2 result (the selected hook's id)
- agent_reasoning: 2-3 sentences explaining why you chose this hook and approach

## Target Persona
25-35 years old, struggled with habits for 6-7 years, tried 10+ habit apps and failed.
They feel "I'm a broken person." They're in give-up mode but secretly want to change.

## Content Rules
- Hook must punch in 1-2 seconds (TikTok scroll speed)
- Default language: Japanese (日本語)
- 4 tones: strict, gentle, philosophical, provocative
- If no good hooks exist, create an original one based on the persona

## CRITICAL RULES
- NEVER end without calling save_post_record
- If posting fails, STILL call save_post_record with the error details
- ALWAYS include agent_reasoning
"""
```

---

## 環境情報

| 項目 | 値 |
|------|-----|
| Staging URL | `https://anicca-proxy-staging.up.railway.app` |
| Staging API Token | `49cfa330fa7cb5c8ef1d91df159b45261a0a56d0866844262efa8bea55eb015d` |
| Staging DB | `postgresql://postgres:WgyHhBwqrEVFsXiQNOPrLaNhEayQrVdJ@ballast.proxy.rlwy.net:51992/railway` |
| GitHub Repo | `Daisuke134/anicca.ai` |
| TIKTOK_ACCOUNT_ID | `28152` (@anicca.self) |
| GitHub Secrets（7件設定済み） | OPENAI_API_KEY, BLOTATO_API_KEY, FAL_API_KEY, EXA_API_KEY, API_BASE_URL, API_AUTH_TOKEN, APIFY_API_TOKEN |
| GHA Workflow 場所 | `.github/workflows/anicca-daily-post.yml`（dev のみ、main には未反映） |

---

## 補足事項（ギャップ分析で判明）

### G-1: hook_candidate_id 追跡の詳細

Thompson Sampling モード（`strategy=thompson`）では API が `{ selected: { id: "xxx", ... } }` を返す。
Agent ループ内で `get_hook_candidates` の結果からIDを抽出し、`last_hook_candidate_id` 変数に格納する。

```python
# anicca_tiktok_agent.py ループ内
if fn_name == "get_hook_candidates":
    result_data = json.loads(result)
    selected = result_data.get("selected")
    if selected:
        last_hook_candidate_id = selected.get("id")
```

### G-2: PROXY_BASE_URL エラー修正（緊急）

| 項目 | 内容 |
|------|------|
| ファイル | `apps/api/src/config/environment.js:17-18` |
| 問題 | Track A で追加した `userTypeService.js` → `logger.js` → `environment.js` のimportチェーンにより、nudge-cron が起動時に `PROXY_BASE_URL is required` で即死 |
| 修正 | throw → console.warn に変更。PROXY_BASE_URL はデスクトップ/Web用で nudge-cron には不要 |

```javascript
// 変更前
if (IS_PRODUCTION && !PROXY_BASE_URL) {
  throw new Error('PROXY_BASE_URL is required in production environment');
}

// 変更後
if (IS_PRODUCTION && !PROXY_BASE_URL) {
  console.warn('[environment] PROXY_BASE_URL is not set in production (not required for cron jobs)');
}
```

### G-3: バックエンド API 確認済み

`POST /api/admin/tiktok/posts` は完全実装済み。バリデーション・重複防止（409）・エラーハンドリング全て実装済み。Phase 1 でバックエンド変更は不要。

### G-4: requirements.txt 確認済み

`openai>=1.40.0` + `requests>=2.31.0` で全依存関係カバー済み。変更不要。

### G-5: ローカルテスト時の環境変数チェックリスト

| 変数 | 必要 | 用途 |
|------|------|------|
| OPENAI_API_KEY | ✅ | Agent ループ + evaluate_image |
| FAL_API_KEY | ✅ | generate_image |
| BLOTATO_API_KEY | ✅ | post_to_tiktok |
| EXA_API_KEY | ✅ | search_trends |
| API_BASE_URL | ✅ | api_client（Staging URLを指定） |
| API_AUTH_TOKEN | ✅ | api_client 認証 |
| TIKTOK_ACCOUNT_ID | ❌ | config.py にデフォルト値 `28152` あり |

### G-6: GHA workflow は main にファイルを置くだけ（main で実行するわけではない）

GitHub Actions の仕様:
- `schedule`（cron）は **default branch（main）にファイルがないと発火しない**
- `workflow_dispatch`（手動実行）も **main にファイルがないと UI に表示されない**
- ただし **実行時は `actions/checkout@v4` で dev ブランチを checkout できる**

つまり:
- main には `.github/workflows/*.yml` ファイルだけ存在すればよい
- 実際の Agent コード（`scripts/anicca-agent/`）は dev → main マージ後に反映される
- Phase 4 は「main にワークフローファイルを置く」だけ。main で Agent を実行するわけではない

---

## 完全タスクリスト

### Phase 0: 緊急修正（nudge-cron 復旧）

| # | タスク | 対象ファイル | 修正内容 | 対応Issue |
|---|--------|-------------|---------|-----------|
| 0-1 | PROXY_BASE_URL throw → warn | `apps/api/src/config/environment.js` | L17-18 の throw を console.warn に変更 | G-2 |

### Phase 1: Agent ロバスト化（コード修正）

| # | タスク | 対象ファイル | 修正内容 | 対応Issue |
|---|--------|-------------|---------|-----------|
| 1-1 | save_post_record 強制呼び出し | `anicca_tiktok_agent.py` | ループ後に追跡変数チェック→未呼び出しなら強制save | C-1 |
| 1-2 | Thompson Sampling strategy パラメータ追加 | `tools.py`, `api_client.py` | tool定義にstrategy追加、実装でAPIに渡す | C-2 |
| 1-3 | 空 blotato_post_id バリデーション | `tools.py` (save_post_record) | 空文字チェック、エラー返却 | C-3 |
| 1-4 | 空 image_url バリデーション | `tools.py` (generate_image, evaluate_image) | 空URLチェック、明確なエラー返却 | C-4 |
| 1-5 | 3ツールにtry/except追加 | `tools.py` (get_yesterday_performance) | 構造化エラーJSON返却 | H-1 |
| 1-6 | evaluate_image デフォルト修正 | `tools.py` | score=5時 recommendation="regenerate" | H-2, M-1 |
| 1-7 | search_trends mandatory化 | `anicca_tiktok_agent.py` | System Prompt修正 | M-2 |
| 1-8 | agent_reasoning required化 | `tools.py` | save_post_record の required 配列に追加 | M-3 |
| 1-9 | System Prompt 構造化 | `anicca_tiktok_agent.py` | 全体をMandatory Workflow形式に書き換え | M-4 |
| 1-10 | hook_candidate_id 追跡 | `anicca_tiktok_agent.py` | get_hook_candidates 結果からID追跡（G-1参照） | C-1補助 |

### Phase 2: dev push & Staging 検証

| # | タスク | コマンド |
|---|--------|---------|
| 2-1 | 全28ユニットテスト実行 | `cd apps/api && npm test` |
| 2-2 | dev にコミット＆push | `git add && git commit && git push origin dev` |
| 2-3 | Staging 自動デプロイ確認 | ヘルスチェック: `curl https://anicca-proxy-staging.up.railway.app/health` |
| 2-4 | nudge-cron 起動確認 | PROXY_BASE_URL エラーが消えたか確認 |

### Phase 3: ローカルフルフローテスト（実際のTikTok投稿）

| # | タスク | 詳細 |
|---|--------|------|
| 3-1 | 環境変数設定 | G-5 のチェックリスト参照。API_BASE_URL は Staging URL を指定 |
| 3-2 | Agent をローカル実行 | `cd scripts/anicca-agent && python anicca_tiktok_agent.py` |
| 3-3 | TikTok投稿確認 | @anicca.self に実際に投稿されたか確認 |
| 3-4 | DB記録確認 | `tiktok_posts` テーブルにレコードが保存されたか確認 |
| 3-5 | ログ確認 | save_post_record が呼ばれたか、agent_reasoning が含まれているか |

### Phase 4: GitHub Actions 有効化

| # | タスク | 詳細 |
|---|--------|------|
| 4-1 | main に workflow ファイルのみコピー | main を checkout → `.github/workflows/` の2ファイルだけ追加 → commit & push。Agent コードは含めない（G-6参照） |
| 4-2 | workflow_dispatch で手動テスト | GitHub Actions UI → 「Use workflow from: dev」を選択して実行 |
| 4-3 | 実行ログ確認 | 正常終了・投稿成功を確認 |

### Phase 5: main マージ & 1.5.0 リリース

| # | タスク | 詳細 |
|---|--------|------|
| 5-1 | dev → main マージ | 全テスト PASS + フルフローテスト完了後 |
| 5-2 | Production デプロイ確認 | main push → Railway 自動デプロイ → ヘルスチェック |
| 5-3 | Production DB マイグレーション | `wisdom_patterns_pattern_name_key` UNIQUE 制約適用 |
| 5-4 | 1.5.0 タグ作成 | `git tag v1.5.0 && git push origin v1.5.0` |
| 5-5 | cron 初回実行確認 | 翌日 00:00 UTC の自動実行を確認 |

---

## 境界（やらないこと）

| やらないこと | 理由 |
|-------------|------|
| 他の1.5.0スペック（time-sensitive, backend-cleanup, daily-metrics） | 別エージェントの担当 |
| iOS アプリ変更 | この機能はバックエンド + Agent のみ |
| fetch_metrics.py の修正 | 既にrobustなエラーハンドリングがある |
| 新しい API エンドポイント追加 | 既存エンドポイントで十分 |
| Agent のモデル変更（gpt-4o以外） | 現時点で十分 |

---

## 修正対象ファイル一覧

| ファイル | 変更種別 |
|---------|---------|
| `scripts/anicca-agent/anicca_tiktok_agent.py` | 修正（System Prompt + 追跡ロジック） |
| `scripts/anicca-agent/tools.py` | 修正（バリデーション + エラーハンドリング + schema） |
| `scripts/anicca-agent/api_client.py` | 修正（strategy パラメータ追加） |

**変更しないファイル:**
- `scripts/anicca-agent/config.py` — 変更不要
- `scripts/anicca-agent/fetch_metrics.py` — 変更不要
- `apps/api/` 配下 — Phase 1では変更なし
