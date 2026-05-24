#!/usr/bin/env bash
# api_clients.sh — production-ready curl wrappers for civic data APIs.
# Source from mode scripts: source "$SKILL/scripts/lib/api_clients.sh"

# ── load .env ────────────────────────────────────────────────────────────────
_pol_load_env() {
  local envf="${OPENCLAW_ENV:-$HOME/.openclaw/.env}"
  if [[ -f "$envf" ]]; then
    set -a
    # shellcheck disable=SC1090
    source "$envf"
    set +a
  fi
}
_pol_load_env

# ── shared ───────────────────────────────────────────────────────────────────
_pol_ua="anicca-politician/0.1.0 (https://aniccaai.com/politics; {{profile.contact.personalEmail}})"
_pol_dryrun="${POLITICIAN_DRY_RUN:-true}"

# Print the curl invocation only (no execution) when DRY=1.
_pol_curl() {
  local dry="${POL_API_DRY:-0}"
  if [[ "$dry" == "1" ]]; then
    printf '[would-run] curl '
    printf '%q ' "$@"
    printf '\n'
    return 0
  fi
  curl -fsSL --user-agent "$_pol_ua" "$@"
}

# ── regulations.gov v4 ───────────────────────────────────────────────────────
# Docs: https://api.regulations.gov/
# v4 access tightened Aug 2025 — requires real-name registration through api.data.gov.
pol_regulations_search_dockets() {
  local query="${1:-artificial intelligence}"
  local since="${2:-$(date -u -d '7 days ago' +%Y-%m-%dT00:00:00Z 2>/dev/null || date -u -v-7d +%Y-%m-%dT00:00:00Z)}"
  local url="https://api.regulations.gov/v4/dockets?filter[searchTerm]=$(printf '%s' "$query" | jq -sRr @uri)&filter[lastModifiedDate][ge]=${since}&page[size]=25"
  _pol_curl -H "X-Api-Key: ${REGULATIONS_GOV_API_KEY:-MISSING}" "$url"
}
pol_regulations_search_comments() {
  local docket="$1"
  local url="https://api.regulations.gov/v4/comments?filter[docketId]=${docket}&sort=-postedDate&page[size]=25"
  _pol_curl -H "X-Api-Key: ${REGULATIONS_GOV_API_KEY:-MISSING}" "$url"
}

# ── congress.gov v3 ──────────────────────────────────────────────────────────
# Docs: https://api.congress.gov/
pol_congress_search_bills() {
  local query="${1:-artificial intelligence}"
  local congress="${2:-119}"
  local url="https://api.congress.gov/v3/bill/${congress}?api_key=${CONGRESS_GOV_API_KEY:-MISSING}&format=json&limit=25"
  _pol_curl "$url"
}
pol_congress_bill_detail() {
  local congress="$1" bill_type="$2" number="$3"
  local url="https://api.congress.gov/v3/bill/${congress}/${bill_type}/${number}?api_key=${CONGRESS_GOV_API_KEY:-MISSING}&format=json"
  _pol_curl "$url"
}

# ── api.open.fec.gov ─────────────────────────────────────────────────────────
# Docs: https://api.open.fec.gov/developers/
pol_fec_committees_by_terms() {
  local term="${1:-artificial intelligence}"
  local url="https://api.open.fec.gov/v1/names/committees/?q=$(printf '%s' "$term" | jq -sRr @uri)&api_key=${OPENFEC_API_KEY:-DEMO_KEY}"
  _pol_curl "$url"
}
pol_fec_committee_totals() {
  local committee_id="$1"
  local cycle="${2:-2026}"
  local url="https://api.open.fec.gov/v1/committee/${committee_id}/totals/?cycle=${cycle}&api_key=${OPENFEC_API_KEY:-DEMO_KEY}"
  _pol_curl "$url"
}

# ── opensecrets.org ──────────────────────────────────────────────────────────
# Docs: https://www.opensecrets.org/open-data/api-documentation
pol_opensecrets_industry_top() {
  local industry_code="${1:-B12}"  # B12 = TV/Movies/Music; AI typically tracked under B13/B12 mix
  local cycle="${2:-2026}"
  local url="https://www.opensecrets.org/api/?method=industries&id=${industry_code}&cycle=${cycle}&output=json&apikey=${OPENSECRETS_API_KEY:-MISSING}"
  _pol_curl "$url"
}
pol_opensecrets_pac_search() {
  local term="$1"
  # OpenSecrets has no full-text search endpoint; we use the 'getOrgs' method as proxy.
  local url="https://www.opensecrets.org/api/?method=getOrgs&org=$(printf '%s' "$term" | jq -sRr @uri)&output=json&apikey=${OPENSECRETS_API_KEY:-MISSING}"
  _pol_curl "$url"
}

# ── lda.congress.gov (LDA online filing) ─────────────────────────────────────
# No public REST API as of 2026-05. The portal uses session-cookie auth.
# Until an API ships, we render a printable form bundle.
pol_lda_form_url() {
  echo "https://lda.congress.gov/LD/help/Default.htm?Form=LD-2"
}

# ── google news / RSS fallback ───────────────────────────────────────────────
pol_news_rss_ai_policy() {
  # Free fallback: Google News RSS for AI-policy keywords.
  local url='https://news.google.com/rss/search?q=%22AI+policy%22+OR+%22AI+regulation%22+OR+%22AI+legislation%22&hl=en-US&gl=US&ceid=US:en'
  _pol_curl "$url"
}

# ── precondition guards ──────────────────────────────────────────────────────
pol_require_env() {
  local var="$1" fallback_msg="${2:-}"
  if [[ -z "${!var:-}" ]]; then
    echo "[skip: ${var} missing — see SKILL.md bootstrap. ${fallback_msg}]" >&2
    return 1
  fi
  return 0
}
