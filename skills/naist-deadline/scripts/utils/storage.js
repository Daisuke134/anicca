const fs = require('fs');
const path = require('path');

const DEFAULT_FILE = path.join(__dirname, '../../data/deadlines.json');

function getFilePath() {
  return process.env.DEADLINES_FILE || DEFAULT_FILE;
}

function read() {
  const filePath = getFilePath();
  if (!fs.existsSync(filePath)) {
    return { schemaVersion: 1, updatedAt: new Date().toISOString(), deadlines: [] };
  }
  try {
    return JSON.parse(fs.readFileSync(filePath, 'utf8'));
  } catch {
    return { schemaVersion: 1, updatedAt: new Date().toISOString(), deadlines: [] };
  }
}

function write(data) {
  const filePath = getFilePath();
  const dir = path.dirname(filePath);
  if (!fs.existsSync(dir)) fs.mkdirSync(dir, { recursive: true });
  const tmpFile = filePath + '.tmp';
  data.updatedAt = new Date().toISOString();
  fs.writeFileSync(tmpFile, JSON.stringify(data, null, 2), 'utf8');
  fs.renameSync(tmpFile, filePath);
}

module.exports = { read, write };
