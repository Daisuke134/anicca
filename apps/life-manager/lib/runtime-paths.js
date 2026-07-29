"use strict";

const os = require("node:os");
const path = require("node:path");

const MODES = new Set(["local", "cloud"]);
const LEGACY_SEGMENT = /(?:^|\/)(?:\.openclaw|profitable-claude|life-manager-v0)(?:\/|$)/i;

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

// The portable Life Manager data root: LM_DATA_DIR when set, otherwise the
// XDG-style default the launchd installers already create
// (<home>/.local/state/life-manager). Never a legacy runtime root.
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
    resolved = path.resolve(home, ".local", "state", "life-manager");
  }
  if (LEGACY_SEGMENT.test(resolved) || hasLegacyAniccaRoot(resolved)) {
    throw new Error("Life Manager data root resolves beneath a forbidden legacy runtime root");
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
