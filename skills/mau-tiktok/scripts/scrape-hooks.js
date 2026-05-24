#!/usr/bin/env node
/**
 * mau-tiktok: Scrape viral YouTube Shorts hooks
 * Usage: node scrape-hooks.js --lang en --count 1
 */

const { execSync } = require("child_process");
const fs = require("fs");
const path = require("path");

const WORKSPACE = path.join(
  process.env.HOME,
  ".openclaw/workspace/mau-tiktok"
);
const USED_FILE = path.join(WORKSPACE, "used_hooks.json");
const CREATORS_FILE = path.join(WORKSPACE, "creators.json");

function ensureDirs(lang) {
  fs.mkdirSync(path.join(WORKSPACE, "hooks/raw", lang), { recursive: true });
}

function loadUsed() {
  if (!fs.existsSync(USED_FILE)) return { used: [] };
  return JSON.parse(fs.readFileSync(USED_FILE, "utf-8"));
}

function saveUsed(data) {
  fs.writeFileSync(USED_FILE, JSON.stringify(data, null, 2));
}

function loadCreators() {
  return JSON.parse(fs.readFileSync(CREATORS_FILE, "utf-8"));
}

function scrapeCreator(creatorUrl, creatorName, count, usedIds, lang) {
  const downloaded = [];
  const rawDir = path.join(WORKSPACE, "hooks/raw", lang);

  try {
    const listCmd = `yt-dlp --flat-playlist --print id --print title "${creatorUrl}" --playlist-end 50`;
    const output = execSync(listCmd, { encoding: "utf-8", timeout: 60000 });
    const lines = output.trim().split("\n");

    const videos = [];
    for (let i = 0; i < lines.length - 1; i += 2) {
      videos.push({ id: lines[i].trim(), title: lines[i + 1]?.trim() || "" });
    }

    let downloadCount = 0;
    for (const video of videos) {
      if (downloadCount >= count) break;
      if (usedIds.includes(video.id)) {
        console.log(`[SKIP] Already used: ${video.id} — ${video.title}`);
        continue;
      }

      const safeName = creatorName.replace(/[^a-zA-Z0-9]/g, "");
      const outPath = path.join(rawDir, `${safeName}_${video.id}.mp4`);
      try {
        console.log(`[DL] ${video.id} — ${video.title}`);
        execSync(
          `yt-dlp -f "bestvideo[height<=1920]+bestaudio/best[height<=1920]" --merge-output-format mp4 -o "${outPath}" "https://www.youtube.com/shorts/${video.id}"`,
          { encoding: "utf-8", timeout: 120000 }
        );
        downloaded.push({ id: video.id, file: path.basename(outPath) });
        downloadCount++;
      } catch (dlErr) {
        console.error(`[ERR] Failed to download ${video.id}:`, dlErr.message);
      }
    }
  } catch (err) {
    console.error(`[ERR] Failed to list videos from ${creatorUrl}:`, err.message);
  }

  return downloaded;
}

function main() {
  const args = process.argv.slice(2);
  const countIdx = args.indexOf("--count");
  const count = countIdx >= 0 ? parseInt(args[countIdx + 1], 10) : 1;
  const langIdx = args.indexOf("--lang");
  const lang = langIdx >= 0 ? args[langIdx + 1] : null;

  if (!lang) {
    console.error("[ERR] --lang is required (en or ja)");
    process.exit(1);
  }

  ensureDirs(lang);

  const { creators } = loadCreators();
  const usedData = loadUsed();

  const filtered = creators.filter((c) => c.lang === lang);

  if (filtered.length === 0) {
    console.log(`[ERR] No creators found for lang: ${lang}`);
    process.exit(1);
  }

  const allDownloaded = [];

  for (const creator of filtered) {
    console.log(`\n=== Scraping: ${creator.name} (${creator.url}) [${creator.lang}] ===`);
    const results = scrapeCreator(creator.url, creator.name, count, usedData.used, lang);
    allDownloaded.push(...results);
  }

  // Update used hooks
  usedData.used.push(...allDownloaded.map((d) => d.id));
  saveUsed(usedData);

  console.log(`\n=== Done: Downloaded ${allDownloaded.length} new hooks ===`);
  allDownloaded.forEach((d) => console.log(`  → ${d.file}`));
  return allDownloaded;
}

if (require.main === module) {
  main();
}

module.exports = { main };
