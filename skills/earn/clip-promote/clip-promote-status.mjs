// clip-promote-status.mjs — REQ-LV-120: clip-promote's own status judgment, independent of the
// Cadence Contract (REQ-LV-100 explicitly excludes clip-promote — campaign-dependent posting
// frequency has no fixed cadence to contract against). Looks ONLY at record-payout.mjs's own
// status:"recorded" lines (task:"promote.fun clip payout") for a JST-today ts. Never calls
// cadence_met().
const JST_OFFSET_SECONDS = 9 * 60 * 60;

function jstDateFromEpochSeconds(ts) {
  const d = new Date((ts + JST_OFFSET_SECONDS) * 1000);
  const yyyy = d.getUTCFullYear();
  const mm = String(d.getUTCMonth() + 1).padStart(2, "0");
  const dd = String(d.getUTCDate()).padStart(2, "0");
  return `${yyyy}-${mm}-${dd}`;
}

export function clipPromoteStatus(payoutRows, todayJstDate) {
  const paidToday = payoutRows.some(
    (row) =>
      row.status === "recorded" &&
      row.task === "promote.fun clip payout" &&
      jstDateFromEpochSeconds(row.ts) === todayJstDate,
  );
  return { status: paidToday ? "payout-today" : "no-payout-today" };
}
