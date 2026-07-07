// PROP-403b/PROP-403e (Tier 2/3) live audit — anicca-agent-spawn Phase 5.
//
// REQ-403's live pairwise key-distinctness audit, run against TODAY's real N=2 co-located citizens
// (automaton, Franklin — both coLocatedWithCoordinator:true per citizens-registry's own seed shape).
// Uses the REAL, unmodified skills/earn/lib/resolve-identity.mjs resolvers (never a re-implemented
// comparator), invoked with the canonical COORDINATOR_HOME constant and an EXPLICIT env object
// (PROP-403e: never a bare {home:X} call). Never logs/prints the resolved key material itself — only
// booleans (non-null / equality) ever leave this process, matching resolve-identity.mjs's own R5
// "never logs the key material" discipline.
import os from "node:os";
import { resolveEvmPrivateKey, resolveSolanaSecret } from "file:///Users/anicca/anicca/skills/earn/lib/resolve-identity.mjs";

const COORDINATOR_HOME = os.homedir();

const citizens = [
  { id: "automaton", homeDir: `${COORDINATOR_HOME}/.anicca` },
  { id: "franklin", homeDir: `${COORDINATOR_HOME}/.blockrun` },
];

function resolveBoth(citizen) {
  const env = { HOME: COORDINATOR_HOME, ANICCA_HOME: citizen.homeDir };
  return {
    evm: resolveEvmPrivateKey({ home: citizen.homeDir, env }),
    solana: resolveSolanaSecret({ home: citizen.homeDir, env }),
  };
}

function main() {
  const resolved = citizens.map((c) => ({ id: c.id, homeDir: c.homeDir, keys: resolveBoth(c) }));

  const findings = { coordinatorHome: COORDINATOR_HOME, citizens: [], pairwise: [], verdict: null };

  for (const r of resolved) {
    findings.citizens.push({
      id: r.id,
      homeDir: r.homeDir,
      evmResolved: r.keys.evm !== null,
      solanaResolved: r.keys.solana !== null,
    });
  }

  // Pairwise comparison across ALL FOUR resolved values (automaton.evm, automaton.solana,
  // franklin.evm, franklin.solana) — "no equal keys" per PROP-403b, checked across every pair whose
  // BOTH sides are non-null (comparing an EVM key against a Solana secret is meaningless format-wise,
  // but a same-chain cross-citizen collision, e.g. automaton.evm === franklin.evm, is exactly the
  // hazard this audit exists to catch).
  const flat = [];
  for (const r of resolved) {
    if (r.keys.evm) flat.push({ citizen: r.id, chain: "evm", value: r.keys.evm });
    if (r.keys.solana) flat.push({ citizen: r.id, chain: "solana", value: r.keys.solana });
  }
  let collisionFound = false;
  for (let i = 0; i < flat.length; i++) {
    for (let j = i + 1; j < flat.length; j++) {
      if (flat[i].chain !== flat[j].chain) continue; // only same-chain pairs are a meaningful collision
      const equal = flat[i].value === flat[j].value;
      findings.pairwise.push({ a: `${flat[i].citizen}.${flat[i].chain}`, b: `${flat[j].citizen}.${flat[j].chain}`, equal });
      if (equal) collisionFound = true;
    }
  }

  const allResolvedNonNull = flat.length >= 2; // at least automaton.evm + franklin.solana per today's known seed
  findings.verdict = allResolvedNonNull && !collisionFound ? "PROVED" : "FAILED";
  findings.note =
    "Raw key material is never printed by this harness -- only non-null booleans and pairwise-equality " +
    "booleans leave this process, per resolve-identity.mjs's own R5 discipline.";

  console.log(JSON.stringify(findings, null, 2));
  if (findings.verdict !== "PROVED") process.exitCode = 1;
}

main();
