// economy/gig/lib/board.mjs — CLI wrapper so run.sh (bash) can read REAL board state via gig.mjs's own
// gigList() (never re-implements board reads). Two read-only views:
//   `open`             — candidates the model can decide to take (decideGigAction's take-eligibility
//                         input, and the raw material the model reasons over via $ANICCA_ARGS).
//   `paid-to <address>` — gigs where THIS instance was the taker and has ALREADY been paid — run.sh
//                         diffs this against its own seen-payouts bookkeeping to detect new inbound
//                         revenue to record on the earn ledger (deterministic bookkeeping, not judgment).
import path from "node:path";
import { fileURLToPath } from "node:url";
import { gigList } from "../gig.mjs";

async function main(cmd, arg) {
  if (cmd === "open") {
    const { gigs } = await gigList({ status: "open" });
    return gigs;
  }
  if (cmd === "paid-to" && arg) {
    const { gigs } = await gigList({ status: "paid" });
    return gigs.filter((g) => g.taker && g.taker.toLowerCase() === arg.toLowerCase());
  }
  return [];
}

if (process.argv[1] && path.resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  const [, , cmd, arg] = process.argv;
  main(cmd, arg)
    .then((r) => console.log(JSON.stringify(r)))
    .catch(() => console.log("[]"));
}
