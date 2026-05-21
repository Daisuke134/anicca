import fs from 'node:fs/promises';
import path from 'node:path';

export const DLQ_DIR = process.env.DLQ_DIR || '/tmp/anicca/dlq';
export const ARCHIVE_DAYS = 14;

function buildArchiveDir(baseDir) {
  return path.join(baseDir, 'archive');
}

function parseJsonl(content) {
  return String(content || '')
    .split('\n')
    .map((line) => line.trim())
    .filter(Boolean)
    .map((line) => {
      try {
        return JSON.parse(line);
      } catch {
        return null;
      }
    })
    .filter(Boolean);
}

function toJsonl(entries) {
  if (!entries.length) return '';
  return `${entries.map((entry) => JSON.stringify(entry)).join('\n')}\n`;
}

export async function monitorDLQ(options = {}) {
  const baseDir = options.dir || DLQ_DIR;
  const archiveDir = options.archiveDir || buildArchiveDir(baseDir);
  const nowMs = options.nowMs || Date.now();

  let files = [];
  try {
    files = await fs.readdir(baseDir);
  } catch (error) {
    if (error?.code === 'ENOENT') {
      return { active: 0, archived: 0 };
    }
    throw error;
  }

  await fs.mkdir(archiveDir, { recursive: true });

  let active = 0;
  let archived = 0;

  for (const file of files) {
    if (!file.endsWith('.jsonl')) continue;

    const fullPath = path.join(baseDir, file);
    const raw = await fs.readFile(fullPath, 'utf-8').catch(() => '');
    const entries = parseJsonl(raw);
    const keep = [];
    const archive = [];

    for (const entry of entries) {
      const ts = new Date(entry.timestamp || entry.createdAt || 0).getTime();
      const ageDays = Number.isFinite(ts)
        ? (nowMs - ts) / (1000 * 60 * 60 * 24)
        : 0;

      if (ageDays > ARCHIVE_DAYS) archive.push(entry);
      else keep.push(entry);
    }

    active += keep.length;
    archived += archive.length;

    if (archive.length > 0) {
      const archivePath = path.join(archiveDir, file);
      await fs.appendFile(archivePath, toJsonl(archive), 'utf-8');
    }

    if (keep.length > 0) {
      await fs.writeFile(fullPath, toJsonl(keep), 'utf-8');
    } else {
      await fs.rm(fullPath, { force: true });
    }
  }

  return { active, archived };
}

export default {
  monitorDLQ,
  ARCHIVE_DAYS,
  DLQ_DIR,
};
