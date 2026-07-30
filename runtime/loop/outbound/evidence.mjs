// runtime/loop/outbound/evidence.mjs — the Evidence Contract (spec §4).
//
// ★ THE SELF-IMPROVE LAYER MUST NEVER WRITE TO THIS FILE. ★
// The LEARN stage may rewrite templates, targeting and cadence config. It may not touch this
// module, because the reward signal is "verified evidence count" — an agent allowed to edit its
// own gate would learn to loosen the gate instead of doing the work. Any diff to this file must
// come from a human-reviewed commit, never from an automated reflection pass.
//
// Success is E1 ∧ E2 ∧ E3. One missing limb ⇒ status=failed + the reason goes to Telegram.
//   E1  external response  : an HTTP 2xx receipt, a confirmation-email record, or a ticket id.
//   E2  artifact           : PNG magic number 89 50 4E 47 AND >= 5000 bytes.
//   E3  canonical URL      : parseable, not a /join/complete/ one-shot URL, subdomain preserved,
//                            recorded together with the HEAD status the CALLER observed.
//
// This module is PURE: no fetch, no fs, no clock, no writes. It takes evidence as DATA and
// judges it. The caller performs the HTTP HEAD and reads the artifact off disk, then hands the
// observations here. That separation is deliberate — a gate that fetches its own proof can be
// fooled by whoever controls the network; a gate that only judges recorded facts cannot.

export const PNG_MAGIC = Object.freeze([0x89, 0x50, 0x4e, 0x47]);
export const ARTIFACT_MIN_BYTES = 5000;

const ONE_SHOT_URL_MARKER = "/join/complete/";

function failure(code, detail) {
  return Object.freeze({ code, detail });
}

function isByteSource(value) {
  return value instanceof Uint8Array || (typeof Buffer !== "undefined" && Buffer.isBuffer(value));
}

function checkE1(e1) {
  if (!e1 || typeof e1 !== "object") {
    return [failure("E1_ABSENT", "no external response was recorded")];
  }
  const kind = String(e1.kind || "");
  if (kind === "http") {
    const status = Number(e1.status);
    if (!Number.isInteger(status)) {
      return [failure("E1_ABSENT", "http receipt carries no status code")];
    }
    if (status < 200 || status > 299) {
      return [failure("E1_NOT_2XX", `external system answered ${status}, not 2xx`)];
    }
    return [];
  }
  if (kind === "email") {
    if (!String(e1.message_id || "").trim()) {
      return [failure("E1_EMAIL_UNIDENTIFIED", "confirmation-email record has no message id")];
    }
    return [];
  }
  if (kind === "ticket") {
    if (!String(e1.ticket_id || "").trim()) {
      return [failure("E1_TICKET_UNIDENTIFIED", "ticket record has no ticket id")];
    }
    return [];
  }
  return [failure("E1_ABSENT", `unknown external response kind ${JSON.stringify(kind)}`)];
}

function checkE2(e2) {
  if (!e2 || typeof e2 !== "object") {
    return [failure("E2_ABSENT", "no artifact was recorded")];
  }
  const bytes = e2.bytes;
  if (!isByteSource(bytes)) {
    // A path alone is not evidence. The caller must read the file and pass the bytes, so that
    // the gate judges what is actually on disk rather than a filename someone typed.
    return [failure("E2_ABSENT", "artifact bytes were not supplied (a path alone is not evidence)")];
  }
  if (bytes.length < 4 || PNG_MAGIC.some((byte, index) => bytes[index] !== byte)) {
    return [failure("E2_NOT_PNG", "artifact does not start with the PNG magic number 89 50 4E 47")];
  }
  if (bytes.length < ARTIFACT_MIN_BYTES) {
    return [failure("E2_TOO_SMALL", `artifact is ${bytes.length} bytes, floor is ${ARTIFACT_MIN_BYTES}`)];
  }
  return [];
}

function parseUrl(raw) {
  try {
    return new URL(String(raw));
  } catch {
    return null;
  }
}

function checkE3(e3) {
  if (!e3 || typeof e3 !== "object" || !String(e3.url || "").trim()) {
    return [failure("E3_ABSENT", "no canonical URL was recorded")];
  }
  const canonical = parseUrl(e3.url);
  if (!canonical) {
    return [failure("E3_UNPARSEABLE", `canonical URL ${JSON.stringify(String(e3.url))} does not parse`)];
  }
  if (canonical.pathname.includes(ONE_SHOT_URL_MARKER)) {
    return [failure("E3_ONE_SHOT_URL", `canonical URL contains ${ONE_SHOT_URL_MARKER} (one-shot result URL)`)];
  }
  if (String(e3.source_url || "").trim()) {
    const source = parseUrl(e3.source_url);
    if (!source) {
      return [failure("E3_UNPARSEABLE", "source URL does not parse")];
    }
    if (source.hostname !== canonical.hostname) {
      const droppedSubdomain = source.hostname.endsWith(`.${canonical.hostname}`);
      return [droppedSubdomain
        ? failure("E3_SUBDOMAIN_LOST", `canonical host ${canonical.hostname} dropped the subdomain of ${source.hostname}`)
        : failure("E3_HOST_MISMATCH", `canonical host ${canonical.hostname} differs from source host ${source.hostname}`)];
    }
  }
  if (!Number.isInteger(Number(e3.head_status))) {
    return [failure("E3_NO_HEAD_STATUS", "canonical URL was recorded without an observed HEAD status")];
  }
  if (Number(e3.head_status) !== 200) {
    return [failure("E3_HEAD_NOT_200", `canonical URL answered HEAD ${e3.head_status}, not 200`)];
  }
  return [];
}

/**
 * Judge a recorded evidence bundle. Pure and deterministic.
 * @param {{e1?: object|null, e2?: object|null, e3?: object|null}} input
 * @returns {{ok: boolean, failures: ReadonlyArray<{code: string, detail: string}>}}
 */
export function verifyEvidence(input) {
  const bundle = input && typeof input === "object" ? input : {};
  const failures = Object.freeze([
    ...checkE1(bundle.e1),
    ...checkE2(bundle.e2),
    ...checkE3(bundle.e3),
  ]);
  return Object.freeze({ ok: failures.length === 0, failures });
}
