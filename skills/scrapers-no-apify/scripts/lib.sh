#!/usr/bin/env bash
# scrapers-no-apify lib — source this in your script to use fallback scrapers.

scrape_tt_profile() {
  local handle="${1:?handle required}"
  agent-{{profile.lateness.stakeholders.channel}} open "https://www.tiktok.com/@${handle}" 2>/dev/null >&2
  sleep 2
  local result
  result=$(agent-{{profile.lateness.stakeholders.channel}} eval 'JSON.stringify({
    handle: "'"$handle"'",
    followers: document.querySelector("[data-e2e=followers-count]")?.textContent || null,
    following: document.querySelector("[data-e2e=following-count]")?.textContent || null,
    likes: document.querySelector("[data-e2e=likes-count]")?.textContent || null,
    bio: document.querySelector("[data-e2e=user-bio]")?.textContent || null,
    title: document.title
  })' 2>/dev/null)
  agent-{{profile.lateness.stakeholders.channel}} close >/dev/null 2>&1
  if echo "$result" | grep -q "見つかりません\|not found\|not_found"; then
    echo '{"error":"not_found"}'
    return 1
  fi
  echo "${result#\"}" | sed 's/\\"/"/g; s/"$//' | sed 's/^"\|"$//g'
}

scrape_ig_profile() {
  local handle="${1:?handle required}"
  agent-{{profile.lateness.stakeholders.channel}} open "https://www.instagram.com/${handle}" 2>/dev/null >&2
  sleep 2
  local result
  result=$(agent-{{profile.lateness.stakeholders.channel}} eval 'JSON.stringify({
    handle: "'"$handle"'",
    title: document.title,
    metaDesc: document.querySelector("meta[property=\"og:description\"]")?.content || null,
    followers: (document.body.innerText.match(/(\d[\d.,]*[KMB]?)\s+[Ff]ollowers/) || [])[1]
  })' 2>/dev/null)
  agent-{{profile.lateness.stakeholders.channel}} close >/dev/null 2>&1
  echo "${result#\"}" | sed 's/\\"/"/g; s/"$//' | sed 's/^"\|"$//g'
}

scrape_yt_channel() {
  local url="${1:?url required}"
  yt-dlp --skip-download --no-warnings --print '{"channel":%(channel)j,"followers":%(channel_follower_count)j,"video":%(title)j,"views":%(view_count)j}' "$url" 2>/dev/null | head -1
}

download_tt_video() {
  local url="${1:?tiktok URL required}"
  local out_dir="${2:-/tmp}"
  echo "▶ downloading via snaptik.app..." >&2
  agent-{{profile.lateness.stakeholders.channel}} open "https://snaptik.app/en2" 2>/dev/null >&2
  sleep 2
  agent-{{profile.lateness.stakeholders.channel}} fill 'input[name=url]' "$url" 2>/dev/null >&2 || \
    agent-{{profile.lateness.stakeholders.channel}} fill 'input[type=text]' "$url" 2>/dev/null >&2
  agent-{{profile.lateness.stakeholders.channel}} click 'button:contains("Get"), button[type=submit]' 2>/dev/null >&2
  sleep 5
  echo "  manual download required: agent-{{profile.lateness.stakeholders.channel}} screenshot $out_dir/snaptik.png to capture URL" >&2
  agent-{{profile.lateness.stakeholders.channel}} close >/dev/null 2>&1
}
