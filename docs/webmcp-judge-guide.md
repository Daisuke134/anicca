# Life Manager Money Printer — 60-second judge guide

Live app: <https://aniccaai.com/money-printer>

No login, payment, API key, or private Life Manager account is required. The judge tenant is isolated from owner
credentials and external-effect authority. It may change only its internal opportunity/workroom state.

## Primary path — ChatGPT in-app browser

1. Open the live app. Confirm the banner says `Judge guest — external effects disabled`.
2. Ask ChatGPT:

   > List the Site tools exposed by this page. Call `inspect_money_printer`, summarize the board and money truth,
   > then inspect one qualified workroom. Do not perform an external application, delivery, payment, or money effect.

3. Confirm the response is structured and matches the visible board. `Paid & verified` may be empty even when an
   application receipt exists; applications and opportunity value are not revenue.
4. Optional internal write:

   > Use `add_opportunity` for one public paid-opportunity URL, then inspect its workroom and show the visible state
   > change. Stop at qualification and do not create an external effect.

The page currently exposes five focused tools: `inspect_money_printer`, `add_opportunity`, `inspect_workroom`,
`inspect_next_human_task`, and the state-dependent `record_human_answer`.

## What to look for

- Multiple public opportunities from a page-independent cloud scout.
- Durable job/receipt activity that survives page close and worker restart.
- A read-only verified Lancers `application_receipt` for project `5593484`, proposal `27863414`.
- `Paid & verified` remains zero without a payment receipt.
- No private credential, raw model response, provider error, Telegram chat ID, or owner state appears.

## Chrome fallback

Use Chrome 149 or newer, enable `chrome://flags/#enable-webmcp-testing`, restart Chrome, and open the same URL.
Inspect the page's available tools and repeat the read call before trying the internal write. The implementation is
top-level imperative `document.modelContext.registerTool()`; it does not depend on an iframe or declarative markup.

## Known limits during evidence collection

- The 24-hour record requires three successful natural 8-hour scout windows from one deployed release; that
  observation is still accumulating.
- The judge tenant blocks external effects. The displayed Lancers application is imported read-only from an
  independently verified provider receipt and append-only local ledger.
- A browser/client rollout issue does not change server truth; compare the live Dashboard and use the Chrome fallback.
