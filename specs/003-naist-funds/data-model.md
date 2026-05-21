# Data Model: naist-funds

**Date**: 2026-02-24
**Branch**: `003-naist-funds`

## Grant（助成金エンティティ）

スクレイピングで取得するデータの正規化形式。

```json
{
  "id": "string",          // SHA256(url + name)の先頭12文字。重複防止キー
  "name": "string",        // 助成金・公募名
  "organization": "string",// 主催機関（JSPS, JST, JFUND等）
  "amount": "string|null", // 金額（「上限200万円」等の文字列。不明ならnull）
  "deadline": "string|null",// 締切日（ISO 8601: YYYY-MM-DD。不明ならnull）
  "summary": "string",     // 概要（100文字以内に要約）
  "url": "string",         // 詳細ページURL
  "category": "string",    // "科研費" | "奨学金" | "研究助成"
  "fetchedAt": "string"    // ISO 8601 UTC。取得日時
}
```

### バリデーションルール

| フィールド | ルール |
|-----------|--------|
| id | SHA256(url+name) の先頭12文字。重複キーとして使用 |
| deadline | `null` の場合は表示時「締切不明」 |
| summary | 100文字超は切り捨て + `…` |
| category | 3値のみ許可。不明時は「研究助成」にフォールバック |

---

## NotifiedCache（通知済みキャッシュ）

`data/cache.json` のスキーマ:

```json
{
  "notified": [
    {
      "id": "string",       // Grant.id
      "notifiedAt": "string" // ISO 8601 UTC
    }
  ],
  "lastFetchedAt": "string|null" // 最後に全件取得した日時
}
```

### キャッシュ管理ルール

- `notified` は最大100件保持（古い順に削除）
- Grant.id が `notified` 配列に含まれる → スキップ（重複防止）
- `lastFetchedAt` から7日以上経過 → 全件再取得

---

## GuideKnowledge（申請手順ナレッジ）

`data/guides.json` のスキーマ:

```json
{
  "guides": [
    {
      "id": "string",         // "jsps-dc1" 等
      "keywords": ["string"], // マッチキーワード（「学振」「DC1」「特別研究員」等）
      "name": "string",       // 正式名称
      "steps": ["string"],    // 申請手順（番号付き、配列形式）
      "officialUrl": "string",// 公式サイトURL
      "deadline": "string|null" // 締切（毎年変動するため参考値。nullあり）
    }
  ]
}
```

### 初期ナレッジ（静的シード）

| id | 対象 | キーワード |
|----|------|-----------|
| jsps-dc1 | 学振DC1特別研究員 | 学振, DC1, 特別研究員, JSPS |
| jsps-dc2 | 学振DC2特別研究員 | 学振, DC2, 特別研究員 |
| jst-presto | JST さきがけ | さきがけ, PRESTO, JST |
| jst-crest | JST CREST | CREST, JST, 戦略的創造研究 |

---

## 状態遷移

```
Grant取得フロー:
  Firecrawl → rawMarkdown → parse → Grant[]
      ↓
  cache.jsonと照合
      ↓
  新規のみ → Slack投稿 → cache.json更新
      ↓
  締切30日以内 → ⚠️マーク付きで表示

ガイド検索フロー:
  ユーザー入力 → keywords照合 → HIT → steps返却
                                 ↓
                               MISS → officialUrl案内
```
