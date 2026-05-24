#!/usr/bin/env bash
# 06-publish.sh — Postiz publish (X + TikTok DRAFT + IG DRAFT + YT DRAFT)
set -euo pipefail

SKILL_DIR="${SKILL_DIR:-$HOME/.openclaw/skills/sao-content-factory}"
source "$SKILL_DIR/lib/postiz.sh"

[ -n "${VERSION_DIR:-}" ] || { echo "VERSION_DIR not set" >&2; exit 2; }
ENTITY_LOCAL="$VERSION_DIR/docs/entity.json"

VIDEO="$VERSION_DIR/output/reel_9x16_en.mp4"
VIDEO_SMALL="$VERSION_DIR/output/reel_9x16_en_small.mp4"
[ -f "$VIDEO" ] || { echo "ERR: video missing: $VIDEO" >&2; exit 3; }

# Upload video to Postiz
echo "  uploading video..." >&2
VIDEO_URL=$(postiz_upload "$VIDEO_SMALL")
VIDEO_ID=$(/opt/homebrew/bin/postiz upload "$VIDEO" 2>&1 | sed -n '/^{/,$p' | jq -r '.id')
[ -z "$VIDEO_URL" ] && { echo "ERR: video upload returned no URL" >&2; exit 4; }

# Build post JSON
THREAD=$(cat "$VERSION_DIR/docs/x_thread.json")
CAPTION=$(cat "$VERSION_DIR/docs/social_caption.txt")
SCHEDULE=$(date -u -v+2M +"%Y-%m-%dT%H:%M:%SZ" 2>/dev/null || date -u -d "+2 minutes" +"%Y-%m-%dT%H:%M:%SZ")

X_INT=$(jq -r '.publish.x_integration' "$ENTITY_LOCAL")
TT_INT=$(jq -r '.publish.tiktok_integration' "$ENTITY_LOCAL")
IG_INT=$(jq -r '.publish.ig_integration' "$ENTITY_LOCAL")
YT_INT=$(jq -r '.publish.yt_integration' "$ENTITY_LOCAL")

# X thread: each tweet object gets the same image array (only first tweet should have video)
X_VALUE=$(echo "$THREAD" | jq --arg url "$VIDEO_URL" --arg id "$VIDEO_ID" \
  'to_entries | map(
    if .key == 0 then
      {content: .value.content, image: [{path: $url, id: $id}]}
    else
      {content: .value.content, image: []}
    end
  )')

POST_JSON="$VERSION_DIR/docs/postiz_post.json"
jq -n \
  --arg date "$SCHEDULE" \
  --arg caption "$CAPTION" \
  --arg url "$VIDEO_URL" \
  --arg id "$VIDEO_ID" \
  --arg x_int "$X_INT" \
  --arg tt_int "$TT_INT" \
  --arg ig_int "$IG_INT" \
  --arg yt_int "$YT_INT" \
  --argjson x_value "$X_VALUE" \
  '{
    type: "schedule",
    date: $date,
    shortLink: true,
    tags: [],
    posts: [
      {
        integration: {id: $x_int},
        value: $x_value,
        settings: {who_can_reply_post: "everyone"}
      },
      {
        integration: {id: $tt_int},
        value: [{
          content: $caption,
          image: [{path: $url, id: $id}]
        }],
        settings: {
          privacy_level: "SELF_ONLY",
          duet: "no",
          stitch: "no",
          comment: "yes",
          brand_content_toggle: false,
          brand_organic_toggle: false,
          autoAddMusic: "no",
          content_posting_method: "DIRECT_POST",
          title: "SAO content",
          isPhoto: false,
          photoCoverIndex: 0
        }
      },
      {
        integration: {id: $ig_int},
        value: [{
          content: $caption,
          image: [{path: $url, id: $id}]
        }],
        settings: {
          post_type: "post",
          collaborators: [],
          thumbnail: null
        }
      },
      {
        integration: {id: $yt_int},
        value: [{
          content: $caption,
          image: [{path: $url, id: $id}]
        }],
        settings: {
          title: "SAO content",
          type: "private",
          thumbnail: null,
          tags: []
        }
      }
    ]
  }' > "$POST_JSON"

# Submit
echo "  submitting to Postiz..." >&2
POST_IDS=$(postiz_post_json "$POST_JSON")
echo "$POST_IDS" > "$VERSION_DIR/docs/postiz_post_ids.txt"

# Andon job application (one-shot)
JOB_ENABLED=$(jq -r '.job_application.enabled // false' "$ENTITY_LOCAL")
JOB_SENT_FLAG="$SKILL_DIR/state/${ENTITY}-job-sent"
if [ "$JOB_ENABLED" = "true" ] && [ ! -f "$JOB_SENT_FLAG" ]; then
  echo "  sending job application {{profile.lateness.stakeholders.channel}}..." >&2
  TO=$(jq -r '.job_application.to' "$ENTITY_LOCAL")
  SUBJECT=$(jq -r '.job_application.subject' "$ENTITY_LOCAL")
  FROM=$(jq -r '.job_application.from_account' "$ENTITY_LOCAL")
  COVER_LETTER="$VERSION_DIR/docs/cover_letter.txt"
  PDF="$VERSION_DIR/docs/cover_letter.pdf"
  # If pre-existing cover letter from manual run dir, copy it
  REF_DIR="$HOME/anicca-project/sao-content-factory/assets/$ENTITY/v1/docs"
  if [ -f "$REF_DIR/{{profile.lateness.stakeholders.channel}}_body.txt" ]; then
    cp "$REF_DIR/{{profile.lateness.stakeholders.channel}}_body.txt" "$COVER_LETTER"
    cp "$REF_DIR/cover_letter_v1.pdf" "$PDF"
  fi
  if [ -f "$COVER_LETTER" ] && [ -f "$PDF" ]; then
    MSG_ID=$(/opt/homebrew/bin/gog --account="$FROM" --json gmail send \
      --to "$TO" --subject "$SUBJECT" \
      --body-file "$COVER_LETTER" \
      --attach "$VIDEO_SMALL" --attach "$PDF" \
      | jq -r '.messageId // empty')
    [ -n "$MSG_ID" ] && echo "$MSG_ID" > "$JOB_SENT_FLAG"
  fi
fi

echo "phase 06 ok (postIds=$(echo $POST_IDS | tr '\n' ' '))"
