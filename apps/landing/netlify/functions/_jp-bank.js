// _jp-bank.js — pure validator + notes serializer for JP bank recipients (③ bank-direct).
// Used by income-signup.js (server-side validate before storing) and unit-tested with Node.
// Zengin (全銀) constraints: bankCode 4 digits, branchCode 3 digits, accountType 1=普通/2=当座/4=貯蓄,
// accountNumber up to 7 digits, beneficiaryName in 半角カナ (the only charset Zengin transfers accept).

// 半角カナ block U+FF61–U+FF9F + digits, HALF-WIDTH space, and punctuation Zengin allows in names.
// FIND-F: fullwidth space (U+3000) is NOT Zengin-valid and was wrongly accepted — removed.
const HANKAKU_NAME = /^[｡-ﾟ0-9A-Z()./\- ]+$/;

function normalizeAccountNumber(n) {
  const d = String(n || '').replace(/\D/g, '');
  return d ? d.padStart(7, '0').slice(-7) : '';
}

function validateJpBank(b = {}) {
  const errors = [];
  const bankCode = String(b.bankCode || '').trim();
  const branchCode = String(b.branchCode || '').trim();
  const accountType = String(b.accountType || '1').trim();
  const accountNumber = String(b.accountNumber || '').replace(/\D/g, '');
  const beneficiaryName = String(b.beneficiaryName || '').trim();

  if (!/^\d{4}$/.test(bankCode)) errors.push('bankCode must be 4 digits');
  if (!/^\d{3}$/.test(branchCode)) errors.push('branchCode must be 3 digits');
  if (!['1', '2', '4'].includes(accountType)) errors.push('accountType must be 1, 2, or 4');
  if (!/^\d{1,7}$/.test(accountNumber)) errors.push('accountNumber must be 1-7 digits');
  if (!beneficiaryName || !HANKAKU_NAME.test(beneficiaryName)) errors.push('beneficiaryName must be 半角カナ (e.g. ﾀﾅｶ ﾀﾛｳ)');

  return {
    valid: errors.length === 0,
    errors,
    bank: errors.length === 0
      ? { bankCode, branchCode, accountType, accountNumber: normalizeAccountNumber(accountNumber), beneficiaryName }
      : null,
  };
}

// serialize into the recipients.notes `key=val;` format the watcher parses.
function buildBankNotes(bank) {
  return [
    'method=bank',
    'country=jp',
    `bankCode=${bank.bankCode}`,
    `branchCode=${bank.branchCode}`,
    `accountType=${bank.accountType}`,
    `accountNumber=${bank.accountNumber}`,
    `beneficiaryName=${bank.beneficiaryName}`,
  ].join(';');
}

module.exports = { validateJpBank, buildBankNotes, normalizeAccountNumber };
