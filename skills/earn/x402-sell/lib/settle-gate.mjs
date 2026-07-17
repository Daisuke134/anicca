// v2.6+ は settle 失敗時にも PAYMENT-RESPONSE を付与する。存在チェックでは偽陽性になる(FIX-3再発)。
// base64 デコードして SettleResponse.success===true のみ settled とする。
export function isSettled(headerValue) {
  if (!headerValue) return false;
  try {
    const d = JSON.parse(Buffer.from(String(headerValue), "base64").toString("utf8"));
    return d && d.success === true;
  } catch { return false; }
}
export function decodePayer(headerValue) {
  if (!headerValue) return null;
  try {
    const d = JSON.parse(Buffer.from(String(headerValue), "base64").toString("utf8"));
    return d?.payer || null;
  } catch { return null; }
}
