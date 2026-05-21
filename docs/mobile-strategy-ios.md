# Anicca モバイル戦略決定（2025-08-29）

## 結論（Decision)
- モバイルは「iOSネイティブ」に全振りし、PWAは後回し。
- デスクトップ（Electron）は現行どおり“定刻・自動起動・OS連携の本丸”。
- 目的: 6:00 起床など「時刻厳守・能動ガイド・確実な通知/起動」を長期安定で提供すること。

## 背景（Context）
- Web 版（Next.js）は WebRTC で音声双方向が可能で、端末によってはホーム画面に戻っても会話が継続するケースがある。
- ただし iOS のブラウザ（WebKit）上では、背景時の録音/自動再生は OS 仕様の影響を強く受け、将来の OS 変更で破綻しうる。製品の柱としてはリスクが高い。
- 一方、iOS ネイティブは通知・前面制御・Siri/Shortcuts 連携・URL スキームなど OS 連携が豊富で、要件の中核（起床・誘導・ズーム起動）を堅実に実装できる。

## 現状（コード根拠）
- デスクトップ（Electron）
  - 定期タスク: `node-cron` + `~/.anicca/scheduled_tasks.json`（`src/main-voice-simple.ts`）。
  - 自動更新/常駐: `electron-updater` と Tray、`powerSaveBlocker('prevent-app-suspension')`。
  - URL/アプリ起動: `open_url` ツール → `shell.openExternal('zoommtg://...')`（`src/agents/tools.ts`）。
- Web（Next.js）
  - 音声双方向: `navigator.mediaDevices.getUserMedia({ audio: true })` + WebRTC（`anicca-web/app/page.tsx`）。
  - Slack 接続 UI: `components/ServiceConnections.tsx`。PWA（manifest/Service Worker/Push）は未導入。

## PWA が満たせない点（iOS の現実制約）
- 背景からの「自動音声開始/マイク開始」ができない（ユーザー操作必須）。
- 「6:00 に必ず実行して発話」の保証がない（タブ/OSによるサスペンド）。
- 任意時刻に Zoom を“自動起動”は不可（ユーザー操作が必要）。
- → 一時的に動く端末があっても、OS アップデートで挙動が変わり得るため、長期安定の柱にできない。

## iOS ネイティブで満たせること（実装パターン）
- 起床（6:00）
  - ローカル通知で確実に“気づかせる”。必要なら Critical Alerts を申請。
  - Night‑Stand（就寝用前面画面）なら 6:00 にアプリ前面のまま TTS で自動発話 → そのまま音声対話開始。
- 定刻ガイド（7:00 瞑想、8:00 出発 など）
  - 通知 → タップ → 即前面 → `startVoiceSession()` 注入で即会話。前面時は自動発話も可。
- Zoom 誘導
  - 前面なら自動で `zoommtg://...` 起動。背景時は通知アクションから 1 タップで起動。
- Siri ライクな即応
  - Siri Shortcuts で「Anicca を開いて」→ 即前面・即リッスン。ウィジェット/通知アクションも活用。

## アーキテクチャ（推奨）
- 「薄い iOS 殻 + 既存 Web クライアント（WKWebView）」
  - 既存の WebRTC/Realtime ロジックを最大限再利用。
  - ネイティブ層で通知/起動/スリープ抑止/DeepLink（Zoom・OAuth）/オーディオ権限を提供。
  - アプリ起動時に Web 側へ `startVoiceSession()` をブリッジ注入して即リッスン。
- 既存プロキシ（Railway）・ツール API は共通で流用。

## ユースケース適合性（要点）
- 6:00 起床で“必ず起こす/話す”
  - iOS ネイティブ: 前面（Night‑Stand）なら自動発話◯／背景でも通知→1タップで◯。
  - PWA: ×（自動発話不可、時刻厳守の保証なし）。
- 会議前自律誘導（Zoom）
  - iOS ネイティブ: 前面なら自動◯／背景は通知アクションから◯。
  - PWA: ×（自動起動不可）。
- “Siri みたいにすぐ呼べる”
  - iOS ネイティブ: Shortcuts/ウィジェットで◯。
  - PWA: ×。

## ロードマップ（一本化）
1) iOS 殻 + WKWebView（最小）
- 通知権限・ローカル通知、通知アクション設計（起床/会議/瞑想）。
- アプリ起動で Web に `startVoiceSession()` 注入、即リッスン。
- DeepLink: `zoommtg://`、OAuth コールバック（Proxy 連携）。
- Night‑Stand 画面（スリープ抑止・暗転・大きな時計・緊急停止）。

2) 体験強化
- Siri Shortcuts（音声コマンドで即前面・即リッスン）。
- 高齢者モード（大ボタン UI、反復通知＋読み上げ、服薬記録→必要なら家族へ通知）。

3) 保守と拡張
- ログ/診断の標準化、障害時フォールバック（通知→誘導）。
- CarPlay/ウィジェット、通知スヌーズ等の追加。

## リスクと対処
- iOS の「完全背景から自動発話/録音」は不可 → Night‑Stand 前面運用と通知で設計。
- 省電力/端末差 → 前面時のスリープ抑止とオーディオセッション管理で安定化。
- 審査（Critical Alerts/背景動作） → 申請理由の明確化、オプトイン UI、通常通知の代替ルートを併記。

## 非目標（Out of Scope）
- PWA 単独での“時刻厳守 自動発話/Zoom 自動起動”。
- iOS で“完全背景”からのマイク常時監視/ホットワード起動。

## 例え（理解補助）
- PWAは“マンションの一室を借りる”感じ。夜中に勝手にベルは鳴らせない。
- ネイティブは“自分の家”。決まった時間に確実に目覚まし・呼びかけができる（ただし家のルール＝OS規約の範囲内）。

## 参照（Repo）
- デスクトップ: `src/main-voice-simple.ts`, `src/agents/tools.ts`, `src/services/desktopAuthService.ts`, `src/config.ts`
- Web: `anicca-web/app/page.tsx`, `anicca-web/components/ServiceConnections.tsx`

---
本ドキュメントは「迷わず実装を進める」ための意思決定ログです。以降は iOS ネイティブ（薄殻 + WKWebView）を主軸に設計・実装を進めます。

