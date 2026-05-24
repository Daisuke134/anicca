#!/usr/bin/env node
/**
 * mau-tiktok: Trim hooks to 3s + stitch with CTA v7 video
 * Usage: node trim-and-stitch.js --lang en --count 1
 *
 * MUST use filter_complex concat (NOT -f concat -c copy — causes 11s instead of 9s)
 */

const { execSync } = require("child_process");
const fs = require("fs");
const path = require("path");

const WORKSPACE = path.join(
  process.env.HOME,
  ".openclaw/workspace/mau-tiktok"
);

function ensureDirs(lang) {
  fs.mkdirSync(path.join(WORKSPACE, "hooks/trimmed", lang), { recursive: true });
  fs.mkdirSync(path.join(WORKSPACE, "output", lang), { recursive: true });
}

function getUntrimmedHooks(lang) {
  const rawDir = path.join(WORKSPACE, "hooks/raw", lang);
  const trimmedDir = path.join(WORKSPACE, "hooks/trimmed", lang);

  if (!fs.existsSync(rawDir)) return [];

  const raw = fs.readdirSync(rawDir).filter((f) => f.endsWith(".mp4"));
  const trimmed = fs.existsSync(trimmedDir)
    ? new Set(fs.readdirSync(trimmedDir).filter((f) => f.endsWith(".mp4")))
    : new Set();

  return raw.filter((f) => !trimmed.has(f));
}

function trimHook(filename, lang) {
  const input = path.join(WORKSPACE, "hooks/raw", lang, filename);
  const output = path.join(WORKSPACE, "hooks/trimmed", lang, filename);

  const cmd = `ffmpeg -i "${input}" -t 3 -vf "scale=1080:1920:force_original_aspect_ratio=decrease,pad=1080:1920:(ow-iw)/2:(oh-ih)/2" -c:v libx264 -preset fast -crf 23 -c:a aac -b:a 128k -ar 44100 -y "${output}"`;

  try {
    execSync(cmd, { encoding: "utf-8", timeout: 60000, stdio: "pipe" });
    console.log(`[TRIM] ${filename} → 3s @ 1080x1920`);
    return true;
  } catch (err) {
    console.error(`[ERR] Trim failed for ${filename}:`, err.message);
    return false;
  }
}

function stitchVideo(hookFile, lang, index) {
  const hookPath = path.join(WORKSPACE, "hooks/trimmed", lang, hookFile);
  const ctaPath = path.join(WORKSPACE, `cta_${lang}_final.mp4`);
  const outputPath = path.join(
    WORKSPACE,
    "output",
    lang,
    `mau_${lang}_${Date.now()}_${index}.mp4`
  );

  if (!fs.existsSync(ctaPath)) {
    console.error(`[ERR] CTA file not found: ${ctaPath}`);
    return null;
  }

  // MUST: filter_complex concat with re-encode (NOT -f concat -c copy)
  const cmd = `ffmpeg -i "${hookPath}" -i "${ctaPath}" -filter_complex "[0:v][0:a][1:v][1:a]concat=n=2:v=1:a=1[outv][outa]" -map "[outv]" -map "[outa]" -c:v libx264 -preset fast -crf 18 -pix_fmt yuv420p -c:a aac -b:a 192k -y "${outputPath}"`;

  try {
    execSync(cmd, { encoding: "utf-8", timeout: 120000, stdio: "pipe" });
    console.log(`[STITCH] ${hookFile} + CTA → ${path.basename(outputPath)}`);
    return outputPath;
  } catch (err) {
    console.error(`[ERR] Stitch failed:`, err.message);
    return null;
  }
}

function main() {
  const args = process.argv.slice(2);
  const langIdx = args.indexOf("--lang");
  const lang = langIdx >= 0 ? args[langIdx + 1] : "en";
  const countIdx = args.indexOf("--count");
  const count = countIdx >= 0 ? parseInt(args[countIdx + 1], 10) : 1;

  ensureDirs(lang);

  // Step 1: Trim all untrimmed hooks for this lang
  const untrimmed = getUntrimmedHooks(lang);
  console.log(`[INFO] ${untrimmed.length} hooks to trim (${lang})`);
  for (const f of untrimmed) {
    trimHook(f, lang);
  }

  // Step 2: Stitch trimmed hooks with CTA
  const trimmedDir = path.join(WORKSPACE, "hooks/trimmed", lang);
  const trimmedFiles = fs.existsSync(trimmedDir)
    ? fs.readdirSync(trimmedDir).filter((f) => f.endsWith(".mp4")).slice(-count)
    : [];

  console.log(`\n[INFO] Stitching ${trimmedFiles.length} videos (${lang})`);
  const outputs = [];
  for (let i = 0; i < trimmedFiles.length; i++) {
    const result = stitchVideo(trimmedFiles[i], lang, i);
    if (result) outputs.push(result);
  }

  console.log(`\n=== Done: ${outputs.length} videos created ===`);
  outputs.forEach((o) => console.log(`  → ${o}`));
  return outputs;
}

if (require.main === module) {
  main();
}

module.exports = { main };
