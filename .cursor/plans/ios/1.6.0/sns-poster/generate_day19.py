#!/usr/bin/env python3
"""Generate Day 19 Build in Public image"""
import requests
from fal_ai import FalAIClient

def main():
    client = FalAIClient()
    
    prompt = """Viral TikTok Instagram carousel slide, 9:16 vertical aspect ratio, pure black background, white text.

Clean minimal to-do list:

"Day 19 of building Anicca
2026/1/21

☑ Submitted v1.1.0 to App Store
☑ Built Thompson Sampling for nudges
☑ 14 unit tests + CI - all passing
☑ Full social media rebrand decided

Let's keep going."

Modern clean typography, high contrast, monochrome Buddhist minimalism. No color accents, no gradients, only black and white. Text must be perfectly legible and centered."""

    print("🍌 Generating Day 19 image with Nano Banana Pro...")
    result = client.generate_image_nano_banana(prompt, aspect_ratio="9:16")
    
    images = result.get("images", [])
    if images:
        url = images[0].get("url", "")
        print(f"✅ Image URL: {url}")
        
        # Download the image
        r = requests.get(url)
        with open("day19_anicca.png", "wb") as f:
            f.write(r.content)
        print("✅ Saved to day19_anicca.png")
        return url
    else:
        print(f"❌ Error: {result}")
        return None

if __name__ == "__main__":
    main()

