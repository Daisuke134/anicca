# Clip marketing loop manifest — the ONLY per-loop config. Engine is SHARED in ../ .
# (Documents clip's config in the same manifest shape as capafy so a new loop = copy + edit.)
#
#   WHO (persona) · WHAT PROBLEM · WHAT you sell (product) · HOW (content adapter)

# ── WHO / WHAT PROBLEM ──
MKT_PERSONA="people scrolling short-form who want the best moments of long videos"
MKT_PROBLEM="long videos are too long; the good 15s is buried"

# ── WHAT you sell (product) ──
MKT_INSTANCE="clip"
MKT_PRODUCT_SOURCE="YouTube source videos (clip pipeline)"
MKT_LISTING_URL_FMT=""                          # clip monetizes via reach/affiliate, not a listing URL
MKT_BIO_LINK=""
MKT_LANDING_SITE_ID=""

# ── HOW (content) ──
MKT_CONTENT_ADAPTER="clip-cut"                   # cut the best moment from a long video
MKT_NICHE="AI / money / wealth"

# ── account / provision (fed to shared provision_prompt.sh) ──
MKT_ACCOUNT_STATE_FILE="$HOME/.cloak/clip-accounts.json"
MKT_HANDLE_PREFIX="aiclips"
MKT_PROFILE_PREFIX="clip-en"
MKT_GMAIL_PLUS_TAG_PREFIX="aiclips"
MKT_BIO_TEXT="one-line AI / money / wealth bio, NO link"

# ── cadence ──
MKT_CADENCE_HOUR="12"
