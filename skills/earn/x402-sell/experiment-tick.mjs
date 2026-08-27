#!/usr/bin/env node
// Brain-independent five-minute revenue controller. launchd invokes this one-shot every 300s;
// model/tool-call failures therefore cannot stall the bounded offer experiment.
import { fileURLToPath } from 'node:url';

import { activateExperiment } from './store-activate.mjs';
import { improveAndApply } from './store-improve.mjs';

export async function runExperimentTick(env = process.env, deps = {}) {
  const improve = deps.improve || improveAndApply;
  const activate = deps.activate || activateExperiment;
  const result = await improve(env);
  if (result?.experiment?.action !== 'applied') return result;
  const activation = await activate(env);
  return { ...result, activation };
}

const isMain = process.argv[1] && fileURLToPath(import.meta.url) === process.argv[1];
if (isMain) {
  runExperimentTick()
    .then((result) => process.stdout.write(`${JSON.stringify(result)}\n`))
    .catch((error) => {
      process.stdout.write(`${JSON.stringify({ error: String(error?.message || error) })}\n`);
      process.exitCode = 1;
    });
}
