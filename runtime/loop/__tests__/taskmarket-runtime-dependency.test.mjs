import test from 'node:test';
import assert from 'node:assert/strict';
import { execFileSync } from 'node:child_process';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const REPO_ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '../../..');

test('production root node_modules resolves the TaskMarket x402 client dependency', () => {
  const output = execFileSync(
    process.execPath,
    ['--input-type=module', '-e', "await import('@blockrun/llm'); process.stdout.write('resolved')"],
    { cwd: REPO_ROOT, encoding: 'utf8' },
  );

  assert.equal(output, 'resolved');
});
