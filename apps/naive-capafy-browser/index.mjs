import { createBrowserMcpHandler } from './src/server.mjs';

const handle = createBrowserMcpHandler();

export default {
  fetch(request) {
    return handle(request);
  },
};
