// Akash sovereign host path (previously MISSING — run.sh:140 referenced a nonexistent deploy-akash.sh).
// spec27b. buildAkashSDL() makes the SDL; deployAkash() drives the `akash` CLI (injectable exec for
// tests) to create a deployment + resolve the resulting lease dseq. No fake id: if no lease materializes
// or the create tx fails, it throws.
function buildAkashSDL(childId) {
  return `version: "2.0"
services:
  anicca:
    image: ghcr.io/daisuke134/anicca-genesis:latest
    env:
      - ANICCA_CHILD_ID=${childId}
      - ANICCA_ROLE=child
    expose:
      - port: 8080
        as: 80
        to:
          - global: true
profiles:
  compute:
    anicca:
      resources:
        cpu:
          units: 0.5
        memory:
          size: 512Mi
        storage:
          size: 1Gi
  placement:
    akash:
      pricing:
        anicca:
          denom: uakt
          amount: 1000
deployment:
  anicca:
    akash:
      profile: anicca
      count: 1
`;
}

// Resolve a dseq from the lease list (the durable id the child is hosted under).
function leaseDseqFrom(json) {
  try {
    const o = typeof json === "string" ? JSON.parse(json) : json;
    const leases = (o && o.leases) || [];
    const id = leases[0] && leases[0].lease && leases[0].lease.lease_id;
    return (id && id.dseq) || "";
  } catch { return ""; }
}

async function deployAkash(childId, { exec, writeFile, sdlPath = `/tmp/${childId}.akash.yml`, owner = process.env.AKASH_OWNER, node = process.env.AKASH_NODE || "https://rpc.akashnet.net:443", chainId = process.env.AKASH_CHAIN_ID || "akashnet-2", keyName = process.env.AKASH_KEY_NAME || "anicca" } = {}) {
  await writeFile(sdlPath, buildAkashSDL(childId));

  const create = await exec(`akash tx deployment create ${sdlPath} --from ${keyName} --node ${node} --chain-id ${chainId} --gas auto --gas-adjustment 1.4 -y -o json`);
  if (create.code !== 0 || /error|insufficient/i.test(String(create.stdout))) {
    throw new Error(`akash deployment create failed: ${String(create.stdout).slice(0, 200)}`);
  }

  // poll the market for the lease the providers bid into
  let dseq = "";
  for (let i = 0; i < 6 && !dseq; i++) {
    const ls = await exec(`akash query market lease list --owner ${owner} --node ${node} -o json`);
    dseq = leaseDseqFrom(ls.stdout);
  }
  if (!dseq) throw new Error("akash: no lease materialized for the deployment");
  return dseq;
}

module.exports = { buildAkashSDL, deployAkash, leaseDseqFrom };
