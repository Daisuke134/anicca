import { createSellerApp } from '../src/server.mjs';

const app = createSellerApp();
const publicRoutes = new Set(['/', '/healthz', '/funding-rates', '/.well-known/x402.json', '/llms.txt']);

export const GET = (request) => {
  const url = new URL(request.url);
  const route = url.searchParams.get('__route') ?? (url.pathname === '/api/index' ? '/' : null);
  if (!publicRoutes.has(route)) return Response.json({ error: 'not_found' }, { status: 404 });
  url.pathname = route;
  url.searchParams.delete('__route');
  return app.fetch(new Request(url, request));
};
