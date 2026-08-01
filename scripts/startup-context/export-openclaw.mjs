#!/usr/bin/env node

import { copyFile, mkdir, readFile, writeFile } from "node:fs/promises";
import { basename, resolve } from "node:path";

import { contextDigest, loadStartupContext, validatePublicArtifact } from "./lib.mjs";

const ALLOWED_FILES = [
  "README.md",
  "answers.en.md",
  "answers.ja.md",
  "assets.json",
  "deck.md",
  "one-pager.md",
];

function option(name) {
  const index = process.argv.indexOf(name);
  return index >= 0 ? process.argv[index + 1] : null;
}

const targetOption = option("--target");
if (!targetOption) throw new Error("--target is required; use a dedicated Life Manager current-kit directory");

const target = resolve(targetOption);
if (target.split("/").includes("submitted")) throw new Error("submitted history is immutable and cannot be an export target");
if (!/life-manager/i.test(basename(target))) throw new Error("export target basename must identify Life Manager");

const source = resolve(new URL("../../fundraising/application-kit/", import.meta.url).pathname);
const context = await loadStartupContext(new URL("../../.agents/startup-context.json", import.meta.url));
const files = [];

for (const file of ALLOWED_FILES) {
  const content = await readFile(resolve(source, file), "utf8");
  const errors = validatePublicArtifact(content, context);
  if (errors.length > 0) throw new Error(`${file} failed validation:\n${errors.join("\n")}`);
  files.push({ file, bytes: Buffer.byteLength(content) });
}

await mkdir(target, { recursive: true });
for (const { file } of files) await copyFile(resolve(source, file), resolve(target, file));

const manifest = {
  context_version: context.context_version,
  context_digest: contextDigest(context),
  source: "fundraising/application-kit",
  files,
  protected_path: "submitted/**",
};
await writeFile(resolve(target, "export-manifest.json"), `${JSON.stringify(manifest, null, 2)}\n`, "utf8");
process.stdout.write(`${JSON.stringify(manifest, null, 2)}\n`);
