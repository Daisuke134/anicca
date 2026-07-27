# H3 ORG-checkup Design

## Goal

`done="胃・大腸・脳ドックの実カレンダー履歴が別々の care category として分類され、本人の安定した実測周期だけが既存 11a→11b→11c chain に到達し、年次・隔年の周期を判定するのに十分な履歴を cloud runtime が取得する"`

H3 は新しい医療判断器ではない。既存の PHYSICAL care detector に、長周期の検診を失わず通す分類・履歴・候補検索・事後報告の adapter を足す。

## Evidence

| Source | URL | Core evidence |
|---|---|---|
| 国立がん研究センター がん情報サービス | https://ganjoho.jp/public/pre_scr/screening/about_scr01.html | 「胃がん検診」は 2 年に 1 回、「大腸がん検診」は 1 年に 1 回と掲載される。 |
| 厚生労働省「がん予防重点健康教育及びがん検診実施のための指針」 | https://www.mhlw.go.jp/content/10900000/001266928.pdf | 胃がん検診は原則 2 年に 1 回、他の対象検診は原則年 1 回という公的指針がある。 |
| 日本脳ドック学会 | https://jbds.jp/guideline/ | 学会は「脳ドックの水準と有効性の向上」を目的に 2026 ガイドラインを発行している。公開ページには全員共通の再受診周期は掲示されていない。 |
| Google Calendar API Events.list | https://developers.google.com/workspace/calendar/api/v3/reference/events/list | `timeMin` / `timeMax` と `nextPageToken` により過去の event window を完全走査できる。 |

## Decision

### 1. Category

追加する canonical care type は次の 3 つ。

| care type | 分類対象 | candidate search |
|---|---|---|
| `gastric_screening` | 胃がん検診、胃検診、胃ドック、胃カメラ、胃内視鏡、gastric/stomach screening、gastroscopy | `胃がん検診 胃内視鏡` |
| `colorectal_screening` | 大腸がん検診、大腸検診、大腸ドック、大腸カメラ、大腸内視鏡、便潜血、colorectal/colon screening、colonoscopy | `大腸がん検診 大腸内視鏡` |
| `brain_dock` | 脳ドック、brain dock、brain screening | `脳ドック` |

Specific checkup category は generic `clinic` より先に照合する。同じ event を通院と検診の両方に数えない。

### 2. Cadence

公的な 1 年 / 2 年という値は、分類の妥当性と必要履歴幅を決める根拠にだけ使う。detector へ固定 interval として入力しない。

既存の安全条件をそのまま維持する。

| Input state | Decision |
|---|---|
| 履歴 0〜2 回 | silence |
| 3 回 / 2 gap | `observe_only` |
| 4 回以上、gap 不安定 | `observe_only` |
| 4 回以上、本人 gap が安定、1.5× median 超過 | actionable |
| explicit goal | 既存 goal rule |

年齢、症状、既往歴、検査結果がない runtime が公的対象年齢や診療上の interval を決めることは禁止する。検査結果や診断も保存しない。

### 3. History

現行約 18 か月では、年次なら 4 visit、隔年なら 4 visit を観測できない。default care history を 10 年に拡張する。

理由:

- 隔年 4 visit は最初から最後まで 6 年。
- 既存 action threshold は最終 visit から 3 年超（2 年 cadence × 1.5）。
- action 時点で最初の visit を window 内に残すには約 9 年が必要。
- 10 年なら境界と日付揺れを含められる。

完全性を推測しない既存 cursor walk は維持する。hard cap は 10,000 events に上げる。cursor が cap 後も続く場合は `history_unavailable` として fail closed し、partial history を daily claim に書かない。

### 4. End-to-end path

```text
Google Calendar (10y, complete cursor walk)
  → classifyCareHistory (specific before clinic)
  → detectCalendarCare (personal cadence only)
  → lm_care_scan_log
  → actionable only
  → anchored category-specific Places search
  → existing route evaluator / Steel booking gate
  → existing aftercare renderer + calendar receipt
```

11b/11c の gate、生活圏 hard filter、usual-provider precedence、double-booking guard、phone prohibition は変更しない。

## Files

| File | Change |
|---|---|
| `lib/events.js` | 10-year default window and honest 10,000-event cap |
| `lib/care-daily-runtime.js` | three specific categories and precedence |
| `lib/care-candidate-search.js` | category-bound Places queries |
| `lib/i18n.js` | Japanese labels and emoji |
| focused `*.test.js` files | RED/GREEN contracts |
| `eval/phy-cases.jsonl` | stable checkup cadence and no-history safety cases |
| consolidation SSOT | H3 evidence and TODO state |

## Non-goals

| Excluded | Reason |
|---|---|
| 医療ガイドラインを個人へ自動適用 | 年齢・症状・既往歴・医師判断がなく unsafe |
| 検査結果、診断、病名の推論 | care detector の既存 no-diagnosis contract |
| 検査方法の推奨 | Life Manager は本人の過去行動を再現するだけ |
| phone booking | §9.5 の absolute prohibition |
| browser implementation rewrite | H3 は既存 Steel path の category adapter |

## Verification

| Layer | Proof |
|---|---|
| Unit | classification precedence, keyword-bound search, i18n report |
| Detector | stable annual/biennial personal cadence acts; no/single visit stays silent |
| History | default 10 years, cursor completeness, cap failure |
| Integration | actionable checkup runs existing 11b chain; observe-only does not |
| Full | `npm test` and `npm run eval` |
| Production | merged SHA equals Railway deployment SHA; service health passes |

