// economy/gig/lib/act.mjs — CLI bridge from run.sh (bash) to gig.mjs's mutating operations. Routes ONE
// action descriptor (argv[2], JSON — non-sensitive fields only) to the matching gig.mjs call; adds NO
// decision logic of its own (HARD RULE #0: this is the tool, run.sh + the model's $ANICCA_ARGS is where
// WHICH gig / WHAT task / WHAT bounty is decided). The signing key NEVER travels via argv (ps-visible)
// or inside the JSON descriptor — it comes in only via the SIGNKEY env var, mirroring lib/wallet.mjs.
import path from "node:path";
import { fileURLToPath } from "node:url";
import { gigPost, gigTake, gigDeliver, gigVerifyAndPay } from "../gig.mjs";

export async function act(input, { signKey = process.env.SIGNKEY } = {}) {
  switch (input && input.action) {
    case "post":
      return gigPost({
        posterPrivateKey: signKey,
        posterAgentId: input.posterAgentId,
        taskSpec: input.taskSpec,
        bountyUsdcBase: input.bountyUsdcBase,
      });
    case "take":
      return gigTake({
        gigId: input.gigId,
        takerAddress: input.takerAddress,
        takerAgentId: input.takerAgentId,
      });
    case "deliver":
      return gigDeliver({ gigId: input.gigId, deliverable: input.deliverable });
    case "verify_and_pay":
      return gigVerifyAndPay({
        gigId: input.gigId,
        verified: input.verified === true,
        posterPrivateKey: signKey,
      });
    default:
      return { ok: false, reason: `unknown action: ${input && input.action}` };
  }
}

if (process.argv[1] && path.resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  let input = {};
  try {
    input = JSON.parse(process.argv[2] || "{}");
  } catch (e) {
    console.log(JSON.stringify({ ok: false, reason: `bad JSON arg: ${e.message}` }));
    process.exit(0);
  }
  act(input)
    .then((r) => console.log(JSON.stringify(r)))
    .catch((e) => console.log(JSON.stringify({ ok: false, reason: e.message || String(e) })));
}
