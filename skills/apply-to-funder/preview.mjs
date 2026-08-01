#!/usr/bin/env node

import { readFile } from "node:fs/promises";
import { resolve } from "node:path";

import { loadStartupContext } from "../../scripts/startup-context/lib.mjs";
import { compileFunderPreview } from "./lib/context.mjs";

function option(name) {
  const index = process.argv.indexOf(name);
  return index >= 0 ? process.argv[index + 1] : null;
}

const funderId = option("--funder");
if (!funderId || !/^[a-z0-9-]+$/.test(funderId)) {
  throw new Error("Usage: preview.mjs --funder <lowercase-id>");
}

const context = await loadStartupContext(new URL("../../.agents/startup-context.json", import.meta.url));
const funderPath = new URL(`../../fundraising/funders/${funderId}.json`, import.meta.url);
const funderConfig = JSON.parse(await readFile(funderPath, "utf8"));
const preview = await compileFunderPreview({ context, funderConfig });

process.stdout.write(`${JSON.stringify(preview, null, 2)}\n`);
