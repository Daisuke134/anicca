"use strict";

const fs = require("node:fs");
const path = require("node:path");

const CONTRACT_METHODS = Object.freeze([
  "plan",
  "execute",
  "reconcile",
  "verify",
  "report",
]);
const DEFINITION_KEYS = new Set([
  "adapter_id",
  "loop_id",
  "capability",
  "effect_classes",
  "module_ref",
  "factory_export",
]);
const EFFECT_CLASSES = new Set(["none", "publish", "message", "money"]);
const IDENTIFIER = /^[a-z0-9][a-z0-9.-]*$/;
const JAVASCRIPT_EXPORT = /^[A-Za-z_$][A-Za-z0-9_$]*$/;
const CREDENTIAL_KEY = /(?:api[_-]?key|credential|password|secret|token)/i;
const LEGACY_OR_ABSOLUTE = /(?:^\/|^[a-z]:[\\/]|\\|(?:^|\/)\.\.(?:\/|$)|:\/\/|\.openclaw|profitable-claude|life-manager-v0|\/Users\/)/i;

function requiredIdentifier(value, label) {
  const text = String(value == null ? "" : value).trim();
  if (!IDENTIFIER.test(text)) throw new Error(`${label} invalid`);
  return text;
}

function portableModuleRef(value) {
  const ref = String(value == null ? "" : value).trim();
  if (!ref || LEGACY_OR_ABSOLUTE.test(ref) || !ref.endsWith(".js")) {
    throw new Error("adapter module must be a portable repository-relative JavaScript path");
  }
  return ref;
}

function javascriptExport(value) {
  const name = String(value == null ? "" : value).trim();
  if (!JAVASCRIPT_EXPORT.test(name)) {
    throw new Error("adapter factory export invalid");
  }
  return name;
}

function normalizeDefinition(input) {
  if (!input || typeof input !== "object" || Array.isArray(input)) {
    throw new Error("adapter definition invalid");
  }
  for (const key of Object.keys(input)) {
    if (CREDENTIAL_KEY.test(key)) {
      throw new Error("adapter registry cannot contain credentials");
    }
    if (!DEFINITION_KEYS.has(key)) {
      throw new Error(`adapter definition field unsupported: ${key}`);
    }
  }
  const effectClasses = input.effect_classes;
  if (
    !Array.isArray(effectClasses)
    || effectClasses.length < 1
    || effectClasses.some((value) => !EFFECT_CLASSES.has(value))
  ) {
    throw new Error("adapter effect classes invalid");
  }
  return Object.freeze({
    adapter_id: requiredIdentifier(input.adapter_id, "adapter id"),
    loop_id: requiredIdentifier(input.loop_id, "loop id"),
    capability: requiredIdentifier(input.capability, "adapter capability"),
    effect_classes: Object.freeze([...new Set(effectClasses)]),
    module_ref: portableModuleRef(input.module_ref),
    factory_export: javascriptExport(input.factory_export),
  });
}

function assertAdapterContract(adapter, adapterId) {
  if (!adapter || typeof adapter !== "object" || Array.isArray(adapter)) {
    throw new Error(`adapter ${adapterId} invalid`);
  }
  for (const method of CONTRACT_METHODS) {
    if (typeof adapter[method] !== "function") {
      throw new Error(`adapter ${adapterId} missing ${method}`);
    }
  }
  return adapter;
}

function createLoopAdapterRegistry({ definitions, adapters } = {}) {
  if (!Array.isArray(definitions) || definitions.length < 1) {
    throw new Error("adapter definitions are required");
  }
  if (!adapters || typeof adapters !== "object" || Array.isArray(adapters)) {
    throw new Error("adapter implementations are required");
  }
  const normalized = definitions.map(normalizeDefinition);
  const byId = new Map();
  const byLoopId = new Map();
  const byCapability = new Map();

  for (const definition of normalized) {
    if (byId.has(definition.adapter_id)) {
      throw new Error(`adapter id duplicate: ${definition.adapter_id}`);
    }
    if (byLoopId.has(definition.loop_id)) {
      throw new Error(`loop id duplicate: ${definition.loop_id}`);
    }
    if (byCapability.has(definition.capability)) {
      throw new Error(`capability duplicate: ${definition.capability}`);
    }
    const adapter = assertAdapterContract(
      adapters[definition.adapter_id],
      definition.adapter_id,
    );
    byId.set(definition.adapter_id, adapter);
    byLoopId.set(definition.loop_id, adapter);
    byCapability.set(definition.capability, adapter);
  }

  return Object.freeze({
    list: () => [...normalized],
    hasCapability: (capability) => byCapability.has(capability),
    getByCapability(capability) {
      const adapter = byCapability.get(capability);
      if (!adapter) throw new Error(`capability adapter unavailable: ${capability}`);
      return adapter;
    },
    getReconciliationAdapter(capability) {
      const adapter = byCapability.get(capability);
      if (!adapter) throw new Error(`capability adapter unavailable: ${capability}`);
      return Object.freeze({
        inspectEffect: (effect) => adapter.reconcile(effect),
      });
    },
    getByLoopId(loopId) {
      const adapter = byLoopId.get(loopId);
      if (!adapter) throw new Error(`loop adapter unavailable: ${loopId}`);
      return adapter;
    },
  });
}

function loadLoopAdapterManifest(manifestPath) {
  const absolute = path.resolve(String(manifestPath || ""));
  let parsed;
  try {
    parsed = JSON.parse(fs.readFileSync(absolute, "utf8"));
  } catch (error) {
    throw new Error(`loop adapter manifest invalid: ${error.message}`);
  }
  if (
    !parsed
    || parsed.schema_version !== 1
    || !Array.isArray(parsed.adapters)
    || parsed.adapters.length < 1
  ) {
    throw new Error("loop adapter manifest contract invalid");
  }
  return Object.freeze({
    schema_version: 1,
    adapters: Object.freeze(parsed.adapters.map(normalizeDefinition)),
  });
}

function createConfiguredLoopAdapterRegistry(options = {}) {
  const appRoot = path.resolve(options.appRoot || path.join(__dirname, ".."));
  const manifestPath = path.resolve(
    options.manifestPath || path.join(appRoot, "config/loop-adapters.json"),
  );
  const manifest = loadLoopAdapterManifest(manifestPath);
  const requireModule = options.requireModule || require;
  const servicesByAdapter = options.servicesByAdapter || {};
  const adapters = {};

  for (const definition of manifest.adapters) {
    const modulePath = path.resolve(appRoot, definition.module_ref);
    if (modulePath !== appRoot && !modulePath.startsWith(`${appRoot}${path.sep}`)) {
      throw new Error("adapter module escaped the application root");
    }
    const loaded = requireModule(modulePath);
    const factory = loaded && loaded[definition.factory_export];
    if (typeof factory !== "function") {
      throw new Error(`adapter factory unavailable: ${definition.factory_export}`);
    }
    adapters[definition.adapter_id] = factory(
      servicesByAdapter[definition.adapter_id] || {},
    );
  }
  return createLoopAdapterRegistry({
    definitions: manifest.adapters,
    adapters,
  });
}

module.exports = {
  CONTRACT_METHODS,
  createLoopAdapterRegistry,
  loadLoopAdapterManifest,
  createConfiguredLoopAdapterRegistry,
};
