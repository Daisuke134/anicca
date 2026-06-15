const { test } = require("node:test");
const assert = require("node:assert");
const { buildAkashSDL, deployAkash } = require("../deploy-akash");

test("buildAkashSDL embeds the child id and is a valid SDL skeleton", () => {
  const sdl = buildAkashSDL("anicca-c001");
  assert.match(sdl, /version:\s*"2\.0"/);
  assert.match(sdl, /services:/);
  assert.match(sdl, /ANICCA_CHILD_ID=anicca-c001/);
  assert.match(sdl, /deployment:/);
  assert.match(sdl, /profiles:/);
});

test("deployAkash returns a lease/dseq id from the CLI output", async () => {
  // injectable exec: simulate `akash tx deployment create` returning a txhash + dseq
  const calls = [];
  const exec = async (cmd) => {
    calls.push(cmd);
    if (cmd.includes("deployment create")) return { stdout: JSON.stringify({ txhash: "ABC123", logs: [] }), code: 0 };
    if (cmd.includes("query market lease list")) return { stdout: JSON.stringify({ leases: [{ lease: { lease_id: { dseq: "7654321" } } }] }), code: 0 };
    return { stdout: "", code: 0 };
  };
  const id = await deployAkash("anicca-c001", { exec, writeFile: async () => {}, sdlPath: "/tmp/x.yml" });
  assert.equal(id, "7654321");
  assert.ok(calls.some((c) => c.includes("deployment create")));
});

test("deployAkash throws when no lease materializes (no fake id)", async () => {
  const exec = async (cmd) => {
    if (cmd.includes("deployment create")) return { stdout: JSON.stringify({ txhash: "ABC" }), code: 0 };
    return { stdout: JSON.stringify({ leases: [] }), code: 0 };
  };
  await assert.rejects(() => deployAkash("anicca-c001", { exec, writeFile: async () => {}, sdlPath: "/tmp/x.yml" }), /no lease/i);
});

test("deployAkash throws when the create tx fails", async () => {
  const exec = async () => ({ stdout: "error: insufficient funds", code: 1 });
  await assert.rejects(() => deployAkash("anicca-c001", { exec, writeFile: async () => {}, sdlPath: "/tmp/x.yml" }), /akash/i);
});
