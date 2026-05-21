# Research: naist-events

## Decision 1: Webスクレイピングツール

- **Decision**: Firecrawl CLI（`/opt/homebrew/bin/firecrawl scrape <url> markdown`）
- **Rationale**: プロジェクト絶対ルール（CLAUDE.md）。WebFetch禁止、Firecrawl必須。naist-fundsで実績あり。
- **Alternatives considered**: Playwright（重すぎる）、axios+cheerio（HTML構造変化に弱い）

## Decision 2: スクレイピング対象URL

- **Decision**: `https://www.naist.jp/event/` または `https://www.naist.jp/events/`
- **Rationale**: NAISTの公式イベントページ。Firecrawlでmarkdown取得後、今週の日付を含む行を抽出する。
- **Note**: 実際のURLはMac Mini上で `firecrawl scrape https://www.naist.jp/event/ markdown` を実行して確認が必要。

## Decision 3: 今週フィルタリング

- **Decision**: Node.js の `Date` オブジェクトで月曜〜日曜を算出し、イベントの日付がその範囲内かをチェック
- **Rationale**: 外部ライブラリなし。naist-deadlineで確立したパターンと同様。
- **Alternatives considered**: moment.js, dayjs（依存追加不要のためネイティブを優先）

## Decision 4: カレンダー連携

- **Decision**: `gog calendar events add primary` CLI（naist-calendarスキル実装済み）
- **Rationale**: Mac Miniに既存のnaist-calendarスキルがgog CLIを使用していることを確認。環境変数: `GOG_ACCOUNT=keiodaisuke@gmail.com`, `GOG_KEYRING_PASSWORD=shizen1234`
- **Integration**: `add-to-calendar.js` がgog CLIをexecSyncで呼び出す

## Decision 5: Slack投稿

- **Decision**: naist-fundsと同じ `openclaw message send` パターン
- **Rationale**: 既存実装と統一。`utils/slack.js` をそのままコピー＆流用。
- **Channel ID**: `C091G3PKHL2`

## Decision 6: イベントキャッシュ管理

- **Decision**: `data/cache.json` にnotified配列（`title:date` 文字列のハッシュ）を保存
- **Rationale**: naist-fundsのcache.jsonパターンと統一。atomic write（tmp + renameSync）。
- **ID生成**: `${event.title.slice(0,20)}:${event.date}` の文字列

## Decision 7: テストフレームワーク

- **Decision**: Jest（naist-fundsと同じ）
- **Rationale**: 既存スキルと統一。Node.js 18+ on Mac Mini確認済み。

## Decision 8: cronスケジュール

- **Decision**: `20 9 * * 1`（毎週月曜09:20 JST）
- **Rationale**: specで定義済み。naist-fundsの09:15と5分ずらして競合回避。

## Decision 9: naist.jp/event/ URL確認

- **Decision**: スクレイピングURLは `https://www.naist.jp/event/` と `https://www.naist.jp/seminar/` の両方を試みる
- **Rationale**: NAISTのイベントページはセミナーと一般イベントが分かれている可能性がある。実行時に404が返ったもう一方を使う。
- **Fallback**: 両方失敗した場合は「イベント情報を取得できませんでした」とSlack投稿してexit 0
