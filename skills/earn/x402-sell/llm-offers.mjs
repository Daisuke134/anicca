// Pure, dependency-free offer catalog shared by the persistent seller and rsynced agent body.
// Keep external SDK imports out of this module: Franklin's runtime intentionally has no local
// node_modules, while the repository-hosted seller has the paid-request dependencies.
export const LLM_OFFER_VARIANTS = Object.freeze([
  {
    id: 'eco-margin',
    price: '$0.015',
    upstreamMaxUsd: 0.010,
    description: 'GLM-5 Turbo LLM answer via BlockRun, paid by this seller wallet. No model account or API key needed. GET /llm?prompt=<text>&maxTokens=1..512.',
  },
  {
    id: 'eco-market',
    price: '$0.012',
    upstreamMaxUsd: 0.010,
    description: 'Keyless GLM-5 Turbo inference over x402. The seller pays BlockRun compute from its own wallet. GET /llm?prompt=<text>&maxTokens=1..512.',
  },
  {
    id: 'eco-premium',
    price: '$0.020',
    upstreamMaxUsd: 0.010,
    description: 'Managed GLM-5 Turbo compute for autonomous agents: one x402 payment, no provider signup, no API keys. GET /llm?prompt=<text>&maxTokens=1..512.',
  },
]);

export function assertProfitableOffer(offer) {
  const priceUsd = Number(String(offer?.price || '').replace(/^\$/, ''));
  const upstreamMaxUsd = Number(offer?.upstreamMaxUsd);
  if (!(Number.isFinite(priceUsd) && Number.isFinite(upstreamMaxUsd) && priceUsd > upstreamMaxUsd)) {
    throw new Error('offer price must exceed upstream max cost');
  }
  return offer;
}

for (const offer of LLM_OFFER_VARIANTS) assertProfitableOffer(offer);
