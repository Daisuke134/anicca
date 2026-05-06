// Anicca Cafe waitlist — POST { email } → store in Supabase cafe_waitlist + send confirmation
exports.handler = async (event) => {
  if (event.httpMethod !== 'POST') return { statusCode: 405, body: 'method not allowed' };
  let body;
  try {
    body = JSON.parse(event.body || '{}');
  } catch {
    return { statusCode: 400, body: 'bad json' };
  }
  const email = String(body.email || '').trim().toLowerCase();
  if (!email || !email.includes('@')) return { statusCode: 400, body: 'invalid email' };

  const SUPABASE_URL = process.env.SUPABASE_URL;
  const SUPABASE_SERVICE_ROLE_KEY = process.env.SUPABASE_SERVICE_ROLE_KEY;
  const RESEND_API_KEY = process.env.RESEND_API_KEY;

  if (SUPABASE_URL && SUPABASE_SERVICE_ROLE_KEY) {
    await fetch(`${SUPABASE_URL}/rest/v1/cafe_waitlist`, {
      method: 'POST',
      headers: {
        apikey: SUPABASE_SERVICE_ROLE_KEY,
        Authorization: `Bearer ${SUPABASE_SERVICE_ROLE_KEY}`,
        'Content-Type': 'application/json',
        Prefer: 'resolution=merge-duplicates,return=minimal',
      },
      body: JSON.stringify({
        email,
        signed_up_at: new Date().toISOString(),
        source: 'aniccaai.com/cafe',
      }),
    }).catch(() => {});
  }

  if (RESEND_API_KEY) {
    await fetch('https://api.resend.com/emails', {
      method: 'POST',
      headers: {
        Authorization: `Bearer ${RESEND_API_KEY}`,
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        from: 'Anicca Cafe <onboarding@resend.dev>',
        to: email,
        subject: "You're on the Anicca Cafe waitlist — June 1 launch",
        html: `<p>Thanks for signing up.</p>
<p>Anicca Cafe launches on Uber Eats Tokyo on <strong>June 1, 2026</strong>.</p>
<p>One drink, one ingredient: cold-pressed mango juice, ¥1,500 / 350ml. Made in a Shinjuku ghost kitchen, delivered to your door.</p>
<p>You'll get one email on launch day with your Uber Eats link. We won't spam you.</p>
<p>10% of every cup's profit goes to 10 humans on basic income. Open source: github.com/Daisuke134/anicca</p>
<p>— Anicca</p>`,
      }),
    }).catch(() => {});
  }

  return { statusCode: 200, body: JSON.stringify({ ok: true }) };
};
