#!/usr/bin/env python3
"""
build_config.py — parse a LISTING.md (+ icon + edit_url) into the JSON config that
drive_cp1.py consumes. Reads everything from the LISTING so publish_one.sh stays generic.

Usage: build_config.py <LISTING.md> <icon_path> <edit_url> [out.json]
LISTING.md must contain:
  header line with "Primary Model: <model>" and "category: <cat> ... tags: a, b, c"
  a pricing table:  | cycle | price | cap | trial |  rows (trial = "No Free Trial" or "<N>h")
  ## Title / ## shortDescription / ## welcomeMessage / ## detailedDescription
test_input is extracted from the welcomeMessage "Example:" line.
"""
import json, re, sys


def main():
    listing, icon, edit_url = sys.argv[1], sys.argv[2], sys.argv[3]
    out = sys.argv[4] if len(sys.argv) > 4 else None
    L = open(listing, encoding="utf-8").read()

    title = re.search(r"## Title\n(.+)", L).group(1).strip()
    short = re.search(r"## shortDescription\n(.+?)\n## welcomeMessage", L, re.S).group(1).strip()
    welcome = re.search(r"## welcomeMessage\n(.+?)\n## detailedDescription", L, re.S).group(1).strip()
    detailed = re.split(r"\n## detailedDescription[^\n]*\n", L)[-1].strip()

    model_m = re.search(r"Primary Model:\s*([^·\n]+)", L)
    model = model_m.group(1).strip() if model_m else "Claude Sonnet 4.6"
    cat_m = re.search(r"category:\s*([^\(·\n]+)", L)
    category = cat_m.group(1).strip() if cat_m else "ライティング"
    tags_m = re.search(r"tags:\s*([^\n]+)", L)
    tags = [t.strip() for t in tags_m.group(1).split(",")][:3] if tags_m else []

    # pricing table rows
    plans = []
    for row in re.findall(r"\|\s*(day|week|month)\s*\|\s*\$?([0-9.]+)\s*\|\s*([0-9]+)\s*\|\s*([^|]+)\|", L, re.I):
        cyc, price, cap, trial = row
        tnum = re.search(r"(\d+)", trial)
        plans.append({"cycle": cyc.lower(), "price": price, "cap": cap,
                      "trial": int(tnum.group(1)) if tnum else None})
    if not plans:
        print("ERROR: no pricing rows parsed from LISTING", file=sys.stderr); sys.exit(2)

    ex = re.search(r'Example:\s*"?([^"\n]+)"?', welcome)
    test_input = ex.group(1).strip() if ex else "test input"

    cfg = {
        "edit_url": edit_url, "title": title, "short": short, "welcome": welcome,
        "detailed": detailed, "privacy_url": "https://aniccaai.com/privacy",
        "support_email": "contact@aniccaai.com", "tags": tags, "category": category,
        "icon": icon, "model": model, "provider": "openrouter.ai",
        "test_input": test_input, "plans": plans,
    }
    js = json.dumps(cfg, ensure_ascii=False)
    if out:
        open(out, "w", encoding="utf-8").write(js)
        print(f"config → {out} | title={len(title)} short={len(short)} plans={len(plans)} cat={category} model={model}")
    else:
        print(js)


if __name__ == "__main__":
    main()
