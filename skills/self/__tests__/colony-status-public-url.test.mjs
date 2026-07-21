import test from "node:test";
import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";

const scriptUrl = new URL("../colony-status.sh", import.meta.url);

test("franklin1 status reports the live public x402 URL", async () => {
  const script = await readFile(scriptUrl, "utf8");

  assert.match(script, /http\(\)/);
  assert.match(script, /url=:10001 public=\$\(http/);
  assert.doesNotMatch(script, /no X402_PUBLIC_URL = cannot list on Bazaar/);
});
