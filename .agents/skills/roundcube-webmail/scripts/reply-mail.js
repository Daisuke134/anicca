#!/usr/bin/env node
/**
 * roundcube-webmail-skill: reply-mail.js
 * Logs into Roundcube (SAML+TOTP), opens a mail by UID, and sends a reply.
 *
 * Required env vars:
 *   WEBMAIL_USERNAME, WEBMAIL_PASSWORD, WEBMAIL_TOTP_SECRET
 *   WEBMAIL_REPLY_UID   - UID of the mail to reply to
 *   WEBMAIL_REPLY_TEXT  - Reply body text
 *
 * Optional:
 *   WEBMAIL_URL         - Defaults to https://mailbox.naist.jp/roundcube/
 *   WEBMAIL_REPLY_ALL   - 'true' to reply-all (default: false)
 *   SLACK_WEBHOOK_URL   - Post confirmation to Slack
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
const WEBMAIL_REPLY_UID   = process.env.WEBMAIL_REPLY_UID;
const WEBMAIL_REPLY_TEXT  = process.env.WEBMAIL_REPLY_TEXT;
const WEBMAIL_REPLY_ALL   = process.env.WEBMAIL_REPLY_ALL || 'false';
const SLACK_WEBHOOK_URL   = process.env.SLACK_WEBHOOK_URL;

if (!WEBMAIL_USERNAME) {
  console.error('Missing env: WEBMAIL_USERNAME (.env に設定してください)');
  process.exit(1);
}
if (!WEBMAIL_REPLY_UID || !WEBMAIL_REPLY_TEXT) {
  console.error('Missing env: WEBMAIL_REPLY_UID, WEBMAIL_REPLY_TEXT');
  process.exit(1);
}

async function login(page) {
  // Step 1: NAIST IdP TOTP
  await page.goto(WEBMAIL_URL, { waitUntil: 'networkidle' });
  const totp = authenticator.generate(WEBMAIL_TOTP_SECRET);
  await page.fill('#username_input', WEBMAIL_USERNAME);
  await page.fill('#password_input', totp);
  await page.click('button[type="submit"], input[type="submit"]');
  await page.waitForSelector('#rcmloginuser', { timeout: 20000 });

  // Step 2: Roundcube native login
  await page.fill('#rcmloginuser', WEBMAIL_USERNAME);
  await page.fill('#rcmloginpwd', WEBMAIL_PASSWORD);
  await page.click('#rcmloginsubmit');
  await page.waitForLoadState('networkidle');

  const task = await page.evaluate(() => window.rcmail?.task);
  if (task !== 'mail') throw new Error('Login failed - rcmail task: ' + task);
}

async function replyToMail(page) {
  const replyAll = WEBMAIL_REPLY_ALL === 'true';

  // Open the mail by UID
  await page.goto(
    `${WEBMAIL_URL}?_task=mail&_action=show&_mbox=INBOX&_uid=${WEBMAIL_REPLY_UID}`,
    { waitUntil: 'networkidle' }
  );
  await page.waitForSelector('[command="reply"]', { timeout: 10000 });

  // Click reply button
  const cmd = replyAll ? '[command="reply-all"]' : '[command="reply"]';
  await page.click(cmd);

  // Wait for compose window
  await page.waitForSelector('#composebody', { timeout: 15000 });
  await page.waitForTimeout(1000); // allow TinyMCE to initialize

  // Detect TinyMCE and fill body
  const hasTinyMCE = await page.evaluate(
    () => typeof tinymce !== 'undefined' && !!tinymce.get('composebody')
  );
  if (hasTinyMCE) {
    await page.evaluate(
      (text) => tinymce.get('composebody').setContent(text),
      WEBMAIL_REPLY_TEXT
    );
  } else {
    await page.fill('#composebody', WEBMAIL_REPLY_TEXT);
  }

  // Send
  await page.click('[command="send"], .btn.btn-primary.send');

  // Wait for inbox to confirm send completed
  await page.waitForSelector('tr[id^="rcmrow"]', { timeout: 15000 });
  console.log(`[reply] sent to UID ${WEBMAIL_REPLY_UID}`);
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
    await login(page);
    await replyToMail(page);

    const msg = `✉️ *NAIST Mail* — UID ${WEBMAIL_REPLY_UID} に返信しました`;
    console.log(msg);

    if (SLACK_WEBHOOK_URL) {
      await postToSlack(SLACK_WEBHOOK_URL, msg);
      console.log('[slack] posted');
    }
  } finally {
    await browser.close();
  }
})();
