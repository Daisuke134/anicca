// Stripe Customer Portal entry point — one-click direct redirect from email.
// GET /account?cid=<stripe_customer_id>   → 302 to Stripe portal (preferred, used in emails)
// GET /account?email=<email>              → fallback: lookup customer by email, 302
// GET /account                            → friendly fallback page (no form, just info)
exports.handler = async (event) => {
  const STRIPE_KEY = process.env.STRIPE_SECRET_KEY;
  if (!STRIPE_KEY) return { statusCode: 500, body: 'missing config' };

  const ORIGIN = (event.headers && (event.headers.origin || event.headers.Origin)) || 'https://aniccaai.com';
  const params = event.queryStringParameters || {};
  const cid = params.cid || '';
  const email = params.email || '';

  // PATH 1: cid present → 1-API-call direct portal redirect (used in welcome / daily emails)
  if (cid && /^cus_[A-Za-z0-9]+$/.test(cid)) {
    const portal = await createPortalSession(STRIPE_KEY, cid, ORIGIN);
    if (portal.url) return { statusCode: 302, headers: { Location: portal.url }, body: '' };
    return { statusCode: portal.status || 500, body: JSON.stringify(portal.body || {}) };
  }

  // PATH 2: email fallback → search customer by email, redirect
  if (email) {
    const customerSearch = await fetch(
      `https://api.stripe.com/v1/customers/search?query=${encodeURIComponent('email:"' + email + '"')}&limit=1`,
      { headers: { Authorization: 'Basic ' + Buffer.from(STRIPE_KEY + ':').toString('base64') } }
    );
    const cs = await customerSearch.json();
    const customer = cs.data && cs.data[0];
    if (customer) {
      const portal = await createPortalSession(STRIPE_KEY, customer.id, ORIGIN);
      if (portal.url) return { statusCode: 302, headers: { Location: portal.url }, body: '' };
    }
    return notFoundPage(email);
  }

  // PATH 3: no params → minimal info page directing to email
  return {
    statusCode: 200,
    headers: { 'Content-Type': 'text/html; charset=utf-8' },
    body: `<!DOCTYPE html><html><head><meta charset="utf-8"><title>Manage subscription</title>
      <style>body{font-family:Georgia,serif;max-width:560px;margin:80px auto;padding:24px;color:#2A2520;background:#FBF7EF;line-height:1.7;text-align:center}</style>
      </head><body>
      <h1 style="font-weight:300">Manage your subscription</h1>
      <p>The "Manage subscription" link inside any Anicca email takes you<br />directly to your Stripe billing portal.</p>
      <p style="font-size:14px;color:#8B7355">If you can't find that email, contact <a href="mailto:hello@aniccaai.com">hello@aniccaai.com</a>.</p>
      </body></html>`,
  };
};

async function createPortalSession(stripeKey, customerId, origin) {
  const params = new URLSearchParams();
  params.append('customer', customerId);
  params.append('return_url', `${origin}/letter`);
  const res = await fetch('https://api.stripe.com/v1/billing_portal/sessions', {
    method: 'POST',
    headers: {
      Authorization: 'Basic ' + Buffer.from(stripeKey + ':').toString('base64'),
      'Content-Type': 'application/x-www-form-urlencoded',
    },
    body: params.toString(),
  });
  const json = await res.json();
  if (!res.ok) return { status: res.status, body: json };
  return { url: json.url };
}

function notFoundPage(email) {
  return {
    statusCode: 200,
    headers: { 'Content-Type': 'text/html; charset=utf-8' },
    body: `<!DOCTYPE html><html><body style="font-family:Georgia,serif;max-width:480px;margin:80px auto;padding:24px;text-align:center;color:#2A2520;background:#FBF7EF">
      <p>No active subscription found for ${email}.</p>
      <p style="font-size:13px;color:#8B7355"><a href="https://aniccaai.com/letter" style="color:#2A2520">Subscribe to Daily Anicca Letter →</a></p>
      </body></html>`,
  };
}
