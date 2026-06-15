/**
 * /me page structural test (spec27 A-install/me)
 *
 * Tests that the /me page:
 * 1. Is a static export (force-static)
 * 2. Contains all required UI sections from spec20 §3 wireframe
 * 3. Does NOT touch shared files (LaunchNav, skills-lock.json)
 * 4. Imports only from its own new file (no edits to Foundation files)
 *
 * Uses Node.js built-in test runner (node --test). ESM format (package.json type=module).
 */
import { test } from 'node:test';
import assert from 'node:assert';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));

const PAGE_PATH = path.join(__dirname, '..', 'app', 'me', 'page.tsx');
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

test('page declares force-static export', () => {
  assert.ok(
    src.includes("export const dynamic = 'force-static'"),
    'Missing force-static export directive',
  );
});

// ─── 2. Metadata ──────────────────────────────────────────────────────────────

test('page exports metadata with title and description', () => {
  assert.ok(src.includes('export const metadata'), 'Missing metadata export');
  assert.ok(src.includes("title: 'Me"), 'Missing title in metadata');
  assert.ok(src.includes('description:'), 'Missing description in metadata');
});

// ─── 3. Required UI sections (spec20 §3) ──────────────────────────────────────

test('page uses LaunchNav with active=/me', () => {
  assert.ok(
    src.includes('LaunchNav active="/me"'),
    'LaunchNav must be used with active="/me"',
  );
});

test('page has money hero section with sent-to-you, earned, subscription status', () => {
  assert.ok(src.includes('あなたへ送金済'), 'Missing sent-to-you label');
  assert.ok(src.includes('今月の稼ぎ'), 'Missing earned-this-month label');
  assert.ok(src.includes('サブスク'), 'Missing subscription status label');
});

test('page has withdraw CTA button', () => {
  assert.ok(src.includes('銀行に引き出す'), 'Missing withdraw button text');
  assert.ok(src.includes('billing.stripe.com'), 'Missing Stripe billing URL');
});

test('page has your-anicca instance card', () => {
  assert.ok(src.includes('あなたのAnicca'), 'Missing your-Anicca card label');
  assert.ok(src.includes('モデル'), 'Missing model field');
  assert.ok(src.includes('残高'), 'Missing balance field');
  assert.ok(src.includes('残命'), 'Missing runway field');
});

test('page has colony summary card', () => {
  assert.ok(src.includes('総資産'), 'Missing total assets label');
  assert.ok(src.includes('全コロニーを見る'), 'Missing colony link');
});

test('page has children (self-spawned) section', () => {
  assert.ok(src.includes('子（自己増殖）'), 'Missing children section label');
  assert.ok(src.includes('anicca-001'), 'Missing first child instance');
  assert.ok(src.includes('anicca-002'), 'Missing second child instance');
});

test('page has activity log section', () => {
  assert.ok(src.includes('行動ログ'), 'Missing activity log label');
  assert.ok(src.includes('0xwork'), 'Missing 0xwork activity entry');
  assert.ok(src.includes('litcoin'), 'Missing litcoin activity entry');
});

test('page has life context section', () => {
  assert.ok(src.includes('あなたの生活'), 'Missing life context section');
  assert.ok(src.includes('連携時のみ'), 'Missing "connected only" qualifier');
});

test('page has action buttons: Talk, Pause, Daily Report', () => {
  assert.ok(src.includes('Aniccaと話す'), 'Missing "talk to Anicca" button');
  assert.ok(src.includes('一時停止'), 'Missing pause button');
  assert.ok(src.includes('日次報告'), 'Missing daily report button');
});

test('page links to /install and /dashboard', () => {
  assert.ok(src.includes('href="/install"'), 'Missing link to /install');
  assert.ok(src.includes('href="/dashboard"'), 'Missing link to /dashboard');
});

// ─── 4. Collision rule — must NOT edit shared files ────────────────────────────

test('LaunchNav.tsx is NOT modified by this page (collision rule)', () => {
  const navSrc = fs.readFileSync(LAUNCH_NAV_PATH, 'utf-8');
  // Foundation pre-wired /me. Builder only replaces app/me/page.tsx body.
  assert.ok(
    navSrc.includes("href: '/me'"),
    'LaunchNav must still have /me route pre-wired by Foundation',
  );
});

test('skills-lock.json exists and was NOT touched by this builder', () => {
  assert.ok(
    fs.existsSync(SKILLS_LOCK_PATH),
    'skills-lock.json must exist (Foundation pre-wired)',
  );
});

// ─── 5. No placeholder text remains ───────────────────────────────────────────

test('placeholder text is removed from /me page', () => {
  assert.ok(
    !src.includes('FOUNDATION PLACEHOLDER'),
    'FOUNDATION PLACEHOLDER comment must be removed',
  );
  assert.ok(
    !src.includes('Coming online with the launch build'),
    'Old placeholder text must be replaced',
  );
});
