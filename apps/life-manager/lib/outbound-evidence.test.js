"use strict";

const assert = require("node:assert/strict");
const { createHash } = require("node:crypto");
const test = require("node:test");

const {
  verifyOutboundEvidence,
} = require("./outbound-evidence.js");

const PNG_SIGNATURE = Buffer.from([0x89, 0x50, 0x4e, 0x47, 0x0d, 0x0a, 0x1a, 0x0a]);

function pngBytes(size = 5000) {
  const bytes = Buffer.alloc(size, 0x61);
  PNG_SIGNATURE.copy(bytes, 0);
  return bytes;
}

function fixture(bytes = pngBytes()) {
  const digest = createHash("sha256").update(bytes).digest("hex");
  return {
    input: {
      tenantId: "dais",
      attemptRef: `runtime-attempt://dais/${"a".repeat(64)}/1`,
      externalReceiptRef: "gmail-message://dais/msg-123",
      artifactRef: `object://sha256/${digest}`,
      canonicalUrl: "https://lu.ma/tokyo-founders-2026",
    },
    dependencies: {
      async readExternalReceipt(tenantId, ref) {
        assert.equal(tenantId, "dais");
        assert.equal(ref, "gmail-message://dais/msg-123");
        return {
          kind: "confirmation_mail",
          provider_id: "msg-123",
          observed_at: "2026-08-01T03:00:00.000Z",
        };
      },
      async readArtifact(tenantId, ref) {
        assert.equal(tenantId, "dais");
        assert.equal(ref, `object://sha256/${digest}`);
        return bytes;
      },
      async fetchImpl(url, options) {
        assert.equal(url, "https://lu.ma/tokyo-founders-2026");
        assert.equal(options.method, "HEAD");
        assert.equal(options.redirect, "manual");
        assert.ok(options.signal);
        return { status: 200 };
      },
    },
  };
}

test("E1, E2, and E3 together produce one immutable verified evidence result", async () => {
  const { input, dependencies } = fixture();
  const first = await verifyOutboundEvidence(input, dependencies);
  const second = await verifyOutboundEvidence(input, dependencies);

  assert.equal(first.status, "verified");
  assert.deepEqual(first.missing, []);
  assert.equal(first.attempt_ref, input.attemptRef);
  assert.deepEqual(first.evidence, {
    e1: {
      kind: "confirmation_mail",
      ref: "gmail-message://dais/msg-123",
      provider_id: "msg-123",
      observed_at: "2026-08-01T03:00:00.000Z",
    },
    e2: {
      ref: input.artifactRef,
      sha256: input.artifactRef.slice("object://sha256/".length),
      size_bytes: 5000,
      media_type: "image/png",
    },
    e3: {
      url: "https://lu.ma/tokyo-founders-2026",
      status_code: 200,
    },
  });
  assert.match(first.evidence_hash, /^[0-9a-f]{64}$/);
  assert.equal(first.evidence_hash, second.evidence_hash);
  assert.equal(Object.isFrozen(first), true);
  assert.doesNotMatch(JSON.stringify(first), /keiodaisuke|cookie|password|PNG\r\n/i);
});

test("each missing tier independently prevents a success claim", async () => {
  const e1 = fixture();
  e1.dependencies.readExternalReceipt = async () => {
    throw new Error("confirmation mail unavailable");
  };
  const missingE1 = await verifyOutboundEvidence(e1.input, e1.dependencies);
  assert.equal(missingE1.status, "failed");
  assert.deepEqual(missingE1.missing, ["E1"]);

  const mismatchedE1 = fixture();
  mismatchedE1.dependencies.readExternalReceipt = async () => ({
    kind: "provider_response",
    provider_id: "http-200",
    observed_at: "2026-08-01T03:00:00.000Z",
  });
  const mismatchedReceipt = await verifyOutboundEvidence(
    mismatchedE1.input,
    mismatchedE1.dependencies,
  );
  assert.equal(mismatchedReceipt.status, "failed");
  assert.deepEqual(mismatchedReceipt.missing, ["E1"]);

  const e2 = fixture(pngBytes(4999));
  const missingE2 = await verifyOutboundEvidence(e2.input, e2.dependencies);
  assert.equal(missingE2.status, "failed");
  assert.deepEqual(missingE2.missing, ["E2"]);

  const e3 = fixture();
  e3.dependencies.fetchImpl = async () => ({ status: 302 });
  const missingE3 = await verifyOutboundEvidence(e3.input, e3.dependencies);
  assert.equal(missingE3.status, "failed");
  assert.deepEqual(missingE3.missing, ["E3"]);
});

test("one-shot URLs and raw identity or filesystem values never become evidence", async () => {
  const oneShot = fixture();
  oneShot.input.canonicalUrl = "https://lu.ma/join/complete/secret-result";
  let fetched = false;
  oneShot.dependencies.fetchImpl = async () => {
    fetched = true;
    return { status: 200 };
  };
  const rejectedUrl = await verifyOutboundEvidence(oneShot.input, oneShot.dependencies);
  assert.equal(rejectedUrl.status, "failed");
  assert.deepEqual(rejectedUrl.missing, ["E3"]);
  assert.equal(fetched, false);

  const unsafe = fixture();
  unsafe.input.externalReceiptRef = "redacted@example.invalid";
  unsafe.input.artifactRef = "/Users/operator/confirmation.png";
  unsafe.input.canonicalUrl = "http://lu.ma/tokyo-founders-2026";
  let readersCalled = false;
  unsafe.dependencies.readExternalReceipt = async () => {
    readersCalled = true;
  };
  unsafe.dependencies.readArtifact = async () => {
    readersCalled = true;
  };
  unsafe.dependencies.fetchImpl = async () => {
    readersCalled = true;
  };
  const rejected = await verifyOutboundEvidence(unsafe.input, unsafe.dependencies);
  assert.equal(rejected.status, "failed");
  assert.deepEqual(rejected.missing, ["E1", "E2", "E3"]);
  assert.equal(readersCalled, false);
});

test("E3 verifies the canonical connpass URL without dropping its group subdomain", async () => {
  const connpass = fixture();
  connpass.input.canonicalUrl = (
    "https://data-learning-guild.connpass.com/event/400425?utm_source=search#about"
  );
  connpass.dependencies.fetchImpl = async (url, options) => {
    assert.equal(url, "https://data-learning-guild.connpass.com/event/400425/");
    assert.equal(options.method, "HEAD");
    assert.equal(options.redirect, "manual");
    return { status: 200 };
  };

  const result = await verifyOutboundEvidence(connpass.input, connpass.dependencies);
  assert.equal(result.status, "verified");
  assert.equal(
    result.evidence.e3.url,
    "https://data-learning-guild.connpass.com/event/400425/",
  );
});

test("an attempt reference from another tenant cannot read or verify evidence", async () => {
  const crossTenant = fixture();
  crossTenant.input.attemptRef = `runtime-attempt://another-tenant/${"a".repeat(64)}/1`;
  let dependenciesCalled = false;
  crossTenant.dependencies.readExternalReceipt = async () => {
    dependenciesCalled = true;
  };
  crossTenant.dependencies.readArtifact = async () => {
    dependenciesCalled = true;
  };
  crossTenant.dependencies.fetchImpl = async () => {
    dependenciesCalled = true;
  };

  const result = await verifyOutboundEvidence(crossTenant.input, crossTenant.dependencies);
  assert.equal(result.status, "failed");
  assert.equal(result.attempt_ref, null);
  assert.deepEqual(result.missing, ["E1", "E2", "E3"]);
  assert.equal(dependenciesCalled, false);
});
