"""
slop-scan — a $0-to-serve, deterministic AI-slop detection gig API.

The product an AI SELLS via x402 (ag402): POST text → get a slop score + the exact
AI-tell markers + fix hints. Pure heuristics, NO paid LLM call → zero serving cost →
every USDC paid is margin → TRUE self-funded (no human, no captcha, no Dais money).

Run:  uvicorn slop_scan_api:app --host 127.0.0.1 --port 8799
Wrap: ag402 serve --target http://127.0.0.1:8799 --port 8402 --price 0.002 --address <SOLANA_PUBKEY>
Call: POST /scan {"text": "..."}  (behind the ag402 gateway → 402 → pay USDC → 200)
"""
import re
from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI(title="slop-scan", version="1.0")

# Deterministic AI-slop tells (English + a few JP), each (label, compiled regex, weight)
TELLS = [
    ("em_dash_overuse",      re.compile(r"—"),                                              3),
    ("delve",                re.compile(r"\bdelve\b", re.I),                                 6),
    ("tapestry",             re.compile(r"\btapestry\b", re.I),                              6),
    ("realm",                re.compile(r"\bin the realm of\b", re.I),                       5),
    ("landscape",            re.compile(r"\b(navigat\w+|ever.?(evolv|chang)\w+)\b", re.I),   4),
    ("not_just_but",         re.compile(r"\bnot just\b[^.]{0,40}\bbut\b", re.I),             5),
    ("its_not_x_its_y",      re.compile(r"\bit'?s not\b[^.]{0,30}\bit'?s\b", re.I),          6),
    ("moreover_furthermore", re.compile(r"\b(moreover|furthermore|additionally)\b", re.I),   3),
    ("crucial_vital",        re.compile(r"\b(crucial|vital|pivotal|paramount)\b", re.I),     2),
    ("testament",            re.compile(r"\ba testament to\b", re.I),                        5),
    ("game_changer",         re.compile(r"\bgame.?changer\b", re.I),                         4),
    ("unlock_potential",     re.compile(r"\bunlock\w*\b[^.]{0,20}\bpotential\b", re.I),      5),
    ("dive_deep",            re.compile(r"\b(dive deep|deep dive)\b", re.I),                 3),
    ("in_conclusion",        re.compile(r"\bin conclusion\b", re.I),                         3),
    ("rich_history",         re.compile(r"\b(rich (history|culture|tradition))\b", re.I),    3),
    ("when_it_comes_to",     re.compile(r"\bwhen it comes to\b", re.I),                      3),
    ("jp_dash",              re.compile(r"――"),                                             3),
    ("jp_sara_ni",           re.compile(r"さらに|また、"),                                    1),
]

class ScanIn(BaseModel):
    text: str

@app.get("/health")
def health():
    return {"ok": True, "service": "slop-scan", "version": "1.0"}

@app.get("/scan")
def scan_get(text: str = ""):
    return _scan(text)

@app.post("/scan")
def scan(body: ScanIn):
    return _scan(body.text or "")

def _scan(text: str):
    words = max(1, len(re.findall(r"\w+", text)))
    markers = []
    raw = 0
    for label, rx, weight in TELLS:
        hits = rx.findall(text)
        n = len(hits)
        if n:
            raw += n * weight
            markers.append({"tell": label, "count": n, "weight": weight})
    # normalize per 100 words → 0..100 slop score
    density = raw / words * 100
    score = min(100, round(density * 4, 1))
    verdict = ("clean" if score < 8 else "some_tells" if score < 25 else "heavy_ai_slop")
    markers.sort(key=lambda m: -m["count"] * m["weight"])
    return {
        "slop_score": score,           # 0 (human) .. 100 (heavy AI slop)
        "verdict": verdict,
        "word_count": words,
        "markers": markers[:12],
        "fix_hint": "Cut em-dashes, kill flagged buzzwords, vary sentence rhythm, remove rule-of-three + hedging.",
    }
