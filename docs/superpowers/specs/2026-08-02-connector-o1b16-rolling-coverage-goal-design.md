# O1B-16 Rolling 21-Day Event Coverage Goal Design

created: 2026-08-02 JST
scope: 今日を含む21暦日のcoverage window、日別状態、immutable snapshot

## 1. Goal

ユーザーtimezoneの今日から20日後まで、exactly 21暦日を毎run再計算する。未解決日は必ず`open`とし、
「候補が見つからない」を解決済みに変換しない。

## 2. Current finding

正本specには21日coverageの完了条件があるが、production codeにcoverage goal、日別state、rolling recomputation、
snapshot storeはない。既存Calendar readは別organ用であり、primary calendarだけを読む経路もある。

## 3. Alternatives

### A. `now + n * 24h`で21日を作る

DSTやtimezone境界でlocal dateが重複・欠落するため不採用。

### B. User timezoneのlocal dateを起点に暦日加算する（採用）

`YYYY-MM-DD`を暦として0〜20日加算し、exactly 21個のdate keyを作る。日付goalに不要なmidnight instant変換を避ける。

### C. Google Calendar query windowそのものをcoverage goalにする

Calendar eventの存在は東京対面event参加確定を意味せず、空き時間も判定できないため不採用。

## 4. Snapshot contract

`buildRollingEventCoverage(input)`は次を返す。

- tenant、timezone、`calculated_at`
- `window_start_date`、`window_end_date`、`horizon_days=21`
- exactly 21個の`days`
- `open / covered_existing / covered_new / unavailable`のcount
- content-addressed `coverage_snapshot_id`

各dayは`date / status / evidence_refs`だけを持つ。`open`はevidence 0件。解決済みstateは後続stageが生成した
trusted evidence refsを1件以上必要とする。同じ日へ複数の異なるstateが来た場合は選ばずfail closedする。

## 5. Rolling behavior

snapshotは過去snapshotをpatchしない。毎run、現在timezoneの今日を起点に21日を再構築する。

```text
8/02 run: 8/02 ... 8/22
8/03 run: 8/03 ... 8/23
            ↑8/02を落とす  ↑新しい日をopenで追加
```

既存event cancelや予定変更は、後続resolverがその日のresolved evidenceを返さなければ次snapshotで自動的に
`open`へ戻る。古いsnapshotは監査履歴として残す。

## 6. Responsibility boundary

O1B-16が行う:

- timezone-local today
- 21暦日の生成
- resolved dayの構造・日付・参照整合性
- count、content hash、immutable保存

O1B-17〜24が行う:

- Luma inventory完走
- eventの意味評価
- registration
- 全Calendar/free interval/移動時間
- paid policy
- `covered_existing / covered_new / unavailable`の実証

O1B-16はCalendar eventのtitleやkeywordからstatusを判断しない。

## 7. Durable store

`lm_event_coverage_snapshots`へsnapshot全体をreference-only JSONとしてappendする。tenant、window start/end、
calculated timestampを列にも持ち、最新viewを提供する。UPDATE/DELETEは禁止する。同じsnapshot IDのretryは完全一致時だけ成功。

## 8. Live proof

実Google Calendarを今日〜20日後の範囲でread-only取得し、raw title/location/attendeeを保存・表示せず、event countと
date coverageだけを証拠化する。O1B23前なのでCalendarだけからresolved stateを作らず、初回snapshotは21日すべて
`open`であることを正直に保存する。翌日相当のfixtureではwindowが1日slideすることを実証する。

## 9. Completion criteria

- JST/DST timezone fixtureでexactly 21 unique dates
- todayと20日後を含み、21日後を含まない
- conflicting/out-of-window/ungrounded resolved dayを拒否
- immutable store/current viewを実DBで確認
- 実Calendar raw PIIをevidenceへ残さない
- O1B17へ渡すopen day listが正しい
