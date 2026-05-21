# docs/screenshots/scripts/extract_screenshots.py
# l.md Bible Step 3: xcresulttool で .xcresult から画像抽出
# Xcode 26対応: xcresulttool get test-results activities API使用
# Usage: python3 scripts/extract_screenshots.py <xcresult_path> <output_dir>

import subprocess
import json
import sys
import os
import yaml


def get_activities(xcresult_path, test_id):
    """test-results activities APIでattachmentsを取得"""
    result = subprocess.run(
        ['xcrun', 'xcresulttool', 'get', 'test-results', 'activities',
         '--path', xcresult_path, '--test-id', test_id, '--format', 'json'],
        capture_output=True, text=True
    )
    if result.stdout:
        return json.loads(result.stdout)
    return {}


def find_attachments_in_activities(data, name_filter):
    """activitiesからname_filterにマッチするattachmentを探す"""
    results = []

    def recurse(obj):
        if isinstance(obj, dict):
            if 'attachments' in obj:
                for att in obj['attachments']:
                    name = att.get('name', '')
                    pid = att.get('payloadId', '')
                    if name_filter in name and pid:
                        results.append((name, pid))
            for v in obj.values():
                recurse(v)
        elif isinstance(obj, list):
            for item in obj:
                recurse(item)

    recurse(data)
    return results


def export_screenshot(xcresult_path, payload_id, output_path):
    """payloadIdでPNGをexport（Xcode 26: export object --legacy）"""
    subprocess.run([
        'xcrun', 'xcresulttool', 'export', 'object', '--legacy',
        '--path', xcresult_path,
        '--id', payload_id,
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

    # YAML駆動: screenshots.yaml の screens[].id から取得
    config_path = os.path.join(os.path.dirname(__file__), '..', 'config', 'screenshots.yaml')
    with open(config_path, 'r', encoding='utf-8') as f:
        config = yaml.safe_load(f)
    expected_names = [s['id'] for s in config['screens']]

    for name in expected_names:
        print(f"🔍 Searching for '{name}'...")
        # ScreenshotTests/testCaptureScreen1() の形式に変換
        method = 'testCapture' + name[0].upper() + name[1:]
        test_id = f"ScreenshotTests/{method}()"
        activities = get_activities(xcresult_path, test_id)
        matches = find_attachments_in_activities(activities, name)
        if matches:
            found_name, payload_id = matches[0]
            output_path = os.path.join(output_dir, f"{name}.png")
            export_screenshot(xcresult_path, payload_id, output_path)
            print(f"✅ Exported: {output_path}")
        else:
            print(f"⚠️  Not found: {name} (test_id: {test_id})")


if __name__ == "__main__":
    main()
