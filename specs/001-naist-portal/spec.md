# Feature Specification: NAIST Portal Access

**Feature Branch**: `001-naist-portal`
**Created**: 2026-02-23
**Status**: Draft

## User Scenarios & Testing *(mandatory)*

### User Story 1 - 成績・履修確認 (Priority: P1)

NAISTユーザーが `#ai-<name>` チャンネルで「成績確認して」または「履修状況教えて」と言うと、AniccaがNAISTポータルにアクセスして現在の成績・履修情報をSlackに返す。

**Why this priority**: 最も頻繁に使われる機能。手動でポータルを開いて認証を通すのが面倒なため、代理アクセスの価値が最も高い。

**Independent Test**: ユーザーが「成績確認して」と送ったとき、Aniccaがポータルにアクセスして成績一覧をSlackに返せれば完結。

**Acceptance Scenarios**:

1. **Given** 認証情報が設定済み, **When** ユーザーが「成績確認して」と送信, **Then** 30秒以内に成績一覧がSlackに投稿される
2. **Given** 認証情報が未設定, **When** スキルを実行, **Then** セットアップ手順がSlackに返る

---

### User Story 2 - お知らせ確認 (Priority: P2)

ユーザーが「ポータルのお知らせは？」と言うと、未読のお知らせ一覧をSlackに返す。

**Why this priority**: 履修変更期限・奨学金締切等の重要通知を見逃さないため。

**Independent Test**: 「お知らせ確認して」→ ポータルのお知らせ一覧テキストが返る。

**Acceptance Scenarios**:

1. **Given** ポータルに未読お知らせあり, **When** 「お知らせ確認して」と送信, **Then** 未読お知らせのタイトルと日付がSlackに投稿される
2. **Given** 未読お知らせなし, **When** 確認, **Then** 「新着お知らせはありません」と返る

---

### Edge Cases

- セッションが切れている → 再認証して再試行（最大1回）
- ポータルがメンテナンス中 → エラーメッセージをSlackに投稿
- 認証情報が未設定 → セットアップ手順をSlackに案内
- ポータルの構造が変更された → エラーをSlackに通知

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: ユーザーはチャットメッセージ1つでNAISTポータルの成績・履修情報を取得できること
- **FR-002**: システムはNAISTの認証（2段階認証を含む）を自動で通過してポータルにアクセスできること
- **FR-003**: 認証情報は安全な場所に保管され、チャット上・設定ファイル内に平文で露出しないこと
- **FR-004**: 取得した成績・お知らせは日本語で読みやすい形式でSlackに投稿されること
- **FR-005**: 認証情報が未設定の場合、ユーザーに初回セットアップ手順が案内されること
- **FR-006**: `#ai-<name>` チャンネルでのリクエストに応じてオンデマンドで実行できること

### Key Entities

- **PortalSession**: NAISTポータルへの認証済みアクセス状態
- **PortalCredentials**: ポータルへのアクセスに必要なユーザー識別情報（安全な保管場所に格納）
- **AcademicRecord**: 科目名・単位数・評価等の成績・履修情報
- **PortalNotice**: タイトル・日付を含むお知らせ情報

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: ユーザーが「成績確認して」と送信してから30秒以内にSlackに結果が返る
- **SC-002**: 認証情報が正常に設定されている場合、ポータルへのアクセス成功率が95%以上
- **SC-003**: 初回セットアップが5ステップ以内で完了できる
- **SC-004**: ポータルの構造が変更された場合、エラーがSlackに通知される

## Assumptions

- NAISTポータルにはウェブブラウザからアクセスできる
- NAISTの2段階認証はTOTPアプリ（Google Authenticator等）と互換性がある
- ユーザーはNAISTポータルの有効なアカウントを持っている
