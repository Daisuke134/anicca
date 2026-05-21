#!/usr/bin/env node
/**
 * roundcube-webmail-skill: read-mail.js
 * Logs into Roundcube (SAML+TOTP), reads INBOX, posts to Slack or stdout.
 */
const { chromium } = require('playwright');
const { authenticator } = require('otplib');
const { execSync } = require('child_process');
const https = require('https');
const fs = require('fs');
const path = require('path');

// OWASP Logging: pw:* outputs full HTTP traffic including credentials
if (process.env.DEBUG?.includes('pw:')) {
  console.error('[security] DEBUG=pw:* は認証情報を含む全通信をログ出力するため実行できません');
  process.exit(1);
}

function fromKeychain(service) {
  try {
    return execSync(
      `security find-generic-password -a naist-mail -s ${service} -w`,
      { stdio: ['pipe', 'pipe', 'pipe'] }
    ).toString().trim();
  } catch {
    console.error(`[error] Keychain に ${service} がありません。bash scripts/setup-keychain.sh を先に実行してください。`);
    process.exit(1);
  }
}

const WEBMAIL_URL         = process.env.WEBMAIL_URL || 'https://mailbox.naist.jp/roundcube/';
const WEBMAIL_USERNAME    = process.env.WEBMAIL_USERNAME;
const WEBMAIL_PASSWORD    = fromKeychain('WEBMAIL_PASSWORD');
const WEBMAIL_TOTP_SECRET = fromKeychain('WEBMAIL_TOTP_SECRET');
const SLACK_WEBHOOK_URL   = process.env.SLACK_WEBHOOK_URL;
const WEBMAIL_MAX_EMAILS  = process.env.WEBMAIL_MAX_EMAILS || '10';
const WEBMAIL_UNREAD_ONLY = process.env.WEBMAIL_UNREAD_ONLY || 'false';

const SESSION_FILE = path.join(__dirname, '../.session.json');
const SAVE_SESSION = process.argv.includes('--save-session');

if (!WEBMAIL_USERNAME) {
  console.error('Missing env: WEBMAIL_USERNAME (.env に設定してください)');
  process.exit(1);
}

async function login(page, context) {
  // Check saved session
  if (fs.existsSync(SESSION_FILE)) {
    try {
      const state = JSON.parse(fs.readFileSync(SESSION_FILE, 'utf8'));
      await context.addCookies(state.cookies);
      await page.goto(WEBMAIL_URL + '?_task=mail&_mbox=INBOX', { waitUntil: 'networkidle' });
      const task = await page.evaluate(() => window.rcmail?.task);
      if (task === 'mail') {
        console.log('[session] reused saved session');
        return;
      }
    } catch(e) {}
  }

  // Step 1: NAIST IdP TOTP
  await page.goto(WEBMAIL_URL, { waitUntil: 'networkidle' });
  const totp = authenticator.generate(WEBMAIL_TOTP_SECRET);
  await page.fill('#username_input', WEBMAIL_USERNAME);
  await page.fill('#password_input', totp);
  await page.click('button[type="submit"], input[type="submit"]');
  // Wait for Roundcube login form to appear after SAML redirect
  await page.waitForSelector('#rcmloginuser', { timeout: 20000 });

  // Step 2: Roundcube native login
  await page.fill('#rcmloginuser', WEBMAIL_USERNAME);
  await page.fill('#rcmloginpwd', WEBMAIL_PASSWORD);
  await page.click('#rcmloginsubmit');
  await page.waitForLoadState('networkidle');
  await page.waitForTimeout(3000);

  const task = await page.evaluate(() => window.rcmail?.task);
  if (task !== 'mail') throw new Error('Login failed - rcmail task: ' + task);

  if (SAVE_SESSION) {
    const state = await context.storageState();
    fs.writeFileSync(SESSION_FILE, JSON.stringify(state));
    console.log('[session] saved');
  }
}

async function readInbox(page) {
  const max = parseInt(WEBMAIL_MAX_EMAILS);
  const unreadOnly = WEBMAIL_UNREAD_ONLY === 'true';

  await page.waitForSelector('tr[id^="rcmrow"]', { timeout: 10000 }).catch(() => {});

  return page.evaluate(({ max, unreadOnly }) => {
    const rows = Array.from(document.querySelectorAll('tr[id^="rcmrow"]'));
    return rows
      .filter(r => !unreadOnly || r.classList.contains('unread'))
      .slice(0, max)
      .map(row => ({
        subject: row.querySelector('.subject')?.innerText?.split('\n')[0]?.trim(),
        from: row.querySelector('.from')?.innerText?.split('\n')[0]?.trim() || row.querySelector('.sender')?.innerText?.split('\n')[0]?.trim() || null,
        date: row.querySelector('.date')?.innerText?.trim(),
        unread: row.classList.contains('unread'),
      }));
  }, { max, unreadOnly });
}

function postToSlack(webhook, text) {
  return new Promise((resolve, reject) => {
    const body = JSON.stringify({ text });
    const url = new URL(webhook);
    const req = https.request({
      hostname: url.hostname, path: url.pathname,
      method: 'POST', headers: { 'Content-Type': 'application/json', 'Content-Length': Buffer.byteLength(body) }
    }, res => res.statusCode === 200 ? resolve() : reject(new Error('Slack status: ' + res.statusCode)));
    req.on('error', reject);
    req.write(body);
    req.end();
  });
}

(async () => {
  const browser = await chromium.launch({ headless: true });
  const context = await browser.newContext();
  const page = await context.newPage();

  try {
    await login(page, context);
    const emails = await readInbox(page);
    const unreadCount = emails.filter(e => e.unread).length;

    const lines = emails.map((e, i) => {
      const sender = e.from || e.subject || '(unknown)';
      const subj = e.from ? e.subject : '';
      return `${i+1}. ${e.unread ? '🔵' : '⚪'} *${sender}*${subj ? `\n   ${subj}` : ''}\n   ${e.date}`;
    });
    const summary = `📬 *NAIST Mail* — 未読 ${unreadCount}件\n\n` + lines.join('\n\n');

    console.log(summary);

    if (SLACK_WEBHOOK_URL) {
      await postToSlack(SLACK_WEBHOOK_URL, summary);
      console.log('[slack] posted');
    }
  } finally {
    await browser.close();
    if (fs.existsSync(SESSION_FILE)) {
      fs.unlinkSync(SESSION_FILE);
      console.log('[session] deleted');
    }
  }
})();
