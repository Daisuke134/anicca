# iPad対応 SPEC（iOS 1.6.2）

最終更新: 2026-02-10  
対象ブランチ: `dev`  
成果物: 実装の指針となる仕様書（本ファイル）。このSPEC自体は実装を含まない。

---

## 0. 背景 / 目的

Anicca を iPad でも「iPhone拡大表示」ではなく **iPadアプリとして提供**し、以下を満たす。

- 画面サイズが大きい/可変（Split View / Stage Manager）でも破綻しない
- キーボード/ポインタ利用時の体験が最低限成立する
- iPhone UI の“単純拡大”ではなく、必要箇所は iPad の標準パターンへ寄せる

---

## 1. 現状（リポジトリからの観測）

### 1.1 UI技術の前提（SwiftUI主体）

- SwiftUI App ライフサイクル: `aniccaios/aniccaios/aniccaiosApp.swift`
- `UIApplicationDelegateAdaptor` で AppDelegate を併用: `aniccaios/aniccaios/AppDelegate.swift`
- 主要画面は SwiftUI（`NavigationStack` など）で構築されている（例: `aniccaios/aniccaios/Views/MyPathTabView.swift`）

結論: **iPad対応は SwiftUI を主戦場**とし、UIKit（`UISplitViewController` 等）は原則使わない（例外は「SwiftUIで実現困難かつ効果が大きい」場合のみ）。

### 1.2 デプロイターゲット / デバイス設定

- iOS デプロイターゲット（主要アプリ）: `IPHONEOS_DEPLOYMENT_TARGET = 16.6`（`aniccaios/aniccaios.xcodeproj/project.pbxproj`）
- 現状のターゲットデバイス: `TARGETED_DEVICE_FAMILY = 1`（= iPhone のみ）

### 1.3 iPadマルチタスク要件に関わる設定

- `UIRequiresFullScreen = true`（`aniccaios/aniccaios/Info.plist`）
  - これは iPad の Split View / Slide Over / Stage Manager の“可変ウィンドウ”体験を強く制限するため、iPad対応では必ず見直し対象。
- `INFOPLIST_KEY_UIApplicationSupportsIndirectInputEvents = YES`（`project.pbxproj`）
  - ポインタ（トラックパッド/マウス）対応の前提は既に入っている。

---

## 2. ターゲット / 対応範囲

### 2.1 対象OS

- **iPadOS 16.6+**（現状の iOS デプロイターゲットに合わせる）
  - `NavigationSplitView` / `NavigationStack` を前提に設計する（いずれも iOS 16+ で安定運用しやすい）。

### 2.2 対象デバイス

- iPad 10.9", iPad Air 11", iPad Pro 11", iPad Pro 12.9/13"（シミュレータで代表機種をカバー）

---

## 3. スコープ定義（Minimum / Recommended）

### 3.1 Minimum（必須）

「App Store に iPad 対応として提出しても破綻しない」最低ライン。

- iPad をターゲットに含める（`TARGETED_DEVICE_FAMILY` を iPhone+iPad へ）
- **iPad の可変サイズ**に追従できる（横画面、Split View、Stage Manager のウィンドウリサイズで致命的崩れなし）
- 主要フローが成立
  - 起動 → オンボーディング → メイン画面 → 通知タップ → NudgeCard 表示
  - 課金（Paywall）表示/購入/復元の最低限動作
- iPad の HIG を大きく逸脱しないモーダル挙動（「常に全画面」等の違和感が強い箇所を最小限だけ補正）
- 主要インタラクションの pointer/keyboard での“操作不能”を潰す（最低限）

### 3.2 Recommended（推奨）

「iPadらしい生産性」を出す（ただし全面刷新はしない）。

- `NavigationSplitView` による **sidebar + detail**（横幅が `regular` の時）
- NudgeCard / Paywall の iPad最適（フォームファクタに応じて sheet/detent を使い分け）
- 主要操作のキーボードショートカット
- ホバー/ポインタの affordance 改善（hover effect、行ハイライト、クリック領域拡大）
- マルチウィンドウ（複数Window）を意識した状態分離（少なくとも“壊れない”）

---

## 4. レイアウト戦略（SwiftUI）

### 4.1 基本方針

- 画面幅が広い iPad では **読みやすさ優先で「最大幅を制限」**する
  - 例: コンテンツ領域を `maxWidth: 600..720` 程度に抑え、中央寄せ（タイポ/可読性の維持）
- `horizontalSizeClass` だけで断定しない
  - iPad でも Split View では `compact` になり得るため、**サイズクラス + 実寸幅**（`GeometryReader`）の併用を許容する

### 4.2 ナビゲーション（Minimum）

- 現状の `NavigationStack` を維持し、iPad で破綻する View を個別に是正
- 画面の「余白が不自然」「行が広すぎて読めない」問題は最大幅制限で解決する

### 4.3 ナビゲーション（Recommended）

- 横幅 `regular` かつ一定幅以上（例: `>= 900pt`）では `NavigationSplitView` を採用
  - Sidebar: セクション（例: My Path / Subscription / Account）をリスト化
  - Detail: 現在の `MyPathTabView` の内容を、セクション単位に分割して表示
- Split View でも `compact` に落ちるケースは `NavigationStack` に自動フォールバック

> UIKit の `UISplitViewController` は採用しない（SwiftUIで統一し、実装負債を増やさない）。

### 4.4 方向（Orientation）

- iPad は **Portrait / Landscape** を両対応（現状のInfo設定に沿う）
- `UIRequiresFullScreen` を見直した場合、Split View / Stage Manager での縦横切替も成立させる

---

## 5. マルチウィンドウ / Stage Manager

### 5.1 Minimum

- Stage Manager のウィンドウリサイズで致命的に崩れない
- Split View（1/2, 1/3）で主要画面が操作不能にならない

### 5.2 Recommended

- **複数Window**を開かれても壊れない（少なくともクラッシュしない）
  - 現状 `AppState.shared` がシングルトンのため、複数Windowで状態共有される前提になる
  - 望ましい最終形は「Window単位の `AppState`」だが、影響が大きいので段階導入する

段階導入案（推奨）:

1. v1: 共有状態のままでもクラッシュ/無限presentが起きないようにガードを追加
2. v2: `@StateObject` を `WindowGroup` スコープに寄せ、scene storage の導入を検討

---

## 6. 入力（キーボード / ポインタ）

### 6.1 キーボードショートカット（Recommended）

最低限、iPadでの外付けキーボード利用を想定し以下を付与する（SwiftUIの `.keyboardShortcut`）。

- 追加（例: struggles 追加）: `⌘N`
- 閉じる（sheet/モーダル）: `Esc`
- 設定/アカウント系へ遷移（存在する場合）: `⌘,`

### 6.2 ポインタ（Minimum）

- 主要ボタン/カードがクリック可能な領域になっている（`contentShape` 等で補強）
- 行/カード UI に hover affordance（Recommended: `.hoverEffect(.highlight)`）を検討

---

## 7. アセット（App Icon / Launch Screen / スクリーンショット）

### 7.1 App Icon

- `Assets.xcassets/AppIcon.appiconset` に iPad idiom の icon が存在する（観測済み）
- Minimum: 既存の AppIcon が iPad ビルドで問題なく解決されること

### 7.2 Launch Screen

- `Info.plist` に `UILaunchScreen` があるが中身は空（観測済み）
- Minimum: iPad でも起動直後に崩れ/黒画面/不自然なスケールが出ないこと
- Recommended: 背景色・ロゴ等を `UILaunchScreen` で定義し、iPadでも自然に見せる

### 7.3 App Store スクリーンショット（運用）

- iPad 対応で提出する場合、App Store Connect で iPad 用スクリーンショット枠が増える
- Minimum: 提出に必要なサイズのスクリーンショットを用意する
  - 例: iPad Pro 12.9/13"（縦横どちらかで統一）など

---

## 8. テスト計画

### 8.1 手動テスト（Minimum）

シミュレータ:

- iPad Pro 11"
- iPad Pro 12.9/13"
- iPad（10th gen）

観点:

- Portrait / Landscape
- Split View: 1/2, 1/3
- Stage Manager: ウィンドウ幅を最小近くまで縮める → 最大まで広げる
- NudgeCard / Paywall / オンボーディングの表示崩れ
- ポインタ操作（クリックできない、hoverが分からない等）
- キーボード（Escで閉じる等、導入した範囲）

### 8.2 自動テスト（Recommended）

- 既存 `maestro/` のフローを iPad ターゲットでも走らせる（必要なら iPad 用 config を追加）
- 画面崩れ検知:
  - まずは「代表スクリーンを固定デバイスで撮って差分比較」を導入（将来）
  - すでに `CardScreenshotGenerator` があるため、同様の発想で iPadの代表画面キャプチャを自動化できる余地がある（ただし本SPECでは“将来候補”扱い）

---

## 9. 受け入れ条件（Acceptance Criteria）

### 9.1 Minimum（must）

- iPad 実機/シミュレータで **iPhone拡大表示にならず**起動する
- 主要フローが完走できる
  - オンボーディング完了
  - メイン画面操作
  - 通知タップからの NudgeCard 表示・dismiss・👍👎
  - Paywall 表示・購入/復元（テスト環境で）
- Split View / Stage Manager のウィンドウサイズ変更で
  - クラッシュしない
  - 重要操作が画面外に隠れて操作不能にならない

### 9.2 Recommended（should）

- `regular` 幅で `NavigationSplitView` により情報探索が速い
- 主要シートが iPadらしい表示（中央寄せ/適切な detent）
- キーボードショートカットが最低限機能する

---

## 10. 非ゴール（Non-goals）

- Mac Catalyst 対応
- iPad専用の全面UI刷新（新デザインシステム導入など）
- iOS/iPadOS 15 以下のサポート
- iPad専用機能（Pencil 連携、ドラッグ&ドロップ全面対応 等）の追加

---

## 11. ロールアウト計画

1. Dev で iPad を有効化し、シミュレータで Minimum を満たすまで UI 崩れ修正
2. TestFlight（社内/限定）で iPad 実機検証
3. App Store 提出
   - iPad スクリーンショット準備
   - 必要なら段階的リリース（Phased Release）を利用

---

## 12. 実装タスクリスト（チェックリスト + ラフ見積）

見積は「実装者 1人・既存コード理解済み」を前提にしたラフ（±50% あり）。

### 12.1 プロジェクト設定

- [ ] `TARGETED_DEVICE_FAMILY` を iPhone+iPad に変更（アプリ本体、Widget、NotificationService 等）: 0.5d
- [ ] `UIRequiresFullScreen` の方針決定と更新（Split View / Stage Manager を許可するなら `false`）: 0.25d
- [ ] iPad の `UISupportedInterfaceOrientations~ipad` を必要に応じて明示: 0.25d

### 12.2 UI（Minimum）

- [ ] 主要画面の最大幅制限（読みやすさの担保）: 0.5d
- [ ] オンボーディングの iPad 表示（中央寄せ/余白/フォント）調整: 0.5d
- [ ] NudgeCard / Paywall の iPad 表示崩れを修正（fullScreenCoverの見直し含む）: 0.5d
- [ ] Split View / Stage Manager リサイズ時の崩れ修正（特に `ScrollView` / `sheet` / `toolbar`）: 1.0d

### 12.3 UI（Recommended）

- [ ] `NavigationSplitView` 導入（regular 幅で sidebar+detail）: 1.5d
- [ ] 主要ショートカットの付与（⌘N, Esc, ⌘, 等）: 0.5d
- [ ] hover affordance / pointer最適化（必要箇所のみ）: 0.5d
- [ ] マルチウィンドウでの状態衝突を抑えるガード（クラッシュ/無限present対策）: 0.5d

### 12.4 テスト / 運用

- [ ] iPad シミュレータでの手動テスト項目をチェックリスト化し、結果を残す: 0.5d
- [ ] Maestro を iPad でも回す（必要なら iPad 用 flow / config を追加）: 0.5d
- [ ] App Store iPad スクショ作成（必要サイズに合わせて）: 0.5d

