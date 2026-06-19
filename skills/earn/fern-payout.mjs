// fern-payout.mjs — ③ bank-direct UBI rail via Fern (fernhq.com).
// Off-ramps anicca's USDC (Base) into a recipient's bank: JP (JPY/Zengin) or US (USD).
// Built to the documented Fern API (https://api.fernhq.com). REQUIRES FERN_API_KEY
// (private beta — request at hello@fernhq.com). UNVERIFIED until a real key + a real run;
// per VDD, "done" only after a real transaction lands fiat in a real bank (A4).
//
// Flow per recipient (all API, recipient does Fern-hosted KYC once):
//   1. createCustomer(email) -> { customerId, kycLink }  (recipient completes kycLink once)
//   2. createBankPaymentAccount(customerId, bank) -> destinationPaymentAccountId
//   3. createQuote(USDC/BASE source -> bank destination, amount)
//   4. createTransaction(quoteId) -> executes; webhook/get confirms fiat landed
//
// Env: FERN_API_KEY. Source = anicca's Base USDC (a Fern crypto wallet / FERN_SOURCE_ACCOUNT_ID).

const BASE = 'https://api.fernhq.com';
const KEY = process.env.FERN_API_KEY;

async function fern(method, path, body) {
  if (!KEY) throw new Error('FERN_API_KEY not set (Fern private beta — request at hello@fernhq.com)');
  const res = await fetch(BASE + path, {
    method,
    headers: { Authorization: `Bearer ${KEY}`, 'Content-Type': 'application/json' },
    ...(body ? { body: JSON.stringify(body) } : {}),
  });
  const json = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(`Fern ${method} ${path} ${res.status}: ${JSON.stringify(json).slice(0, 300)}`);
  return json;
}

// 1. Customer (returns a hosted KYC link the recipient completes once)
export async function createCustomer({ email, firstName, customerType = 'INDIVIDUAL' }) {
  return fern('POST', '/customers', { customerType, firstName, email });
}

// 2. Recipient bank account (JP: bankAccountCurrency JPY; US: USD)
export async function createBankPaymentAccount({ customerId, bankName, bankAccountCurrency, bankAccountOwnerEmail, account }) {
  return fern('POST', '/payment-accounts', {
    customerId,
    paymentAccountType: 'EXTERNAL_BANK_ACCOUNT',
    externalBankAccount: { bankName, bankAccountCurrency, bankAccountOwnerEmail, ...account },
  });
}

// 3. Quote: anicca USDC on Base -> recipient bank (JPY/USD)
export async function createQuote({ sourcePaymentAccountId, sourceAmount, destinationPaymentAccountId }) {
  return fern('POST', '/quotes', {
    source: { sourcePaymentAccountId, sourceCurrency: 'USDC', sourcePaymentMethod: 'BASE', sourceAmount: String(sourceAmount) },
    destination: { destinationPaymentAccountId },
  });
}

// 4. Execute the payout (uses a valid, unexpired quoteId)
export async function createTransaction({ quoteId }) {
  return fern('POST', '/transactions', { quoteId });
}

export async function getTransaction(id) { return fern('GET', `/transactions/${id}`); }

// Orchestrator: one recipient, USDC(Base) -> their bank. Returns the transaction.
// recipient = { email, firstName, bankName, currency('JPY'|'USD'), account:{...} }, amountUsdc
export async function payoutToBank(recipient, amountUsdc, sourcePaymentAccountId) {
  const cust = await createCustomer({ email: recipient.email, firstName: recipient.firstName });
  // NOTE: recipient must complete cust.kycLink before a transaction can settle.
  const acct = await createBankPaymentAccount({
    customerId: cust.customerId || cust.id,
    bankName: recipient.bankName,
    bankAccountCurrency: recipient.currency,
    bankAccountOwnerEmail: recipient.email,
    account: recipient.account || {},
  });
  const quote = await createQuote({
    sourcePaymentAccountId,
    sourceAmount: amountUsdc,
    destinationPaymentAccountId: acct.paymentAccountId || acct.id,
  });
  const tx = await createTransaction({ quoteId: quote.quoteId || quote.id });
  return { customer: cust, account: acct, quote, transaction: tx };
}

// CLI self-check (no key needed): prints the configured flow without calling Fern.
if (process.argv[1] && process.argv[1].endsWith('fern-payout.mjs')) {
  console.log(JSON.stringify({
    base: BASE,
    keySet: !!KEY,
    endpoints: ['POST /customers', 'POST /payment-accounts', 'POST /quotes', 'POST /transactions'],
    note: 'UNVERIFIED until FERN_API_KEY + a real transaction lands fiat in a real bank (A4).',
  }, null, 2));
}
