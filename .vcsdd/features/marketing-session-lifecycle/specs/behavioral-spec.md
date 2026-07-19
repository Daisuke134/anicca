# Behavioral Spec: Marketing Session Lifecycle

- REQ-001: provision は signup/profile 成功後、`warming`、`browser`、`started_warming=作成日` の row を追加する。
- REQ-002: provision は `Client().login`、`login_by_sessionid`、instagrapi settings 作成を実行しない。
- REQ-003: day は `started_warming` から `経過日数 + 1` で計算し、day1-2 は warming を維持する。
- REQ-004: day>=3 の warming account は初回だけ password login、timeline feed probe、settings dump を行う。
- REQ-005: feed probe 成功後だけ `session_owner=instagrapi`、`status=ready` にする。
- REQ-006: settings または login-attempt marker がある account は password relogin しない。dead session は ready にしない。
- REQ-007: goal-monitor は `session_owner=instagrapi` かつ day>=3 の account だけを verify-only 対象にする。
- REQ-008: browser/day1-2 account は cooked marker を作らない。
- REQ-009: clip の両 pass は共有 provision renderer を唯一の lifecycle 正本にする。
- REQ-010: state write は既存 row 数、順序、非対象 row を保つ。
