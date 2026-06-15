#!/usr/bin/env node
// telnyx-verify-number.mjs — verify a destination number on the Telnyx account so the
// D60 portal level allows outbound calls to it (Telnyx error 10010 "non-verified numbers").
//
// Telnyx places a real verification CALL (or SMS) to the number with a code; once the code
// is submitted, the number is permanently verified and the B-call Charon runner
// (life-call-telnyx.mjs) can dial it. For +818046270314 the callee is Dais, who hears/reads
// the code (he is the callee in the loop, exactly as the B-call spec intends).
//
// Usage:
//   node scripts/telnyx-verify-number.mjs --request --method call   place the verify call to Dais
//   node scripts/telnyx-verify-number.mjs --request --method sms     send the verify code via SMS
//   node scripts/telnyx-verify-number.mjs --submit --code 123456     submit the code → verified
//   node scripts/telnyx-verify-number.mjs --status                   list verified numbers
//   (override the target with --number=+E164; default = +818046270314)
const API = process.env.TELNYX_API_KEY;
const args = process.argv.slice(2);
let NUMBER = process.env.LIFE_CALL_TO || "+818046270314";
let METHOD = "call";
let CODE = "";
for (const a of args) {
  if (a.startsWith("--number=")) NUMBER = a.slice("--number=".length);
  else if (a.startsWith("--method=")) METHOD = a.slice("--method=".length);
  else if (a === "--method") METHOD = args[args.indexOf(a) + 1];
  else if (a.startsWith("--code=")) CODE = a.slice("--code=".length);
  else if (a === "--code") CODE = args[args.indexOf(a) + 1];
}
const REQUEST = args.includes("--request");
const SUBMIT = args.includes("--submit");
const STATUS = args.includes("--status");

function die(m) { console.error("FATAL:", m); process.exit(1); }
if (!API) die("TELNYX_API_KEY missing in env");

async function tx(method, p, body) {
  const res = await fetch(`https://api.telnyx.com/v2${p}`, {
    method,
    headers: { Authorization: `Bearer ${API}`, "Content-Type": "application/json" },
    body: body ? JSON.stringify(body) : undefined,
  });
  const j = await res.json().catch(() => ({}));
  return { ok: res.ok, status: res.status, j };
}

async function main() {
  if (STATUS) {
    const r = await tx("GET", "/verified_numbers");
    console.log(JSON.stringify(r.j, null, 2));
    process.exit(r.ok ? 0 : 1);
  }
  if (REQUEST) {
    const r = await tx("POST", "/verified_numbers", {
      phone_number: NUMBER,
      verification_method: METHOD === "sms" ? "sms" : "call",
    });
    console.log(JSON.stringify({ requested: NUMBER, method: METHOD, ...r.j }, null, 2));
    process.exit(r.ok ? 0 : 1);
  }
  if (SUBMIT) {
    if (!CODE) die("--code <verification code> required for --submit");
    const r = await tx("POST", `/verified_numbers/${encodeURIComponent(NUMBER)}/actions/verify`, {
      verification_code: CODE,
    });
    console.log(JSON.stringify(r.j, null, 2));
    process.exit(r.ok ? 0 : 2);
  }
  die("one of --request | --submit | --status is required");
}
main().catch((e) => die(e.message));
