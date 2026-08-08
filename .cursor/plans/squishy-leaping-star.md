# Connpass detail の start/end を現行公開DOMから読む

## Context

Connector の日次 wake は Luma → Connpass の順で候補を探索するが、Connpass detail 読取りが安全失敗し続けて
実 registration まで到達していない。本セッションで failure を2段階に分解した。

1. `connpass_detail_read_failed`（全失敗が1コードに潰れて原因不明）
   → public field 別に分離（commit `a5c7edd4a`）。
2. 分離後の live wake で `connpass_detail_title_invalid_failed` を取得
   → 現行 connpass detail ページは `application/ld+json` を **0ブロック**しか出さず、先頭 `<h1>` も空。
     実 title は `div.current_event_title`。title 源を追加（commit `e828ffd07`）。
3. 直後の live wake（`wake-34c7e996d29e9c74277979ac`）で次の exact code
   **`connpass_detail_start_invalid_failed`** を取得。

つまり残る根本原因は同じ「JSON-LD 不在」であり、`event.startDate` / `event.endDate` が常に null になる。
本計画はこの start（次いで end）を、実測した現行公開DOMだけを根拠に閉じる。

### 実測した現行DOM（read-only、公開ページ）

`https://openforce.connpass.com/event/399614/` の SSR HTML に hCalendar microformat が存在する:

```html
<span class="dtstart"><span class="value-title" title="2026-07-31T21:00:00Z"></span> ... </span>
〜
<span class="dtend"><span class="value-title" title="2026-07-31T23:30:00Z"></span> ... </span>
```

`title` 属性は UTC ISO instant で、`Date.parse` がそのまま受け付ける。
表示テキスト側（`2026/08/01(土) 06:00 ～ 08:30`）はパース不要。

## 変更対象

### 1. `apps/life-manager/lib/connpass-browser-discovery.js`

`readEventDetail` の page 内抽出に DOM fallback を1つ足す。既存 helper を再利用する:

- `text(selector)` は textContent 用なので、属性用に同スコープで `attr(selector, name)` を追加する
  （`document.querySelector(selector)?.getAttribute(name)` を trim して空なら null）。
- `starts_at: event.startDate || attr(".dtstart .value-title", "title")`
- 本スライスでは **start だけ**。`ends_at` は次スライス（同じ機構、`.dtend .value-title`）。

`normalizeConnpassEventDetail` 側の validation は一切緩めない
（title 300字上限、`Number.isFinite`、`end <= start` の RANGE 判定はそのまま）。

### 2. `apps/life-manager/lib/connpass-browser-discovery.test.js`

既存の readEventDetail テスト（`global.document` を差し替える形式、L45- と L84- が雛形）に合わせて RED を追加:

- JSON-LD 0件・`.current_event_title` あり・`.dtstart .value-title[title]="2026-07-31T21:00:00Z"` の fake document
- 期待: `result.starts_at === "2026-07-31T21:00:00Z"`
- 期待: `.dtstart` 不在時は `starts_at === null`（fail-closed 維持、normalize 側が START_INVALID を投げる）

`connector-connpass-workflow.js` と `connector-minimal-runner.js` は変更しない
（進捗217で allowlist と code preserve は既に配線済み）。

## 検証

1. RED 確認 → 最小 patch → focused suite:
   ```
   node --test \
     apps/life-manager/lib/connpass-browser-discovery.test.js \
     apps/life-manager/lib/connector-connpass-workflow.test.js \
     apps/life-manager/lib/connector-minimal-runner.test.js \
     apps/life-manager/lib/connector-minimal-production.test.js
   ```
   （現状 28/28 GREEN が baseline。新 RED 2件を足して 30/30 を目標）
2. spec `docs/superpowers/specs/2026-08-01-dais-life-manager-five-phase-execution-spec.md` に進捗219を追記
   （Active remaining TODO SSOT 見出しの前に挿入。TODO 表自体は進捗216のまま）
3. commit → push（`feature/connector-native-completion`）
4. schedule は unloaded のまま `bash skills/connector/run.sh` を foreground 1回発火
5. safe evidence のみ読む: `~/.local/state/life-manager/connector-native/wake-reports.jsonl` の `safe_reason` と
   `action-history.jsonl` の該当 wake 行。次の exact code（想定 `connpass_detail_end_invalid_failed`）を取得
6. Telegram 進捗報告（送信先 target が未解決。下記「未解決」参照）

## 既知の後続（本計画のスコープ外）

| 順 | 項目 |
|---|---|
| 次 | `.dtend .value-title` で end を閉じる |
| その後 | 実 candidate（無料・受付中・Calendar非衝突）に到達 → cached/direct action → 親 readback |
| Item 14 | `connector-production-browser-harness.js:135` の bounded action proposer が `input.provider !== "luma"` で reject。Connpass fallback を同一 page/session/最大10 step で通すために provider-neutral 化が必要 |

## 未解決

- Telegram 進捗報告の送信先: `openclaw message send` は `--target` 必須だが、
  `LM_CONNECTOR_TELEGRAM_TARGET` / `LM_DEV_TELEGRAM_TARGET` / `LM_ADMIN_TELEGRAM_CHAT_ID` は
  `~/.openclaw/.env` に存在しない（key 名のみ確認、値は出力していない）。
  connector loop 自身は Telegram positive ID を取れているので、その解決経路を辿るのが次の一手。

## 完了と主張しない条件

実 registration bundle（provider readback / Calendar event ID + 独立 readback / full-page PNG SHA /
Telegram message・photo positive IDs / durable `applied_bundle`）が揃うまで「動いている」と言わない。
現時点で Submit 0、Calendar write 0、PNG 0、applied_bundle 0。
