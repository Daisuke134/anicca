import { createServer } from 'node:http';
import { Readable } from 'node:stream';
import { createBrowserMcpHandler } from './server.mjs';

const handle = createBrowserMcpHandler({ env: process.env });
const port = Number(process.env.PORT ?? 3000);

if (!Number.isInteger(port) || port < 1 || port > 65535) {
  throw new Error('PORT must be an integer from 1 to 65535');
}

const server = createServer((incoming, outgoing) => {
  void (async () => {
    const host = incoming.headers.host ?? 'localhost';
    const url = new URL(incoming.url ?? '/', 'http://' + host);
    const method = incoming.method ?? 'GET';
    const headers = new Headers();
    for (const [name, value] of Object.entries(incoming.headers)) {
      if (Array.isArray(value)) headers.set(name, value.join(', '));
      else if (value !== undefined) headers.set(name, value);
    }
    const init = { method, headers };
    if (method !== 'GET' && method !== 'HEAD') {
      init.body = Readable.toWeb(incoming);
      init.duplex = 'half';
    }
    const request = new Request(url, init);
    const response = await handle(request);
    outgoing.writeHead(response.status, Object.fromEntries(response.headers));
    outgoing.end(Buffer.from(await response.arrayBuffer()));
  })().catch(() => {
    if (!outgoing.headersSent) outgoing.writeHead(500, { 'content-type': 'text/plain' });
    outgoing.end('Internal Server Error');
  });
});

server.listen(port, '0.0.0.0');
