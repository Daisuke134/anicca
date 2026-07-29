"""test_ytdlp_parse.py — RED (Phase 2a, feature claude-p-loop-verification).
PROP-LV-003 / REQ-LV-012 (video) + REQ-LV-014 (affiliate, reuses this SAME function, no duplicate
implementation). parse_ytdlp_json(json_text) -> {view_count:int|None, like_count:int|None}. Pure
string/dict parsing only — NEVER fabricates a value; malformed/missing -> None, never a crash.

Shared home (skills/_shared/lib/) because both video (REQ-LV-012/013, this repo) and affiliate
(REQ-LV-014, the former private implementation) call the identical function per spec's "重複実装しない".

ytdlp_parse.py does not exist yet -> ImportError -> RED.
"""
import sys, os, json
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(__file__)), "lib"))
from ytdlp_parse import parse_ytdlp_json  # RED: does not exist yet

P = 0
F = 0


def chk(name, got, want):
    global P, F
    if got == want:
        print(f"  ok {name} ({got})")
        P += 1
    else:
        print(f"  FAIL {name} want={want} got={got}")
        F += 1


# normal case: full yt-dlp --dump-json output has view_count and like_count
normal = json.dumps({"id": "123", "view_count": 45210, "like_count": 890, "title": "clip"})
chk("normal JSON -> view_count extracted", parse_ytdlp_json(normal), {"view_count": 45210, "like_count": 890})

# view_count present, like_count missing (yt-dlp sometimes omits likes for some extractors)
no_likes = json.dumps({"id": "123", "view_count": 100})
chk("view_count only -> like_count is None (not fabricated)", parse_ytdlp_json(no_likes), {"view_count": 100, "like_count": None})

# view_count missing entirely -> None, must not crash
no_views = json.dumps({"id": "123", "like_count": 5})
chk("view_count missing -> None (not crash, not 0)", parse_ytdlp_json(no_views), {"view_count": None, "like_count": 5})

# both missing
neither = json.dumps({"id": "123"})
chk("both missing -> both None", parse_ytdlp_json(neither), {"view_count": None, "like_count": None})

# malformed JSON string -> must not raise, returns the None-shaped dict
chk("malformed JSON string -> both None, no exception", parse_ytdlp_json("{not valid json!!!"), {"view_count": None, "like_count": None})

# empty string
chk("empty string -> both None", parse_ytdlp_json(""), {"view_count": None, "like_count": None})

# view_count present as a string (defensive — yt-dlp always emits int, but don't crash on drift)
weird_type = json.dumps({"view_count": "not-a-number"})
result = parse_ytdlp_json(weird_type)
chk("view_count wrong type -> None (not a crash, not a fabricated int)", result["view_count"], None)

print(f"=== test_ytdlp_parse: {P} passed {F} failed ===")
sys.exit(0 if F == 0 else 1)
