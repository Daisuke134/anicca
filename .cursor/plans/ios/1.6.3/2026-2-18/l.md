App Storeのスクリーンショット更新のたびに、こんな作業をしていませんか？

XCUITestでスクショを撮影
Figmaで一枚ずつデバイスフレームをはめ込む
キャッチコピーを配置して調整
端末サイズごとに微調整
エクスポートして命名
そこまで時間はかからないものの、機能追加のたびに同じ作業を繰り返すのは面倒ですよね。しかも、コピーを少し変えたいだけでも全画像を作り直し。

「撮影からストア提出用の画像生成まで、全部自動でやってくれたら楽なのに...」

そこで、XCUITest + Python Pillowを使って、撮影から加工まで完全自動化することにしました。
この記事では、個人開発でも実践できる自動化の仕組みを詳しく解説します。

完成イメージ
このパイプラインで生成されるApp Store用スクリーンショットの例です。
デバイスフレーム、キャッチコピー、背景装飾まで、すべて自動生成されます。



これらは音声日記アプリ「KOE」で実際に採用したアプリストアのスクリーンショットです。
コマンド一つで、このような完成度の高い画像が自動生成されます。



この記事で得られること
スクリーンショット自動化の仕組み全体像
Fastlane Snapfileに依存しない標準的な実装方法
Python + Pillowによる画像加工の実践テクニック
sin関数で描くパノラマ背景の実装
YAML駆動設計による保守性の高い構成
すぐに使えるサンプルコード
自動化の全体像
今回構築するパイプラインは以下の4ステップです：

準備（アプリ側実装）: CommandLine引数でモックデータ注入と画面遷移を制御
撮影（XCUITest）: 標準の XCTAttachment でスクリーンショット撮影
抽出（Python）: xcrun xcresulttool でxcresultバンドルから画像を救出
加工（Python + Pillow）: デバイスフレームとキャッチコピーを合成
# 実行コマンド
make generate-store-screenshots

たったこれだけで、以下が自動実行されます：

シミュレータ起動
アプリ起動（モックデータ注入）
画面遷移してスクリーンショット撮影
画像を抽出
フレーム合成・テキスト描画
ストア提出用画像の完成
ディレクトリ構成
記事で登場する各ファイルの全体像です：

.
├── KOE-ios/                       # アプリ本体
│   ├── App/
│   │   └── DebugManager.swift    # モックデータ注入・画面制御
│   └── Features/
│       └── ...
│
├── KOE-iosUITests/                # UIテスト
│   └── KOE_iosUITests.swift      # スクリーンショット撮影
│
├── docs/
│   └── screenshots/
│       ├── config/
│       │   └── screenshots.yaml   # デザイン設定（色・フォント・レイアウト）
│       ├── scripts/
│       │   ├── extract_screenshots.py   # xcresultから画像抽出
│       │   └── process_screenshots.py   # フレーム合成・テキスト描画
│       ├── resources/
│       │   └── iphone17_bezel.png       # Apple Design Resourcesから取得
│       ├── raw/                   # 抽出された生スクリーンショット
│       └── processed/             # 加工済み画像（ストア提出用）
│
└── Makefile                       # パイプライン統合とショートカットコマンド

実装の詳細
Step 1: モックデータ注入と画面制御(アプリ側実装)
自動撮影で最も重要なのは「毎回同じ表示」を実現することです。そのために、アプリ側で起動引数を受け取って、モックデータの注入と特定画面への自動遷移を制御します。

DebugManagerによる一元管理
DebugManager というクラスを作り、起動時の制御を一元化します。これにより、UITestから起動引数 (CommandLine.arguments) を経由してアプリの状態をコントロールできるようになります。

// App/DebugManager.swift

import SwiftUI
import SwiftData

@Observable
class DebugManager {
    var showInbox: Bool = false
    var skipOnboarding: Bool = false

    func configure(with container: ModelContainer) {
        // 起動引数をチェック
        if CommandLine.arguments.contains("--debug-inbox") {
            // 1. オンボーディングをスキップ
            skipOnboarding = true

            // 2. データを全削除してクリーンな状態に
            deleteAllData(from: container)

            // 3. 撮影用のモックデータを注入
            populateMockData(into: container)

            // 4. 少し待ってから目的の画面へ遷移（安定性のため）
            DispatchQueue.main.asyncAfter(deadline: .now() + 1.0) {
                self.showInbox = true
            }
        }
    }

    private func deleteAllData(from container: ModelContainer) {
        let context = ModelContext(container)
        // すべてのエントリを削除（例）
        try? context.delete(model: Entry.self)
        try? context.save()
    }

    private func populateMockData(into container: ModelContainer) {
        let context = ModelContext(container)
        let calendar = Calendar.current

        // 相対日付でモックデータを生成
        // 「昨日」「2日前」などにすることで、いつ撮影しても新鮮
        let yesterday = calendar.date(byAdding: .day, value: -1, to: Date())!
        let twoDaysAgo = calendar.date(byAdding: .day, value: -2, to: Date())!

        context.insert(Entry(text: "今日はいい天気でした", createdAt: yesterday))
        context.insert(Entry(text: "新しいカフェを見つけました", createdAt: twoDaysAgo))

        try? context.save()
    }
}

ポイント解説
相対日付の重要性
Date() から相対的に日付を生成することで、撮影日に関係なく現実時間に則した画面になります。絶対日付だと、たとえば数年前の年日などが表示されていると、アプリがアップデートされていないように見受けられてしまうので都度計算することをお勧めします。

DispatchQueue.main.asyncAfter の理由
データ注入直後に画面遷移すると、描画が間に合わないことがありました。
これは数秒待つことで、安定して目的の画面をキャプチャできるようになります。

App起動時の呼び出し

// App/YourApp.swift

@main
struct YourApp: App {
    let modelContainer: ModelContainer
    @StateObject private var debugManager = DebugManager()

    init() {
        // SwiftDataのコンテナ初期化
        do {
            modelContainer = try ModelContainer(for: Entry.self)
        } catch {
            fatalError("Could not initialize ModelContainer")
        }
    }

    var body: some Scene {
        WindowGroup {
            ContentView()
                .modelContainer(modelContainer)
                .environmentObject(debugManager)
                .onAppear {
                    // 起動時にDebugManagerを設定
                    debugManager.configure(with: modelContainer)
                }
        }
    }
}

Step 2: スクリーンショット撮影(XCUITest実装)
次に、実際に撮影を行うUIテストを書きます。UITest内でアプリに起動引数を渡し、Step 1で作成した DebugManager にモックデータを注入させ、目的の画面に遷移させてからスクリーンショットを撮影します。

スクショ撮影を自動化する際、Fastlane Snapshotを採用されるパターンが多いかと思いますが、ここでは、Fastlane独自の snapshot("name") を使わない方針にしています。

なぜ SnapshotHelper を使わないのか
Fastlaneの公式ドキュメントでは SnapshotHelper.swift の使用を推奨しています。
しかし、これにはいくつかの課題があります。

プロジェクトに追加のファイルが必要
Fastlaneのバージョンアップ時に互換性問題が起きうる
内部実装がブラックボックスで、問題時のデバッグが困難
代わりに標準の XCTAttachment を使えば、これらの問題から解放されます。Appleの公式機能だけで完結するため、長期メンテナンスにも強くなります。

実装例
// UITests/ScreenshotTests.swift

import XCTest

final class ScreenshotTests: XCTestCase {

    override func setUpWithError() throws {
        continueAfterFailure = false

        // システムアラート（マイク許可など）を自動で処理
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
    func testCaptureOnboarding() throws {
        let app = XCUIApplication()
        app.launch()

        // オンボーディング画面の表示を待つ
        sleep(2)

        takeScreenshot(named: "onboarding")
    }

    @MainActor
    func testCaptureHomeEmpty() throws {
        let app = XCUIApplication()
        app.launchArguments = ["--debug-home-empty"]
        app.launch()

        sleep(3)

        takeScreenshot(named: "home_empty")
    }

    @MainActor
    func testCaptureInbox() throws {
        let app = XCUIApplication()
        // Step 1で作った引数を渡す
        app.launchArguments = ["--debug-inbox"]
        app.launch()

        // 画面遷移とデータ表示を待つ
        sleep(5)

        takeScreenshot(named: "inbox")
    }

    @MainActor
    func testCaptureRecording() throws {
        let app = XCUIApplication()
        app.launchArguments = ["--debug-recording"]
        app.launch()

        sleep(4)

        takeScreenshot(named: "recording")
    }

    // 標準機能だけで撮影するヘルパー
    private func takeScreenshot(named name: String) {
        let screenshot = XCUIScreen.main.screenshot()
        let attachment = XCTAttachment(screenshot: screenshot)
        attachment.name = name
        // これが重要！デフォルトは成功時に削除されてしまう
        attachment.lifetime = .keepAlways
        add(attachment)
    }
}

システムアラートへの対応
「マイクの使用を許可しますか？」などのシステムアラートが出ると撮影が止まってしまいます。addUIInterruptionMonitor で自動応答させることでこの問題を回避できます。

参考: Apple公式: Handling UI Interruptions

Step 3: 画像の抽出(Pythonスクリプト)
標準の XCTAttachment を使うと、画像は .xcresult バンドルの中に格納されます。
ここから画像を抽出するPythonスクリプトを書きます。

xcrun xcresulttool コマンドを使うことで、テスト結果バンドルから添付ファイル(スクリーンショット)を取り出すことができます。

# scripts/extract_screenshots.py

import subprocess
import json
import sys
import os

def get_attachment_list(xcresult_path):
    """xcresultからアタッチメントのリストを取得"""
    result = subprocess.run(
        ['xcrun', 'xcresulttool', 'get', '--path', xcresult_path, '--format', 'json'],
        capture_output=True,
        text=True
    )
    return json.loads(result.stdout)

def find_screenshots(data, name_filter):
    """再帰的にスクリーンショットのIDを探す"""
    screenshots = []

    def recurse(obj):
        if isinstance(obj, dict):
            # スクリーンショットの添付を発見
            if obj.get('_type', {}).get('_name') == 'ActionTestAttachment':
                name = obj.get('name', {}).get('_value', '')
                if name_filter in name:
                    attachment_id = obj.get('payloadRef', {}).get('id', {}).get('_value')
                    if attachment_id:
                        screenshots.append((name, attachment_id))

            for value in obj.values():
                recurse(value)
        elif isinstance(obj, list):
            for item in obj:
                recurse(item)

    recurse(data)
    return screenshots

def export_screenshot(xcresult_path, attachment_id, output_path):
    """指定されたIDのスクリーンショットをエクスポート"""
    subprocess.run([
        'xcrun', 'xcresulttool', 'export',
        '--path', xcresult_path,
        '--id', attachment_id,
        '--output-path', output_path,
        '--type', 'file'
    ], check=True)

def main():
    if len(sys.argv) < 3:
        print("Usage: python extract_screenshots.py <xcresult_path> <output_dir>")
        sys.exit(1)

    xcresult_path = sys.argv[1]
    output_dir = sys.argv[2]

    os.makedirs(output_dir, exist_ok=True)

    print(f"📦 Analyzing {xcresult_path}...")
    data = get_attachment_list(xcresult_path)

    # 期待するスクリーンショット名
    expected_names = ["onboarding", "home_empty", "inbox", "recording"]

    for name in expected_names:
        print(f"🔍 Searching for '{name}'...")
        screenshots = find_screenshots(data, name)

        if screenshots:
            # 最初に見つかったものを使用
            found_name, attachment_id = screenshots[0]
            output_path = os.path.join(output_dir, f"{name}.png")
            export_screenshot(xcresult_path, attachment_id, output_path)
            print(f"✅ Exported: {output_path}")
        else:
            print(f"⚠️  Not found: {name}")

if __name__ == "__main__":
    main()

注意: この例では expected_names をハードコードしていますが、実際にはYAML設定ファイル(screenshots.yaml)から画面ID一覧を読み込んで動的に取得します。そうすることで、画面を追加・削除する際にPythonコードを触る必要がなくなります。

xcresulttoolの出力構造
xcresulttool の出力JSONは非常に複雑で、深くネストされた構造になっていますが、再帰的に探索する関数を書くことで、確実に目的の画像を見つけられるようになります。

参考: WWDC 2019: Testing in Xcode

Step 4: 画像加工とフレーム合成(Python + Pillow)
ここが本記事の最大のこだわりポイントです。生のスクリーンショットに、デバイスフレームとキャッチコピーを合成して、App Store提出用の画像に仕上げます。

Pythonの画像処理ライブラリ Pillow (PIL Fork) を使えば、コードだけで完結します。Pillowは画像の読み込み、リサイズ、テキスト描画、合成など、あらゆる画像操作を簡単に実行できる強力なライブラリです。

デバイスフレームの画像は、Apple公式が提供している素材を使用しています。現状は iPhone 17 (6.7インチ) の1サイズのみに対応しています。

Apple Design Resources


今後も、iPhoneやiPadなどの複数のサイズに対応したり、多言語対応や異なるレイアウトを自動生成するようにアップデートしていく予定です。その際はまた改めて記事にします。

レイアウトの考え方
App Storeのスクリーンショットは、iPhone 6.7インチの場合 1290 x 2796 ピクセルです。この縦長のキャンバスに、どうテキストとデバイスフレームを配置するかが重要です。

採用したレイアウト戦略:

上部エリア（0〜1000px）: キャッチコピーとサブタイトル

タイトルのY座標: 200px（上から余白を持たせて配置）
サブタイトルのY座標: タイトルY + 250px（行間を考慮）
X座標: 100px（左余白）
下部エリア（1200〜2796px）: デバイスフレームとスクリーンショット

デバイスのY座標: 1200px（上部テキストと被らない位置）
デバイスのX座標: center（水平方向に中央揃え）
とてもシンプルではありますが、プレビューされた時にまずテキストが目に入り、次にアプリの画面が見えるという視線誘導を実現している鉄板のレイアウトになります。

座標計算の実装例：

# 中央揃えの計算
if device_x == "center":
    screenshot_img = Image.open(screenshot_path)
    device_x = (canvas.width - screenshot_img.width) // 2

YAMLで device_x: center と指定するだけで、スクリプト側が自動的に中央座標を計算するようにしています。デバイスサイズが変わっても、コードの修正は不要です。

設計思想：YAML駆動で変更に強く
デザインの定義はすべてYAMLに外出しします。こうすることで、文言修正や色変更のたびにPythonコードを触る必要がなくなります。デバイスフレームのパスもYAMLで管理することで、新しいデバイスへの対応も設定変更だけで済みます。

# config/screenshots.yaml

global:
  canvas:
    width: 1290
    height: 2796
  device:
    name: "iPhone 17"
    bezel_path: "resources/iphone17_bezel.png"
  colors:
    background: "#F5F5F7"
    text: "#1D1D1F"
    wave: "#E8E8EA"
  fonts:
    title:
      path: "/System/Library/Fonts/ヒラギノ角ゴシック W6.ttc"
      size: 100
    subtitle:
      path: "/System/Library/Fonts/ヒラギノ角ゴシック W3.ttc"
      size: 48

screens:
  - id: "onboarding"
    caption:
      title: "書かずに残す\n声の日記"
      subtitle: "話すだけで想いが残る"
    layout:
      text_x: 100
      text_y: 200
      device_x: center
      device_y: 1200

  - id: "home_empty"
    caption:
      title: "今日の気持ちを\n声で残そう"
      subtitle: "タップして話すだけ"
    layout:
      text_x: 100
      text_y: 200
      device_x: center
      device_y: 1200

  - id: "inbox"
    caption:
      title: "ふたりの距離が\n近くなる"
      subtitle: "離れていても相手の今日がわかる"
    layout:
      text_x: 100
      text_y: 200
      device_x: center
      device_y: 1200

  - id: "recording"
    caption:
      title: "手が離せない時も\n声なら残せる"
      subtitle: "料理中、散歩中、いつでも"
    layout:
      text_x: 100
      text_y: 200
      device_x: center
      device_y: 1200

基本的な加工スクリプト
# scripts/process_screenshots.py

import yaml
from PIL import Image, ImageDraw, ImageFont
import os
import math

def load_config(config_path):
    """YAML設定を読み込む"""
    with open(config_path, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)

def create_canvas(config):
    """キャンバスを作成"""
    width = config['global']['canvas']['width']
    height = config['global']['canvas']['height']
    bg_color = config['global']['colors']['background']

    return Image.new('RGB', (width, height), bg_color)

def draw_text(draw, text, x, y, font_config, color):
    """テキストを描画（複数行対応）"""
    font = ImageFont.truetype(font_config['path'], font_config['size'])
    # Pillowは `\n` を自動的に改行として処理してくれる
    draw.text((x, y), text, font=font, fill=color)

def composite_device_frame(canvas, screenshot_path, bezel_path, x, y):
    """デバイスフレームとスクショを合成"""
    screenshot = Image.open(screenshot_path)
    bezel = Image.open(bezel_path).convert('RGBA')

    # ベゼル画像の「画面部分」の位置を計算
    # Apple Design Resourcesのベゼル画像は、デバイスの外枠を含むため、
    # スクリーンショットをはめ込む位置（オフセット）を調整する必要がある
    #
    # 例: iPhone 17のベゼル画像の場合、画面領域は (60, 60) から始まる
    bezel_offset_x = 60  # ベゼルの左端から画面までの距離
    bezel_offset_y = 60  # ベゼルの上端から画面までの距離

    # スクリーンショットをベゼルにはめ込む
    bezel.paste(screenshot, (bezel_offset_x, bezel_offset_y))

    # 完成したデバイスフレームをキャンバスに配置
    canvas.paste(bezel, (x, y), bezel)

def draw_panoramic_wave(canvas, draw, screen_index, total_screens, config):
    """
    複数スクリーンで繋がる波形を描画
    """
    width = config['global']['canvas']['width']
    height = config['global']['canvas']['height']
    wave_color = config['global']['colors']['wave']

    # 全スクリーンを横に並べた「仮想的な全体座標」を想定
    total_width = total_screens * width
    global_offset = screen_index * width

    # 波のパラメータ
    base_y = height // 3

    # 複数の波を重ねて「声」っぽさを演出
    waves = [
        {'freq': 0.01, 'amp': 80, 'phase': 0},
        {'freq': 0.02, 'amp': 40, 'phase': 1.5},
        {'freq': 0.015, 'amp': 60, 'phase': 3.0},
    ]

    for x in range(width):
        global_x = global_offset + x

        # 複数の sin波を合成
        y_offset = 0
        for wave in waves:
            y_offset += math.sin(global_x * wave['freq'] + wave['phase']) * wave['amp']

        y = int(base_y + y_offset)

        # 波を太くするため、垂直方向に数ピクセル描画
        for dy in range(-3, 4):
            if 0 <= y + dy < height:
                draw.point((x, y + dy), fill=wave_color)

def process_screen(config, screen_config, index, total):
    """1枚のスクリーンショットを加工"""
    print(f"🎨 Processing: {screen_config['id']}")

    canvas = create_canvas(config)
    draw = ImageDraw.Draw(canvas)

    # 背景の装飾（パノラマ背景）
    draw_panoramic_wave(canvas, draw, index, total, config)

    # タイトルとサブタイトルを描画
    layout = screen_config['layout']
    colors = config['global']['colors']
    fonts = config['global']['fonts']

    draw_text(
        draw,
        screen_config['caption']['title'],
        layout['text_x'],
        layout['text_y'],
        fonts['title'],
        colors['text']
    )

    draw_text(
        draw,
        screen_config['caption']['subtitle'],
        layout['text_x'],
        layout['text_y'] + 250,
        fonts['subtitle'],
        colors['text']
    )

    # デバイスとスクショの合成
    screenshot_path = f"raw/{screen_config['id']}.png"
    bezel_path = config['global']['device']['bezel_path']
    device_x = layout['device_x']
    device_y = layout['device_y']

    # "center" なら中央揃え（ベゼルを含めた全体の幅を考慮）
    if device_x == "center":
        bezel_img = Image.open(bezel_path)
        device_x = (canvas.width - bezel_img.width) // 2

    composite_device_frame(canvas, screenshot_path, bezel_path, device_x, device_y)

    # 保存
    output_path = f"processed/{screen_config['id']}.png"
    canvas.save(output_path)
    print(f"✅ Saved: {output_path}")

def main():
    config = load_config('config/screenshots.yaml')
    screens = config['screens']

    os.makedirs('processed', exist_ok=True)

    for i, screen in enumerate(screens):
        process_screen(config, screen, i, len(screens))

if __name__ == "__main__":
    main()

🎨 こだわりポイント1: 数学で描く「パノラマ背景」
アプリストアのスクリーンショットは複数のスクリーンショットを横に並べた時に、背景が自然に繋がる「パノラマ効果」を表現すると最後まで見てもらいやすいです。

今回のアプリは「声」がテーマなので、音波(波形)を背景に描くことにしました。これを画像素材で用意しようとすると、端末サイズごとに調整が必要で大変です。しかし、sin関数を使ってプログラムで描画することで、どんなサイズでも自動対応できるようになります。

パノラマの仕組み
ここでは、複数のスクリーンショットにまたがって連続する波形を描画します。
実装のポイントは以下の3ステップです。

全スクショを横に並べた「仮想的な世界」を想定する
例: 4枚のスクショがあれば、幅は 1290 × 4 = 5160px の仮想空間
各スクショは、その世界の一部を切り取ったもの
1枚目: x = 0〜1290
2枚目: x = 1290〜2580
3枚目: x = 2580〜3870
4枚目: x = 3870〜5160
sin関数の入力に「全体座標のX」を使う
これにより、スクショを並べた時に波が連続する
こうすることで、スクリーンショット1枚目は x=0〜1290、2枚目は x=1290〜2580 の波を描くことになり、並べた時にピタリと繋がります。

# 再掲: パノラマ背景の核心部分

def draw_panoramic_wave(canvas, draw, screen_index, total_screens, config):
    width = config['global']['canvas']['width']

    # このスクリーンの開始位置（全体座標）
    global_offset = screen_index * width

    for x in range(width):
        # 全体座標でのX位置
        global_x = global_offset + x

        # sin関数の入力は「全体座標」
        y = base_y + math.sin(global_x * frequency) * amplitude
        draw.point((x, y), fill=wave_color)

最初は各スクリーンショットで独立して sin(x) を描いていたため、並べた時に波が不連続になってしまっていました。この「全体座標」の考え方を取り入れることで、美しく繋がる背景を実現できました。

ビフォー(不連続):

スクショ1: sin(0), sin(1), ..., sin(1290)
スクショ2: sin(0), sin(1), ..., sin(1290)  ← またゼロから

アフター(連続):

スクショ1: sin(0), sin(1), ..., sin(1290)
スクショ2: sin(1290), sin(1291), ..., sin(2580)  ← 続いている

この実装により、App Storeのスクショプレビューで横スクロールした時、背景が美しく繋がります。

🎨 こだわりポイント2: YAML駆動で変更に強く
個人開発の序盤は、コピーライティングは何度も変更して試行錯誤しますよね。

「"声の日記"より"音声日記"の方がいいかも」
「サブタイトル要らないかも」
「文字色をもう少し濃くしたい」
こういう変更のたびに該当箇所を探してコードを編集するのは手間がかかりますが、YAMLに外出ししておけば気軽に変更できるようになります。

screens:
  - id: "onboarding"
    caption:
      title: "書かずに残す\n声の日記"  # ← ここを変えるだけ
      subtitle: "話すだけで想いが残る"

Step 5: パイプラインの統合(Makefile)
最後に、これらを一つのコマンドで実行できるようにします。Makefile を使って、各ステップを順次実行するタスクを定義します。

# Makefile

generate-store-screenshots:
	# 1. クリーンアップ
	rm -rf docs/screenshots/raw/* docs/screenshots/processed/* docs/screenshots/output.xcresult

	# 2. XCUITestでスクリーンショット撮影
	xcodebuild test \
	  -scheme "YourApp-mock" \
	  -destination 'platform=iOS Simulator,name=iPhone 17' \
	  -only-testing:YourAppUITests/ScreenshotTests \
	  -resultBundlePath docs/screenshots/output.xcresult \
	  -testLanguage ja

	# 3. xcresultから画像を抽出
	python3 docs/screenshots/scripts/extract_screenshots.py \
	  docs/screenshots/output.xcresult \
	  docs/screenshots/raw

	# 4. Pillowで画像を加工
	python3 docs/screenshots/scripts/process_screenshots.py

実行コマンド
make generate-store-screenshots

たったこれだけで、以下が自動実行されます。

既存の画像をクリーンアップ
シミュレータ起動
アプリ起動(モックデータ注入)
画面遷移
スクショ撮影
.xcresultから画像を抽出
フレーム合成・テキスト描画
その様子を眺めながら飲むコーヒーは格別です☕

ハマりポイントと対策
1. 画像の重複アップロード問題
fastlane deliver でApp Store Connectにスクリーンショットをアップロードする際、デフォルトでは既存の画像に追加しようとします。そのため、実行するたびに同じ画像が増えていってしまいます。

対策: overwrite_screenshots: true を指定

# fastlane/Fastfile

lane :screenshots_upload do
  deliver(
    skip_binary_upload: true,
    skip_metadata: true,
    overwrite_screenshots: true  # 既存の画像を上書き
  )
end

このオプションを付けることで、既存のスクリーンショットを削除してから新しいものをアップロードしてくれます。

2. フォントパスの環境依存
YAML設定例では /System/Library/Fonts/... と絶対パスで指定していますが、これはmacOS環境でのみ有効です。

GitHub ActionsなどのCI環境で実行する場合は、以下の対策が必要です：

対策1: リポジトリ内にフォントを含めて相対パス指定

# config/screenshots.yaml
global:
  fonts:
    title:
      path: "resources/fonts/NotoSansCJK-Bold.ttf"  # 相対パス
      size: 100

対策2: CI環境でシステムフォントをインストール

# .github/workflows/screenshots.yml
- name: Install fonts
  run: |
    sudo apt-get update
    sudo apt-get install -y fonts-noto-cjk

macOSのバージョンによってもフォントパスが異なる可能性があるため、相対パス + リポジトリ管理が最も堅牢です。

3. 実行時間の最適化
Fastlane Snapshot + Frameit の組み合わせは機能が豊富な反面、実行に時間がかかります。

今回の構成では：

XCUITest部分: 5-10分（端末数・画面数に依存）
Python加工部分: 数秒〜数十秒（ほぼ一瞬）
Python + Pillowでの画像処理は非常に高速なため、「デザイン変更だけ」なら raw/ に保存済みの画像を使って、加工スクリプトだけ再実行することもできます。

# 撮影済みの画像を使って、加工だけやり直す
python3 docs/screenshots/scripts/process_screenshots.py

これなら数秒で完了します。

おわりに
一度この環境を作ってしまえば、以下が実現できます。

文字サイズ調整でも、コマンド一発で全スクショ更新
デザイン変更も、YAMLを編集するだけ
新端末対応も、設定追加だけで自動生成
コピーライティングの A/Bテストも気軽に
浮いた時間は、ぜひアプリの本質的な機能開発に集中してください！

紹介：音声日記アプリ「KOE」
この記事で解説した自動化システムは、音声日記アプリ「KOE」の開発で実際に運用しています。





プロダクトの特徴

1日3つまで: 制約により、本当に残したい瞬間だけを記録する設計
音声のみ: テキスト入力を排除し、料理中や移動中でも記録できる
リアルタイム共有: パートナーとの非同期コミュニケーションツールとして機能
シンプルなUI: 録音ボタンだけの極限までシンプルな体験
解決している課題
日記を続けられない最大の理由は「入力の手間」。

キーボードを開く、文章を考える、時間を作る... これらすべてを「タップして話すだけ」に変えることで、継続可能な日記体験を実現しています。

特に、パートナーとの距離が離れているときに「今日の出来事」を共有する手段として、LINEやメールよりも気軽で、でも記録として残る絶妙なバランスを目指しました。

今後も開発の裏側や、なぜこの制約を設けたのか、ユーザーからのフィードバックでどう改善してきたかなど、プロダクト開発の試行錯誤についても記事にしていく予定です。