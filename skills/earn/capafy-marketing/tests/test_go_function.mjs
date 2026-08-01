import assert from "node:assert/strict";
import test from "node:test";

import { campaignQuery } from "../site/netlify/functions/go.mjs";

test("preserves allowlisted Reel attribution parameters", () => {
  assert.equal(
    campaignQuery(
      "https://example.test/go/4866150011?utm_source=instagram&utm_medium=reel&utm_campaign=capafy-skill&verification=ignored",
    ).toString(),
    "utm_source=instagram&utm_medium=reel&utm_campaign=capafy-skill",
  );
});

test("uses legacy bio attribution defaults when parameters are absent", () => {
  assert.equal(
    campaignQuery("https://example.test/go/4866150011").toString(),
    "utm_source=instagram_bio&utm_medium=bio_link&utm_campaign=capafy_marketing",
  );
});
