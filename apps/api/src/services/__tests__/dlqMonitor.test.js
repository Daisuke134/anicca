import fs from 'node:fs/promises';
import path from 'node:path';
import os from 'node:os';
import { afterEach, describe, expect, it } from 'vitest';
import { monitorDLQ } from '../dlqMonitor.js';

const createdDirs = [];

async function mkTmpDir() {
  const dir = await fs.mkdtemp(path.join(os.tmpdir(), 'anicca-dlq-'));
  createdDirs.push(dir);
  return dir;
}

afterEach(async () => {
  await Promise.all(
    createdDirs.splice(0).map((dir) => fs.rm(dir, { recursive: true, force: true }))
  );
});

describe('dlqMonitor', () => {
  it('archives entries older than 14 days', async () => {
    const dir = await mkTmpDir();
    const now = new Date('2026-02-09T12:00:00Z').getTime();
    const oldEntry = { id: 1, timestamp: '2026-01-01T00:00:00Z' };
    const newEntry = { id: 2, timestamp: '2026-02-08T00:00:00Z' };

    await fs.writeFile(
      path.join(dir, 'worker.jsonl'),
      `${JSON.stringify(oldEntry)}\n${JSON.stringify(newEntry)}\n`,
      'utf-8'
    );

    const result = await monitorDLQ({ dir, nowMs: now });
    expect(result).toEqual({ active: 1, archived: 1 });

    const remaining = await fs.readFile(path.join(dir, 'worker.jsonl'), 'utf-8');
    expect(remaining).toContain('"id":2');
    expect(remaining).not.toContain('"id":1');

    const archived = await fs.readFile(path.join(dir, 'archive', 'worker.jsonl'), 'utf-8');
    expect(archived).toContain('"id":1');
  });

  it('returns zero counts when dlq directory does not exist', async () => {
    const dir = path.join(os.tmpdir(), 'anicca-dlq-not-found');
    const result = await monitorDLQ({ dir });
    expect(result).toEqual({ active: 0, archived: 0 });
  });
});
