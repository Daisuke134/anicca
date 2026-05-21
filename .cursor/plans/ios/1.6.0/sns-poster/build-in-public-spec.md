# Build in Public 自動投稿 — Spec

**作成日**: 2026-02-02
**ステータス**: Review v3 (Issues Fixed)

---

## 開発環境

| 項目 | 値 |
|------|-----|
| **ワークツリーパス** | `/Users/cbns03/Downloads/anicca-build-in-public` |
| **ブランチ** | `feature/build-in-public` |
| **ベースブランチ** | `dev` |
| **作業状態** | Spec レビュー中 |

---

## 1. 概要（What & Why）

### What
リリース完了時（or 日次）に、開発ログから「Day X of building Anicca」形式のX投稿を自動生成・投稿する。

### Why
- 現状: 毎回ユーザーが手動で「これ投稿して」と指示している
- 目標: リリースや大きな開発完了時に、自動でX投稿される
- Build in Public は継続が命。自動化しないと途切れる

### スコープ
- **Phase 1**: X投稿のみ（@aniccaxxx JP, @aniccaen EN）
- **Phase 2**: 他プラットフォーム（IG, Threads等）は後で拡張

---

## 2. 受け入れ条件

| # | 条件 | テスト可能 |
|---|------|-----------|
| AC1 | `/post-update` を実行すると、git diff + 日次ログからX投稿文が自動生成される | ✅ |
| AC2 | 生成された投稿文がプレビュー表示され、確認後に Blotato API 経由で X に投稿される | ✅ |
| AC3 | 投稿内容が `.cursor/plans/ios/version-logs/YYYY-MM-DD.md` に自動保存される | ✅ |
| AC4 | Day X カウンターが正しく算出される（開始日: 2026-01-02、最小値: 1） | ✅ |
| AC5 | JP/EN 両方の投稿が生成される（@aniccaxxx, @aniccaen） | ✅ |
| AC6 | SessionEnd Hook で日次ログが自動蓄積される（既存hookを拡張） | ✅ |
| AC7 | 投稿文は280文字以内に収まる（超える場合はスレッド分割） | ✅ |
| AC8 | Blotato API エラー時に「[エラーコード] メッセージ」形式で表示され、30秒後に自動リトライ（最大3回） | ✅ |

---

## 3. As-Is / To-Be

### As-Is（現状）

```
ユーザーが手動で「これ投稿して」と指示
    ↓
エージェントが blotato.py で投稿
    ↓
ログなし、履歴なし
```

**既存の SessionEnd Hook:**
- ファイル: `.claude/hooks/session-end-daily-log.sh`
- 保存先: `.claude/skills/agent-memory/memories/daily-logs/YYYY-MM-DD.md`
- 内容: セッション終了時刻のみ記録（transcript サマリーは未抽出）

**既存の blotato.py の問題:**
- docstring のアカウントキーが古い（`x_xg2grb` と記載、正しくは `x_aniccaxxx`）
- `post_to_x()` のデフォルト引数が `x_xg2grb`（存在しないキー）

### To-Be（変更後）

```
[自動] SessionEnd Hook → transcript サマリー抽出 → 日次ログに追記
    ↓
[手動] /post-update Skill 発火
    ↓
[自動] git diff + 日次ログ読み込み → 投稿文生成（280文字以内）
    ↓
[自動] プレビュー表示 → ユーザー確認
    ↓
[自動] Blotato API → X に投稿（JP + EN）
    ↓
[自動] version-logs/ にログ保存
```

### コンポーネント設計

| コンポーネント | ファイル | 役割 |
|--------------|---------|------|
| **SessionEnd Hook（拡張）** | `.claude/hooks/session-end-daily-log.sh` | 既存hookを拡張: transcript サマリー抽出 → 日次ログに追記 |
| **post-update Skill** | `.claude/skills/build-in-public/SKILL.md` | ログ + git diff → 投稿文生成 → プレビュー → Blotato 投稿 |
| **Blotato投稿（修正）** | `.cursor/plans/ios/sns-poster/blotato.py` | デフォルト引数を `x_aniccaxxx` に修正、docstring 更新 |

---

## 4. 技術仕様

### 4.1 Blotato API 設定

**環境変数設定（`.env`）:**
```bash
# プロジェクトルートの .env ファイルに追加
BLOTATO_API_KEY=blotato_xxxxxxxxxxxxx
```

**APIキー取得方法:**
1. https://app.blotato.com にログイン
2. Settings → API → Generate API Key
3. `.env` に `BLOTATO_API_KEY=` で保存

**レート制限:**
- 100 requests/minute
- 1000 requests/hour

**ネットワークタイムアウト:**
- HTTP リクエスト: 10秒
- タイムアウト時は即座にリトライ（30秒待機後、最大3回）

### 4.2 アカウントキー対応表

| 正しいキー | Blotato ID | 用途 | blotato.py 修正 |
|-----------|-----------|------|-----------------|
| `x_aniccaxxx` | 11820 | JP Build in Public | デフォルト引数に設定 |
| `x_aniccaen` | 11852 | EN Build in Public | - |

**修正箇所（blotato.py）:**
- Line 68: `account: str = "x_xg2grb"` → `account: str = "x_aniccaxxx"`
- Line 74-75: docstring 更新

### 4.3 Transcript JSONL 形式

**ファイル構造:**
```jsonl
{"type":"summary","summary":"今日の開発サマリー...","timestamp":"2026-02-02T12:00:00Z"}
{"type":"message","role":"user","content":"..."}
{"type":"message","role":"assistant","content":"..."}
```

**サマリー抽出ロジック:**
```bash
# 1行目が summary の場合
head -1 "$transcript_path" | jq -r '.summary // empty'

# summary が見つからない場合: 抽出スキップ（既存動作を維持）
```

**フォールバック:**
- `transcript_path` が空 → スキップ
- ファイルが存在しない → スキップ
- `summary` フィールドがない → スキップ
- JSON パースエラー → スキップ + stderr にログ

### 4.4 投稿文生成プロンプト

**LLM使用: Claude（Skill 実行エージェント自身）**

エージェントが以下の情報を読み取り、投稿文を生成:

**入力:**
1. 日次ログ: `.claude/skills/agent-memory/memories/daily-logs/YYYY-MM-DD.md`
2. Git log: `git log --oneline -20`
3. Git diff stat: `git diff HEAD~10..HEAD --stat`（HEAD~10 が存在しない場合は `git log --oneline` のみ使用）

**生成ルール:**
```
1. Day X カウンターを計算: max(1, (today - 2026-01-02).days)
2. 今日のハイライトを2-3行で要約
3. 技術的な変更を1-2行で要約
4. JP版: 日本語、280文字以内
5. EN版: 英語、280文字以内
6. ハッシュタグなし（Build in Public はクリーンに）
```

**出力フォーマット（EN例）:**
```
Day 31 of building Anicca.

Fixed hard paywall bug, users can now start trial properly.

Backend: Railway cron stability improvements.
iOS: Paywall flow debugging complete.
```

### 4.5 スレッド分割アルゴリズム

**文字数カウント:**
- Python: `len(text)` （Unicode 文字数、Twitter の実際のカウントに近い）

**分割ロジック:**
```python
def split_for_thread(text: str, max_chars: int = 280) -> list[str]:
    if len(text) <= max_chars:
        return [text]
    
    # 文で分割を試みる
    sentences = text.replace('\n\n', '\n').split('\n')
    
    posts = []
    current = ""
    for sentence in sentences:
        test = current + ("\n" if current else "") + sentence
        if len(test) <= max_chars - 4:  # 4文字余裕（"1/2 "用）
            current = test
        else:
            if current:
                posts.append(current)
            current = sentence
    if current:
        posts.append(current)
    
    # 番号付け（2投稿以上の場合）
    if len(posts) > 1:
        posts = [f"{i+1}/{len(posts)} {p}" for i, p in enumerate(posts)]
    
    return posts[:3]  # 最大3投稿
```

**スレッド投稿:**
- Blotato API で1投稿目を送信 → `post_id` を取得
- 2投稿目以降は `reply_to: post_id` で送信（Blotato がサポートしている場合）
- サポートしていない場合: 個別投稿（スレッドにならないが許容）

### 4.6 プレビュー表示形式

エージェントがチャットで以下を表示:

```markdown
## 📝 投稿プレビュー

### JP (@aniccaxxx)
```
Day 31 of building Anicca.

ハードペイウォールのバグ修正完了。トライアル開始が正常に動作するように。

Backend: Railway cron安定化
iOS: Paywall フローのデバッグ完了
```
**文字数: 142/280 ✅**

### EN (@aniccaen)
```
Day 31 of building Anicca.

Fixed hard paywall bug, users can now start trial properly.

Backend: Railway cron stability improvements.
iOS: Paywall flow debugging complete.
```
**文字数: 168/280 ✅**

---

**投稿しますか？** (y/n)
```

### 4.7 Version Log 保存形式

**ファイル:** `.cursor/plans/ios/version-logs/YYYY-MM-DD.md`

```markdown
# Build in Public - 2026-02-02

## Day 31

### JP (@aniccaxxx)
Posted at: 2026-02-02T15:30:00+09:00
Status: ✅ Success (post_id: 1234567890)

```
Day 31 of building Anicca.

ハードペイウォールのバグ修正完了。
```

### EN (@aniccaen)
Posted at: 2026-02-02T15:30:05+09:00
Status: ✅ Success (post_id: 1234567891)

```
Day 31 of building Anicca.

Fixed hard paywall bug.
```

## Git Context
- Commits: 15
- Files changed: 23
- Main changes: PaywallView, SubscriptionManager
```

---

## 5. Skill 仕様（`/post-update`）

**ファイル:** `.claude/skills/build-in-public/SKILL.md`

**実行ステップ:**

1. `.claude/skills/agent-memory/memories/daily-logs/YYYY-MM-DD.md` を読む（今日の開発ログ）
2. `git log --oneline -20` で直近の変更を取得
3. `git diff HEAD~10..HEAD --stat` で変更ファイルを把握（エラー時は git log のみ使用）
4. 上記から「Day X of building Anicca」形式の投稿文を生成
   - JP版（@aniccaxxx ID:11820）: 日本語、280文字以内
   - EN版（@aniccaen ID:11852）: 英語、280文字以内
5. **プレビュー表示**（上記形式）→ ユーザー確認待ち
6. Blotato API で X に即時投稿（エラー時は自動リトライ）
7. `mkdir -p .cursor/plans/ios/version-logs/` → `YYYY-MM-DD.md` に投稿内容を保存

### Day X カウンター

```python
from datetime import datetime
day_count = max(1, (datetime.now() - datetime(2026, 1, 2)).days)
```

**エッジケース:**
- 2026-01-02 より前 → Day 1
- 2026-01-02 → Day 1（開始日）
- 2026-01-03 → Day 1（1日経過）
- 2026-02-02 → Day 31

---

## 6. SessionEnd Hook 拡張仕様

既存の `.claude/hooks/session-end-daily-log.sh` を拡張する（新規スクリプト作成しない）。

**変更内容:**
- stdin JSON から `transcript_path` を読み取る
- transcript JSONL の1行目から `summary` フィールドを抽出
- 既存の日次ログにサマリーを追記

**入力形式（stdin JSON）:**
```json
{"session_id": "abc123", "transcript_path": "/path/to/transcript.jsonl", "cwd": "/path/to/project"}
```

**追加するシェルスクリプト:**
```bash
# サマリー抽出
if [ -n "$transcript_path" ] && [ -f "$transcript_path" ]; then
    summary=$(head -1 "$transcript_path" | jq -r '.summary // empty' 2>/dev/null)
    if [ -n "$summary" ]; then
        echo "" >> "$daily_log"
        echo "### Session Summary" >> "$daily_log"
        echo "$summary" >> "$daily_log"
    fi
fi
```

---

## 7. テストマトリックス

| # | To-Be | テスト方法 | カバー |
|---|-------|-----------|--------|
| 1 | SessionEnd Hook でログ蓄積 | セッション終了後に daily-logs/ を確認 | ✅ |
| 2 | `/post-update` で投稿文生成 | Skill 実行 → プレビュー確認 | ✅ |
| 3 | 280文字制限 | 生成文の文字数カウント | ✅ |
| 4 | Blotato API で X 投稿 | テスト投稿 → X で確認 | ✅ |
| 5 | Day X カウンター | `max(1, (today - 2026-01-02).days)` を検証 | ✅ |
| 6 | JP/EN 両方生成 | 2つの投稿文が異なる言語で生成されること | ✅ |
| 7 | version-logs に保存 | 投稿後にファイル存在・内容確認 | ✅ |
| 8 | API エラーハンドリング | 意図的にエラーを発生させてリトライ確認 | ✅ |
| 9 | スレッド分割 | 300文字以上の投稿文でスレッド分割確認 | ✅ |
| 10 | Git エラー（HEAD~10 不在） | 新規リポジトリでフォールバック確認 | ✅ |
| 11 | 日次ログ不在 | ログなしで git のみから生成確認 | ✅ |

---

## 8. 境界

### やること
- X 投稿の自動化（JP + EN）
- 既存 SessionEnd Hook の拡張（transcript サマリー抽出）
- `blotato.py` のデフォルト引数・docstring 修正
- version-logs への保存

### やらないこと
- IG/TikTok/YouTube/Threads への投稿（Phase 2）
- 画像生成（テキストのみ）
- スケジュール投稿（即時のみ）
- 既存の TikTok エージェント（`anicca_tiktok_agent.py`）の変更
- 既存の cross-poster の変更

### 触るファイル
- `.claude/hooks/session-end-daily-log.sh`（拡張: transcript サマリー抽出追加）
- `.claude/skills/build-in-public/SKILL.md`（新規）
- `.cursor/plans/ios/sns-poster/blotato.py`（デフォルト引数修正: `x_xg2grb` → `x_aniccaxxx`、docstring 更新）
- `.cursor/plans/ios/version-logs/*.md`（自動生成）

### 触らないファイル
- `.claude/settings.local.json`（既に SessionEnd Hook 登録済み。変更不要）
- `scripts/anicca-agent/*`（既存 TikTok エージェント）
- `scripts/cross-poster/*`（既存 IG cross-poster）
- `.github/workflows/*`（既存ワークフロー）
- `.cursor/plans/ios/sns-poster/config.py`（参照のみ）

---

## 9. 依存関係

### Python パッケージ（既存、追加インストール不要）
- `requests` - HTTP クライアント
- `python-dotenv` - 環境変数読み込み

### シェルツール
- `jq` - JSON パース（macOS: `brew install jq`、大半の環境でインストール済み）

### 外部サービス
- Blotato API（APIキー必須、`.env` に設定済みであること）

---

## 10. 実行手順

| # | ステップ | 内容 |
|---|---------|------|
| 1 | ワークツリー作成 | `git worktree add ../anicca-build-in-public -b feature/build-in-public` |
| 2 | `blotato.py` 修正 | デフォルト引数 `x_aniccaxxx`, docstring 更新 |
| 3 | SessionEnd Hook 拡張 | transcript サマリー抽出を追加 |
| 4 | Skill ファイル作成 | `.claude/skills/build-in-public/SKILL.md` |
| 5 | `version-logs/` ディレクトリ作成 | `mkdir -p .cursor/plans/ios/version-logs/` |
| 6 | テスト投稿 | `/post-update` 実行 → プレビュー確認 → X で確認 |
| 7 | version-logs 保存確認 | ファイル生成を確認 |

### テストコマンド

```bash
# SessionEnd Hook テスト（手動、stdin でJSON渡し）
echo '{"session_id":"test","transcript_path":"","cwd":"/Users/cbns03/Downloads/anicca-project"}' | bash .claude/hooks/session-end-daily-log.sh

# 日次ログ確認
cat .claude/skills/agent-memory/memories/daily-logs/$(date +%Y-%m-%d).md

# Blotato API 接続テスト
cd .cursor/plans/ios/sns-poster && python3 -c "from blotato import BlotatoClient; c = BlotatoClient(); print(c.get_user())"

# version-logs ディレクトリ確認
ls .cursor/plans/ios/version-logs/
```

---

## 11. エラーハンドリング

| エラー | 対処 |
|--------|------|
| Blotato API 401 | `[401] Unauthorized: APIキー期限切れ` → ユーザーに `.env` の `BLOTATO_API_KEY` 再設定を促す |
| Blotato API 429 | `[429] Rate Limited` → 30秒待って自動リトライ（最大3回） |
| Blotato API 5xx | `[5xx] Server Error` → 投稿文を version-logs に保存、後で手動投稿を促す |
| 日次ログが空/存在しない | git log のみから投稿文を生成（フォールバック） |
| transcript_path が空 | サマリー抽出をスキップ（既存動作を維持） |
| transcript JSON パースエラー | サマリー抽出をスキップ + stderr にログ |
| HEAD~10 が存在しない | `git log --oneline -20` のみ使用 |
| version-logs 書き込み失敗 | エラーを表示するが投稿は続行 |
| version-logs 権限エラー | `[Permission Denied] .cursor/plans/ios/version-logs/ に書き込み権限がありません。chmod u+w で権限を付与してください` → 投稿は続行 |

---

## 12. 参考リソース

| リソース | 用途 |
|---------|------|
| Claude Code Hooks Guide (code.claude.com/docs/en/hooks-guide) | SessionEnd Hook の仕様 |
| GitButler Hooks 事例 (blog.gitbutler.com) | transcript パースの実装例 |
| Blotato API Docs (help.blotato.com/api/start) | 投稿API仕様 |
| `.cursor/plans/ios/sns-poster/config.py` | アカウントID一覧 |
| `.cursor/plans/ios/sns-poster/blotato.py` | Blotato API クライアント |
| `.claude/hooks/session-end-daily-log.sh` | 既存 SessionEnd Hook |

---

## 13. X アカウント（Build in Public 用）

| アカウント | Blotato ID | 言語 | 用途 |
|-----------|-----------|------|------|
| @aniccaxxx | 11820 | JP | Build in Public メイン |
| @aniccaen | 11852 | EN | Build in Public EN |
