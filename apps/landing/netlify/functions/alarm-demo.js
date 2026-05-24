// Anicca Alarm — free one-time demo call (experience before paying).
// POST { name?, phone, wakeTime?, ics_url?, home_address?, stakeholders? }
//   -> 1 free demo per phone (demo_calls table). Places an immediate Twilio call
//      to the imokenet bridge (Gemini Live wake voice), records the demo,
//      and stashes any optional setup into subscriber_profiles as status='demo'
//      so it carries over when they subscribe.
const SUPABASE_URL = process.env.SUPABASE_URL;
const SUPABASE_KEY = process.env.SUPABASE_SERVICE_ROLE_KEY;
const TW_SID = process.env.TWILIO_ACCOUNT_SID;
const TW_TOKEN = process.env.TWILIO_AUTH_TOKEN;
const TW_FROM = process.env.TWILIO_PHONE_NUMBER;
const BRIDGE_URL = process.env.ALARM_BRIDGE_URL; // stable Tailscale Funnel base, e.g. https://...ts.net

async function supa(method, path, body, extra) {
  const r = await fetch(`${SUPABASE_URL}/rest/v1/${path}`, {
    method,
    headers: {
      apikey: SUPABASE_KEY, Authorization: `Bearer ${SUPABASE_KEY}`,
      "Content-Type": "application/json", ...(extra || {}),
    },
    body: body ? JSON.stringify(body) : undefined,
  });
  const txt = await r.text();
  try { return { ok: r.ok, status: r.status, data: JSON.parse(txt) }; } catch { return { ok: r.ok, status: r.status, data: txt }; }
}

function normPhone(p) {
  let t = String(p || "").replace(/[\s\-()]/g, "");
  // Japanese domestic ("08046270314") -> E.164 (+818046270314): drop the trunk 0.
  if (!t.startsWith("+") && t.startsWith("0")) t = "+81" + t.slice(1);
  t = t.replace(/[^\d+]/g, "");
  return /^\+[1-9]\d{6,14}$/.test(t.startsWith("+") ? t : `+${t}`)
    ? (t.startsWith("+") ? t : `+${t}`)
    : null;
}

// Did this phone already ANSWER a demo? (lets a missed call be retried)
async function priorDemoAnswered(callSid) {
  if (!callSid) return false;
  try {
    const r = await fetch(`https://api.twilio.com/2010-04-01/Accounts/${TW_SID}/Calls/${callSid}.json`, {
      headers: { Authorization: "Basic " + Buffer.from(`${TW_SID}:${TW_TOKEN}`).toString("base64") },
    });
    const j = await r.json();
    return j.status === "completed" && Number(j.duration || 0) >= 8;
  } catch { return false; }
}

exports.handler = async (event) => {
  if (event.httpMethod !== "POST") return { statusCode: 405, body: "method not allowed" };
  if (!SUPABASE_URL || !SUPABASE_KEY || !TW_SID || !TW_TOKEN || !TW_FROM || !BRIDGE_URL) {
    return { statusCode: 500, body: "missing config" };
  }
  let b; try { b = JSON.parse(event.body || "{}"); } catch { return { statusCode: 400, body: "bad json" }; }

  const phone = normPhone(b.phone);
  if (!phone) return { statusCode: 400, body: JSON.stringify({ error: "invalid_phone" }) };
  const name = (b.name || "").toString().slice(0, 40);

  // 1 free *answered* demo per phone — but a missed/unanswered call can be retried.
  const existing = await supa("GET", `demo_calls?phone=eq.${encodeURIComponent(phone)}&select=phone,call_sid`);
  const prior = Array.isArray(existing.data) && existing.data[0];
  if (prior && (await priorDemoAnswered(prior.call_sid))) {
    return { statusCode: 409, headers: { "Content-Type": "application/json" }, body: JSON.stringify({ error: "demo_used" }) };
  }

  // place the call: Twilio -> imokenet bridge twiml (Gemini Live wake voice)
  const twiml = `${BRIDGE_URL.replace(/\/$/, "")}/twiml?` +
    new URLSearchParams({ name: name || "there", mode: "wakeup_generic", demo: "1" }).toString();
  const form = new URLSearchParams({ To: phone, From: TW_FROM, Url: twiml, Method: "GET" });
  let callSid;
  try {
    const tr = await fetch(`https://api.twilio.com/2010-04-01/Accounts/${TW_SID}/Calls.json`, {
      method: "POST",
      headers: {
        Authorization: "Basic " + Buffer.from(`${TW_SID}:${TW_TOKEN}`).toString("base64"),
        "Content-Type": "application/x-www-form-urlencoded",
      },
      body: form.toString(),
    });
    const j = await tr.json();
    if (!tr.ok) return { statusCode: 502, body: JSON.stringify({ error: "call_failed", detail: j.message || j }) };
    callSid = j.sid;
  } catch (e) {
    return { statusCode: 502, body: JSON.stringify({ error: "call_failed", detail: String(e) }) };
  }

  // record the demo (1/phone) + ip
  const ip = (event.headers["x-nf-client-connection-ip"] || event.headers["x-forwarded-for"] || "").split(",")[0];
  await supa("POST", "demo_calls?on_conflict=phone",
    { phone, name: name || null, call_sid: callSid, ip: ip || null },
    { Prefer: "resolution=merge-duplicates,return=minimal" });

  // stash optional setup so it carries to subscription
  const profile = { phone, status: "demo", updated_at: new Date().toISOString() };
  if (b.wakeTime) profile.wake_time = b.wakeTime;
  if (b.ics_url) profile.ics_url = b.ics_url;
  if (b.home_address) profile.home_address = b.home_address;
  if (Array.isArray(b.stakeholders)) profile.stakeholders = b.stakeholders;
  await supa("POST", "subscriber_profiles?on_conflict=phone", profile,
    { Prefer: "resolution=merge-duplicates,return=minimal" });

  return { statusCode: 200, headers: { "Content-Type": "application/json" }, body: JSON.stringify({ ok: true, call_sid: callSid }) };
};
