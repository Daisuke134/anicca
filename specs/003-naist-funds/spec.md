# Feature Specification: naist-funds

**Feature Branch**: `003-naist-funds`
**Created**: 2026-02-24
**Status**: Draft
**Input**: User description: "NAIST学生向け科研費・奨学金・研究助成金の新着情報をSlackで週次自動通知し、申請手順の案内もできるスキル"

## User Scenarios & Testing *(mandatory)*

### User Story 1 - 週次助成金情報の自動通知 (Priority: P1)

NAIST学生がSlackを見るだけで、科研費・奨学金・研究助成金の新着情報を毎週自動で受け取れる。
申請期限が近い案件を優先表示し、見落としを防ぐ。

**Why this priority**: 助成金情報の見落としは機会損失に直結する。週2回の自動通知がコアバリュー。

**Independent Test**: Slackチャンネルに助成金一覧メッセージが投稿されることを確認できる。

**Acceptance Scenarios**:

1. **Given** 月曜・木曜09:15 JST になったとき、**When** cronが起動したとき、**Then** 最新の助成金情報がSlackに投稿される
2. **Given** 助成金情報が取得できたとき、**When** Slackに投稿するとき、**Then** 名前・締切・金額・概要・URLを含む
3. **Given** 締切が30日以内の助成金があるとき、**When** 一覧を表示するとき、**Then** ⚠️マークで強調表示される

---

### User Story 2 - 申請手順の案内 (Priority: P2)

「〇〇の申請方法は？」とSlackで質問したとき、Aniccaが申請手順をステップ形式で回答する。

**Why this priority**: 情報通知だけでなく行動を促すのがAniccaの本質。手順案内でコンバージョン向上。

**Independent Test**: 「学振DC1の申請方法は？」に対してステップ形式の回答が返ることを確認できる。

**Acceptance Scenarios**:

1. **Given** ユーザーが「〇〇の申請方法」と質問したとき、**When** Aniccaがナレッジから検索したとき、**Then** ステップ形式で手順を回答する
2. **Given** 申請手順が不明な案件のとき、**When** 検索してもヒットしないとき、**Then** 公式URLを案内して「詳細は公式サイトで確認を」と回答する

---

### User Story 3 - 手動でリフレッシュ (Priority: P3)

「助成金情報を更新して」とSlackで指示したとき、cronを待たずに即時取得・投稿する。

**Why this priority**: 急ぎの確認ニーズに対応。cronの補完機能。

**Independent Test**: 「助成金情報を更新して」に対してSlackに最新情報が即時投稿されることを確認できる。

**Acceptance Scenarios**:

1. **Given** ユーザーが「助成金情報を更新して」と指示したとき、**When** Aniccaが実行したとき、**Then** 最新の助成金情報がSlackに投稿される

---

### Edge Cases

- ソースサイトがダウン・スクレイピング失敗した場合 → エラーをSlack通知し、前回取得データを使用する
- 助成金情報が0件の場合 → 「新着情報はありません」をSlackに投稿する
- 重複投稿防止 → 同じ案件を前回通知済みの場合は除外する（IDキャッシュ）

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: スキルは月曜・木曜09:15 JSTにcronで自動起動しなければならない
- **FR-002**: JSPS（日本学術振興会）・JST（科学技術振興機構）・jfund.or.jp から助成金情報を取得しなければならない
- **FR-003**: 取得した情報をSlackチャンネルに投稿しなければならない（名前・締切・金額・概要・URL必須）
- **FR-004**: 締切30日以内の案件を⚠️マークで強調表示しなければならない
- **FR-005**: 前回通知済みの案件のIDをキャッシュし、重複投稿を防がなければならない
- **FR-006**: 「〇〇の申請方法」への質問に対してステップ形式で回答しなければならない
- **FR-007**: 取得失敗時はエラー内容をSlackに通知しなければならない
- **FR-008**: 手動起動（即時実行）に対応しなければならない

### Key Entities

- **Grant（助成金）**: id, name, organization, amount, deadline, summary, url, category（科研費/奨学金/助成金）
- **NotifiedCache**: grantId, notifiedAt（重複防止）
- **GuideKnowledge**: keyword[], steps[], officialUrl（申請手順ナレッジ）

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 月曜・木曜09:15 JSTに助成金情報がSlackに自動投稿される（週2回）
- **SC-002**: 締切30日以内の案件が⚠️マークで正しく強調表示される
- **SC-003**: 申請方法の質問に対して3秒以内にステップ形式の回答が返る
- **SC-004**: 同じ案件が2週連続で重複投稿されない
- **SC-005**: ソース取得失敗時に30秒以内にSlackエラー通知が届く

## Assumptions

- Firecrawl CLIを使用してJSPS/JST/jfund.or.jpをスクレイピングする
- Slackへの投稿はOpenClaw `exec` + `openclaw message send` を使用する
- データキャッシュはJSONファイル（naist-funds/data/cache.json）に保存する
- 申請手順ナレッジは静的JSONファイルで管理する（naist-funds/data/guides.json）
