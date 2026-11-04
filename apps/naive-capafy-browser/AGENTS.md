# Naive Capafy Browser App

This is one Naive fullstack App that exposes a single MCP tool for its existing Capafy-only Computer.

- The agent decides actions from the page it observes; this server only validates and forwards one browser action.
- Keep the Computer ID fixed in App secrets. Never accept a Computer ID, Identity ID, email, service name or auth URL from the tool caller.
- Require the platform VETTA_MCP_TOKEN and use only the app-approved NAIVE_API_KEY with computers:write.
- Limit navigation to HTTPS on capafy.ai and its subdomains. The Computer allow-list is a second boundary.
- Never add a generic Naive API proxy, shell execution, Capafy business API calls, payment/payout actions, or credential-returning responses.
- Use operation_id as the SDK Idempotency-Key; one operation_id must describe one exact action.
- Keep runtime credentials out of logs, source, responses and browser input. The provider's Identity vault owns generated passwords.
- Do not create another Publisher, fake accounts, self-purchases, or camera-KYC workarounds.

Production runtime: Node 22.x. Naïve hosting requires a root Fetch entrypoint selected by `package.json.main`; set it to `index.mjs` and pass original `/healthz` and `/mcp` paths to the shared MCP handler. Do not add `vercel.json` rewrites or an unnecessary `api/` Function. `src/node.mjs` is only the local `npm start` adapter. Tests: `npm test`.
