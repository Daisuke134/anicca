"use strict";

const fs = require("node:fs");
const path = require("node:path");

const MANIFEST_PATH = path.join(__dirname, "../config/yc-submitted-update-provider.json");
const OPERATION_TYPES = Object.freeze(["demo_update", "progress_update", "team_update", "founder_profile_update"]);
const FIELD_INVENTORY = Object.freeze({
  demo_update: Object.freeze(["demo_video"]),
  progress_update: Object.freeze(["productLink", "productCreds", "howfar", "worked", "techstack", "people_using", "have_revenue"]),
  team_update: Object.freeze(["others2", "cofounder"]),
  founder_profile_update: Object.freeze(["fhack", "fability", "projects", "awards", "testScores", "clubs"]),
});
const ROUTES = Object.freeze({
  demo_update: "/apps/{application_id}/edit/demo",
  progress_update: "/apps/{application_id}/edit/progress",
  team_update: "/apps/{application_id}/edit/cofounder",
  founder_profile_update: "/bio/721f696b-0566-4a16-bda7-a9c368b1eac1/edit",
});
const ACTIVATIONS = Object.freeze({ demo_update: "Save & back", progress_update: "Submit update", team_update: "Submit update", founder_profile_update: "Save founder profile" });
const READBACKS = Object.freeze({ demo_update: "remote_media_ready_and_remove_control", progress_update: "exact_value_and_selected_option_after_submit", team_update: "exact_value_after_submit", founder_profile_update: "exact_value_after_save" });
const QUESTIONS = Object.freeze({ people_using: "Are people using your product?", have_revenue: "Do you have revenue?" });

function fail(reason) { throw new Error(`YC submitted update provider ${reason} invalid`); }
function stable(value) {
  if (Array.isArray(value)) return `[${value.map(stable).join(",")}]`;
  if (value && typeof value === "object") return `{${Object.keys(value).sort().map((key) => `${JSON.stringify(key)}:${stable(value[key])}`).join(",")}}`;
  return JSON.stringify(value);
}
function exactKeys(value, keys, label) {
  if (!value || typeof value !== "object" || Array.isArray(value) || stable(Object.keys(value).sort()) !== stable([...keys].sort())) fail(label);
}
function deepFreeze(value) {
  if (value && typeof value === "object" && !Object.isFrozen(value)) { Object.freeze(value); for (const nested of Object.values(value)) deepFreeze(nested); }
  return value;
}
function validateField(type, field) {
  const isFile = type === "demo_update";
  const isChoice = type === "progress_update" && ["people_using", "have_revenue"].includes(field.name);
  exactKeys(field, isFile || isChoice ? ["name", "kind", "locator"] : ["name", "kind", "locator", "setter"], "field schema");
  if (isFile) {
    if (field.kind !== "file") fail("file kind");
    exactKeys(field.locator, ["strategy", "selector", "cardinality"], "file locator");
    if (field.locator.strategy !== "css_exact" || field.locator.selector !== "input[type=file][accept=\"video/*\"]" || field.locator.cardinality !== 1) fail("file locator");
    return;
  }
  if (isChoice) {
    if (field.kind !== "choice") fail("choice kind");
    exactKeys(field.locator, ["strategy", "question_text", "option_values", "cardinality"], "choice locator");
    if (field.locator.strategy !== "question_scoped_option" || field.locator.question_text !== QUESTIONS[field.name] || stable(field.locator.option_values) !== stable(["Yes", "No"]) || field.locator.cardinality !== 1) fail("choice locator");
    return;
  }
  if (!(["productLink", "productCreds"].includes(field.name) ? field.kind === "text" : field.kind === "textarea")) fail("text kind");
  exactKeys(field.locator, ["strategy", "selector", "cardinality"], "text locator");
  if (field.locator.strategy !== "css_exact" || field.locator.selector !== `[name=${field.name}]` || field.locator.cardinality !== 1) fail("text locator");
  exactKeys(field.setter, ["strategy", "events"], "setter");
  if (field.setter.strategy !== "native_value_setter" || stable(field.setter.events) !== stable(["input", "change", "blur"])) fail("setter");
}
function validateManifest(manifest) {
  exactKeys(manifest, ["schema_version", "provider_id", "browser_route_id", "mode", "application_submit_operations", "operations"], "manifest");
  if (manifest.schema_version !== 2 || manifest.provider_id !== "yc-submitted-update" || manifest.browser_route_id !== "yc-application" || manifest.mode !== "typed_update" || manifest.application_submit_operations !== 0 || !Array.isArray(manifest.operations) || stable(manifest.operations.map(({ operation_type }) => operation_type)) !== stable(OPERATION_TYPES)) fail("identity");
  if (/Submit application|Save changes|9223|selector_filter/i.test(JSON.stringify(manifest))) fail("unsafe pattern");
  for (const operation of manifest.operations) {
    exactKeys(operation, ["operation_type", "route_template", "atomic", "fields", "activation", "readback"], "operation");
    const type = operation.operation_type;
    if (operation.route_template !== ROUTES[type] || operation.atomic !== true || !Array.isArray(operation.fields) || stable(operation.fields.map(({ name }) => name)) !== stable(FIELD_INVENTORY[type])) fail("operation contract");
    exactKeys(operation.activation, ["kind", "text", "count"], "activation");
    if (operation.activation.kind !== "button_exact_text" || operation.activation.text !== ACTIVATIONS[type] || operation.activation.count !== 1) fail("activation");
    exactKeys(operation.readback, ["required", "strategy"], "readback");
    if (operation.readback.required !== true || operation.readback.strategy !== READBACKS[type]) fail("readback");
    for (const field of operation.fields) validateField(type, field);
  }
  return manifest;
}
function loadYcSubmittedUpdateProviderManifest(options = {}) {
  let manifest;
  try { manifest = JSON.parse((options.readFile || fs.readFileSync)(options.path || MANIFEST_PATH, "utf8")); } catch { fail("file"); }
  return deepFreeze(validateManifest(manifest));
}

module.exports = { loadYcSubmittedUpdateProviderManifest };
