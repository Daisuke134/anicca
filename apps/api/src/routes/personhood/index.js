import express from 'express';
import { verifyPersonhood } from '../../services/personhood/worldid.js';
import { makeNullifierStore } from '../../services/personhood/nullifierStore.js';

// POST /personhood/verify — World ID sybil gate for a UBI claim.
// Body: { proof, merkle_root, nullifier_hash, verification_level, recipient }
// `recipient` is the claim's payout destination; it is used as the signal the IDKit proof was bound
// to on the frontend, so a valid proof cannot be relayed to a different recipient (security #3).
const router = express.Router();
const ACTION = process.env.WORLDCOIN_ACTION || 'claim-ubi';

router.post('/verify', async (req, res) => {
  const { proof, merkle_root, nullifier_hash, verification_level, recipient } = req.body || {};
  if (!recipient) return res.status(400).json({ ok: false, reason: 'recipient_required' });
  try {
    const result = await verifyPersonhood({
      proofBundle: { proof, merkle_root, nullifier_hash, verification_level },
      signal: recipient,
      store: makeNullifierStore({ action: ACTION, signal: recipient }),
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
});

export default router;
