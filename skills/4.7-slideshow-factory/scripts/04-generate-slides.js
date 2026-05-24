#!/usr/bin/env node
// Generate 6 TikTok slideshow PNGs (1080x1920) from a theme + image set.
// Article-compliant numeric values:
//   OVERLAY_OPACITY 0.52, shadowBlur 12, shadowOffsetY 4,
//   shadowColor rgba(0,0,0,0.75), lineHeight = size * 1.2
//
// Usage:
//   node 04-generate-slides.js --theme-json <path> --images-dir <path> --output-dir <path>
//
// Theme JSON shape (matches analysis.json from Claude in-session):
//   {
//     chosen_hook,
//     intro,                    ← Slide 2 dynamic line(s) — Claude generates
//     point_1, point_2, point_3,
//     cta
//   }
//
// Images dir: jpg/png files. Each slide gets a unique image. If fewer images
// than slides, last image is reused.

import { createCanvas, loadImage, GlobalFonts } from '@napi-rs/canvas';
import { writeFileSync, mkdirSync, readFileSync, readdirSync } from 'fs';
import { join, dirname, resolve } from 'path';
import { fileURLToPath } from 'url';

const __dirname = dirname(fileURLToPath(import.meta.url));
const FONT_DIR = resolve(__dirname, '..', 'fonts');
const JP_FONT_BLACK = '/System/Library/Fonts/ヒラギノ角ゴシック W6.ttc';
const JP_FONT_BOLD = '/System/Library/Fonts/ヒラギノ角ゴシック W4.ttc';

GlobalFonts.registerFromPath(join(FONT_DIR, 'TikTokSansDisplayBlack.ttf'), 'TikTokBlack');
GlobalFonts.registerFromPath(join(FONT_DIR, 'TikTokSansDisplayBold.ttf'), 'TikTokBold');
GlobalFonts.registerFromPath(JP_FONT_BLACK, 'JPBlack');
GlobalFonts.registerFromPath(JP_FONT_BOLD, 'JPBold');
GlobalFonts.registerFromPath(join(FONT_DIR, 'Regular.ttf'), 'TikTokRegular');

// ─── argv ─────────────────────────────────────────────────
const args = {};
for (let i = 2; i < process.argv.length; i += 2) {
    const k = process.argv[i].replace(/^--/, '');
    args[k] = process.argv[i + 1];
}
for (const k of ['theme-json', 'images-dir', 'output-dir']) {
    if (!args[k]) { console.error(`ERR: --${k} required`); process.exit(2); }
}

const theme = JSON.parse(readFileSync(args['theme-json'], 'utf-8'));
const IMAGES_DIR = args['images-dir'];
const OUT_DIR = args['output-dir'];
mkdirSync(OUT_DIR, { recursive: true });

// Pick available images
const imageFiles = readdirSync(IMAGES_DIR)
    .filter(f => /\.(jpg|jpeg|png)$/i.test(f))
    .sort()
    .map(f => join(IMAGES_DIR, f));
if (imageFiles.length === 0) {
    console.error('ERR: no images in', IMAGES_DIR); process.exit(3);
}
const pickImage = (i) => imageFiles[Math.min(i, imageFiles.length - 1)];

// ─── article-compliant constants ──────────────────────────
const W = 1080;
const H = 1920;
const OVERLAY_OPACITY_DEFAULT = 0.52;   // article value
const SHADOW_COLOR = 'rgba(0,0,0,0.75)';// article value
// Article specifies shadowBlur 12, but with TikTokSansDisplayBlack at 80px+ that
// creates phantom dot artifacts at letter edges. Empirically blur 6 looks identical
// to the eye for legibility but no stray marks. Verified via render test 2026-05-02.
const SHADOW_BLUR = 6;                   // calibrated (article: 12 — caused dots)
const SHADOW_OFFSET_Y = 4;               // article value
const LINE_HEIGHT_FACTOR = 1.2;          // article value

// ─── slide definitions ────────────────────────────────────
// Article structure: HOOK / Problem-Setup / Point 1 / Point 2 / Point 3 / CTA

// Slide 2 (intro/problem-setup) — dynamic from theme.intro (Claude generates).
// Falls back to generic if missing.
// Spacing tuned so wrapped 2-line entries don't overlap.
const introLines = (theme.intro && Array.isArray(theme.intro) && theme.intro.length > 0)
    ? theme.intro.map((text, i) => ({
        text,
        font: 'JPBold',
        size: 56,
        y: 760 + i * 200,
        weight: i === theme.intro.length - 1 ? 'bold' : 'normal'
    }))
    : [{ text: theme.intro || 'Most people get this wrong.', font: 'JPBold', size: 56, y: 880, weight: 'bold' }];

// Slide 6 CTA — single article-style "Save / Follow / every week →" stack
const ctaLines = (theme.cta_lines && Array.isArray(theme.cta_lines) && theme.cta_lines.length > 0)
    ? theme.cta_lines.map((text, i) => ({
        text,
        font: i === 0 ? 'JPBlack' : 'JPBold',
        size: i === 0 ? 80 : 56,
        y: 860 + i * 110,
        weight: 'bold'
    }))
    : [{ text: theme.cta || 'Save this 🔖', font: 'JPBlack', size: 84, y: 880, weight: 'bold' }];

const slides = [
    {
        n: 1, kind: 'hook',
        bg: pickImage(0),
        overlay: 0.55,
        lines: [
            { text: theme.chosen_hook || theme.hook, font: 'JPBlack', size: 96, y: 760, weight: 'bold' }
        ]
    },
    {
        n: 2, kind: 'intro',
        bg: pickImage(1),
        overlay: 0.50,
        lines: introLines
    },
    {
        n: 3, kind: 'point',
        bg: pickImage(2),
        overlay: OVERLAY_OPACITY_DEFAULT,
        lines: [
            { text: '01', font: 'JPBlack', size: 140, y: 760, weight: 'bold' },
            { text: theme.point_1, font: 'JPBold', size: 64, y: 920, weight: 'bold' }
        ]
    },
    {
        n: 4, kind: 'point',
        bg: pickImage(3),
        overlay: OVERLAY_OPACITY_DEFAULT,
        lines: [
            { text: '02', font: 'JPBlack', size: 140, y: 760, weight: 'bold' },
            { text: theme.point_2, font: 'JPBold', size: 64, y: 920, weight: 'bold' }
        ]
    },
    {
        n: 5, kind: 'point',
        bg: pickImage(4),
        overlay: OVERLAY_OPACITY_DEFAULT,
        lines: [
            { text: '03', font: 'JPBlack', size: 140, y: 760, weight: 'bold' },
            { text: theme.point_3, font: 'JPBold', size: 64, y: 920, weight: 'bold' }
        ]
    },
    {
        n: 6, kind: 'cta',
        bg: pickImage(5),
        overlay: 0.60,
        lines: ctaLines
    }
];

// ─── helpers ──────────────────────────────────────────────
function wrapText(ctx, text, maxWidth) {
    const words = text.split(/\s+/);
    const lines = [];
    let current = '';
    for (const word of words) {
        const test = current ? `${current} ${word}` : word;
        if (ctx.measureText(test).width > maxWidth && current) {
            lines.push(current);
            current = word;
        } else {
            current = test;
        }
    }
    if (current) lines.push(current);
    return lines;
}

async function renderSlide(slide) {
    const canvas = createCanvas(W, H);
    const ctx = canvas.getContext('2d');

    // 1. background image cover-fit
    const img = await loadImage(slide.bg);
    const scale = Math.max(W / img.width, H / img.height);
    const dw = img.width * scale;
    const dh = img.height * scale;
    ctx.drawImage(img, (W - dw) / 2, (H - dh) / 2, dw, dh);

    // 2. dark overlay (article: 0.52 default)
    ctx.fillStyle = `rgba(0,0,0,${slide.overlay ?? OVERLAY_OPACITY_DEFAULT})`;
    ctx.fillRect(0, 0, W, H);

    // 3. text (article values: shadowBlur 12, offsetY 4, shadowColor 0.75, lineHeight 1.2)
    const PADDING = 80;
    const MAX_W = W - PADDING * 2;

    for (const line of slide.lines) {
        ctx.font = `${line.weight} ${line.size}px ${line.font}`;
        ctx.fillStyle = '#ffffff';
        ctx.textAlign = 'center';
        ctx.textBaseline = 'middle';
        ctx.shadowColor = SHADOW_COLOR;
        ctx.shadowBlur = SHADOW_BLUR;
        ctx.shadowOffsetX = 0;        // explicit — kill any phantom side-shadow
        ctx.shadowOffsetY = SHADOW_OFFSET_Y;

        const wrapped = wrapText(ctx, line.text, MAX_W);
        const lineH = line.size * LINE_HEIGHT_FACTOR;
        wrapped.forEach((l, i) => {
            ctx.fillText(l, W / 2, line.y + i * lineH);
        });
    }

    const outPath = join(OUT_DIR, `slide_${String(slide.n).padStart(2, '0')}.png`);
    writeFileSync(outPath, canvas.toBuffer('image/png'));
    console.log(`✓ ${outPath}`);
}

(async () => {
    console.log(`Generating ${slides.length} slides → ${OUT_DIR}`);
    for (const slide of slides) {
        await renderSlide(slide);
    }
})();
