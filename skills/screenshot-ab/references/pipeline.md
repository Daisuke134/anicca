# Pipeline — l.md Bible 全パッチ

ソース: l.md（KOE app） / 核心の引用: 「make generate-store-screenshots — たったこれだけで、シミュレータ起動→撮影→抽出→フレーム合成→完成」

---

## Makefile（l.md Step 5 完全版）

```makefile
# Makefile — l.md Bible 100%
# Set these in your .env or override: make generate-store-screenshots PROJECT=YourApp BUNDLE_ID=com.your.app
PROJECT     ?= YourApp
SCHEME      ?= YourApp
BUNDLE_ID   ?= com.your.app
SIMULATOR   ?= iPhone 16
TEST_TARGET ?= $(PROJECT)UITests/ScreenshotTests

generate-store-screenshots:
	# 1. クリーンアップ
	rm -rf docs/screenshots/raw/* docs/screenshots/processed/* docs/screenshots/output.xcresult
	mkdir -p docs/screenshots/raw docs/screenshots/processed

	# 2. XCUITestでスクリーンショット撮影 → output.xcresult（l.md Step2）
	xcodebuild test \
	  -project $(PROJECT)/$(PROJECT).xcodeproj \
	  -scheme $(SCHEME) \
	  -destination 'platform=iOS Simulator,name=$(SIMULATOR)' \
	  -only-testing:$(TEST_TARGET) \
	  -resultBundlePath docs/screenshots/output.xcresult \
	  -testLanguage ja

	# 3. xcresultから画像抽出（l.md Step3）
	python3 docs/screenshots/scripts/extract_screenshots.py \
	  docs/screenshots/output.xcresult \
	  docs/screenshots/raw

	# 4. PIL合成（l.md Step4）
	cd docs/screenshots && python3 scripts/process_screenshots.py

# デザイン変更のみ再実行（raw/ 撮影済み → 数秒で完了）
process-only:
	cd docs/screenshots && python3 scripts/process_screenshots.py
```

---

## screenshots.yaml（完全版 — 毎回これを正として使う）

```yaml
# docs/screenshots/config/screenshots.yaml
# l.md Bible 100% — YAML駆動設計
# ヘッドラインを変えたい → caption.title だけ編集して make generate-store-screenshots

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
  - id: "screen1"
    caption:
      title: "HEADLINE_SCREEN1"
      subtitle: "SUBTITLE_SCREEN1"
    layout:
      text_x: 100
      text_y: 200
      device_x: center
      device_y: 1200

  - id: "screen2"
    caption:
      title: "HEADLINE_SCREEN2"
      subtitle: "SUBTITLE_SCREEN2"
    layout:
      text_x: 100
      text_y: 200
      device_x: center
      device_y: 1200

  - id: "screen3"
    caption:
      title: "HEADLINE_SCREEN3"
      subtitle: "SUBTITLE_SCREEN3"
    layout:
      text_x: 100
      text_y: 200
      device_x: center
      device_y: 1200
```

---

## extract_screenshots.py（l.md Step 3 完全版）

`docs/screenshots/scripts/extract_screenshots.py` に配置:

```python
# docs/screenshots/scripts/extract_screenshots.py
# l.md Bible Step 3: xcresulttool で .xcresult から画像抽出
# Usage: python3 scripts/extract_screenshots.py <xcresult_path> <output_dir>

import subprocess
import json
import sys
import os
import yaml


def get_attachment_list(xcresult_path):
    result = subprocess.run(
        ['xcrun', 'xcresulttool', 'get', '--path', xcresult_path, '--format', 'json'],
        capture_output=True, text=True
    )
    return json.loads(result.stdout)


def find_screenshots(data, name_filter):
    screenshots = []

    def recurse(obj):
        if isinstance(obj, dict):
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

    # YAML駆動: screenshots.yaml の screens[].id から動的に取得
    config_path = os.path.join(os.path.dirname(__file__), '..', 'config', 'screenshots.yaml')
    with open(config_path, 'r', encoding='utf-8') as f:
        config = yaml.safe_load(f)
    expected_names = [s['id'] for s in config['screens']]

    for name in expected_names:
        print(f"🔍 Searching for '{name}'...")
        screenshots = find_screenshots(data, name)
        if screenshots:
            found_name, attachment_id = screenshots[0]
            output_path = os.path.join(output_dir, f"{name}.png")
            export_screenshot(xcresult_path, attachment_id, output_path)
            print(f"✅ Exported: {output_path}")
        else:
            print(f"⚠️  Not found: {name}")


if __name__ == "__main__":
    main()
```

---

## process_screenshots.py（l.md Step 4 完全版）

`docs/screenshots/scripts/process_screenshots.py` に配置:

```python
# docs/screenshots/scripts/process_screenshots.py
# l.md Bible Step 4: PIL でフレーム合成・テキスト描画
# Run from docs/screenshots/: python3 scripts/process_screenshots.py

import yaml
from PIL import Image, ImageDraw, ImageFont
import os
import math


def load_config(config_path):
    with open(config_path, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)


def create_canvas(config):
    width = config['global']['canvas']['width']
    height = config['global']['canvas']['height']
    bg_color = config['global']['colors']['background']
    return Image.new('RGB', (width, height), bg_color)


def draw_text(draw, text, x, y, font_config, color):
    font = ImageFont.truetype(font_config['path'], font_config['size'])
    draw.text((x, y), text, font=font, fill=color)


def composite_device_frame(canvas, screenshot_path, bezel_path, x, y):
    screenshot = Image.open(screenshot_path)
    bezel = Image.open(bezel_path).convert('RGBA')
    bezel_offset_x = 60
    bezel_offset_y = 60
    bezel.paste(screenshot, (bezel_offset_x, bezel_offset_y))
    canvas.paste(bezel, (x, y), bezel)


def draw_panoramic_wave(canvas, draw, screen_index, total_screens, config):
    """複数スクリーンで繋がる波形（l.md パノラマ背景）"""
    width = config['global']['canvas']['width']
    height = config['global']['canvas']['height']
    wave_color = config['global']['colors']['wave']
    global_offset = screen_index * width
    base_y = height // 3
    waves = [
        {'freq': 0.01, 'amp': 80, 'phase': 0},
        {'freq': 0.02, 'amp': 40, 'phase': 1.5},
        {'freq': 0.015, 'amp': 60, 'phase': 3.0},
    ]
    for x in range(width):
        global_x = global_offset + x
        y_offset = sum(math.sin(global_x * w['freq'] + w['phase']) * w['amp'] for w in waves)
        y = int(base_y + y_offset)
        for dy in range(-3, 4):
            if 0 <= y + dy < height:
                draw.point((x, y + dy), fill=wave_color)


def process_screen(config, screen_config, index, total):
    print(f"🎨 Processing: {screen_config['id']}")
    canvas = create_canvas(config)
    draw = ImageDraw.Draw(canvas)
    draw_panoramic_wave(canvas, draw, index, total, config)
    layout = screen_config['layout']
    colors = config['global']['colors']
    fonts = config['global']['fonts']
    draw_text(draw, screen_config['caption']['title'], layout['text_x'], layout['text_y'], fonts['title'], colors['text'])
    draw_text(draw, screen_config['caption']['subtitle'], layout['text_x'], layout['text_y'] + 250, fonts['subtitle'], colors['text'])
    screenshot_path = f"raw/{screen_config['id']}.png"
    bezel_path = config['global']['device']['bezel_path']
    device_x = layout['device_x']
    device_y = layout['device_y']
    if os.path.exists(screenshot_path) and os.path.exists(bezel_path):
        if device_x == "center":
            bezel_img = Image.open(bezel_path)
            device_x = (canvas.width - bezel_img.width) // 2
        composite_device_frame(canvas, screenshot_path, bezel_path, device_x, device_y)
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
```
