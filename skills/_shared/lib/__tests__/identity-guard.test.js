// node:test — identity-guard: prove the earn skill can NEVER touch user PII (spec 28 §3).
// THE WALL: earn uses Anicca's OWN identity/wallet only; user gcal/Gmail/phone is life-only.
import { test } from "node:test";
import assert from "node:assert/strict";
import {
  assertOwnIdentityOnly,
  assertOwnEarnSource,
  findUserPIIEnv,
} from "../identity-guard.mjs";

test("own-identity earn sources pass the guard", () => {
  for (const source of ["x402", "0xwork", "content", "x402-serve", "crypto"]) {
    assert.equal(assertOwnEarnSource(source), true, `${source} should be allowed`);
  }
});

test("a user-identity earn source THROWS (cold-mail / gmail / contacts)", () => {
  for (const source of ["gmail-coldmail", "user-contacts", "calendar-outreach", "telegram-blast"]) {
    assert.throws(() => assertOwnEarnSource(source), /MALICE-GUARD/, `${source} must be blocked`);
  }
});

test("an unknown source fails closed (not silently allowed)", () => {
  assert.throws(() => assertOwnEarnSource("mystery-channel"), /MALICE-GUARD/);
});

test("findUserPIIEnv detects a user-PII env var", () => {
  assert.equal(findUserPIIEnv({ BLOCKRUN_WALLET_KEY: "0xkey" }), null);
  assert.equal(findUserPIIEnv({ USER_EMAIL: "a@b.com" }), "USER_EMAIL");
  assert.equal(findUserPIIEnv({ GOOGLE_LOGIN_EMAIL: "x@y.com" }), "GOOGLE_LOGIN_EMAIL");
  assert.equal(findUserPIIEnv({ COMPOSIO_API_KEY: "k" }), "COMPOSIO_API_KEY");
  assert.equal(findUserPIIEnv({ TELEGRAM_BOT_TOKEN: "t" }), "TELEGRAM_BOT_TOKEN");
});

test("assertOwnIdentityOnly: clean own-wallet env + own source PASSES", () => {
  const env = { BLOCKRUN_WALLET_KEY: "0xkey", BASE_RPC_URL: "https://base", PATH: "/usr/bin" };
  assert.equal(assertOwnIdentityOnly({ source: "x402" }, { env }), true);
});

test("assertOwnIdentityOnly: a user-PII env var present THROWS even with an own source", () => {
  const env = { BLOCKRUN_WALLET_KEY: "0xkey", USER_GMAIL_TOKEN: "leaked" };
  assert.throws(() => assertOwnIdentityOnly({ source: "x402" }, { env }), /user-PII env "USER_GMAIL_TOKEN"/);
});

test("assertOwnIdentityOnly: Composio (user gcal/Gmail grant) in env THROWS", () => {
  const env = { BLOCKRUN_WALLET_KEY: "0xkey", COMPOSIO_API_KEY: "user-grant" };
  assert.throws(() => assertOwnIdentityOnly({ source: "0xwork" }, { env }), /MALICE-GUARD/);
});
