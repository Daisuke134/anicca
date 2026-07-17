# OpenAI Build Week — Life Manager (cloud web app) エントリー spec

作成 2026-07-17。調査正本 = `docs/2026-07-17-openai-build-week-hackathon.md`。
done = "Devpost に Life Manager の提出が完了し、確認画面を実測した"（締切 Jul 22 09:00 JST）。

## 不変条件（全て MUST）

1. Track = **Apps for Your Life**。対象 = Life Manager cloud web app（`apps/life-call/`、Railway、origin/main）。
2. core functionality の majority は **Codex CLI session 内で実装**する（提出に /feedback Codex Session ID 必須）。
   **Luna(proxy)/Claude での実装は core にカウントされない** — Codex Session ID が出ないため。
   Fable = plan/spec/verify、Codex = implement。
3. 既存プロジェクト規定に従い、7/13 以降の拡張を dated commits + Codex session log で証明できる状態を保つ。
4. README に (a) Codex がどこで workflow を加速したか (b) GPT-5.6 と Codex の使い方 (c) 既存 vs 新規の区別、を明記。
5. 審査員が無料でテストできること（審査期間末 8/5 PT まで）。
6. デモ動画 <3分・public YouTube・音声で Codex+GPT-5.6 の使い方を説明。
7. ~~$100 無料クレジット申請~~ → **実測 2026-07-17: フォームは配布終了で closed**（"we've given out all available credits"）。クレジットは取得不可。実装は ChatGPT Plus の Codex 枠で行い、超過 API 利用のみ自腹。

## 役割分担（fable-luna-sol-harness との関係）

| 役割 | 担当 | hackathon 上の意味 |
|---|---|---|
| plan / spec / 検証 / 提出作業 | Fable（私） | 審査対象外の采配 |
| **hackathon feature の実装** | **Codex CLI 0.143.0（ChatGPT ログイン済み）** | Session ID = 提出必須の証跡 |
| review | Sol xhigh（solx）可 | 補助。証跡には使わない |
| Luna subagent | hackathon core には使わない | Codex session が残らないため |

## TODO（順序の正本。TaskList と二重トラック）

| # | タスク | 期限 | 状態 |
|---|---|---|---|
| 1 | Devpost 登録 + $100 クレジット申請 | 7/18 04:00 JST | done（登録 DONE 実測。クレジットは配布終了=取得不可） |
| 2 | feature 選定（SSOT spec + apps/life-call 読了後に決定） | 7/18 | pending |
| 3 | Codex CLI で実装 + Railway デプロイ | 7/20 | pending |
| 4 | README + 審査員テストアクセス | 7/20 | pending |
| 5 | デモ動画 <3分 + YouTube 公開 | 7/21 | pending |
| 6 | Devpost 提出 | 7/22 09:00 JST | pending |

## 実測記録（2026-07-17 夜）

- Devpost 登録 DONE: keiodaisuke@gmail.com（Devpost native email+password。Google OAuth は passkey 2FA 壁で不可＝既知事象）。確認バナー "Thanks for registering!" 実測。
- $100 クレジット form: closed（配布終了）。取得不可、リトライ無意味。
- 副産物: OpenAI Platform 新規 org 作成済み — org name "Aniccaai" / org-5cTQRUbzJCnZXb1xn0MfRiux / contact@aniccaai.com。product 内 GPT-5.6 API 呼び出しはこの org を使える。
- Codex 実装は ChatGPT Plus の Codex 枠（ログイン済み）で行う。

## feature 決定（2026-07-17 scout 実読調査に基づく）

現状実測: app の LLM は **Gemini のみ**（ask.js/notify.js=gemini-2.5-flash、通話=gemini-2.5-flash-native-audio、OpenAI 呼び出しゼロ）。GPT-5.6 統合は完全新規 = hackathon の「新規拡張」として最適な証跡になる。

**採用（Codex で実装する core）:**
1. **search-before-ask（issue #11 直撃）**: 場所曖昧イベントを GPT-5.6 の検索+推論で先に解決し、質問を closed [はい/いいえ] 化。触る = `lib/ask.js:257-277` + 新規 `lib/gpt-resolve.js`。impact story = 実在ユーザーの実在課題（審査基準③）。
2. **Morning Briefing 通話オープナー**: T-10/T-5 電話の冒頭を GPT-5.6 生成の「今日の見通し」に差替え。触る = 新規 `lib/gpt-brief.js` + `scheduler.js` / `lib/call-logic.js`。デモ映え最強（電話が GPT-5.6 の声の台本で始まる）。
3. （時間余れば）Nightly Digest: GPT-5.6 が一日総括を TG 送信。

却下: #4 カレンダー衛生（gcal 書込リスク）/#5 Health 提案（Gmail scope、2日で無理）。

**前提作業（hackathon 以前に直さないとデモ自体が死ぬ）:**
- Telnyx 残高は 07-17 に $25 補充済みだが、実発信の再確認（SSOT spec の V1）が未実施。
- `.worktrees/lm-call-fix`（fix/lm-call-dial-burn、f82010e65、dial 失敗時 dedup rollback 修正）が未 merge。npm test 173/173 は spec 主張のみ＝このセッション未検証 → merge 前に再実行必須。

## 未決事項

- 審査員テストアクセスの形（demo account / demo 動画中心 + test-call endpoint）は実装後に確定。Stripe $20/mo 課金が入口にあるため、審査員用に無料 demo 経路が必要（要件: "Testing access must be free of charge"）。
