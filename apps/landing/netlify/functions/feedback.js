// In-app feedback → Resend email to Dais. POST { text, locale, appVersion }
// Mirrors lead-magnet.js pattern (Resend api.resend.com/emails).
export const handler = async (event) => {
  if (event.httpMethod !== 'POST') return { statusCode: 405, body: 'method not allowed' };
  let body;
  try { body = JSON.parse(event.body || '{}'); }
  catch { return { statusCode: 400, body: 'bad json' }; }

  const text = String(body.text || '');
  const locale = String(body.locale || 'en');
  const appVersion = String(body.appVersion || 'unknown');

  if (text.length < 5) return { statusCode: 400, body: JSON.stringify({ error: 'text too short' }) };
  if (text.length > 2000) return { statusCode: 413, body: JSON.stringify({ error: 'text too long' }) };

  const RESEND_API_KEY = process.env.RESEND_API_KEY;
  if (RESEND_API_KEY) {
    const r = await fetch('https://api.resend.com/emails', {
      method: 'POST',
      headers: { Authorization: `Bearer ${RESEND_API_KEY}`, 'Content-Type': 'application/json' },
      body: JSON.stringify({
        from: 'Anicca Feedback <onboarding@resend.dev>',
        to: 'keiodaisuke@gmail.com',
        subject: `[Anicca Feedback] ${locale} ${new Date().toISOString()}`,
        text: `App version: ${appVersion}\nLocale: ${locale}\n\n---\n\n${text}`,
      }),
    });
    if (!r.ok) {
      const txt = await r.text();
      return { statusCode: 502, body: JSON.stringify({ error: `resend: ${txt}` }) };
    }
  }
  return { statusCode: 200, body: JSON.stringify({ ok: true }) };
};
