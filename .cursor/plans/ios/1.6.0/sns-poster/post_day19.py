#!/usr/bin/env python3
"""Post Day 19 to X @xg2grb"""
from blotato import BlotatoClient

def main():
    client = BlotatoClient()

    caption = """Day 19 of building Anicca to $1k MRR. Still $18. 2026/1/21

✅ Submitted v1.1.0 to App Store (learning system + language fix)
✅ Built Thompson Sampling - nudges learn what resonates with YOU
✅ 14 unit tests, E2E tests, GitHub Actions CI - all passing
✅ Decided on full rebrand: SNS = product, not funnel

Let's keep going.

#buildinpublic #indiehacker #ios #swiftui #anicca"""

    image_url = "https://v3b.fal.media/files/b/0a8b640a/yrRIPjOPR4jW-x7Q0Sf5g.png"

    print("📤 Posting to X @xg2grb...")
    result = client.post_to_x(caption, media_urls=[image_url], account="x_xg2grb")
    print("✅ Posted!")
    print(f"Response: {result}")

if __name__ == "__main__":
    main()

