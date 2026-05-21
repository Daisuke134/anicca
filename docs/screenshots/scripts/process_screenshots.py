# docs/screenshots/scripts/process_screenshots.py
# l.md Bible 100% — PIL でフレーム合成・テキスト描画
# Run from docs/screenshots/: python3 scripts/process_screenshots.py
# Or via Makefile: make generate-store-screenshots

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
    draw.text((x, y), text, font=font, fill=color)


def composite_device_frame(canvas, screenshot_path, bezel_path, x, y):
    """デバイスフレームとスクショを合成"""
    screenshot = Image.open(screenshot_path)
    bezel = Image.open(bezel_path).convert('RGBA')

    bezel_offset_x = 60
    bezel_offset_y = 60

    bezel.paste(screenshot, (bezel_offset_x, bezel_offset_y))
    canvas.paste(bezel, (x, y), bezel)


def draw_panoramic_wave(canvas, draw, screen_index, total_screens, config):
    """複数スクリーンで繋がる波形を描画"""
    width = config['global']['canvas']['width']
    height = config['global']['canvas']['height']
    wave_color = config['global']['colors']['wave']

    total_width = total_screens * width
    global_offset = screen_index * width

    base_y = height // 3

    waves = [
        {'freq': 0.01, 'amp': 80, 'phase': 0},
        {'freq': 0.02, 'amp': 40, 'phase': 1.5},
        {'freq': 0.015, 'amp': 60, 'phase': 3.0},
    ]

    for x in range(width):
        global_x = global_offset + x

        y_offset = 0
        for wave in waves:
            y_offset += math.sin(global_x * wave['freq'] + wave['phase']) * wave['amp']

        y = int(base_y + y_offset)

        for dy in range(-3, 4):
            if 0 <= y + dy < height:
                draw.point((x, y + dy), fill=wave_color)


def process_screen(config, screen_config, index, total):
    """1枚のスクリーンショットを加工"""
    print(f"🎨 Processing: {screen_config['id']}")

    canvas = create_canvas(config)
    draw = ImageDraw.Draw(canvas)

    draw_panoramic_wave(canvas, draw, index, total, config)

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

    screenshot_path = f"raw/{screen_config['id']}.png"
    bezel_path = config['global']['device']['bezel_path']
    device_x = layout['device_x']
    device_y = layout['device_y']

    if os.path.exists(screenshot_path) and os.path.exists(bezel_path):
        if device_x == "center":
            bezel_img = Image.open(bezel_path)
            device_x = (canvas.width - bezel_img.width) // 2

        composite_device_frame(canvas, screenshot_path, bezel_path, device_x, device_y)
    else:
        if not os.path.exists(screenshot_path):
            print(f"⚠️  raw/{screen_config['id']}.png not found — skipping device composite")
        if not os.path.exists(bezel_path):
            print(f"⚠️  {bezel_path} not found — download from Apple Design Resources")

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
