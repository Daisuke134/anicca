export function allocateBandit(products, opts = {}) {
  const {
    C = 1.5,
    matureWakes = 50,
    minAttemptsToJudge = 30,
  } = opts;
  const totalAttempts = products.reduce((sum, { attempts }) => sum + attempts, 0);
  const ranked = products
    .map(({ path, external, attempts, ageWakes }) => {
      const exploitation = external / Math.max(attempts, 1);
      const exploration = C * Math.sqrt(Math.log(totalAttempts + 1) / (attempts + 1));
      const score = exploitation + exploration;
      let decision = 'EXPLORE';

      if (ageWakes >= matureWakes && external === 0 && attempts >= minAttemptsToJudge) {
        decision = 'DROP';
      } else if (external > 0) {
        decision = 'KEEP';
      }

      return { path, score, exploitation, exploration, decision };
    })
    .sort((a, b) => b.score - a.score || a.path.localeCompare(b.path, 'en'));

  return {
    totalAttempts,
    ranked,
    keep: ranked.filter(({ decision }) => decision === 'KEEP').map(({ path }) => path),
    explore: ranked.filter(({ decision }) => decision === 'EXPLORE').map(({ path }) => path),
    drop: ranked.filter(({ decision }) => decision === 'DROP').map(({ path }) => path),
  };
}
