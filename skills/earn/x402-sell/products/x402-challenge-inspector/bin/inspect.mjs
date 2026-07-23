#!/usr/bin/env node
import { readFileSync } from 'node:fs';
import { inspectX402Challenge } from '../src/inspector.mjs';

try {
  const input = readFileSync(0, 'utf8');
  process.stdout.write(`${JSON.stringify(inspectX402Challenge(input))}\n`);
} catch (error) {
  process.stderr.write(`${String(error?.message || error)}\n`);
  process.exit(1);
}
