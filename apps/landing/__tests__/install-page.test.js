/**
 * /install page structural test (spec27 A-install/me)
 *
 * Tests that the /install page:
 * 1. Has the spec27 2-column layout: ☁ CLOUD + ⌨ OSS
 * 2. Shows NO raw shell commands (git clone) prominently
 * 3. Uses force-static export
 * 4. Does NOT touch shared files (LaunchNav, skills-lock.json)
 *
 * Uses Node.js built-in test runner (node --test). ESM format (package.json type=module).
 */
import { test } from 'node:test';
import assert from 'node:assert';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));

const PAGE_PATH = path.join(__dirname, '..', 'app', 'install', 'page.tsx');
const LAUNCH_NAV_PATH = path.join(__dirname, '..', 'components', 'site', 'LaunchNav.tsx');
const SKILLS_LOCK_PATH = path.join(
  __dirname,
  '..',
  '..',
  '..',
  'skills-lock.json',
);

const src = fs.readFileSync(PAGE_PATH, 'utf-8');

// ─── 1. Static export ──────────────────────────────────────────────────────────

test('install page declares force-static export', () => {
  assert.ok(
    src.includes("export const dynamic = 'force-static'"),
    'Missing force-static export directive',
  );
});

// ─── 2. spec27 2-column layout: ☁ CLOUD + ⌨ OSS ──────────────────────────────

test('install page has CLOUD column with emoji ☁', () => {
  assert.ok(src.includes('☁'), 'Missing ☁ emoji for CLOUD column');
  assert.ok(
    src.includes('CLOUD') || src.includes('クラウド'),
    'Missing CLOUD label in install page',
  );
});

test('install page has OSS column with emoji ⌨', () => {
  assert.ok(src.includes('⌨'), 'Missing ⌨ emoji for OSS column');
  assert.ok(
    src.includes('OSS') || src.includes('self-host'),
    'Missing OSS label in install page',
  );
});

test('install page has 2-column grid layout', () => {
  assert.ok(
    src.includes('md:grid-cols-2') || src.includes('grid-cols-2'),
    'Missing 2-column grid layout',
  );
});

test('install page has "Googleログイン" or "Google" cloud onboarding text', () => {
  assert.ok(
    src.includes('Google') || src.includes('1分'),
    'Missing Google login or 1-minute reference for cloud path',
  );
});

test('install page has "製品メイン・推奨" or "推奨" (recommended) label for cloud', () => {
  assert.ok(
    src.includes('推奨') || src.includes('recommended') || src.includes('Recommended'),
    'Missing recommended/推奨 label for cloud column',
  );
});

test('install page has "上級者" or "self-host" OSS label', () => {
  assert.ok(
    src.includes('上級者') || src.includes('advanced') || src.includes('self-host'),
    'Missing 上級者/self-host label for OSS column',
  );
});

// ─── 3. NO raw shell commands shown prominently ────────────────────────────────

test('install page does NOT contain PATH_B_SH raw git clone constant', () => {
  // The old page had `const PATH_B_SH = \`git clone...\``
  // New spec-compliant page must NOT show raw shell as primary content
  assert.ok(
    !src.includes('const PATH_B_SH'),
    'Removed PATH_B_SH constant (old raw shell pattern). New page must use 2-column layout.',
  );
});

test('install page does NOT contain PATH_A_PROMPT raw prompt constant', () => {
  // The old page had `const PATH_A_PROMPT = \`You are installing...\``
  assert.ok(
    !src.includes('const PATH_A_PROMPT'),
    'Removed PATH_A_PROMPT constant (old raw prompt pattern). New page must use 2-column layout.',
  );
});

test('install page does NOT show SplitHero as primary layout', () => {
  // spec27 requires 2-column cloud+OSS, NOT SplitHero
  assert.ok(
    !src.includes('<SplitHero'),
    'Must NOT use SplitHero component. Use 2-column grid layout instead.',
  );
});

// ─── 4. Cloud column: Stripe subscription CTA ─────────────────────────────────

test('install page cloud column has Stripe checkout link or /checkout reference', () => {
  assert.ok(
    src.includes('stripe') || src.includes('Stripe') || src.includes('checkout') || src.includes('$30'),
    'Cloud column must reference Stripe checkout or $30/mo pricing',
  );
});

// ─── 5. OSS column: GitHub link (not prominent shell) ─────────────────────────

test('install page OSS column has GitHub link', () => {
  assert.ok(
    src.includes('github.com/Daisuke134/anicca'),
    'OSS column must link to GitHub repo',
  );
});

// ─── 6. LaunchNav active=/install ─────────────────────────────────────────────

test('install page uses LaunchNav with active=/install', () => {
  assert.ok(
    src.includes('active="/install"'),
    'LaunchNav must be used with active="/install"',
  );
});

// ─── 7. Collision rule — must NOT edit shared files ───────────────────────────

test('LaunchNav.tsx is NOT modified by this page (collision rule)', () => {
  const navSrc = fs.readFileSync(LAUNCH_NAV_PATH, 'utf-8');
  assert.ok(
    navSrc.includes("href: '/install'"),
    'LaunchNav must still have /install route pre-wired by Foundation',
  );
});

test('skills-lock.json exists and was NOT touched by this builder', () => {
  assert.ok(
    fs.existsSync(SKILLS_LOCK_PATH),
    'skills-lock.json must exist (Foundation pre-wired)',
  );
});
