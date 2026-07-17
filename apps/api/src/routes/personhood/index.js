import express from 'express';
import rateLimit from 'express-rate-limit';
import { verifyPersonhood } from '../../services/personhood/worldid.js';
import { makeNullifierStore } from '../../services/personhood/nullifierStore.js';

// POST /personhood/verify — World ID sybil gate for a UBI claim.
// Body: { proof, merkle_root, nullifier_hash, verification_level, recipient }
// `recipient` is the claim's payout destination; it is used as the signal the IDKit proof was bound
// to on the frontend, so a valid proof cannot be relayed to a different recipient (security #3).
const router = express.Router();
const ACTION = process.env.WORLDCOIN_ACTION || 'claim-ubi';

// Rate limit: each verify hits Worldcoin's upstream before the dedup short-circuits, so cap the
// flood surface (VCSDD FIND-003). 20 req / 5 min per IP — generous for a real human claim.
const verifyLimiter = rateLimit({ windowMs: 5 * 60 * 1000, max: 20, standardHeaders: true, legacyHeaders: false });

// Testable handler factory — deps injected so the route can be exercised without a live DB/Worldcoin
// (closes VCSDD FIND-002). Production route uses the real defaults.
export function makeVerifyHandler({ verify = verifyPersonhood, makeStore = makeNullifierStore, action = ACTION } = {}) {
  return async (req, res) => {
    const { proof, merkle_root, nullifier_hash, verification_level, recipient } = req.body || {};
    if (!recipient) return res.status(400).json({ ok: false, reason: 'recipient_required' });
    try {
      const result = await verify({
        proofBundle: { proof, merkle_root, nullifier_hash, verification_level },
        signal: recipient,
        store: makeStore({ action, signal: recipient }),
      });
      if (!result.allowed) {
        const code = result.reason === 'already_claimed' ? 409 : result.reason === 'level_too_low' ? 403 : 422;
        return res.status(code).json({ ok: false, reason: result.reason });
      }
      return res.json({ ok: true, nullifier_hash: result.nullifier_hash });
    } catch (e) {
      // misconfig (missing WORLDCOIN_APP_ID / store) or upstream error — never leak details, never allow.
      console.error('[personhood/verify]', e?.message);
      return res.status(500).json({ ok: false, reason: 'verify_error' });
    }
  };
}

router.post('/verify', verifyLimiter, makeVerifyHandler());

export default router;
