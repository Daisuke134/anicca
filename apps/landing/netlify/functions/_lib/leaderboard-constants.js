// Agents at Arms leaderboard constants (VCSDD GREEN).
// excludeSet(row) is PER-ROW: it must contain the row's OWN id so self-transfers never count as
// earnings, plus our own instances and the parent-treasury/seed wallets.

// Our canonical instance wallet ids (0x, lowercased at use). Fill as instances come online.
const OUR_INSTANCE_IDS = [];

// Parent-treasury / seed wallets. Inflows FROM these are seed funding, NOT earnings.
// TODO: replace the placeholder with the real founder/treasury Base wallet(s) (e.g. 0x810f…).
const SEED_ADDRESSES = ["0x00000000000000000000000000000000000000a1"];

function excludeSet(row) {
  const s = new Set();
  if (row && row.id) s.add(String(row.id).toLowerCase());
  for (const a of OUR_INSTANCE_IDS) s.add(String(a).toLowerCase());
  for (const a of SEED_ADDRESSES) s.add(String(a).toLowerCase());
  return s;
}

module.exports = { OUR_INSTANCE_IDS, SEED_ADDRESSES, excludeSet };
