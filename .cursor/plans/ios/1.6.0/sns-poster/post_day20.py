#!/usr/bin/env python3
"""Generate Day 20 image and post to X @aniccaen (English)"""
import requests
from fal_ai import FalAIClient
from blotato import BlotatoClient

def main():
    # Generate image
    fal = FalAIClient()
    
    prompt = """Viral TikTok Instagram carousel slide, 9:16 vertical aspect ratio, pure black background, white text.

Clean minimal to-do list:

"Day 20 of building Anicca
2026/1/22

☑ Growing X, TikTok, IG, YouTube steadily
☑ Iterated masters thesis - final round coming
☑ Added LLM generated nudges
☑ Improved content card loading
☑ Scheduled posts in JP and EN
☑ Improved ASA keywords

Let's keep going."

Modern clean typography, high contrast, monochrome Buddhist minimalism. No color accents, no gradients, only black and white. Text must be perfectly legible and centered."""

    print("🍌 Generating Day 20 image...")
    result = fal.generate_image_nano_banana(prompt, aspect_ratio="9:16")
    
    images = result.get("images", [])
    if not images:
        print(f"❌ Error: {result}")
        return
    
    image_url = images[0].get("url", "")
    print(f"✅ Image URL: {image_url}")
    
    # Save locally
    r = requests.get(image_url)
    with open("day20_anicca.png", "wb") as f:
        f.write(r.content)
    print("✅ Saved to day20_anicca.png")
    
    # Post to X @aniccaen (English)
    caption = """Day 20 of building Anicca to $1k MRR. Still $18. 2026/1/22

✅ Growing X, TikTok, IG, YouTube steadily
✅ Iterated master's thesis - final round coming
✅ Added LLM generated nudges on Anicca
✅ Improved content card loading delay
✅ Scheduled posts in JP and EN
✅ Improved ASA keywords - hope conversion improves

Let's keep going.

#buildinpublic #indiehacker #ios #swiftui #anicca"""

    blotato = BlotatoClient()
    
    # First upload the media
    print("📤 Uploading media...")
    try:
        media_result = blotato.upload_media(image_url)
        uploaded_url = media_result.get("url", image_url)
        print(f"✅ Media uploaded: {uploaded_url}")
    except Exception as e:
        print(f"⚠️ Media upload failed, using original URL: {e}")
        uploaded_url = image_url
    
    print("📤 Posting to X @aniccaen (English)...")
    try:
        result = blotato.post_to_x(caption, media_urls=[uploaded_url], account="x_nudges")
        print("✅ Posted!")
        print(f"Response: {result}")
    except Exception as e:
        print(f"❌ Post failed: {e}")
        # Try without media
        print("📤 Trying without media...")
        result = blotato.post_to_x(caption, media_urls=[], account="x_nudges")
        print("✅ Posted (text only)!")
        print(f"Response: {result}")

if __name__ == "__main__":
    main()

