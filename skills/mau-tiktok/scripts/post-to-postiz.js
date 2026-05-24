#!/usr/bin/env node
/**
 * mau-tiktok: Post stitched videos to Postiz API
 * Usage: node post-to-postiz.js --lang en|ja
 *
 * Reads config.json for integration IDs, .env for POSTIZ_API_KEY.
 * Policy:
 * - EN: TikTok + Instagram + YouTube
 * - JA: TikTok + Instagram + YouTube (when configured)
 */

const { execSync } = require("child_process");
const fs = require("fs");
const path = require("path");

const WORKSPACE = path.join(process.env.HOME, ".openclaw/workspace/mau-tiktok");
const CONFIG_FILE = path.join(WORKSPACE, "config.json");
const LOG_FILE = path.join(WORKSPACE, "post-log.json");

function loadApiKey() {
  const config = JSON.parse(fs.readFileSync(CONFIG_FILE, "utf-8"));
  const envFile = config.postiz.env_file.replace("~", process.env.HOME);
  const envContent = fs.readFileSync(envFile, "utf-8");
  const match = envContent.match(/POSTIZ_API_KEY=(.+)/);
  if (!match) {
    console.error("[ERR] POSTIZ_API_KEY not found in .env");
    process.exit(1);
  }
  return match[1].trim();
}

function loadConfig() {
  return JSON.parse(fs.readFileSync(CONFIG_FILE, "utf-8"));
}

function getLatestVideo(lang) {
  const outputDir = path.join(WORKSPACE, "output", lang);
  if (!fs.existsSync(outputDir)) return null;

  const files = fs
    .readdirSync(outputDir)
    .filter((f) => f.endsWith(".mp4"))
    .map((f) => ({
      name: f,
      path: path.join(outputDir, f),
      mtime: fs.statSync(path.join(outputDir, f)).mtimeMs,
    }))
    .sort((a, b) => b.mtime - a.mtime);

  return files.length > 0 ? files[0] : null;
}

function uploadMedia(filePath, apiKey, mimeType) {
  console.log(`[UPLOAD] ${path.basename(filePath)}`);
  const cmd = `curl -s -X POST "https://api.postiz.com/public/v1/upload" -H "Authorization: ${apiKey}" -F "file=@${filePath};filename=${path.basename(filePath)};type=${mimeType}"`;
  try {
    const response = execSync(cmd, { encoding: "utf-8", timeout: 60000 });
    const data = JSON.parse(response);
    if (!data.id || !data.path) {
      console.error("[ERR] Upload returned unexpected payload:", response.substring(0, 300));
      return null;
    }
    console.log(`[UPLOAD] OK — id: ${data.id}`);
    return { id: data.id, path: data.path };
  } catch (err) {
    console.error("[ERR] Upload failed:", err.message);
    return null;
  }
}

function uploadThumbnail(lang, apiKey) {
  const thumbPath = path.join(WORKSPACE, `cta_thumbnail_${lang}.jpg`);
  if (!fs.existsSync(thumbPath)) {
    console.log(`[THUMB] No thumbnail found at ${thumbPath}, skipping`);
    return null;
  }
  return uploadMedia(thumbPath, apiKey, "image/jpeg");
}

function makeVideoValue(videoId, videoPath, caption) {
  return [
    {
      content: caption,
      image: [{ id: videoId, path: videoPath }],
    },
  ];
}

function postToTikTok(integrationId, videoId, videoPath, caption, title, apiKey) {
  console.log(`[POST] TikTok → ${integrationId}`);
  const body = {
    type: "now",
    date: new Date().toISOString(),
    shortLink: false,
    tags: [],
    posts: [
      {
        integration: { id: integrationId },
        value: makeVideoValue(videoId, videoPath, caption),
        settings: {
          __type: "tiktok",
          type: "direct",
          title,
          privacy_level: "PUBLIC_TO_EVERYONE",
          duet: true,
          stitch: true,
          comment: true,
          autoAddMusic: "no",
          brand_content_toggle: false,
          brand_organic_toggle: false,
          video_made_with_ai: false,
          content_posting_method: "DIRECT_POST",
        },
      },
    ],
  };
  return callPostiz(body, apiKey, "TikTok");
}

function postToInstagram(integrationId, videoId, videoPath, caption, apiKey) {
  console.log(`[POST] Instagram → ${integrationId}`);
  const body = {
    type: "now",
    date: new Date().toISOString(),
    shortLink: false,
    tags: [],
    posts: [
      {
        integration: { id: integrationId },
        value: makeVideoValue(videoId, videoPath, caption),
        settings: {
          __type: "instagram-standalone",
          post_type: "post",
          type: "now",
          tags: [],
        },
      },
    ],
  };
  return callPostiz(body, apiKey, "Instagram");
}

function postToYouTube(integrationId, videoId, videoPath, caption, title, apiKey, thumbnail) {
  console.log(`[POST] YouTube → ${integrationId}`);
  const settings = {
    __type: "youtube",
    title,
    selfDeclaredMadeForKids: "no",
    type: "public",
  };
  if (thumbnail) settings.thumbnail = thumbnail;

  const body = {
    type: "now",
    date: new Date().toISOString(),
    shortLink: false,
    tags: [],
    posts: [
      {
        integration: { id: integrationId },
        value: makeVideoValue(videoId, videoPath, caption),
        settings,
      },
    ],
  };
  return callPostiz(body, apiKey, "YouTube");
}

function callPostiz(body, apiKey, platform) {
  const tmpFile = path.join(WORKSPACE, `_tmp_post_${platform}.json`);
  fs.writeFileSync(tmpFile, JSON.stringify(body));
  try {
    const cmd = `curl -s -X POST "https://api.postiz.com/public/v1/posts" -H "Authorization: ${apiKey}" -H "Content-Type: application/json" -d @${tmpFile}`;
    const response = execSync(cmd, { encoding: "utf-8", timeout: 30000 });
    fs.unlinkSync(tmpFile);
    try {
      const data = JSON.parse(response);
      if (Array.isArray(data) && data.length > 0 && data[0].postId) {
        console.log(`[POST] ${platform} OK — post id: ${data[0].postId}`);
        return { success: true, id: data[0].postId };
      }
      if (data.id) {
        console.log(`[POST] ${platform} OK — post id: ${data.id}`);
        return { success: true, id: data.id };
      }
      if (data.message || data.error || data.statusCode) {
        const msg = JSON.stringify(data).substring(0, 500);
        console.error(`[POST] ${platform} error payload: ${msg}`);
        return { success: false, error: msg };
      }
      console.error(`[POST] ${platform} response:`, response.substring(0, 300));
      return { success: false, error: response.substring(0, 300) };
    } catch {
      console.error(`[POST] ${platform} non-JSON response:`, response.substring(0, 300));
      return { success: false, error: response.substring(0, 300) };
    }
  } catch (err) {
    if (fs.existsSync(tmpFile)) fs.unlinkSync(tmpFile);
    console.error(`[ERR] ${platform} post failed:`, err.message);
    return { success: false, error: err.message };
  }
}

function appendLog(entry) {
  let log = [];
  if (fs.existsSync(LOG_FILE)) {
    try {
      log = JSON.parse(fs.readFileSync(LOG_FILE, "utf-8"));
    } catch {
      log = [];
    }
  }
  log.push(entry);
  fs.writeFileSync(LOG_FILE, JSON.stringify(log, null, 2));
}

function main() {
  const args = process.argv.slice(2);
  const langIdx = args.indexOf("--lang");
  const lang = langIdx >= 0 ? args[langIdx + 1] : null;

  if (!lang) {
    console.error("[ERR] --lang is required (en or ja)");
    process.exit(1);
  }

  const apiKey = loadApiKey();
  const config = loadConfig();
  const integrations = config.integrations[lang];
  const caption = config.captions[lang];
  const title = (config.titles && config.titles[lang]) || caption.substring(0, 85);

  if (!integrations) {
    console.error(`[ERR] No integrations found for lang: ${lang}`);
    process.exit(1);
  }

  const video = getLatestVideo(lang);
  if (!video) {
    console.error(`[ERR] No videos found in output/${lang}/`);
    process.exit(1);
  }

  console.log(`\n=== Posting: ${video.name} (${lang}) ===\n`);

  const uploaded = uploadMedia(video.path, apiKey, "video/mp4");
  if (!uploaded) {
    console.error("[ERR] Upload failed, aborting");
    process.exit(1);
  }

  const results = {};
  const thumbnail = uploadThumbnail(lang, apiKey);

  // Dais 2026-05-22: mau-tiktok posts ONLY to YouTube (limited accounts).
  // NO TikTok, NO Instagram — those platforms are intentionally skipped here.
  if (integrations.youtube && integrations.youtube.id) {
    results.youtube = postToYouTube(integrations.youtube.id, uploaded.id, uploaded.path, caption, title, apiKey, thumbnail);
  } else {
    console.error("[ERR] mau-tiktok is YouTube-only but no youtube integration configured");
  }

  const logEntry = {
    timestamp: new Date().toISOString(),
    lang,
    video: video.name,
    results,
  };
  appendLog(logEntry);

  const successCount = Object.values(results).filter((r) => r && r.success).length;
  const totalCount = Object.keys(results).length;
  console.log(`\n=== Done: ${successCount}/${totalCount} platforms posted ===`);

  if (totalCount === 0) {
    console.error("[ERR] No platform integrations configured");
    process.exit(1);
  }

  if (successCount === 0) {
    process.exit(1);
  }
}

if (require.main === module) {
  main();
}

module.exports = { main };
