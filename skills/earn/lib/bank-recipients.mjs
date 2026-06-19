// bank-recipients.mjs — parse a recipients.notes string (the `key=val;` format written by the landing
// income-signup _jp-bank.buildBankNotes) into a bankWatcherPass recipient. Closes the round-trip:
// /income form → income-signup (validate+store notes) → here (parse) → bankWatcherPass → gmo-furikomi.

export function parseNotes(notes) {
  const kv = {};
  for (const part of String(notes || '').split(';')) {
    const i = part.indexOf('=');
    if (i > 0) kv[part.slice(0, i).trim()] = part.slice(i + 1).trim();
  }
  return kv;
}

// row: { id, notes } from Supabase recipients. Returns a bank recipient or null (not a JP bank row).
export function parseBankRecipient(row = {}) {
  const kv = parseNotes(row.notes);
  if (kv.method !== 'bank') return null;
  // FIND-105 (dispatch-boundary dedupe): a row carrying a GMO submit ref was ALREADY sent once. Never
  // auto-redispatch it (that is double-pay) even if a human flips it back to 'queued'. Deliberate re-send
  // requires the operator to explicitly clear ref= first — an intentional action, not an accidental requeue.
  if (kv.ref) return null;
  if ((kv.country || '').toLowerCase() === 'jp') {
    if (!kv.bankCode || !kv.branchCode || !kv.accountNumber || !kv.beneficiaryName) return null;
    return {
      id: row.id,
      provider: 'gmo',
      currency: 'JPY',
      raw: row.notes, // FIND-101: keep original notes so claim can preserve them while stamping claimed_at
      bank: {
        bankCode: kv.bankCode,
        branchCode: kv.branchCode,
        accountType: kv.accountType || '1',
        accountNumber: kv.accountNumber,
        beneficiaryName: kv.beneficiaryName,
      },
    };
  }
  return null; // non-JP bank rows: future rails (Rain/etc.)
}

// map a list of recipient rows → bank recipients (drops non-bank / incomplete).
export function bankRecipientsFromRows(rows = []) {
  return rows.map(parseBankRecipient).filter(Boolean);
}
