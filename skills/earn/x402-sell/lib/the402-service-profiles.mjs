const RESEARCH_SOURCES = Object.freeze([
  {
    url: 'https://github.com/coinbase/agentkit/blob/main/typescript/agentkit/src/action-providers/x402/README.md',
    raw: 'https://raw.githubusercontent.com/coinbase/agentkit/main/typescript/agentkit/src/action-providers/x402/README.md',
  },
  {
    url: 'https://developers.cloudflare.com/agents/tools/payments/x402/',
    raw: 'https://raw.githubusercontent.com/cloudflare/cloudflare-docs/production/src/content/docs/agents/tools/payments/x402/index.mdx',
  },
  {
    url: 'https://github.com/coinbase/x402/blob/main/docs/guides/mcp-server-with-x402.md',
    raw: 'https://raw.githubusercontent.com/coinbase/x402/main/docs/guides/mcp-server-with-x402.md',
  },
  {
    url: 'https://the402.ai/docs/providers',
    raw: 'https://api.the402.ai/docs/provider-guide.md',
  },
]);

const EXPLAINER_SOURCES = Object.freeze([
  {
    url: 'https://www.rfc-editor.org/rfc/rfc9110.html#section-15.5.3',
    raw: 'https://www.rfc-editor.org/rfc/rfc9110.txt',
    needle: '15.5.3.  402 Payment Required',
    occurrence: 2,
  },
  {
    url: 'https://www.rfc-editor.org/rfc/rfc7231#section-6.5.2',
    raw: 'https://www.rfc-editor.org/rfc/rfc7231.txt',
    needle: '6.5.2.  402 Payment Required',
  },
  {
    url: 'https://www.iana.org/assignments/http-status-codes/http-status-codes.xhtml',
    raw: 'https://www.iana.org/assignments/http-status-codes/http-status-codes.xhtml',
    needle: '>402<',
  },
]);

const RESEARCH_PROFILE = Object.freeze({
  kind: 'x402_adoption_research',
  minWords: 800,
  maxWords: 1_200,
  sources: RESEARCH_SOURCES,
  instructions: 'The report must contain a short landscape overview; 3–5 concrete examples of frameworks or platforms experimenting with agent payments; key adoption obstacles; and exactly three outlook bullets for the next 12 months. Do not claim that LangChain, CrewAI, or AutoGen natively supports x402 unless a supplied source proves it; distinguish adapters from native support. Use a factual tone with no marketing fluff.',
});

const EXPLAINER_PROFILE = Object.freeze({
  kind: 'http402_explainer',
  minWords: 600,
  maxWords: 900,
  sources: EXPLAINER_SOURCES,
  instructions: 'Write exactly four level-2 markdown sections and no title heading: (1) what HTTP status codes are, (2) what 402 means and its history as reserved for future use, (3) the general request → 402 → pay → retry pattern in plain terms, and (4) one simple everyday analogy. Keep it beginner-friendly and fully self-contained. Mention no specific companies, products, current events, or real-time data.',
});

export function the402ServiceProfile(serviceId, {
  researchServiceId,
  explainerServiceId = null,
}) {
  if (typeof serviceId !== 'string' || !serviceId.length) return null;
  if (serviceId === researchServiceId) return RESEARCH_PROFILE;
  if (explainerServiceId && serviceId === explainerServiceId) return EXPLAINER_PROFILE;
  return null;
}
