import assert from "node:assert/strict";
import test from "node:test";

import { loadStartupContext } from "../../../scripts/startup-context/lib.mjs";
import {
  assertSubmissionMatchesPreview,
  compileFunderPreview,
  validateFunderConfig,
} from "../lib/context.mjs";

const contextPath = new URL("../../../.agents/startup-context.json", import.meta.url);
const funderPath = new URL("../../../fundraising/funders/yc-fall-2026.json", import.meta.url);

async function fixture() {
  const context = await loadStartupContext(contextPath);
  const funder = await loadStartupContext(funderPath);
  return { context, funder };
}

test("funder config contains program evidence and no duplicated company facts", async () => {
  const { funder } = await fixture();

  assert.deepEqual(validateFunderConfig(funder), []);
  assert.equal("product_name" in funder, false);
  assert.equal("homepage" in funder, false);
  assert.equal("repository" in funder, false);
  assert.equal("company" in funder, false);
});

test("preview is bound to canonical Life Manager context and cannot submit directly", async () => {
  const { context, funder } = await fixture();
  const preview = await compileFunderPreview({
    context,
    funderConfig: funder,
    now: new Date("2026-08-02T14:00:00+09:00"),
  });

  assert.equal(preview.product.name, "Life Manager");
  assert.equal(preview.product.homepage, context.links.product.url);
  assert.equal(preview.product.repository, context.links.repository.url);
  assert.equal(preview.context_version, context.context_version);
  assert.match(preview.context_digest, /^[a-f0-9]{64}$/);
  assert.equal(preview.mode, "preview");
  assert.equal(preview.submit_allowed, false);
});

test("legacy product fields in funder config fail closed", async () => {
  const { funder } = await fixture();
  const legacy = structuredClone(funder);
  legacy.product_name = "Anicca";
  legacy.repository = "https://github.com/Daisuke134/anicca-oss";

  assert.match(validateFunderConfig(legacy).join("\n"), /duplicated.*product_name/i);
  assert.match(validateFunderConfig(legacy).join("\n"), /duplicated.*repository/i);
});

test("stale startup context cannot compile a preview", async () => {
  const { context, funder } = await fixture();

  await assert.rejects(
    compileFunderPreview({
      context,
      funderConfig: funder,
      now: new Date("2026-10-02T14:00:00+09:00"),
    }),
    /stale/i,
  );
});

test("unverified requested video cannot enter preview attachments", async () => {
  const { context, funder } = await fixture();
  const withVideo = structuredClone(funder);
  withVideo.requested_assets = ["founder_video"];

  await assert.rejects(
    compileFunderPreview({
      context,
      funderConfig: withVideo,
      now: new Date("2026-08-02T14:00:00+09:00"),
    }),
    /founder_video.*unverified/i,
  );
});

test("submission payload must match the exact preview context and artifact digests", async () => {
  const { context, funder } = await fixture();
  const preview = await compileFunderPreview({
    context,
    funderConfig: funder,
    now: new Date("2026-08-02T14:00:00+09:00"),
  });
  const payload = {
    context_digest: preview.context_digest,
    application_digest: preview.application_digest,
  };

  assert.deepEqual(assertSubmissionMatchesPreview({ preview, payload }), []);
  assert.match(
    assertSubmissionMatchesPreview({
      preview,
      payload: { ...payload, context_digest: "0".repeat(64) },
    }).join("\n"),
    /context digest mismatch/i,
  );
});
