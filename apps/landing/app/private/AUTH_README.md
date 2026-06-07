# /private auth setup

Netlify static hosting doesn't natively support `.htpasswd` basic auth. Three paths:

1. **Netlify Edge Function** (recommended) — `netlify/edge-functions/private-auth.ts`:
   ```ts
   export default async (req: Request, ctx) => {
     const auth = req.headers.get('authorization');
     if (!auth || !auth.startsWith('Basic ')) {
       return new Response('Unauthorized', { status: 401, headers: { 'WWW-Authenticate': 'Basic realm="private"' } });
     }
     const expected = 'Basic ' + btoa('dais:' + Deno.env.get('PRIVATE_CFO_PASSWORD'));
     if (auth !== expected) return new Response('Unauthorized', { status: 401 });
     return ctx.next();
   };
   export const config = { path: '/private' };
   ```
   + Netlify env var `PRIVATE_CFO_PASSWORD` set in dashboard.

2. **Robots noindex** (interim, doesn't actually gate): `X-Robots-Tag: noindex` in `netlify.toml` (done).

3. **Tailscale** (Mac mini local): expose via tailnet-only and never publish on Netlify.

Recommended: 1 (Edge Function) — implement when Dais provides Netlify env var.
