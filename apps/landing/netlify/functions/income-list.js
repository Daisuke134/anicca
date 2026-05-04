// GET /api/income/list
// Public ledger: count of active recipients + recent payouts (last 12 months)

const SUPABASE_URL = process.env.SUPABASE_URL;
const SUPABASE_ANON = process.env.SUPABASE_ANON_KEY;

async function supabaseGet(path) {
  const res = await fetch(`${SUPABASE_URL}/rest/v1/${path}`, {
    headers: { apikey: SUPABASE_ANON, Authorization: `Bearer ${SUPABASE_ANON}` },
  });
  return res.ok ? res.json() : null;
}

exports.handler = async () => {
  if (!SUPABASE_URL || !SUPABASE_ANON) {
    return { statusCode: 500, body: 'missing config' };
  }

  const recipients = (await supabaseGet('recipients?select=id,status&status=eq.active')) || [];
  const waitlist = (await supabaseGet('recipients?select=id&status=eq.waitlist')) || [];
  const payouts =
    (await supabaseGet('payouts?select=month,amount_usd,status&status=eq.succeeded&order=paid_at.desc&limit=120')) ||
    [];

  // group by month
  const byMonth = {};
  let totalPaid = 0;
  for (const p of payouts) {
    const m = p.month || 'unknown';
    byMonth[m] = byMonth[m] || { total_usd: 0, count: 0 };
    byMonth[m].total_usd += Number(p.amount_usd || 0);
    byMonth[m].count += 1;
    totalPaid += Number(p.amount_usd || 0);
  }

  return {
    statusCode: 200,
    headers: { 'Content-Type': 'application/json', 'Cache-Control': 'public, max-age=60' },
    body: JSON.stringify({
      active_count: recipients.length,
      waitlist_count: waitlist.length,
      total_paid_usd: Math.round(totalPaid * 100) / 100,
      by_month: byMonth,
      updated_at: new Date().toISOString(),
    }),
  };
};
