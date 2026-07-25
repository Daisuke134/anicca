// facilitator-init.mjs — safe, self-healing x402ResourceServer.initialize() (T2 fix, 2026-07-25).
//
// Root cause this replaces: @x402/express's paymentMiddleware(routes, resourceServer) defaults
// syncFacilitatorOnStart=true, which calls resourceServer.initialize() synchronously at
// middleware-mount time (i.e. at process boot, before any request) and stores the promise WITHOUT
// a .catch() until the first paid request awaits it
// (node_modules/@x402/express/dist/cjs/index.js:148). On Node v25 an unhandled promise rejection
// is FATAL by default (Node 15+) — so a single transient facilitator hiccup (DNS ENOTFOUND, a
// Coinbase 504) during boot killed the ENTIRE process, with zero retry, before it ever served one
// request. That is the confirmed cause of the crash cascades in logs/x402-{claude-p,franklin1,
// franklin2}.err.log and logs/image-franklin1.err.log ("getaddrinfo ENOTFOUND
// api.cdp.coinbase.com" / "Facilitator getSupported failed (504)").
//
// syncFacilitatorOnStart=false is NOT simply "lazy instead of eager": when false, the library
// never calls initialize() AT ALL (paymentMiddlewareFromHTTPServer's initializeHttpServer() early-
// returns whenever !syncFacilitatorOnStart, and the request handler's call site is gated the same
// way) — every request then fails hard with "Facilitator does not support exact on eip155:8453.
// Make sure to call initialize()" forever (verified live 2026-07-25: this was our first attempt at
// this fix and it went straight to 500 on every request). So syncFacilitatorOnStart=false must be
// paired with calling resourceServer.initialize() ourselves — this helper does that, with our own
// try/catch (so a failure can never become an unhandled rejection) plus fast boot-time retries and
// an indefinite background retry loop so the server self-heals once the facilitator recovers,
// instead of either crashing (the original bug) or wedging in a permanently-uninitialized state
// (our first, incomplete fix).
export async function ensureFacilitatorInitialized(
  resourceServer,
  { bootAttempts = 5, bootDelayMs = 1000, backgroundRetryMs = 30_000, log = console.error } = {},
) {
  const attempt = async () => {
    try {
      await resourceServer.initialize();
      return true;
    } catch (err) {
      log(JSON.stringify({ facilitator_init: "failed", error: String((err && err.message) || err) }));
      return false;
    }
  };
  for (let i = 0; i < bootAttempts; i++) {
    if (await attempt()) return true;
    if (i < bootAttempts - 1) await new Promise((r) => setTimeout(r, bootDelayMs * (i + 1)));
  }
  // Still down after boot retries (e.g. an extended facilitator outage): keep the server up and
  // keep trying in the background so it self-heals without a manual restart. unref() so this timer
  // never keeps the process alive on its own.
  const timer = setInterval(async () => {
    if (await attempt()) clearInterval(timer);
  }, backgroundRetryMs);
  timer.unref?.();
  return false;
}
