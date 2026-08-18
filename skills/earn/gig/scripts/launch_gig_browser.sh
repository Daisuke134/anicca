#!/usr/bin/env bash
# Launch the one persistent CloakBrowser process owned by the Gig control plane.
set -euo pipefail

export PATH="/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin:$PATH"
GIG_BROWSER_PORT="${GIG_BROWSER_PORT:-9223}"
GIG_BROWSER_PROFILE="${GIG_BROWSER_PROFILE:-$HOME/.cloak/profiles/gig-daily-driver}"
GIG_BROWSER_FINGERPRINT="${GIG_BROWSER_FINGERPRINT:-80136}"

case "$GIG_BROWSER_PORT" in ''|*[!0-9]*) exit 64 ;; esac
mkdir -p "$GIG_BROWSER_PROFILE"
chromium_bin="$(
  ls -d "$HOME"/.cloakbrowser/chromium-*/Chromium.app/Contents/MacOS/Chromium \
    2>/dev/null | sort -V | tail -1
)"
[ -x "$chromium_bin" ] || {
  echo "Gig CloakBrowser binary not found" >&2
  exit 69
}

# Chromium 145 offers ML-KEM by default.  The current local network path drops
# its larger TLS ClientHello: curl reaches Coconala, while Chromium establishes
# TCP and then returns ERR_TIMED_OUT.  Chromium's supported temporary policy is
# the vendor-prescribed compatibility switch through version 146:
# https://chromeenterprise.google/policies/#PostQuantumKeyAgreementEnabled
#
# Keep this bounded to the two installed/supported majors.  A later Chromium
# must be re-qualified instead of silently carrying a removed policy forever.
#
# CloakBrowser ships 150+ now, so a machine installing today lands outside that
# range and used to get no switch and not a word about it -- the worst shape this
# failure has, because the symptom is a browser that completes TCP and then times
# out while curl on the same box is fine, with nothing pointing at the cause.
# Say it instead, and still launch: plenty of networks never drop the larger
# ClientHello, and refusing to start would break them for a risk they do not have.
# GIG_BROWSER_TLS_COMPAT=force applies it once someone has qualified a newer major.
apply_tls_compat() {
  /usr/bin/defaults write \
    org.chromium.Chromium PostQuantumKeyAgreementEnabled -bool false
  [ "$(/usr/bin/defaults read \
    org.chromium.Chromium PostQuantumKeyAgreementEnabled)" = "0" ]
}

chromium_version="${chromium_bin#"$HOME/.cloakbrowser/chromium-"}"
chromium_major="${chromium_version%%.*}"
case "${GIG_BROWSER_TLS_COMPAT:-auto}:$chromium_major" in
  auto:145|auto:146|force:*)
    apply_tls_compat || {
      echo "Gig CloakBrowser TLS compatibility policy was not persisted" >&2
      exit 78
    }
    ;;
  *)
    echo "Gig CloakBrowser: Chromium $chromium_major is outside the qualified 145-146 range," \
         "so the ML-KEM compatibility switch was NOT applied. If the site loads under curl but" \
         "this browser times out, that is why -- relaunch with GIG_BROWSER_TLS_COMPAT=force." >&2
    ;;
esac

exec "$chromium_bin" \
  --no-first-run \
  --no-default-browser-check \
  --password-store=basic \
  --use-mock-keychain \
  --disable-sync \
  --no-sandbox \
  --fingerprint="$GIG_BROWSER_FINGERPRINT" \
  --fingerprint-platform=macos \
  --remote-debugging-address=127.0.0.1 \
  --remote-allow-origins='*' \
  --remote-debugging-port="$GIG_BROWSER_PORT" \
  --user-data-dir="$GIG_BROWSER_PROFILE" \
  about:blank
