"use strict";

const SAFE_KEY = /^[A-Za-z0-9_.-]{1,160}$/;
const SECRET_SHAPE = /(?:api[_ -]?key|access[_ -]?token|password|secret|cookie|session)/i;

function unavailable() {
  throw new Error("Luma registration form unavailable");
}

function cleanText(value, max = 500) {
  const text = String(value == null ? "" : value).replace(/\s+/g, " ").trim();
  if (!text || text.length > max || /[\x00-\x1f\x7f]/.test(text)) unavailable();
  return text;
}

function cleanLabel(value) {
  return cleanText(value).replace(/\s*\*\s*$/, "").trim();
}

async function readLumaRegistrationForm(scope) {
  if (!scope || typeof scope.evaluate !== "function") unavailable();
  let rawFields;
  try {
    rawFields = await scope.evaluate((scopeRoot) => {
      const root = scopeRoot && typeof scopeRoot.querySelectorAll === "function"
        ? scopeRoot
        : document;
      const insideRoot = (node) => root === document || node === root || root.contains(node);
      const query = (selector) => {
        const nodes = [...root.querySelectorAll(selector)];
        if (root !== document && typeof root.matches === "function" && root.matches(selector)) {
          nodes.unshift(root);
        }
        return nodes;
      };
      const closestInsideRoot = (node, selector) => {
        let current = node;
        while (current && insideRoot(current)) {
          if (typeof current.matches === "function" && current.matches(selector)) return current;
          if (current === root) break;
          current = current.parentElement;
        }
        return null;
      };
      const clean = (value) => String(value == null ? "" : value).replace(/\s+/g, " ").trim();
      const flag = (node, attribute) => {
        const value = node && node.getAttribute(attribute);
        return value !== null && ["", "1", "true", "required", "yes"].includes(
          String(value).trim().toLowerCase(),
        );
      };
      const rootFor = (node) => closestInsideRoot(
        node,
        "[data-luma-form-field], [data-registration-field], [data-field-name], [data-name], fieldset, [role='group']",
      ) || node;
      const htmlRequired = (node) => Boolean(node && (
        node.hasAttribute("required") || flag(node, "aria-required")
      ));
      const appRequired = (node) => {
        const root = rootFor(node);
        return htmlRequired(node)
          || flag(node, "data-required")
          || flag(node, "data-app-required")
          || flag(root, "data-required")
          || flag(root, "data-app-required")
          || flag(root, "aria-required");
      };
      const exactName = (node, includeHiddenName = false) => {
        const root = rootFor(node);
        const hidden = includeHiddenName ? root.querySelector("input[type='hidden'][name]") : null;
        const names = new Set([
          node.getAttribute("name"),
          root.getAttribute("name"),
          root.getAttribute("data-field-name"),
          root.getAttribute("data-name"),
          hidden && hidden.getAttribute("name"),
        ].map(clean).filter(Boolean));
        return names.size === 1 ? [...names][0] : "";
      };
      const labelledText = (node, root) => {
        const fromIds = (source, value) => String(value || "").split(/\s+/)
          .map((id) => source.ownerDocument && source.ownerDocument.getElementById(id))
          .map((element) => element && clean(element.textContent))
          .filter(Boolean);
        const labels = node.labels ? [...node.labels].map((label) => clean(label.textContent)) : [];
        const owner = closestInsideRoot(node, "label");
        const rootLabel = root.querySelector("label, legend, [data-label]");
        return [
          node.getAttribute("data-label"),
          node.getAttribute("aria-label"),
          ...fromIds(node, node.getAttribute("aria-labelledby")),
          ...labels,
          owner && owner.textContent,
          root.getAttribute("data-label"),
          root.getAttribute("aria-label"),
          ...fromIds(root, root.getAttribute("aria-labelledby")),
          rootLabel && (rootLabel.getAttribute("data-label") || rootLabel.textContent),
        ].map(clean).find(Boolean) || "";
      };
      const optionText = (nodes) => [...nodes]
        .map((node) => clean(node.getAttribute("aria-label") || node.textContent))
        .filter(Boolean);
      const fields = [];
      const seen = new Set();
      const add = (node, raw) => {
        if (seen.has(node)) return;
        seen.add(node);
        fields.push(raw);
      };
      const standard = query(
        "input[name], textarea[name], select[name], input[required], textarea[required], select[required], input[aria-required='true'], textarea[aria-required='true'], select[aria-required='true']",
      );
      for (const node of standard) {
        const tag = node.tagName.toLowerCase();
        const type = tag === "input" ? String(node.getAttribute("type") || "text").toLowerCase() : "";
        const oneTimeCode = tag === "input" && String(node.getAttribute("autocomplete") || "")
          .trim().toLowerCase() === "one-time-code";
        const required = appRequired(node);
        if (tag === "input" && ["hidden", "submit", "button", "image", "reset", "file"].includes(type)) continue;
        if (!required && !node.getAttribute("name")) continue;
        const customDropdown = String(node.getAttribute("role") || "").trim().toLowerCase() === "combobox"
          && String(node.getAttribute("aria-haspopup") || "").trim().toLowerCase() === "listbox";
        const name = exactName(node);
        if (customDropdown && required && !name) continue;
        const root = rootFor(node);
        add(node, {
          label: labelledText(node, root),
          name,
          tag,
          type: oneTimeCode ? "otp" : type,
          html_required: htmlRequired(node),
          app_required: required,
          options: tag === "select" ? optionText(node.querySelectorAll("option")) : [],
        });
      }
      const multiSelects = query([
        "[data-luma-control='multi-select']",
        "[data-control='multi-select']",
        "[data-field-type='multi-select']",
        "[role='listbox'][aria-multiselectable='true']",
        "[role='listbox'][data-multiple='true']",
        "[role='combobox'][aria-multiselectable='true']",
      ].join(", "));
      for (const node of multiSelects) {
        const required = appRequired(node);
        const name = exactName(node, true);
        if (!required && !name) continue;
        const root = rootFor(node);
        add(node, {
          label: labelledText(node, root),
          name,
          tag: node.tagName.toLowerCase(),
          type: "multi-select",
          html_required: htmlRequired(node),
          app_required: required,
          options: optionText(node.querySelectorAll("[role='option'], [aria-pressed]")),
        });
      }
      const checkboxes = query([
        "[role='checkbox']",
        "[data-luma-control='checkbox']",
        "[data-control='checkbox']",
        "[data-field-type='checkbox']",
      ].join(", "));
      for (const node of checkboxes) {
        const required = appRequired(node);
        const name = exactName(node, true);
        if (!required && !name) continue;
        const root = rootFor(node);
        add(node, {
          label: labelledText(node, root),
          name,
          tag: node.tagName.toLowerCase(),
          type: "checkbox",
          html_required: htmlRequired(node),
          app_required: required,
          options: [],
        });
      }
      const dropdowns = query("[role='combobox'][aria-haspopup='listbox']");
      let dropdownOrdinal = 0;
      for (const node of dropdowns) {
        const required = appRequired(node);
        const name = exactName(node, true);
        if (!required || name) continue;
        const root = rootFor(node);
        add(node, {
          label: labelledText(node, root),
          name: `luma_dropdown_${dropdownOrdinal}`,
          tag: node.tagName.toLowerCase(),
          type: "dropdown",
          html_required: htmlRequired(node),
          app_required: required,
          options: optionText(root.querySelectorAll("[role='option']")),
        });
        dropdownOrdinal += 1;
      }
      const requiredControls = query(
        "[required], [aria-required='true'], [data-required], [data-app-required]",
      );
      for (const node of requiredControls) {
        if (!appRequired(node) || [...seen].some((field) => node === field || node.contains(field))) continue;
        const root = rootFor(node);
        add(node, {
          label: labelledText(node, root),
          name: exactName(node, true),
          tag: node.tagName.toLowerCase(),
          type: "unsupported",
          html_required: htmlRequired(node),
          app_required: true,
          options: [],
        });
      }
      return fields.length > 0 ? fields : null;
    });
  } catch {
    unavailable();
  }
  if (rawFields === null) return null;
  return normalizeLumaRegistrationForm(rawFields);
}

function controlFor(field) {
  const type = String(field.type || "").trim().toLowerCase();
  const tag = String(field.tag || "").trim().toLowerCase();
  if (type === "tel") return "phone";
  if (type === "dropdown") return "dropdown";
  if (type === "multi-select") return "multi_select";
  if (type === "checkbox") return "checkbox";
  if (type === "radio") return "radio";
  if (tag === "select") return "select";
  if (tag === "textarea") return "textarea";
  if (["text", "email", "url"].includes(type)) return type;
  unavailable();
}

function normalizeLumaRegistrationForm(rawFields) {
  if (!Array.isArray(rawFields) || rawFields.length < 1 || rawFields.length > 50) unavailable();
  const seen = new Set();
  const fields = rawFields.map((raw) => {
    if (!raw || typeof raw !== "object" || Array.isArray(raw)) unavailable();
    const key = String(raw.name == null ? "" : raw.name).trim();
    const label = cleanLabel(raw.label);
    if (!SAFE_KEY.test(key) || seen.has(key) || SECRET_SHAPE.test(`${key} ${label}`)) unavailable();
    seen.add(key);
    const options = Array.isArray(raw.options) ? raw.options.map((value) => cleanText(value, 200)) : unavailable();
    if (options.length > 100 || new Set(options).size !== options.length) unavailable();
    return Object.freeze({
      key,
      label,
      control: controlFor(raw),
      required: raw.html_required === true || raw.app_required === true,
      options: Object.freeze(options),
    });
  });
  return Object.freeze({ kind: "luma_registration_form", fields: Object.freeze(fields) });
}

module.exports = {
  normalizeLumaRegistrationForm,
  readLumaRegistrationForm,
};
