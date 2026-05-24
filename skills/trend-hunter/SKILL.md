---
name: trend-hunter
description: "Larry スライドショー用のフックテキストを X / TikTok から検索して hooks-ja.json / hooks-en.json を更新する"
metadata: {"openclaw":{"emoji":"🔍","os":["darwin","linux"]}}
---

# trend-hunter

## 目的

Larry（TikTokスライドショー）用のフックテキストを、X と TikTok から検索して
hooks-ja.json または hooks-en.json に追加する。

**このスキルに実行可能スクリプトはない。** SKILL.md を読み、手順をツールで実行する。

## cron からの呼び出し

cron メッセージに `target: larry-ja` または `target: larry-en` が含まれる。
- `target: larry-ja` → 日本語フック検索 → hooks-ja.json 更新
- `target: larry-en` → 英語フック検索 → hooks-en.json 更新

## 必須 env

| キー | 用途 |
|------|------|
| X_BEARER_TOKEN | X 検索（x-research スキル） |
| DANSUGC_API_KEY | TikTok 検索（DanSUGC MCP via mcporter） |

## 実行手順

### Step 1: X 検索（x-research スキル）

**重要**: X検索は単一の短いフレーズで検索する。複数キーワードANDは0件になる。
**X がクレジット切れ・usage切れ・0件でも、そこで止めない。TikTok検索に必ず進み、見つかったフックだけで hooks 更新まで完了させる。**

**target: larry-ja の場合:**
```bash
cd ~/.openclaw/skills/x-research && bun run x-search.ts search "頑張らなくていい" --sort likes --limit 20
cd ~/.openclaw/skills/x-research && bun run x-search.ts search "自分を責めない" --sort likes --limit 20
cd ~/.openclaw/skills/x-research && bun run x-search.ts search "休んでいい" --sort likes --limit 20
cd ~/.openclaw/skills/x-research && bun run x-search.ts search "疲れた" --sort likes --limit 20
cd ~/.openclaw/skills/x-research && bun run x-search.ts search "しんどい" --sort likes --limit 20
```

**target: larry-en の場合:**
```bash
cd ~/.openclaw/skills/x-research && bun run x-search.ts search "you're not lazy" --sort likes --limit 20
cd ~/.openclaw/skills/x-research && bun run x-search.ts search "it's okay to rest" --sort likes --limit 20
cd ~/.openclaw/skills/x-research && bun run x-search.ts search "burnout is real" --sort likes --limit 20
cd ~/.openclaw/skills/x-research && bun run x-search.ts search "healing isn't linear" --sort likes --limit 20
cd ~/.openclaw/skills/x-research && bun run x-search.ts search "you're not broken" --sort likes --limit 20
```

各クエリの結果から ❤️1K+ のポストを抽出する。

### Step 2: TikTok 検索（DanSUGC MCP）

**target: larry-ja の場合:**
```bash
mcporter call dansugc.tiktok_search_videos --args '{"query":"心に響く言葉 共感 メンタル"}' --config ~/.openclaw/workspace/config/mcporter.json
mcporter call dansugc.tiktok_search_videos --args '{"query":"自己嫌悪 頑張りすぎ 疲れた 休む"}' --config ~/.openclaw/workspace/config/mcporter.json
```

**target: larry-en の場合:**
```bash
mcporter call dansugc.tiktok_search_videos --args '{"query":"mental health healing quotes relatable"}' --config ~/.openclaw/workspace/config/mcporter.json
mcporter call dansugc.tiktok_search_videos --args '{"query":"you are not broken anxiety recovery self care"}' --config ~/.openclaw/workspace/config/mcporter.json
```

各クエリの結果から views 10K+ のキャプションを抽出する。

### Step 3: フックテキスト抽出

X と TikTok の結果から、以下のルールでフックテキストを抽出する:

**フォーマットルール:**
- 2-4行（\n で改行）
- 1行あたり 4-6 words
- REACTIONS（反応・共感）であること。アドバイスやラベルではない
- エモーショナル・脆い・心理的洞察

**良い例（JA）:**
```
自己嫌悪って\n本当は自分への\n期待の裏返し
```
```
頑張りすぎずに休んでね？\n→ 休んだら、私の治療費や\n生活費はあなたが出してくれるの？
```

**良い例（EN）:**
```
you're not lazy.\nyou're tired.\nyou've been in\nsurvivor mode
```
```
nobody talks about\nthe version of you\nbefore healing
```

**悪い例:**
```
自己嫌悪の対処法  ← ラベル、アドバイス
```
```
5 tips for anxiety  ← リスト、ラベル
```

### Step 4: 重複チェック

**target: larry-ja:**
```bash
cat /Users/anicca/.openclaw/workspace/tiktok-marketing/hooks-ja.json
```

**target: larry-en:**
```bash
cat /Users/anicca/.openclaw/workspace/tiktok-marketing/hooks-en.json
```

既存の hooks の text と比較:
- 完全一致 → 追加しない
- 80%以上同じ意味 → 追加しない
- 新しいフックのみ追加対象

### Step 5: hooks-XX.json 更新

新フックを追加する。フォーマット:
```json
{
  "text": "新しいフックテキスト\n2行目\n3行目",
  "source": "x-research 2026-03-21",
  "addedDate": "2026-03-21"
}
```

- **最低 3個、最大 10個** の新フックを追加
- プールが **50個未満** なら積極的に追加（目標: 各言語 50個以上維持）
- hooks-XX.json の hooks 配列の末尾に追加
- **更新は必ず一回で行う**。`edit` の分割適用で JSON が壊れやすいので、`python3` で読み込み → 追記 → `write_text()` の atomic write → `json.loads()` で再parse、の順で完了させる

**書き込み先:**
- target: larry-ja → `/Users/anicca/.openclaw/workspace/tiktok-marketing/hooks-ja.json`
- target: larry-en → `/Users/anicca/.openclaw/workspace/tiktok-marketing/hooks-en.json`

### Step 6: Slack #metrics 報告

**送信時は必ず target を明示する。**

```
🔍 larry-trend-hunter ({target}, {date})
━━━━━━━━━━━━━━━━━━━━━
X検索: {N}件ヒット（❤️1K+: {N}件）
TikTok検索: {N}件ヒット（10K+ views: {N}件）
新フック追加: {N}個
現在のプール: {N}個

追加したフック:
1. 「{text}」(source: {source})
2. 「{text}」(source: {source})
3. ...
```

送信先: `channel: {{profile.channels.reportChannel}}` または同等の `target` 指定を必須にする。

## 禁止事項

- demos-mapping.json の hooks_ja/hooks_en には触らない（ReelClaw専用）
- workspace/trends/ や workspace/hooks/ には書かない（旧フロー）
- web_search は使わない
- フック生成にオリジナルを入れない（検索結果のフレーズをそのまま使う）

## 失敗時

- X 検索失敗 → TikTok のみで続行
- TikTok 検索失敗 → X のみで続行
- 両方失敗 → Slack に失敗報告して終了
- 新フックが 3個未満しか見つからない → 見つかった分だけ追加して報告
