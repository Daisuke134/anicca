// Stripe webhook: on payment_intent.succeeded / checkout.session.completed,
// look up the lang via session metadata and email the buyer the PDF link via Resend.
const crypto = require('crypto');

const WRITER_EVENT_TYPES = new Set([
  'checkout.session.completed',
  'customer.subscription.created',
  'customer.subscription.updated',
  'customer.subscription.deleted',
  'invoice.paid',
  'charge.refunded',
]);

function validStripeSignature(body, header, secret, nowSeconds) {
  if (typeof body !== 'string' || typeof header !== 'string' || typeof secret !== 'string') return false;
  let timestamp = null;
  const signatures = [];
  for (const part of header.split(',')) {
    const index = part.indexOf('=');
    if (index < 0) continue;
    const key = part.slice(0, index).trim();
    const value = part.slice(index + 1).trim();
    if (key === 't' && /^\d+$/.test(value)) timestamp = Number(value);
    if (key === 'v1' && /^[a-f0-9]{64}$/.test(value)) signatures.push(value);
  }
  if (!Number.isSafeInteger(timestamp) || Math.abs(nowSeconds - timestamp) > 300 || signatures.length === 0) return false;
  const expected = crypto.createHmac('sha256', secret).update(`${timestamp}.${body}`).digest();
  return signatures.some((value) => {
    const actual = Buffer.from(value, 'hex');
    return actual.length === expected.length && crypto.timingSafeEqual(actual, expected);
  });
}

function writerMetadata(payload) {
  const object = payload && payload.data && payload.data.object;
  return object && (
    object.metadata
    || (object.subscription_details && object.subscription_details.metadata)
    || (object.parent && object.parent.subscription_details && object.parent.subscription_details.metadata)
  );
}

function isWriterEvent(payload) {
  if (payload && typeof payload.type === 'string' && payload.type.startsWith('payout.')) return true;
  if (!payload || !WRITER_EVENT_TYPES.has(payload.type)) return false;
  const metadata = writerMetadata(payload);
  return metadata && (metadata.product === 'writer_article' || metadata.product === 'writer_archive');
}

async function webhookHandler(event, dependencies = {}) {
  const env = dependencies.env || process.env;
  const WEBHOOK_SECRET = env.STRIPE_WEBHOOK_SECRET;

  if (!WEBHOOK_SECRET) {
    return { statusCode: 500, body: 'missing config' };
  }

  // Verify Stripe signature
  const sigHeader = event.headers['stripe-signature'] || event.headers['Stripe-Signature'];
  if (!sigHeader) return { statusCode: 400, body: 'no sig' };
  const nowSeconds = dependencies.nowSeconds || Math.floor(Date.now() / 1000);
  if (!validStripeSignature(event.body, sigHeader, WEBHOOK_SECRET, nowSeconds)) {
    return { statusCode: 400, body: 'bad sig' };
  }

  let payload;
  try { payload = JSON.parse(event.body); } catch { return { statusCode: 400, body: 'bad json' }; }

  // Writer fulfillment is the signed Checkout entitlement itself. Do not run
  // ebook/Letter email or buyer-store side effects; the read-only collector
  // independently turns Stripe objects into accounting receipts.
  if (isWriterEvent(payload)) return { statusCode: 200, body: 'ok writer' };

  const STRIPE_KEY = env.STRIPE_SECRET_KEY;
  const RESEND_API_KEY = env.RESEND_API_KEY;
  if (!STRIPE_KEY || !RESEND_API_KEY) return { statusCode: 500, body: 'missing config' };
  const fetchImpl = dependencies.fetchImpl || fetch;
  const sendEmail = dependencies.sendEmail
    || ((key, email, subject, html) => sendResend(key, email, subject, html, fetchImpl));

  const SUPABASE_URL = env.SUPABASE_URL;
  const SUPABASE_SERVICE_ROLE_KEY = env.SUPABASE_SERVICE_ROLE_KEY;

  // ────────── checkout.session.completed ──────────
  if (payload.type === 'checkout.session.completed') {
    const session = payload.data.object;
    const email = session.customer_details?.email || session.customer_email;
    const lang = (session.metadata?.lang === 'jp') ? 'jp' : 'en';
    const product = session.metadata?.product || 'ebook';
    const mode = session.mode || 'payment';
    if (!email) return { statusCode: 200, body: 'no email' };

    // Subscription = letter newsletter — upsert into subscribers as paid tier
    if (mode === 'subscription' && product === 'letter') {
      if (SUPABASE_URL && SUPABASE_SERVICE_ROLE_KEY) {
        await fetchImpl(`${SUPABASE_URL}/rest/v1/subscribers`, {
          method: 'POST',
          headers: {
            apikey: SUPABASE_SERVICE_ROLE_KEY,
            Authorization: `Bearer ${SUPABASE_SERVICE_ROLE_KEY}`,
            'Content-Type': 'application/json',
            Prefer: 'resolution=merge-duplicates,return=minimal',
          },
          body: JSON.stringify({
            email,
            lang,
            tier: 'paid',
            stripe_customer_id: session.customer,
            stripe_subscription_id: session.subscription,
            signed_up_at: new Date().toISOString(),
          }),
        }).catch(() => {});
      }
      const subject = lang === 'jp' ? '無常の手紙へようこそ' : 'Welcome to the Daily Anicca Letter';
      const html = lang === 'jp' ? jpLetterWelcomeHtml(session.customer) : enLetterWelcomeHtml(session.customer);
      await sendEmail(RESEND_API_KEY, email, subject, html);
      return { statusCode: 200, body: 'ok subscription' };
    }

    // Payment (ebook) — original flow
    if (SUPABASE_URL && SUPABASE_SERVICE_ROLE_KEY) {
      await fetchImpl(`${SUPABASE_URL}/rest/v1/buyers`, {
        method: 'POST',
        headers: {
          apikey: SUPABASE_SERVICE_ROLE_KEY,
          Authorization: `Bearer ${SUPABASE_SERVICE_ROLE_KEY}`,
          'Content-Type': 'application/json',
          Prefer: 'resolution=merge-duplicates,return=minimal',
        },
        body: JSON.stringify({
          email,
          lang,
          stripe_session_id: session.id,
          amount_paid: session.amount_total,
          currency: session.currency,
          purchased_at: new Date().toISOString(),
        }),
      }).catch(() => {});
    }

    const PDF_URL = lang === 'jp'
      ? `https://aniccaai.com/ebooks/anicca-reset-jp.pdf`
      : `https://aniccaai.com/ebooks/anicca-reset-en.pdf`;
    const subject = lang === 'jp' ? '『アニッチャ・リセット』お届けします' : 'Your copy of The Anicca Reset';
    const html = lang === 'jp' ? jpDeliverHtml(PDF_URL) : enDeliverHtml(PDF_URL);
    await sendEmail(RESEND_API_KEY, email, subject, html);
    return { statusCode: 200, body: 'ok ebook' };
  }

  // ────────── customer.subscription.deleted (cancellation) ──────────
  if (payload.type === 'customer.subscription.deleted') {
    const sub = payload.data.object;
    if (SUPABASE_URL && SUPABASE_SERVICE_ROLE_KEY) {
      await fetchImpl(
        `${SUPABASE_URL}/rest/v1/subscribers?stripe_subscription_id=eq.${encodeURIComponent(sub.id)}`,
        {
          method: 'PATCH',
          headers: {
            apikey: SUPABASE_SERVICE_ROLE_KEY,
            Authorization: `Bearer ${SUPABASE_SERVICE_ROLE_KEY}`,
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({ tier: 'expired', unsubscribed_at: new Date().toISOString() }),
        }
      ).catch(() => {});
    }
    return { statusCode: 200, body: 'ok cancel' };
  }

  // ────────── customer.subscription.updated (status changes) ──────────
  if (payload.type === 'customer.subscription.updated') {
    const sub = payload.data.object;
    const tier = (sub.status === 'active' || sub.status === 'trialing') ? 'paid' : 'expired';
    if (SUPABASE_URL && SUPABASE_SERVICE_ROLE_KEY) {
      await fetchImpl(
        `${SUPABASE_URL}/rest/v1/subscribers?stripe_subscription_id=eq.${encodeURIComponent(sub.id)}`,
        {
          method: 'PATCH',
          headers: {
            apikey: SUPABASE_SERVICE_ROLE_KEY,
            Authorization: `Bearer ${SUPABASE_SERVICE_ROLE_KEY}`,
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({ tier }),
        }
      ).catch(() => {});
    }
    return { statusCode: 200, body: 'ok update' };
  }

  return { statusCode: 200, body: 'ignored' };
}

exports.webhookHandler = webhookHandler;
exports.handler = (event) => webhookHandler(event);

async function sendResend(key, email, subject, html, fetchImpl = fetch) {
  await fetchImpl('https://api.resend.com/emails', {
    method: 'POST',
    headers: { Authorization: `Bearer ${key}`, 'Content-Type': 'application/json' },
    body: JSON.stringify({ from: 'Anicca <onboarding@resend.dev>', to: email, subject, html }),
  }).catch(() => {});
}

function enLetterWelcomeHtml(customerId) {
  const manageUrl = customerId ? `https://aniccaai.com/account?cid=${customerId}` : 'https://aniccaai.com/account';
  return `
  <div style="font-family: Georgia, serif; max-width: 560px; margin: 0 auto; padding: 24px; color: #2A2520; line-height: 1.7;">
    <h1 style="font-weight: 300;">Welcome.</h1>
    <p>Your daily letters on impermanence start tomorrow morning.</p>
    <p>You've subscribed to the <em>Daily Anicca Letter</em>. One short meditation, every morning, on the body's emotional weather. The first 14 days are free. After that, $9.99/month.</p>
    <p>Read each letter slowly. Let it settle. The teaching is in the noticing, not in the rushing.</p>
    <p>— Anicca</p>
    <hr style="border:none; border-top: 1px solid #E5DCC9; margin: 32px 0;" />
    <p style="font-size:13px; color:#8B7355;">If you'd like the full 49-lesson book: <a href="https://aniccaai.com/monk" style="color:#2A2520;">The Anicca Reset — $10.99</a></p>
    <p style="text-align:center; margin: 24px 0 8px 0;">
      <a href="${manageUrl}" style="display:inline-block; border:1px solid #8B7355; color:#8B7355; padding: 10px 22px; text-decoration:none; letter-spacing:2px; font-size:11px; text-transform:uppercase;">Manage subscription</a>
    </p>
  </div>`;
}
function jpLetterWelcomeHtml(customerId) {
  const manageUrl = customerId ? `https://aniccaai.com/account?cid=${customerId}` : 'https://aniccaai.com/account';
  return `
  <div style="font-family: 'Hiragino Mincho ProN', serif; max-width: 560px; margin: 0 auto; padding: 24px; color: #2A2520; line-height: 1.9;">
    <h1 style="font-weight: 300;">ようこそ。</h1>
    <p>明日の朝から、無常をめぐる短い手紙を毎日お届けします。</p>
    <p>『無常の手紙』をご購読いただきありがとうございます。一通あたり約2分。365通、毎日1通ずつ。最初の14日間は無料、以後は月¥980。</p>
    <p>急がず、ゆっくり読んでください。気づくこと、それが教えです。</p>
    <p>— アニッチャ</p>
    <hr style="border:none; border-top: 1px solid #E5DCC9; margin: 32px 0;" />
    <p style="font-size:13px; color:#8B7355;">49章すべて読みたい方は: <a href="https://aniccaai.com/achan" style="color:#2A2520;">『アニッチャ・リセット』 — ¥1,580</a></p>
    <p style="text-align:center; margin: 24px 0 8px 0;">
      <a href="${manageUrl}" style="display:inline-block; border:1px solid #8B7355; color:#8B7355; padding: 10px 22px; text-decoration:none; letter-spacing:2px; font-size:11px;">サブスクリプションを管理</a>
    </p>
  </div>`;
}

function enDeliverHtml(url) {
  return `
  <div style="font-family: Georgia, serif; max-width: 560px; margin: 0 auto; padding: 24px; color: #2A2520; line-height: 1.7;">
    <h1 style="font-weight: 300;">Welcome.</h1>
    <p>Your copy of <em>The Anicca Reset</em> is ready. 49 short chapters on impermanence — read them slowly.</p>
    <p style="text-align:center; margin: 32px 0;">
      <a href="${url}" style="display:inline-block; background:#2A2520; color:#FBF7EF; padding: 14px 28px; text-decoration:none; letter-spacing:2px; font-size:13px;">Download the PDF →</a>
    </p>
    <p>Lifetime access. Read it on any device. Re-read it when you need to be reminded that the thing you're holding is already moving.</p>
    <p>— Anicca</p>
  </div>`;
}

function jpDeliverHtml(url) {
  return `
  <div style="font-family: 'Hiragino Mincho ProN', serif; max-width: 560px; margin: 0 auto; padding: 24px; color: #2A2520; line-height: 1.9;">
    <h1 style="font-weight: 300;">ようこそ。</h1>
    <p>『アニッチャ・リセット』のPDFをお送りします。49の短い章、ゆっくりお読みください。</p>
    <p style="text-align:center; margin: 32px 0;">
      <a href="${url}" style="display:inline-block; background:#2A2520; color:#FBF7EF; padding: 14px 28px; text-decoration:none; letter-spacing:2px; font-size:13px;">PDFをダウンロード →</a>
    </p>
    <p>永久アクセス。いつでも、どの端末でも読めます。あなたが今抱えているものが、すでに動いていることを思い出したいときに、何度でも戻ってきてください。</p>
    <p>— アニッチャ</p>
  </div>`;
}
