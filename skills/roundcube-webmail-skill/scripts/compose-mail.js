#!/usr/bin/env node
/**
 * Send a NEW mail from Roundcube ({{profile.education.institution}}). For replies, prefer reply-mail.js.
 *
 * Required env:
 *   WEBMAIL_USERNAME, WEBMAIL_PASSWORD, WEBMAIL_TOTP_SECRET (keychain)
 *   COMPOSE_TO       comma-separated recipients
 *   COMPOSE_SUBJECT  subject line
 *   COMPOSE_BODY     plain-text body
 * Optional:
 *   COMPOSE_CC       comma-separated CC
 *   COMPOSE_BCC      comma-separated BCC
 *   WEBMAIL_URL      default https://mailbox.naist.jp/roundcube/
 *   SLACK_WEBHOOK_URL  post confirmation to Slack if set
 */
const { chromium } = require('playwright');
const { authenticator } = require('otplib');
const { execSync } = require('child_process');
const https = require('https');

if (process.env.DEBUG?.includes('pw:')) {
  console.error('[security] DEBUG=pw:* not allowed (would log credentials).');
  process.exit(1);
}

function fromKeychain(service) {
  return execSync(
    `security find-generic-password -a naist-mail -s ${service} -w`,
    { stdio: ['pipe', 'pipe', 'pipe'] }
  ).toString().trim();
}

const WEBMAIL_URL         = process.env.WEBMAIL_URL || 'https://mailbox.naist.jp/roundcube/';
const WEBMAIL_USERNAME    = process.env.WEBMAIL_USERNAME;
const WEBMAIL_PASSWORD    = fromKeychain('WEBMAIL_PASSWORD');
const WEBMAIL_TOTP_SECRET = fromKeychain('WEBMAIL_TOTP_SECRET');
const COMPOSE_TO          = process.env.COMPOSE_TO;
const COMPOSE_CC          = process.env.COMPOSE_CC || '';
const COMPOSE_BCC         = process.env.COMPOSE_BCC || '';
const COMPOSE_SUBJECT     = process.env.COMPOSE_SUBJECT;
const COMPOSE_BODY        = process.env.COMPOSE_BODY;
const SLACK_WEBHOOK_URL   = process.env.SLACK_WEBHOOK_URL;

for (const [k, v] of Object.entries({ WEBMAIL_USERNAME, COMPOSE_TO, COMPOSE_SUBJECT, COMPOSE_BODY })) {
  if (!v) { console.error(`Missing env: ${k}`); process.exit(1); }
}

async function login(page) {
  await page.goto(WEBMAIL_URL, { waitUntil: 'networkidle' });
  const totp = authenticator.generate(WEBMAIL_TOTP_SECRET);
  await page.fill('#username_input', WEBMAIL_USERNAME);
  await page.fill('#password_input', totp);
  await page.click('button[type="submit"], input[type="submit"]');
  await page.waitForSelector('#rcmloginuser', { timeout: 20000 });

  await page.fill('#rcmloginuser', WEBMAIL_USERNAME);
  await page.fill('#rcmloginpwd', WEBMAIL_PASSWORD);
  await page.click('#rcmloginsubmit');
  await page.waitForLoadState('networkidle');

  const task = await page.evaluate(() => window.rcmail?.task);
  if (task !== 'mail') throw new Error('Login failed - rcmail task=' + task);
}

async function compose(page) {
  // Roundcube compose URL
  const composeUrl = WEBMAIL_URL.replace(/\/$/, '') + '/?_task=mail&_action=compose';
  await page.goto(composeUrl, { waitUntil: 'networkidle' });

  // Wait for compose form
  await page.waitForSelector('#_to, input[name="_to"], textarea[name="_to"]', { timeout: 15000 });

  // Fill recipients
  const toSel = await page.$('textarea[name="_to"]') ? 'textarea[name="_to"]' : '#_to';
  await page.fill(toSel, COMPOSE_TO);
  if (COMPOSE_CC) {
    // Force reveal CC field — Roundcube hides it behind a header button
    await page.evaluate(() => {
      const cc = document.querySelector('#_cc');
      if (cc) {
        cc.style.display = '';
        cc.removeAttribute('tabindex');
        const row = cc.closest('.form-group, .compose-headers-row, tr');
        if (row) row.style.display = '';
      }
      // Some Roundcube themes also have a "show CC" link
      const link = document.querySelector('a[onclick*="cc"], a[href*="cc"]');
    });
    await page.evaluate((val) => {
      const cc = document.querySelector('#_cc');
      if (cc) {
        const nativeSetter = Object.getOwnPropertyDescriptor(window.HTMLTextAreaElement.prototype, 'value').set;
        nativeSetter.call(cc, val);
        cc.dispatchEvent(new Event('input', { bubbles: true }));
        cc.dispatchEvent(new Event('change', { bubbles: true }));
      }
    }, COMPOSE_CC);
  }
  if (COMPOSE_BCC) {
    const bccSel = await page.$('textarea[name="_bcc"]') ? 'textarea[name="_bcc"]' : '#_bcc';
    if (bccSel) await page.fill(bccSel, COMPOSE_BCC);
  }

  // Subject
  await page.fill('#_subject, input[name="_subject"]', COMPOSE_SUBJECT);

  // Body — prefer plain text
  // First, try to switch to plain-text if a toggle exists
  const isHtmlEditor = await page.$('.tox-edit-area, iframe.cke_wysiwyg_frame, iframe.tox-edit-area__iframe');
  if (isHtmlEditor) {
    // try toggle to plain text via mailvelope/tinymce — Roundcube has #compose-editorselect dropdown
    const toggle = await page.$('select[name="editorSelector"], #composebody-editorSelector');
    if (toggle) {
      await toggle.selectOption('1').catch(() => {}); // 1 = plain
      await page.waitForTimeout(500);
    }
  }
  // Plain textarea
  const bodyTextarea = await page.$('textarea#composebody, textarea[name="_message"]');
  if (bodyTextarea) {
    await bodyTextarea.fill(COMPOSE_BODY);
  } else {
    // fallback to TinyMCE iframe
    const frame = page.frameLocator('iframe.tox-edit-area__iframe').first();
    await frame.locator('body').fill(COMPOSE_BODY);
  }

  // Wait a moment for autosave/validators
  await page.waitForTimeout(800);

  // Send — Roundcube has many variants of the send button. Try several + JS command.
  let sent = false;
  const candidates = [
    '#rcmbtn112',
    '#rcmbtn-send',
    '#compose-send-button',
    'a.button.send',
    'a[rel="send"]',
    'button[name="send"]',
    'a[onclick*="send-attach"]',
    'a[onclick*="\\"send\\""]',
  ];
  for (const sel of candidates) {
    const btn = await page.$(sel);
    if (btn) {
      console.log('[compose] click send via', sel);
      await Promise.all([
        page.waitForLoadState('networkidle').catch(() => {}),
        btn.click().catch(() => {}),
      ]);
      sent = true;
      break;
    }
  }
  if (!sent) {
    console.log('[compose] no send button DOM hit — invoking rcmail.command("send-attach")');
    await page.evaluate(() => {
      if (window.rcmail && typeof window.rcmail.command === 'function') {
        window.rcmail.command('send-attach');
      } else if (window.rcmail) {
        window.rcmail.command('send');
      }
    });
    sent = true;
  }

  // Roundcube shows toast/confirmation
  await page.waitForTimeout(2000);
  const url = page.url();
  console.log('[compose] post-send URL:', url);
}

function postSlack(text) {
  if (!SLACK_WEBHOOK_URL) return;
  const data = JSON.stringify({ text });
  const u = new URL(SLACK_WEBHOOK_URL);
  return new Promise((resolve) => {
    const req = https.request({ host: u.host, path: u.pathname + u.search, method: 'POST', headers: { 'Content-Type': 'application/json', 'Content-Length': Buffer.byteLength(data) } }, (res) => res.on('end', resolve));
    req.on('error', () => resolve());
    req.write(data); req.end();
  });
}

(async () => {
  const {{profile.lateness.stakeholders.channel}} = await chromium.launch({ headless: true });
  const ctx = await {{profile.lateness.stakeholders.channel}}.newContext();
  const page = await ctx.newPage();
  try {
    console.log('[compose] login…');
    await login(page);
    console.log('[compose] login OK');
    await compose(page);
    console.log('[compose] sent');
    await postSlack(`✉️ {{profile.education.institution}} mail sent\nto: ${COMPOSE_TO}\ncc: ${COMPOSE_CC}\nsubject: ${COMPOSE_SUBJECT}`);
  } catch (e) {
    console.error('[compose] ERROR', e.message);
    await page.screenshot({ path: '/tmp/roundcube-compose-error.png', fullPage: true }).catch(() => {});
    await postSlack(`❌ {{profile.education.institution}} mail FAILED ${COMPOSE_SUBJECT} :: ${e.message}`);
    process.exitCode = 1;
  } finally {
    await {{profile.lateness.stakeholders.channel}}.close();
  }
})();
