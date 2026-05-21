2026-02-10: iPad対応のSPECを `.cursor/plans/ios/1.6.2/ipad.md` に追加（仕様書のみ、実装変更なし）。

リポジトリ観測（根拠ファイル）:
- SwiftUI Appライフサイクル: `aniccaios/aniccaios/aniccaiosApp.swift`
- `UIApplicationDelegateAdaptor` で AppDelegate 併用: `aniccaios/aniccaios/AppDelegate.swift`
- main app の `IPHONEOS_DEPLOYMENT_TARGET` は 16.6: `aniccaios/aniccaios.xcodeproj/project.pbxproj`
- `TARGETED_DEVICE_FAMILY = 1`（iPhoneのみ）で、iPad対応には 1,2 へ変更が必要: `project.pbxproj`
- `UIRequiresFullScreen = true`（iPadのSplit View / Stage Manager を阻害する可能性）: `aniccaios/aniccaios/Info.plist`
- `UIApplicationSupportsIndirectInputEvents` は有効（ポインタ前提あり）: `project.pbxproj`

SPEC方針（要点）:
- 対象: iPadOS 16.6+。
- Minimum: iPadで起動がiPhone拡大表示にならず、主要フロー完走、Split View/Stage Managerの可変サイズで破綻なし。
- Recommended: `NavigationSplitView`、iPad向けsheet/detent、keyboard shortcuts、pointer affordance、multiwindow影響の抑制。
- テスト: iPadシミュレータ（11/13等）+ Split View/Stage Manager、必要ならMaestroをiPadでも実行。