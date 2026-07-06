// record.mjs — CLI bridge the run.sh entrypoint uses to append ONE earn-ledger line
// and report whether this wake was profitable (GATE-0). Reads a JSON line from argv[2].
// Usage: node lib/record.mjs '<json>' [ledgerPath]
//   exit 0 = line recorded (profitable OR narrate-only discovery)
//   prints "PROFITABLE" / "NARRATE" on stdout for the shell to branch on (stdout contract is
//   UNCHANGED by the P1 guard below — run.sh's exact-match `[ "$OUT" = "PROFITABLE" ]` checks
//   must keep working; the halt signal is stderr-only, see earn-guard.mjs's CLI for the
//   dedicated exit-code guard clause callers should use to actually stop on HALT).
import path from "node:path";
import { fileURLToPath } from "node:url";
import { deriveLine, isProfitable, appendLedger } from "../../_shared/lib/ledger.mjs";
import { assertOwnIdentityOnly } from "../../_shared/lib/identity-guard.mjs";
import { checkHalt } from "../../_shared/lib/earn-guard.mjs";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const DEFAULT_LEDGER = path.join(__dirname, "..", "state", "earn-ledger.jsonl");

export async function record(jsonStr, ledgerPath = DEFAULT_LEDGER) {
  const input = JSON.parse(jsonStr);
  const line = deriveLine(input);
  // MALICE-GUARD (spec 28 §3): fail CLOSED before any earn line is recorded —
  // no user-PII env may be present and the source must be an own-identity channel.
  assertOwnIdentityOnly(line);
  await appendLedger(ledgerPath, line);
  const profitable = isProfitable(line);
  // P1 (spec §3/§4): after appending, ask whether the CUMULATIVE earn>spend invariant
  // (this skill's history AND this wallet's history) still holds. This never blocks the
  // append (the line already happened) — it only reports whether the NEXT pass may run.
  const halt = await checkHalt(ledgerPath, { wallet: line.wallet, source: line.source });
  return { line, profitable, halt };
}

// Run only when invoked directly (not when imported by tests).
if (process.argv[1] && path.resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  const jsonStr = process.argv[2];
  const ledgerPath = process.argv[3] || DEFAULT_LEDGER;
  if (!jsonStr) {
    console.error("record.mjs: missing JSON arg");
    process.exit(2);
  }
  record(jsonStr, ledgerPath)
    .then(({ line, profitable, halt }) => {
      console.log(profitable ? "PROFITABLE" : "NARRATE");
      console.error(`recorded net=${line.net_usdc} tx=${line.tx || "-"} status=${line.status || "-"}`);
      if (halt.halt) {
        console.error(`P1-GUARD HALT: ${halt.reason} — cumulative earn>spend invariant broken, this skill must STOP (fail-closed).`);
      }
    })
    .catch((e) => {
      console.error("record.mjs error:", e.message);
      process.exit(1);
    });
}
