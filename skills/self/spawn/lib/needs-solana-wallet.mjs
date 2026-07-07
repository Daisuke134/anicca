// REQ-202: pure conditional (a Solana-settled skill present in initialSkills OR deployTarget ===
// "nosana") — bookkeeping over already-given inputs, never a model judgment. SOLANA_SETTLED_SKILLS
// mirrors is-self-funded.mjs's own OWN_FUNDED_FUEL_PROVIDERS pattern: a named, extensible allow-list.
export const SOLANA_SETTLED_SKILLS = new Set(["sol-trade"]);

export function needsSolanaWallet({ initialSkills = [], deployTarget } = {}) {
  const hasSolanaSkill = Array.isArray(initialSkills) && initialSkills.some((skill) => SOLANA_SETTLED_SKILLS.has(skill));
  return hasSolanaSkill || deployTarget === "nosana";
}
