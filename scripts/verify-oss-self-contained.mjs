#!/usr/bin/env node

import { execFileSync } from "node:child_process";
import {
  existsSync,
  readFileSync,
  readlinkSync,
  realpathSync,
} from "node:fs";
import { dirname, isAbsolute, relative, resolve, sep } from "node:path";
import { pathToFileURL } from "node:url";

const REQUIRED_SOURCES = [
  "life-manager",
  "anicca-products",
  "profitable-claude",
  "anicca-dais",
];

const ACTIVE_ROOTS = [
  "apps/life-manager",
  "runtime",
  "scripts",
  "services",
  "skills",
  "install.sh",
  "start-local.sh",
];

const GENERATED_EXTENSIONS = new Set([
  ".gif", ".jpeg", ".jpg", ".log", ".mov", ".mp4", ".png", ".sqlite", ".webp",
]);

const PORTABLE_RUNTIME_FILES = new Set([
  ".gitignore",
  ".gitkeep",
]);

const VERIFIED_VENDOR_ROOTS = [
  "skills/capafy-autopublish/vendor",
];

function git(root, args, encoding = "utf8") {
  return execFileSync("git", args, {
    cwd: root,
    encoding,
    stdio: ["ignore", "pipe", "pipe"],
  });
}

function trackedEntries(root) {
  const raw = git(root, ["ls-files", "-s", "-z"], "buffer");
  return raw
    .toString("utf8")
    .split("\0")
    .filter(Boolean)
    .map((entry) => {
      const match = entry.match(/^(\d{6}) ([0-9a-f]{40,64}) (\d)\t([\s\S]+)$/);
      if (!match) {
        throw new Error(`unparseable git index entry: ${entry.slice(0, 80)}`);
      }
      return { mode: match[1], object: match[2], stage: Number(match[3]), path: match[4] };
    });
}

function isActivePath(path) {
  return ACTIVE_ROOTS.some((root) => path === root || path.startsWith(`${root}/`));
}

function isVerifiedVendorPath(path) {
  return VERIFIED_VENDOR_ROOTS.some((root) => path === root || path.startsWith(`${root}/`));
}

function isTestFixturePath(path) {
  const basename = path.slice(path.lastIndexOf("/") + 1);
  return /(?:^|[._-])tests?(?:[._-]|$)/iu.test(basename)
    || /(^|\/)(?:__tests__|test|tests|fixtures)(\/|$)/u.test(path);
}

function isWithinRoot(root, candidate) {
  const rel = relative(root, candidate);
  return rel === "" || (!rel.startsWith(`..${sep}`) && rel !== ".." && !isAbsolute(rel));
}

function sourceRootViolation(text) {
  const forbidden = [
    /\/Users\/[^/\s"'`]+/u,
    /\/home\/[^/\s"'`]+\/(?:profitable-claude|anicca(?:-oss|-project)?|anicca-dais|\.openclaw)(?=[/}\s"'`]|$)/u,
    /(?:~|\$HOME)\/anicca(?:-oss)?(?=[/}\s"'`]|$)/u,
    /(?:~|\$HOME)\/profitable-claude(?=[/}\s"'`]|$)/u,
    /(?:~|\$HOME)\/anicca-project(?=[/}\s"'`]|$)/u,
    /(?:~|\$HOME)\/\.openclaw(?=[/}\s"'`]|$)/u,
    /\/opt\/life-manager(?=[/}\s"'`]|$)/u,
  ];
  return forbidden.some((pattern) => pattern.test(text));
}

function personalRuntimeDefaultViolation(text) {
  const forbidden = [
    /--target(?:=|\s+)(?:"|')?\d{6,}/u,
    /(?:TELEGRAM|CHAT)[A-Z0-9_]*(?:=|:-)(?:"|')?\d{6,}/u,
    /\b(?!(?:you|user|example)@)[A-Za-z0-9._%+-]+@gmail\.com\b/iu,
  ];
  return forbidden.some((pattern) => pattern.test(text));
}

function looksTextual(path, bytes) {
  if (bytes.includes(0)) return false;
  const extension = path.includes(".") ? path.slice(path.lastIndexOf(".")).toLowerCase() : "";
  return !GENERATED_EXTENSIONS.has(extension);
}

function isRuntimeCopy(path) {
  const basename = path.slice(path.lastIndexOf("/") + 1);
  if (PORTABLE_RUNTIME_FILES.has(basename) || /\.example(?:\.|$)/u.test(basename)) return false;
  return /(^|\/)(?:state|logs?|output|work|sessions?)(\/|$)/u.test(path);
}

function generatedArtifact(path) {
  const extension = path.includes(".") ? path.slice(path.lastIndexOf(".")).toLowerCase() : "";
  return GENERATED_EXTENSIONS.has(extension);
}

function readManifest(root, violations) {
  const manifestPath = "docs/manifests/oss-merge-1-sources.json";
  const absolute = resolve(root, manifestPath);
  if (!existsSync(absolute)) {
    violations.push({ code: "manifest_missing", path: manifestPath, detail: "required source manifest" });
    return;
  }
  let manifest;
  try {
    manifest = JSON.parse(readFileSync(absolute, "utf8"));
  } catch {
    violations.push({ code: "manifest_invalid", path: manifestPath, detail: "invalid JSON" });
    return;
  }
  const ids = new Set(
    Array.isArray(manifest.sources)
      ? manifest.sources.map((source) => source && source.id).filter(Boolean)
      : [],
  );
  for (const id of REQUIRED_SOURCES) {
    if (!ids.has(id)) {
      violations.push({ code: "manifest_source_missing", path: id, detail: "source not classified" });
    }
  }
}

export function verifyRepository(inputRoot) {
  const root = realpathSync(resolve(inputRoot));
  const violations = [];
  const entries = trackedEntries(root);

  for (const entry of entries) {
    const absolute = resolve(root, entry.path);
    if (entry.mode === "160000") {
      violations.push({ code: "gitlink", path: entry.path, detail: "Git submodule dependency" });
      continue;
    }
    if (entry.mode === "120000") {
      let target;
      try {
        target = readlinkSync(absolute);
      } catch {
        target = git(root, ["show", `:${entry.path}`]).trim();
      }
      const resolvedTarget = resolve(dirname(absolute), target);
      if (!isWithinRoot(root, resolvedTarget)) {
        violations.push({ code: "symlink_escape", path: entry.path, detail: "target leaves checkout" });
      }
      continue;
    }
    if (!isActivePath(entry.path) || !existsSync(absolute)) continue;

    if (isRuntimeCopy(entry.path)) {
      violations.push({ code: "runtime_copy", path: entry.path, detail: "runtime data is tracked" });
      continue;
    }
    if (generatedArtifact(entry.path)) {
      violations.push({ code: "generated_artifact", path: entry.path, detail: "generated binary is tracked" });
      continue;
    }
    const bytes = readFileSync(absolute);
    const isFirstPartyText =
      !isVerifiedVendorPath(entry.path)
      && !isTestFixturePath(entry.path)
      && looksTextual(entry.path, bytes);
    const text = isFirstPartyText ? bytes.toString("utf8") : "";
    if (isFirstPartyText && sourceRootViolation(text)) {
      violations.push({
        code: "forbidden_source_root",
        path: entry.path,
        detail: "active source depends on a developer-local root",
      });
    }
    if (isFirstPartyText && personalRuntimeDefaultViolation(text)) {
      violations.push({
        code: "personal_runtime_default",
        path: entry.path,
        detail: "active source embeds a user's messaging or mail destination",
      });
    }
  }

  const runnerPath = "skills/agent-runner/agent_runner.py";
  if (!existsSync(resolve(root, runnerPath))) {
    violations.push({ code: "required_file_missing", path: runnerPath, detail: "canonical runner absent" });
  }

  readManifest(root, violations);
  violations.sort((left, right) =>
    left.path.localeCompare(right.path) || left.code.localeCompare(right.code));
  return { ok: violations.length === 0, violations };
}

function parseArgs(argv) {
  let root = process.cwd();
  let json = false;
  for (let index = 0; index < argv.length; index += 1) {
    const arg = argv[index];
    if (arg === "--root") {
      root = argv[index + 1] || "";
      index += 1;
    } else if (arg === "--json") {
      json = true;
    } else {
      throw new Error(`unknown argument: ${arg}`);
    }
  }
  if (!root) throw new Error("--root requires a path");
  return { root, json };
}

function main() {
  const { root, json } = parseArgs(process.argv.slice(2));
  const result = verifyRepository(root);
  if (json) {
    process.stdout.write(`${JSON.stringify(result)}\n`);
  } else if (result.ok) {
    process.stdout.write("OSS self-contained verification: PASS\n");
  } else {
    process.stderr.write(`OSS self-contained verification: FAIL (${result.violations.length})\n`);
    for (const violation of result.violations) {
      process.stderr.write(`${violation.code}\t${violation.path}\n`);
    }
  }
  process.exitCode = result.ok ? 0 : 1;
}

if (process.argv[1] && pathToFileURL(resolve(process.argv[1])).href === import.meta.url) {
  main();
}
