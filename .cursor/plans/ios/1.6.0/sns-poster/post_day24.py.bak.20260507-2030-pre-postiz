#!/usr/bin/env python3
from fal_ai import FalAIClient
import requests
from config import BLOTATO_API_KEY, BLOTATO_BASE_URL

client = FalAIClient()
headers = {'blotato-api-key': BLOTATO_API_KEY, 'Content-Type': 'application/json'}

# English image
print("Generating English image...")
prompt_en = """Viral TikTok slide, 9:16 vertical, black bg, white text.

Day 24 of building Anicca
2026/1/26
MRR: $18

☐ Removed ATT approval screen
☐ Anicca decides daily nudge plan
☐ Infers surrounding problems → nudges
☐ Localized: ES, FR, DE, PT

#buildinpublic

Modern clean typography, high contrast, monochrome."""

result_en = client.generate_image_nano_banana(prompt_en, aspect_ratio='9:16')
en_url = result_en.get('images', [{}])[0].get('url', '')
print(f'EN_URL: {en_url}')

# Japanese image
print("Generating Japanese image...")
prompt_jp = """Viral TikTok slide, 9:16 vertical, black bg, white text.

Anicca開発24日目
2026/1/26
MRR: $18

☐ ATT許可画面を削除
☐ Aniccaが1日のナッジを決定
☐ 周辺の問題を推測→ナッジ
☐ スペイン語/仏語/独語/葡語対応

#buildinpublic

Modern clean typography, high contrast, monochrome."""

result_jp = client.generate_image_nano_banana(prompt_jp, aspect_ratio='9:16')
jp_url = result_jp.get('images', [{}])[0].get('url', '')
print(f'JP_URL: {jp_url}')

# Post English
print("\nPosting English...")
en_caption = """1/26. Day 24 of building Anicca to 1k MRR. Still $18.

☐ Removed ATT approval screen
☐ Anicca decides the daily nudge plan
☐ Infers surrounding problems → gives nudges
☐ Localized in Spanish, French, German, Portuguese

#buildinpublic #ai"""

resp_en = requests.post(f'{BLOTATO_BASE_URL}/posts', headers=headers, json={
    'post': {
        'accountId': '11852',
        'content': {'text': en_caption, 'mediaUrls': [en_url], 'platform': 'twitter'},
        'target': {'targetType': 'twitter'}
    }
})
print(f'EN Status: {resp_en.status_code}')
print(f'EN Response: {resp_en.text}')

# Post Japanese
print("Posting Japanese...")
jp_caption = """1/26。Anicca開発24日目。MRR $18。

☐ ATT許可画面を削除
☐ Aniccaが1日のナッジプランを決定
☐ 周辺の問題を推測→ナッジ
☐ スペイン語/仏語/独語/葡語対応

#buildinpublic #ai #個人開発"""

resp_jp = requests.post(f'{BLOTATO_BASE_URL}/posts', headers=headers, json={
    'post': {
        'accountId': '11820',
        'content': {'text': jp_caption, 'mediaUrls': [jp_url], 'platform': 'twitter'},
        'target': {'targetType': 'twitter'}
    }
})
print(f'JP Status: {resp_jp.status_code}')
print(f'JP Response: {resp_jp.text}')

print("\n=== DONE ===")
print(f"EN Image: {en_url}")
print(f"JP Image: {jp_url}")

