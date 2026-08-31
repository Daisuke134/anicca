"use strict";

const fs = require("node:fs");
const os = require("node:os");
const path = require("node:path");

const MODES = new Set(["local", "cloud"]);
const LEGACY_SEGMENT = /(?:^|\/)(?:\.openclaw|profitable-claude|mr-bot-v0)(?:\/|$)/i;

function hasLegacyAniccaRoot(resolved) {
  const segments = resolved.split("/").filter(Boolean);
  return segments.some((segment, index) => {
    if (segment.toLowerCase() !== "anicca") return false;
    const isUsername = index === 1 && ["users", "home"].includes(segments[0]?.toLowerCase());
    return !isUsername;
  });
}

function absoluteRoot(env, name) {
  const value = String(env[name] || "").trim();
  if (!value || !path.isAbsolute(value)) {
    throw new Error(`${name} must be an absolute path`);
  }
  const resolved = path.resolve(value);
  if (LEGACY_SEGMENT.test(resolved) || hasLegacyAniccaRoot(resolved)) {
    throw new Error(`${name} resolves beneath a forbidden legacy runtime root`);
  }
  return resolved;
}

function canonicalDataRoot(resolved) {
  let current = resolved;
  const missing = [];
  while (true) {
    let stat;
    try {
      stat = fs.lstatSync(current);
    } catch (error) {
      if (error && error.code === "ENOENT") {
        const parent = path.dirname(current);
        if (parent === current) return resolved;
        missing.unshift(path.basename(current));
        current = parent;
        continue;
      }
      throw new Error("Mr.bot data root cannot be inspected");
    }
    let real;
    try {
      real = fs.realpathSync(current);
    } catch {
      throw new Error("Mr.bot data root symlink cannot be resolved");
    }
    return path.join(real, ...missing);
  }
}

// The portable Mr.bot data root: LM_DATA_DIR when set, otherwise the
// XDG-style default the launchd installers already create
// (<home>/.local/state/mr-bot). Never a legacy runtime root.
function resolveDataRoot(env = {}) {
  const override = String(env.LM_DATA_DIR || "").trim();
  let resolved;
  if (override) {
    if (!path.isAbsolute(override)) {
      throw new Error("LM_DATA_DIR must be an absolute path");
    }
    resolved = path.resolve(override);
  } else {
    const home = String(env.HOME || "").trim() || os.homedir();
    resolved = path.resolve(home, ".local", "state", "mr-bot");
  }
  if (LEGACY_SEGMENT.test(resolved) || hasLegacyAniccaRoot(resolved)) {
    throw new Error("Mr.bot data root resolves beneath a forbidden legacy runtime root");
  }
  const canonical = canonicalDataRoot(resolved);
  if (LEGACY_SEGMENT.test(canonical) || hasLegacyAniccaRoot(canonical)) {
    throw new Error("Mr.bot data root resolves beneath a forbidden legacy runtime root");
  }
  return resolved;
}

function resolveRuntimePaths(env = {}) {
  const mode = String(env.LM_MODE || "").trim();
  if (!MODES.has(mode)) {
    throw new Error("LM_MODE must be local or cloud");
  }
  const dataDir = absoluteRoot(env, "LM_DATA_DIR");
  const cacheDir = absoluteRoot(env, "LM_CACHE_DIR");
  return {
    dataDir,
    cacheDir,
    objectDir: path.join(dataDir, "objects"),
    receiptDir: path.join(dataDir, "receipts"),
    logDir: path.join(dataDir, "logs"),
  };
}

module.exports = { resolveDataRoot, resolveRuntimePaths };
