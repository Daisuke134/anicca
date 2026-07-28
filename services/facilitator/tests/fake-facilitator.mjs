#!/usr/bin/env node

import { readFileSync, writeFileSync } from "node:fs";
import { createServer } from "node:http";

const config = JSON.parse(readFileSync(process.env.CONFIG, "utf8"));
if (process.env.FAKE_FACILITATOR_PID_FILE) {
  writeFileSync(process.env.FAKE_FACILITATOR_PID_FILE, `${process.pid}\n`, "utf8");
}

const supported = {
  kinds: [{
    x402Version: 2,
    scheme: "exact",
    network: "eip155:8453",
  }],
};

const server = createServer((request, response) => {
  response.setHeader("content-type", "application/json");
  if (request.url === "/health") {
    response.end(JSON.stringify({ ok: true }));
    return;
  }
  if (request.url === "/supported") {
    response.end(JSON.stringify(supported));
    return;
  }
  response.statusCode = 404;
  response.end(JSON.stringify({ error: "not_found" }));
});

server.listen(config.port, config.host);
