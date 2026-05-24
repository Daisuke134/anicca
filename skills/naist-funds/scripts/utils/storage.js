const fs = require("fs");
const path = require("path");

function dataDir() {
  return process.env.{{profile.education.institution}}_FUNDS_DATA_DIR ||
    path.join(__dirname, "../../data");
}

function loadCache() {
  const file = path.join(dataDir(), "cache.json");
  if (!fs.existsSync(file)) return { notified: [], lastFetchedAt: null };
  try {
    return JSON.parse(fs.readFileSync(file, "utf8"));
  } catch (e) {
    return { notified: [], lastFetchedAt: null };
  }
}

function saveCache(cache) {
  const dir = dataDir();
  if (!fs.existsSync(dir)) fs.mkdirSync(dir, { recursive: true });
  const file = path.join(dir, "cache.json");
  const tmp = file + ".tmp";
  fs.writeFileSync(tmp, JSON.stringify(cache, null, 2));
  fs.renameSync(tmp, file);
}

function loadGuides() {
  const file = path.join(dataDir(), "guides.json");
  if (!fs.existsSync(file)) return { guides: [] };
  try {
    return JSON.parse(fs.readFileSync(file, "utf8"));
  } catch (e) {
    return { guides: [] };
  }
}

module.exports = { loadCache, saveCache, loadGuides };
