---
name: build-in-public
description: Generates and posts "Day X of building Anicca" tweets on X (Twitter). Use when the user asks to post a development update, share progress on X, or create a Build-in-Public tweet.
disable-model-invocation: true
---

# Build in Public - X自動投稿スキル

Build in Public の「Day X of building Anicca」形式のX投稿を自動生成・投稿する。

## 使用タイミング

ユーザーが以下を依頼した時に発動:
- 「今日の進捗を投稿して」
- 「Build in Public 投稿して」
- 「Day X 投稿」
- `/post-update`

## 実行手順

### Step 1: 情報収集

1. **日次ログを読む**
   ```
   .claude/skills/agent-memory/memories/daily-logs/YYYY-MM-DD.md
   ```

2. **Git履歴を取得**
   ```bash
   git log --oneline -20
   git diff HEAD~10..HEAD --stat  # エラー時は git log のみ使用
   ```

3. **Day X を計算**
   ```python
   from datetime import datetime
   day_count = max(1, (datetime.now() - datetime(2026, 1, 2)).days)
   ```

### Step 2: 投稿文生成

**ルール:**
- 280文字以内
- ハッシュタグなし
- JP版とEN版を両方生成

**フォーマット（EN例）:**
```
Day 31 of building Anicca.

Fixed hard paywall bug, users can now start trial properly.

Backend: Railway cron stability improvements.
iOS: Paywall flow debugging complete.
```

**フォーマット（JP例）:**
```
Day 31 of building Anicca.

ハードペイウォールのバグ修正完了。トライアル開始が正常に動作するように。

Backend: Railway cron安定化
iOS: Paywall フローのデバッグ完了
```

### Step 3: プレビュー表示

以下の形式でプレビューを表示し、ユーザー確認を待つ:

```markdown
## 📝 投稿プレビュー

### JP (@aniccaxxx)
\`\`\`
Day 31 of building Anicca.

ハードペイウォールのバグ修正完了。
\`\`\`
**文字数: 142/280 ✅**

### EN (@aniccaen)
\`\`\`
Day 31 of building Anicca.

Fixed hard paywall bug.
\`\`\`
**文字数: 168/280 ✅**

---

**投稿しますか？** (y/n)
```

### Step 4: X に投稿

ユーザーが承認したら、Blotato API で投稿:

```python
import sys
sys.path.insert(0, '.cursor/plans/ios/1.6.0/sns-poster')
from blotato import BlotatoClient

client = BlotatoClient()

# JP投稿
jp_result = client.post_to_x(jp_text, account="x_aniccaxxx")

# EN投稿
en_result = client.post_to_x(en_text, account="x_aniccaen")
```

**エラーハンドリング:**

| エラー | 対処 |
|--------|------|
| 401 | `[401] APIキー期限切れ` → `.env` の再設定を促す |
| 429 | 30秒待って自動リトライ（最大3回） |
| 5xx | ローカルに保存して後で手動投稿を促す |
| タイムアウト | 即座にリトライ（最大3回） |

### Step 5: ログ保存

投稿成功後、ログを保存:

```bash
mkdir -p .cursor/plans/ios/version-logs/
```

**ファイル:** `.cursor/plans/ios/version-logs/YYYY-MM-DD.md`

```markdown
# Build in Public - 2026-02-02

## Day 31

### JP (@aniccaxxx)
Posted at: 2026-02-02T15:30:00+09:00
Status: ✅ Success

\`\`\`
Day 31 of building Anicca.

ハードペイウォールのバグ修正完了。
\`\`\`

### EN (@aniccaen)
Posted at: 2026-02-02T15:30:05+09:00
Status: ✅ Success

\`\`\`
Day 31 of building Anicca.

Fixed hard paywall bug.
\`\`\`
```

## アカウント情報

| アカウント | Blotato ID | 言語 | キー |
|-----------|-----------|------|------|
| @aniccaxxx | 11820 | JP | `x_aniccaxxx` |
| @aniccaen | 11852 | EN | `x_aniccaen` |

## 280文字超え時のスレッド分割

280文字を超える場合:
1. 文で分割
2. 「1/2」「2/2」形式で番号付け
3. 最大3投稿まで

```python
def split_for_thread(text: str, max_chars: int = 280) -> list[str]:
    if len(text) <= max_chars:
        return [text]
    
    sentences = text.replace('\n\n', '\n').split('\n')
    posts = []
    current = ""
    for sentence in sentences:
        test = current + ("\n" if current else "") + sentence
        if len(test) <= max_chars - 4:
            current = test
        else:
            if current:
                posts.append(current)
            current = sentence
    if current:
        posts.append(current)
    
    if len(posts) > 1:
        posts = [f"{i+1}/{len(posts)} {p}" for i, p in enumerate(posts)]
    
    return posts[:3]
```

## 依存関係

- `requests` - HTTP クライアント
- `python-dotenv` - 環境変数読み込み
- `.env` に `BLOTATO_API_KEY` が設定されていること
