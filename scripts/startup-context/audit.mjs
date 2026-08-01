#!/usr/bin/env node

import { auditStartupContext, loadStartupContext } from "./lib.mjs";

const contextPath = new URL("../../.agents/startup-context.json", import.meta.url);
const context = await loadStartupContext(contextPath);
const result = await auditStartupContext(context);

process.stdout.write(`${JSON.stringify(result, null, 2)}\n`);
if (!result.ok) process.exitCode = 1;
