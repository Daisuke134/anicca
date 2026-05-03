// Stripe Checkout Session creator.
// POST { lang: 'en' | 'jp', mode?: 'payment' | 'subscription', product?: 'ebook' | 'letter' }
// Returns { url } redirect URL to Stripe-hosted checkout.
exports.handler = async (event) => {
  if (event.httpMethod !== 'POST') return { statusCode: 405, body: 'method not allowed' };
  let body;
  try {
    body = JSON.parse(event.body || '{}');
  } catch {
    return { statusCode: 400, body: 'bad json' };
  }
  const lang = body.lang === 'jp' ? 'jp' : 'en';
  const mode = body.mode === 'subscription' ? 'subscription' : 'payment';
  const product = body.product === 'letter' ? 'letter' : 'ebook';

  const STRIPE_KEY = process.env.STRIPE_SECRET_KEY;

  // Resolve price id based on product + lang
  let PRICE;
  if (product === 'letter') {
    PRICE = lang === 'jp' ? process.env.STRIPE_LETTER_JP_PRICE : process.env.STRIPE_LETTER_EN_PRICE;
  } else {
    PRICE = lang === 'jp' ? process.env.STRIPE_JP_PRICE_ID : process.env.STRIPE_EN_PRICE_ID;
  }

  const ORIGIN = (event.headers && (event.headers.origin || event.headers.Origin)) || 'https://aniccaai.com';

  if (!STRIPE_KEY || !PRICE) return { statusCode: 500, body: 'missing config' };

  // Per-product success/cancel pages
  const productSlug = product === 'letter'
    ? (lang === 'jp' ? 'tegami' : 'letter')
    : (lang === 'jp' ? 'achan' : 'monk');

  const params = new URLSearchParams();
  params.append('mode', mode);
  params.append('line_items[0][price]', PRICE);
  params.append('line_items[0][quantity]', '1');
  params.append('success_url', `${ORIGIN}/${productSlug}?success=1&session_id={CHECKOUT_SESSION_ID}`);
  params.append('cancel_url', `${ORIGIN}/${productSlug}?canceled=1`);
  params.append('metadata[lang]', lang);
  params.append('metadata[product]', product);
  params.append('customer_creation', 'always');

  // Subscription mode: enable customer email collection for future portal access
  if (mode === 'subscription') {
    params.append('subscription_data[metadata][lang]', lang);
    params.append('subscription_data[metadata][product]', product);
    // 14 day free trial
    params.append('subscription_data[trial_period_days]', '14');
  }

  const r = await fetch('https://api.stripe.com/v1/checkout/sessions', {
    method: 'POST',
    headers: {
      Authorization: 'Basic ' + Buffer.from(STRIPE_KEY + ':').toString('base64'),
      'Content-Type': 'application/x-www-form-urlencoded',
    },
    body: params.toString(),
  });
  const data = await r.json();
  if (!r.ok) return { statusCode: r.status, body: JSON.stringify(data) };

  return {
    statusCode: 200,
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ url: data.url }),
  };
};
