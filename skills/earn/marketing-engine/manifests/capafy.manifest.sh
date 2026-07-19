# Capafy marketing loop manifest — the ONLY per-loop config. The engine (provision / warmer /
# poster / reach / reflect / ledger / telegram / lease) is SHARED in ../ . To launch a new
# marketing loop you copy this file and change the values below — you NEVER touch engine code.
#
# The 4 things you decide (everything else is generalized distribution):
#   WHO (persona) · WHAT PROBLEM · WHAT you sell (product) · HOW (content adapter)

# ── WHO / WHAT PROBLEM ──
MKT_PERSONA="devs & indie hackers who want ready-made Claude skills instead of building from scratch"
MKT_PROBLEM="building/prompt-engineering an AI skill from zero is slow and repetitive"

# ── WHAT you sell (product) ──
MKT_INSTANCE="capafy"
MKT_PRODUCT_SOURCE="capafy seller endpoint GET /agent/agents (agentStatus=online listings)"
MKT_LISTING_URL_FMT="https://capafy.ai/agent/{id}"
MKT_BIO_LINK="https://capafy-skills-daily.netlify.app"
MKT_LANDING_SITE_ID="41c8e52e-b163-442a-84ff-fd866269bf6c"

# ── HOW (content) ──
MKT_CONTENT_ADAPTER="faceless-video"          # faceless-video | slideshow | carousel | clip-cut
MKT_NICHE="AI tools / productivity"

# ── account / provision (fed to shared provision_prompt.sh) ──
MKT_ACCOUNT_STATE_FILE="$HOME/.cloak/clip-accounts-capafy.json"
MKT_HANDLE_PREFIX="capafy"
MKT_PROFILE_PREFIX="capafy-mkt"
MKT_GMAIL_PLUS_TAG_PREFIX="capafy"
MKT_BIO_TEXT="one-line Claude-skills bio, NO link"

# ── cadence ──
MKT_CADENCE_HOUR="16"                          # daily launchd hour (JST)
