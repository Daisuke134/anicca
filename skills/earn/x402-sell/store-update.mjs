#!/usr/bin/env node
// store-update.mjs — SELF-STORE-1 `update` action for the x402_sell loop slot: force a re-listing
// after the model changed the product catalog (serve-v2.mjs PRODUCTS edited, price changed, etc.).
// Unlike `ensure`'s store-ensure-register.mjs, this always re-registers when the store is reachable
// — an explicit catalog edit is exactly the case the freshness/unchanged-count skip in `ensure`
// should NOT apply to. Reuses store-ensure-register.mjs's payTo/manifest/register helpers rather
// than duplicating them.
//
// Env:
//   X402_PUBLIC_URL   the seller's live https origin (required; else degrades honestly)
//   X402_PAYTO        this instance's own receiving wallet (default: derived from the per-instance key)
//
// Loop child-script contract: prints exactly ONE JSON line on stdout, never throws, always exit 0.
//   {"registered":bool,"productCount"?:n,"reregistered":bool,"reason"?:string}
import { writeFileSync, mkdirSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { resolvePayTo, fetchProductCount, runRegister, stateFilePath, STATE_DIR } from "./store-ensure-register.mjs";

export async function forceUpdate(env = process.env, now = Date.now()) {
  const publicUrl = env.X402_PUBLIC_URL || "";
  if (!publicUrl) return { registered: false, reason: "no public URL" };

  const payTo = resolvePayTo(env);
  if (!payTo) return { registered: false, reason: "no payTo resolvable" };

  let productCount;
  try {
    productCount = await fetchProductCount(publicUrl);
  } catch (e) {
    return { registered: false, reason: `manifest unreachable: ${e.message}` };
  }

  const { ok } = await runRegister(publicUrl, env);
  if (ok) {
    try {
      mkdirSync(STATE_DIR, { recursive: true });
      writeFileSync(stateFilePath(payTo), JSON.stringify({ ts: now, productCount, origin: publicUrl }), "utf8");
    } catch { /* best-effort — a write failure must not flip a real registration to failed */ }
    return { registered: true, productCount, reregistered: true };
  }
  return { registered: false, productCount, reregistered: false, reason: "register-x402scan failed" };
}

const isMain = process.argv[1] && fileURLToPath(import.meta.url) === process.argv[1];
if (isMain) {
  forceUpdate()
    .then((out) => console.log(JSON.stringify(out)))
    .catch((e) => console.log(JSON.stringify({ registered: false, reason: e.message || String(e) })));
}
