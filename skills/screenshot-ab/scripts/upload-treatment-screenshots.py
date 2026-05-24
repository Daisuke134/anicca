#!/usr/bin/env python3
"""
upload-treatment-screenshots.py
Apple API 直接アップロード（asc screenshots upload が Treatment localization に対応しない場合のフォールバック）

Usage:
  python3 upload-treatment-screenshots.py \
    --en-loc EN_LOCALIZATION_ID \
    --ja-loc JA_LOCALIZATION_ID \
    --export-dir /path/to/export
"""

import argparse
import json
import os
import re
import subprocess
import sys
from pathlib import Path

BASE_URL = "https://api.appstoreconnect.apple.com/v1"


def get_token():
    """ASC CLI からトークン取得"""
    result = subprocess.run(["asc", "token"], capture_output=True, text=True)
    if result.returncode != 0:
        print(f"❌ asc token failed: {result.stderr}", file=sys.stderr)
        sys.exit(1)
    return result.stdout.strip()


def headers(token):
    return {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }


def upload_screenshots_for_locale(token, localization_id, locale_dir, device_type="APP_IPHONE_65"):
    """1ロケール分のスクショをアップロード"""
    import requests

    h = headers(token)
    screenshots = sorted(Path(locale_dir).glob("screen*.png"))

    if not screenshots:
        print(f"  ⚠️  No screenshots found in {locale_dir}")
        return

    # 1. screenshotSet 取得 or 作成
    create_payload = {
        "data": {
            "type": "appScreenshotSets",
            "attributes": {"screenshotDisplayType": device_type},
            "relationships": {
                "appStoreVersionExperimentTreatmentLocalization": {
                    "data": {"type": "appStoreVersionExperimentTreatmentLocalizations", "id": localization_id}
                }
            },
        }
    }

    resp = requests.post(f"{BASE_URL}/appScreenshotSets", headers=h, json=create_payload)
    if resp.status_code == 409:
        # Already exists — extract ID from error
        error_detail = resp.json().get("errors", [{}])[0].get("detail", "")
        uuids = re.findall(r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}", error_detail)
        set_id = uuids[-1] if uuids else None
        if not set_id:
            print(f"  ❌ Could not extract screenshot set ID from 409 error")
            return
        print(f"  ♻️  Using existing screenshot set: {set_id}")
    elif resp.status_code in (200, 201):
        set_id = resp.json()["data"]["id"]
        print(f"  ✅ Created screenshot set: {set_id}")
    else:
        print(f"  ❌ Failed to create screenshot set: {resp.status_code} {resp.text}")
        return

    # 2. 既存スクショ全削除
    existing = requests.get(f"{BASE_URL}/appScreenshotSets/{set_id}/appScreenshots", headers=h)
    if existing.status_code == 200:
        for ss in existing.json().get("data", []):
            requests.delete(f"{BASE_URL}/appScreenshots/{ss['id']}", headers=h)
            print(f"  🗑️  Deleted existing screenshot: {ss['id']}")

    # 3. 新スクショアップロード
    for path in screenshots:
        file_size = path.stat().st_size
        file_name = path.name

        # Reserve
        reserve_payload = {
            "data": {
                "type": "appScreenshots",
                "attributes": {"fileName": file_name, "fileSize": file_size},
                "relationships": {
                    "appScreenshotSet": {"data": {"type": "appScreenshotSets", "id": set_id}}
                },
            }
        }
        reserve_resp = requests.post(f"{BASE_URL}/appScreenshots", headers=h, json=reserve_payload)
        if reserve_resp.status_code not in (200, 201):
            print(f"  ❌ Reserve failed for {file_name}: {reserve_resp.status_code} {reserve_resp.text}")
            continue

        screenshot_id = reserve_resp.json()["data"]["id"]
        upload_ops = reserve_resp.json()["data"]["attributes"].get("uploadOperations", [])

        # PUT binary
        for op in upload_ops:
            upload_headers = {h_item["name"]: h_item["value"] for h_item in op.get("requestHeaders", [])}
            with open(path, "rb") as f:
                f.seek(op.get("offset", 0))
                chunk = f.read(op.get("length", file_size))
            requests.put(op["url"], headers=upload_headers, data=chunk)

        # Commit
        import hashlib
        checksum = hashlib.md5(path.read_bytes()).hexdigest()
        commit_payload = {
            "data": {
                "type": "appScreenshots",
                "id": screenshot_id,
                "attributes": {"uploaded": True, "sourceFileChecksum": checksum},
            }
        }
        commit_resp = requests.patch(
            f"{BASE_URL}/appScreenshots/{screenshot_id}", headers=h, json=commit_payload
        )
        if commit_resp.status_code == 200:
            print(f"  ✅ Uploaded: {file_name}")
        else:
            print(f"  ❌ Commit failed for {file_name}: {commit_resp.status_code}")


def main():
    parser = argparse.ArgumentParser(description="Upload treatment screenshots via Apple API")
    parser.add_argument("--en-loc", required=True, help="EN treatment localization ID")
    parser.add_argument("--ja-loc", required=True, help="JA treatment localization ID")
    parser.add_argument("--export-dir", required=True, help="Path to export directory")
    args = parser.parse_args()

    token = get_token()

    print("📸 Uploading EN screenshots...")
    upload_screenshots_for_locale(token, args.en_loc, os.path.join(args.export_dir, "en"))

    print("📸 Uploading JA screenshots...")
    upload_screenshots_for_locale(token, args.ja_loc, os.path.join(args.export_dir, "ja"))

    print("\n✅ Upload complete")


if __name__ == "__main__":
    main()
