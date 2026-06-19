// gmo-furikomi.mjs — ③ JP bank rail adapter: GMO Aozora Net Bank 一括振込API (bulk transfer).
// ONE API call fans out JPY from OUR (法人) account to N recipients' banks (any JP bank, Zengin).
// Field names verified against the official GMO SDK (github.com/gmoaozora/gmo-aozora-api-java
// BulkTransferRequest + BulkTransferInfo). Pure builder is unit-tested; the live submit needs OAuth2
// access (GMO 口座 + 開発者ポータル登録) so it is UNVERIFIED until a real account/token (sunabar sandbox first).
//
// Invariant (資金決済法): we transfer OUR OWN funds as 給付 (own JPY balance → recipients). Never intermediate.

export const API_BASE = process.env.GMO_AOZORA_API_BASE || "https://api.gmo-aozora.com/ganb/api/personal/v1";

// accountTypeCode: "1"=普通(ordinary), "2"=当座(checking), "4"=貯蓄
// transfers: [{ to, amount(JPY int), bank:{ bankCode, branchCode, accountTypeCode?, accountNumber, beneficiaryName } }]
export function buildBulkTransferRequest({ accountId, remitterName, transferDesignatedDate, transferDataName = "ANICCA-UBI", transfers = [] }) {
  if (!accountId || !remitterName || !transferDesignatedDate) throw new Error("accountId, remitterName, transferDesignatedDate required");
  if (!Array.isArray(transfers) || transfers.length === 0) throw new Error("transfers required");
  const bulkTransfers = transfers.map((t, i) => {
    const b = t.bank || {};
    if (!b.bankCode || !b.branchCode || !b.accountNumber || !b.beneficiaryName) {
      throw new Error(`transfer[${i}] missing bank fields (bankCode/branchCode/accountNumber/beneficiaryName)`);
    }
    if (!Number.isInteger(t.amount) || t.amount <= 0) throw new Error(`transfer[${i}] invalid amount`);
    return {
      itemId: String(i + 1),
      beneficiaryBankCode: b.bankCode,
      beneficiaryBranchCode: b.branchCode,
      accountTypeCode: b.accountType || b.accountTypeCode || "1", // accept accountType (from parseBankRecipient) or accountTypeCode; default 普通
      accountNumber: b.accountNumber,
      beneficiaryName: b.beneficiaryName,        // 半角カナ per Zengin
      transferAmount: String(t.amount),
      ediInfo: "",
    };
  });
  const totalAmount = transfers.reduce((s, t) => s + t.amount, 0);
  return {
    accountId,
    remitterName,
    transferDesignatedDate,                  // YYYYMMDD
    transferDataName,
    totalCount: String(transfers.length),
    totalAmount: String(totalAmount),
    bulkTransfers,
  };
}

// LIVE submit — UNVERIFIED until GMO_AOZORA_ACCESS_TOKEN (OAuth2) + a real/sandbox account.
export async function submitBulkTransfer(request, token, base = API_BASE) {
  if (!token) throw new Error("GMO OAuth2 access token required (gmo dev portal / sunabar). UNVERIFIED until real token.");
  // FIND-B: send the idempotency key as a header (out of the JSON body so GMO won't reject an unknown field)
  // so a retry of the SAME batch is de-duped server-side. Defense-in-depth atop the no-auto-requeue policy.
  const { idempotencyKey, ...body } = request;
  const headers = { Authorization: `Bearer ${token}`, "Content-Type": "application/json", "x-access-token": token };
  if (idempotencyKey) headers["x-idempotency-key"] = idempotencyKey;
  const res = await fetch(`${base}/bulktransfer/request`, {
    method: "POST",
    headers,
    body: JSON.stringify(body),
  });
  const json = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(`GMO bulktransfer ${res.status}: ${JSON.stringify(json).slice(0, 300)}`);
  return json; // apptransferNo / status — poll bulktransfer/status to confirm 振込完了
}

// CLI self-check (no token): build + print a sample payload to prove the shape.
if (process.argv[1] && process.argv[1].endsWith("gmo-furikomi.mjs")) {
  const sample = buildBulkTransferRequest({
    accountId: "SANDBOX_ACCT", remitterName: "ｱﾆﾂﾁﬔ", transferDesignatedDate: "20260620",
    transfers: [
      { to: "u1", amount: 20000, bank: { bankCode: "0005", branchCode: "001", accountNumber: "1234567", beneficiaryName: "ﾀﾅｶ ﾀﾛｳ" } },
      { to: "u2", amount: 20000, bank: { bankCode: "9900", branchCode: "008", accountNumber: "7654321", beneficiaryName: "ｻﾄｳ ﾊﾅｺ" } },
    ],
  });
  console.log(JSON.stringify(sample, null, 2));
  console.log("\nUNVERIFIED until GMO OAuth2 token + sunabar/法人 account.");
}
