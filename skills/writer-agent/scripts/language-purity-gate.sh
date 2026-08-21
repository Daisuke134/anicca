#!/usr/bin/env bash
# language-purity-gate.sh — fail-closed QA: block mixed-language artifacts.
# Dais 2026-06-03: 「日本語の記事なのに英語が混ざりすぎていたり、 逆に英語の記事に日本語が混ざっていると不自然」
#                  実 fail 時刻 / タイムスタンプ / ルート構図不明 — こういう ルー語 を block する。
#
# Usage:
#   bash language-purity-gate.sh --markdown-file <f> --lang <ja|en> [--max-ratio 0.10] [--whitelist <file>] [--mode hybrid|char|lingua]
#
# Exit 0 if pure, exit 1 with reason on stderr if mixed.
# Modes (Patch A?-13, spec §8 Round 3):
#   - char (legacy): pure char-ratio heuristic.
#   - lingua:        Lingua-py only (Rust native short-text detector).
#   - hybrid (default): BOTH must vote violation to fail. Lingua catches
#                       ルー語 the ratio misses (e.g. line of mostly katakana that is really English);
#                       char-ratio catches obvious mixed sentences Lingua might be over-confident on.
# Definition (heuristics for char component):
#   - lang=ja → for each line of body text (outside code blocks), the share of ASCII letters
#               (a-zA-Z) over (ASCII letters + CJK chars) must be < max-ratio.
#   - lang=en → for each line, ZERO CJK characters allowed unless on whitelist or inside `code`.
# Hybrid rule (Patch A?-13):
#   - JA line passes if EITHER Lingua says ja OR char-ratio < 0.50.
#   - EN line passes if EITHER Lingua says en OR (cjk count ≤ 5 AND Lingua confidence(en) > 0.85).
#   - Both fail = real ルー語 = block.
set -euo pipefail

MD_FILE=""; LANG=""; MAX_RATIO=0.40; WHITELIST_FILE=""; MODE="hybrid"
while [[ $# -gt 0 ]]; do
  case "$1" in
    --markdown-file) MD_FILE="$2"; shift 2 ;;
    --lang)          LANG="$2"; shift 2 ;;
    --max-ratio)     MAX_RATIO="$2"; shift 2 ;;
    --whitelist)     WHITELIST_FILE="$2"; shift 2 ;;
    --mode)          MODE="$2"; shift 2 ;;
    *) echo "unknown arg: $1" >&2; exit 2 ;;
  esac
done
[[ -f "$MD_FILE" && -n "$LANG" ]] || { echo "FATAL: --markdown-file --lang required" >&2; exit 2; }
case "$MODE" in
  hybrid|char|lingua) ;;
  *) echo "FATAL: --mode must be hybrid|char|lingua (got $MODE)" >&2; exit 2 ;;
esac

# --- DE-SLOP GATE (2026-06-22) — sources: ~/.claude/skills/stop-ai-slop-jp/references/phrases.md + stop-slop ---
# Fail closed on AI-slop phrases + mechanical artifacts (全角ダッシュ, decorative emoji). Body text only
# (skip fenced code blocks via awk). Run on every piece, default-on (not opt-in).
DESLOP_BODY="$(awk 'BEGIN{c=0} /^```/{c=!c; next} !c' "$MD_FILE")"
BANNED_JP='いかがでしたでしょうか|いかがでしたか|ぜひ参考に|近年[^。]{0,8}注目|現代社会において|に他なりません|泥臭|手触り|肌感|解像度|本質的|営み|思考のOS|人生をハック|習慣をインストール|——|――|──'
BANNED_EN="Here's the thing|It turns out|dive deep into|Thanks for reading|in today's [a-z ]*landscape|unlock the power|—"
if [ "$LANG" = "ja" ]; then
  HITS="$(printf '%s\n' "$DESLOP_BODY" | grep -nE "$BANNED_JP" || true)"
elif [ "$LANG" = "en" ]; then
  HITS="$(printf '%s\n' "$DESLOP_BODY" | grep -niE "$BANNED_EN" || true)"
fi
if [ -n "${HITS:-}" ]; then
  echo "de-slop FAILED (lang=$LANG): rewrite these — see stop-ai-slop-jp / stop-slop:" >&2
  printf '%s\n' "$HITS" | head -30 >&2
  exit 1
fi

# Pick venv python for Lingua (falls back to system if unavailable; lingua check skips itself).
SKILL_DIR="${ARTICLE_SKILL_DIR:-${ARTICLE_ROOT:-$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd -P)}}"
LINGUA_PY="${ARTICLE_LINGUA_PY:-$SKILL_DIR/.venv/bin/python}"
[[ -x "$LINGUA_PY" ]] || LINGUA_PY="python3"
export LINGUA_PY

# Default whitelist: brand names, common tech identifiers, URLs.
DEFAULT_WHITELIST=$(cat <<'WL'
Anicca
anicca
aniccaai.com
note.com
substack.com
zenn.dev
dev.to
GitHub
github.com
OpenClaw
openclaw
LLM
LLMs
AI
API
URL
URLs
JSON
SDK
CLI
MCP
Claude
GPT
ChatGPT
Anthropic
OpenAI
Reflexion
Voyager
Hivemind
Postiz
Gmail
Slack
TikTok
YouTube
Instagram
Substack
Note
Zenn
Stripe
RevenueCat
Mac
mini
Tokyo
Opus
Bengt
Betjänt
Andon
Labs
Viggo
Krille
Krafs
Honshōji
Replika
LLaMA
SAO
ALAEW
GPU
CFO
CCO
CTO
ID
SDK
URL
HTML
CSS
URL
Daisuke
Narita
WL
)

WL_PATTERN="$DEFAULT_WHITELIST"
TRACKED_WHITELIST="${ARTICLE_LANGUAGE_WHITELIST:-$SKILL_DIR/reference/language-whitelist.txt}"
if [[ -f "$TRACKED_WHITELIST" ]]; then
  WL_PATTERN+=$'\n'"$(grep -v '^[[:space:]]*#' "$TRACKED_WHITELIST" || true)"
fi
if [[ -n "$WHITELIST_FILE" && -f "$WHITELIST_FILE" ]]; then
  WL_PATTERN+=$'\n'"$(cat "$WHITELIST_FILE")"
fi

CHECK_OUT=$(MD_FILE="$MD_FILE" LANG_TARGET="$LANG" MAX_RATIO="$MAX_RATIO" WL="$WL_PATTERN" MODE="$MODE" "$LINGUA_PY" <<'PY'
import os, re, sys
md = open(os.environ['MD_FILE'], encoding='utf-8').read()
target = os.environ['LANG_TARGET']
max_ratio = float(os.environ['MAX_RATIO'])
mode = os.environ.get('MODE', 'hybrid')
wl = {w.strip() for w in os.environ['WL'].splitlines() if w.strip()}

# Lingua-py: load only if mode != 'char' and library is available.
lingua_detector = None
LANGUAGE_JA = None
LANGUAGE_EN = None
if mode in ('hybrid', 'lingua'):
    try:
        from lingua import Language, LanguageDetectorBuilder
        LANGUAGE_JA = Language.JAPANESE
        LANGUAGE_EN = Language.ENGLISH
        lingua_detector = (LanguageDetectorBuilder
                           .from_languages(LANGUAGE_JA, LANGUAGE_EN)
                           .with_minimum_relative_distance(0.0)
                           .build())
    except Exception as exc:
        if mode == 'lingua':
            print(f'FATAL: --mode lingua requested but lingua-language-detector unavailable: {exc}',
                  file=sys.stderr)
            sys.exit(2)
        lingua_detector = None  # hybrid falls back to char-only when lingua absent

# Strip fenced code blocks (we don't QA code content for language purity)
def strip_fenced(s: str) -> str:
    return re.sub(r'```.*?```', '', s, flags=re.S)

text = strip_fenced(md)
# Strip inline `code` and URLs
text = re.sub(r'`[^`]+`', '', text)
text = re.sub(r'https?://\S+', '', text)
# Strip markdown image/link syntax
text = re.sub(r'!\[[^\]]*\]\([^)]+\)', '', text)
text = re.sub(r'\[[^\]]*\]\([^)]+\)', '', text)

# Frontmatter: drop YAML block
text = re.sub(r'^---\n.*?\n---\n', '', text, flags=re.S, count=1)

violations = []
CJK_RE = re.compile(r'[぀-ヿ㐀-䶿一-鿿豈-﫿ｦ-ﾝ]')
ASCII_LETTER_RE = re.compile(r'[A-Za-z]')

# Hybrid threshold constants (spec §8 Round 3 A?-13)
HYBRID_JA_RATIO_PASS = 0.50      # JA line passes char gate if ratio < 0.50
HYBRID_EN_CJK_MAX    = 5         # EN line passes char gate if cjk count ≤ 5 …
HYBRID_EN_CONF_MIN   = 0.85      #   AND Lingua confidence(en) > 0.85.

def lingua_lang(line):
    if lingua_detector is None:
        return None
    try:
        return lingua_detector.detect_language_of(line)
    except Exception:
        return None

def lingua_conf(line, lang):
    if lingua_detector is None or lang is None:
        return 0.0
    try:
        return float(lingua_detector.compute_language_confidence(line, lang))
    except Exception:
        return 0.0

for lineno, raw_line in enumerate(text.splitlines(), 1):
    line = raw_line.strip()
    if not line: continue
    # Drop whitelist tokens (case-sensitive — they are tech ids)
    redacted = line
    for w in sorted(wl, key=len, reverse=True):
        redacted = redacted.replace(w, ' ')
    cjk = CJK_RE.findall(redacted)
    asc = ASCII_LETTER_RE.findall(redacted)
    n_cjk = len(cjk); n_asc = len(asc)

    if target == 'ja':
        denom = n_cjk + n_asc
        if denom == 0: continue
        ratio = n_asc / denom
        char_fail = (ratio > max_ratio and n_asc >= 2)
        if mode == 'char':
            if char_fail:
                violations.append({'line': lineno, 'kind': 'ja-with-english',
                                   'ratio': round(ratio, 3), 'snippet': line[:120]})
        elif mode == 'lingua':
            lang = lingua_lang(line)
            if lang is not None and lang != LANGUAGE_JA:
                violations.append({'line': lineno, 'kind': 'ja-with-english',
                                   'lingua': str(lang), 'snippet': line[:120]})
        else:  # hybrid: line passes if EITHER lingua=ja OR ratio<0.50
            char_pass = (ratio < HYBRID_JA_RATIO_PASS) or (n_asc < 2)
            lang = lingua_lang(line)
            lingua_pass = (lang is None) or (lang == LANGUAGE_JA)
            if (not char_pass) and (not lingua_pass):
                violations.append({'line': lineno, 'kind': 'ja-with-english',
                                   'ratio': round(ratio, 3),
                                   'lingua': str(lang) if lang else '-',
                                   'snippet': line[:120]})
    else:  # en target
        # Char component: any unwhitelisted CJK outside parens triggers char_fail.
        stripped = re.sub(r'\([^)]*\)', '', line)
        stripped_redact = stripped
        for w in sorted(wl, key=len, reverse=True):
            stripped_redact = stripped_redact.replace(w, ' ')
        real_cjk = CJK_RE.findall(stripped_redact)
        char_fail = (len(real_cjk) > 0)
        if mode == 'char':
            if char_fail:
                violations.append({'line': lineno, 'kind': 'en-with-japanese',
                                   'count': len(real_cjk), 'snippet': line[:120]})
        elif mode == 'lingua':
            lang = lingua_lang(line)
            if lang is not None and lang != LANGUAGE_EN:
                violations.append({'line': lineno, 'kind': 'en-with-japanese',
                                   'lingua': str(lang), 'snippet': line[:120]})
        else:  # hybrid: line passes if EITHER lingua=en OR (cjk ≤ 5 AND lingua_conf(en) > 0.85)
            lang = lingua_lang(line)
            conf_en = lingua_conf(line, LANGUAGE_EN)
            char_pass = (len(real_cjk) <= HYBRID_EN_CJK_MAX) and (conf_en > HYBRID_EN_CONF_MIN)
            lingua_pass = (lang is None) or (lang == LANGUAGE_EN)
            if (not char_pass) and (not lingua_pass):
                violations.append({'line': lineno, 'kind': 'en-with-japanese',
                                   'count': len(real_cjk),
                                   'lingua': str(lang) if lang else '-',
                                   'conf_en': round(conf_en, 3),
                                   'snippet': line[:120]})

if violations:
    print(f'language-purity FAILED: {len(violations)} violation(s) for lang={target} mode={mode}',
          file=sys.stderr)
    for v in violations[:30]:
        print(f"  line {v['line']:>4} ({v['kind']}, "
              f"ratio={v.get('ratio','-')}, cjk={v.get('count','-')}, "
              f"lingua={v.get('lingua','-')}, conf_en={v.get('conf_en','-')})  "
              f"{v['snippet']!r}", file=sys.stderr)
    sys.exit(1)
print(f'language-purity OK (lang={target} mode={mode})')
PY
)
EC=$?
printf '%s\n' "$CHECK_OUT"
exit $EC
