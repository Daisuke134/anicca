// Stripe Customer Portal entry point.
// GET /account?email=<email>  → redirects to Stripe billing portal session
// FTC click-to-cancel compliance: subscribers can manage / cancel any time.
exports.handler = async (event) => {
  const STRIPE_KEY = process.env.STRIPE_SECRET_KEY;
  if (!STRIPE_KEY) return { statusCode: 500, body: 'missing config' };

  const ORIGIN = (event.headers && (event.headers.origin || event.headers.Origin)) || 'https://aniccaai.com';

  // Email comes from query string (linked from email footer of letters)
  const email = (event.queryStringParameters && event.queryStringParameters.email) || '';
  if (!email) {
    return {
      statusCode: 200,
      headers: { 'Content-Type': 'text/html; charset=utf-8' },
      body: `<!DOCTYPE html><html><head><meta charset="utf-8"><title>Manage subscription</title>
        <style>body{font-family:Georgia,serif;max-width:480px;margin:80px auto;padding:24px;color:#2A2520;background:#FBF7EF;line-height:1.7;text-align:center}
        input,button{font-family:inherit;font-size:14px;padding:10px;border:1px solid #8B7355;background:transparent;color:inherit}
        button{background:#2A2520;color:#FBF7EF;cursor:pointer;letter-spacing:2px;text-transform:uppercase;margin-left:8px}</style>
        </head><body>
        <h1 style="font-weight:300">Manage your subscription</h1>
        <p>Enter the email you subscribed with. We'll send you a portal link.</p>
        <form method="GET">
          <input type="email" name="email" placeholder="your@email.com" required />
          <button type="submit">Continue →</button>
        </form>
        </body></html>`,
    };
  }

  // 1) Find Stripe customer by email
  const customerSearch = await fetch(
    `https://api.stripe.com/v1/customers/search?query=${encodeURIComponent('email:"' + email + '"')}&limit=1`,
    { headers: { Authorization: 'Basic ' + Buffer.from(STRIPE_KEY + ':').toString('base64') } }
  );
  const cs = await customerSearch.json();
  const customer = cs.data && cs.data[0];
  if (!customer) {
    return {
      statusCode: 200,
      headers: { 'Content-Type': 'text/html; charset=utf-8' },
      body: `<!DOCTYPE html><html><body style="font-family:Georgia,serif;max-width:480px;margin:80px auto;padding:24px;text-align:center">
        <p>No subscription found for ${email}.</p>
        <p><a href="/account">Try another email</a></p></body></html>`,
    };
  }

  // 2) Create portal session
  const portalParams = new URLSearchParams();
  portalParams.append('customer', customer.id);
  portalParams.append('return_url', `${ORIGIN}/account`);
  const portalRes = await fetch('https://api.stripe.com/v1/billing_portal/sessions', {
    method: 'POST',
    headers: {
      Authorization: 'Basic ' + Buffer.from(STRIPE_KEY + ':').toString('base64'),
      'Content-Type': 'application/x-www-form-urlencoded',
    },
    body: portalParams.toString(),
  });
  const portal = await portalRes.json();
  if (!portalRes.ok) return { statusCode: portalRes.status, body: JSON.stringify(portal) };

  // 3) 302 redirect to portal
  return {
    statusCode: 302,
    headers: { Location: portal.url },
    body: '',
  };
};
