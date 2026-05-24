# Setup Guide — OSS Users

ソース: l.md（KOE app） / 核心の引用: 「DebugManagerというクラスを作り、起動時の制御を一元化します」

## 前提条件

| 項目 | 値 |
|------|-----|
| Xcode | 16+ |
| iOS Deployment Target | 15+ |
| Python | 3.9+ |
| pip packages | `Pillow`, `PyYAML` |

```bash
pip3 install Pillow PyYAML
```

---

## Step 1: DebugManager.swift をアプリに追加（l.md Step 1）

`YourApp/App/ScreenshotDebugManager.swift` として配置:

```swift
// App/ScreenshotDebugManager.swift
// l.md Bible Step 1: CommandLine引数でモックデータ注入と画面遷移を制御
// Pattern: l.md DebugManager.configure() — called from onAppear

#if DEBUG
import Foundation

final class ScreenshotDebugManager {
    static let shared = ScreenshotDebugManager()
    private init() {}

    func configure() {
        // CommandLine引数を読んでアプリの状態を制御する
        // 例: AppState.shared.configureForScreenshots()
        // 各アプリでこのメソッドを実装する
    }
}
#endif
```

`YourApp.swift` の onAppear から呼ぶ:

```swift
// App/YourApp.swift
var body: some Scene {
    WindowGroup {
        ContentView()
            .onAppear {
                #if DEBUG
                ScreenshotDebugManager.shared.configure()
                #endif
            }
    }
}
```

---

## Step 2: ScreenshotTests.swift を UITests に追加（l.md Step 2）

`YourAppUITests/ScreenshotTests.swift` として配置:

```swift
// UITests/ScreenshotTests.swift
// l.md Bible Step 2: XCTAttachment でスクリーンショット撮影（SnapshotHelper不使用）

import XCTest

final class ScreenshotTests: XCTestCase {

    override func setUpWithError() throws {
        continueAfterFailure = false

        // システムアラートを自動で処理
        addUIInterruptionMonitor(withDescription: "System Alert") { alert in
            let allowButtons = ["Allow", "許可", "OK", "開く", "Open"]
            for title in allowButtons {
                if alert.buttons[title].exists {
                    alert.buttons[title].tap()
                    return true
                }
            }
            return false
        }
    }

    @MainActor
    func testCaptureScreen1() throws {
        let app = XCUIApplication()
        app.launchArguments = ["--screenshot-screen1"]
        app.launch()
        sleep(5)
        takeScreenshot(named: "screen1")
    }

    @MainActor
    func testCaptureScreen2() throws {
        let app = XCUIApplication()
        app.launchArguments = ["--screenshot-screen2"]
        app.launch()
        sleep(3)
        takeScreenshot(named: "screen2")
    }

    @MainActor
    func testCaptureScreen3() throws {
        let app = XCUIApplication()
        app.launchArguments = ["--screenshot-screen3"]
        app.launch()
        sleep(5)
        takeScreenshot(named: "screen3")
    }

    // l.md Bible: SnapshotHelper不使用。標準XCTAttachmentだけで完結
    private func takeScreenshot(named name: String) {
        let screenshot = XCUIScreen.main.screenshot()
        let attachment = XCTAttachment(screenshot: screenshot)
        attachment.name = name
        attachment.lifetime = .keepAlways  // 成功時も消えない
        add(attachment)
    }
}
```

---

## Step 3: docs/screenshots/ ディレクトリ構造を作成

```bash
mkdir -p docs/screenshots/{config,scripts,resources,raw,processed}
```

- `config/screenshots.yaml` — デザイン設定（pipeline.md 参照）
- `scripts/extract_screenshots.py` — xcresulttool 抽出スクリプト（pipeline.md 参照）
- `scripts/process_screenshots.py` — PIL 合成スクリプト（pipeline.md 参照）
- `resources/iphone17_bezel.png` — Apple Design Resources から取得

## Step 4: iphone17_bezel.png を取得

Apple Design Resources（公式）からダウンロード:
https://developer.apple.com/design/resources/

`docs/screenshots/resources/iphone17_bezel.png` に配置。

---

## Step 5: Makefile と Python スクリプトを配置

`references/pipeline.md` に全ファイルのコードが書いてある。コピーして配置する。
