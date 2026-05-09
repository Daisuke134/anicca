// Anicca Retreats application — POST { email, retreatId, motive, prior }
// → store in Supabase retreat_applications + Slack notify + Resend confirmation
exports.handler = async (event) => {
  if (event.httpMethod !== 'POST') return { statusCode: 405, body: 'method not allowed' };
  let body;
  try {
    body = JSON.parse(event.body || '{}');
  } catch {
    return { statusCode: 400, body: 'bad json' };
  }
  const email = String(body.email || '').trim().toLowerCase();
  const retreatId = String(body.retreatId || 'any').trim();
  const motive = String(body.motive || '').trim().slice(0, 4000);
  const prior = ['none', 'one', 'multiple'].includes(body.prior) ? body.prior : 'none';
  if (!email || !email.includes('@')) return { statusCode: 400, body: 'invalid email' };

  const SUPABASE_URL = process.env.SUPABASE_URL;
  const SUPABASE_SERVICE_ROLE_KEY = process.env.SUPABASE_SERVICE_ROLE_KEY;
  const RESEND_API_KEY = process.env.RESEND_API_KEY;
  const SLACK_BOT_TOKEN = process.env.SLACK_BOT_TOKEN;
  const SLACK_CHANNEL = process.env.SLACK_CHANNEL_METRICS || 'C091G3PKHL2';

  // 1. Persist to Supabase (best-effort)
  if (SUPABASE_URL && SUPABASE_SERVICE_ROLE_KEY) {
    await fetch(`${SUPABASE_URL}/rest/v1/retreat_applications`, {
      method: 'POST',
      headers: {
        apikey: SUPABASE_SERVICE_ROLE_KEY,
        Authorization: `Bearer ${SUPABASE_SERVICE_ROLE_KEY}`,
        'Content-Type': 'application/json',
        Prefer: 'resolution=merge-duplicates,return=minimal',
      },
      body: JSON.stringify({
        email,
        retreat_id: retreatId,
        motive,
        prior_retreats: prior,
        applied_at: new Date().toISOString(),
        source: 'aniccaai.com/retreat',
        status: 'pending',
      }),
    }).catch(() => {});
  }

  // 2. Slack notify (always — Anicca needs to see new applications fast)
  if (SLACK_BOT_TOKEN) {
    const text = `🏞️ *Anicca Retreats — new application*
*email*: \`${email}\`
*retreat*: \`${retreatId}\`
*prior 10-day retreats*: ${prior}
*why now*: ${motive || '(blank)'}

Phase 3 cron will screen + approve/reject. Reply by hand if urgent.`;
    await fetch('https://slack.com/api/chat.postMessage', {
      method: 'POST',
      headers: {
        Authorization: `Bearer ${SLACK_BOT_TOKEN}`,
        'Content-Type': 'application/json; charset=utf-8',
      },
      body: JSON.stringify({ channel: SLACK_CHANNEL, text, mrkdwn: true }),
    }).catch(() => {});
  }

  // 3. Resend confirmation to applicant
  if (RESEND_API_KEY) {
    await fetch('https://api.resend.com/emails', {
      method: 'POST',
      headers: {
        Authorization: `Bearer ${RESEND_API_KEY}`,
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        from: 'Anicca Retreats <onboarding@resend.dev>',
        to: email,
        subject: 'Your Anicca Retreats application — received',
        html: `<p>Thank you for applying to <strong>Anicca Retreats</strong>.</p>
<p>You applied for: <code>${retreatId}</code></p>
<p>Anicca screens applications within a week and a human reviews each one. If accepted, you'll receive a packing list, the venue address, and arrival instructions about three weeks before the start date.</p>
<p>Until then: there is nothing for you to do. The retreat begins now, in how you wait.</p>
<p>— Anicca<br/>retreat@aniccaai.com</p>`,
      }),
    }).catch(() => {});
  }

  return {
    statusCode: 200,
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ ok: true, email, retreatId }),
  };
};
