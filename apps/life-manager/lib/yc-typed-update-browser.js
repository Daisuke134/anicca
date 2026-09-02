"use strict";

const { createHash } = require("node:crypto");

const ID = "0b61fe42-e383-490d-b60e-04f1ad7ec5df";
const ROUTES = Object.freeze({
  demo_update: `/apps/${ID}/edit/demo`,
  progress_update: `/apps/${ID}/edit/progress`,
  team_update: `/apps/${ID}/edit/cofounder`,
  founder_profile_update: "/bio/721f696b-0566-4a16-bda7-a9c368b1eac1/edit",
});
const ACTIVATIONS = Object.freeze({
  demo_update: "Save & back",
  progress_update: "Submit update",
  team_update: "Submit update",
  founder_profile_update: "Save founder profile",
});
const TEXT_FIELDS = Object.freeze({
  progress_update: Object.freeze(["productLink", "productCreds", "howfar", "worked", "techstack"]),
  team_update: Object.freeze(["others2", "cofounder"]),
  founder_profile_update: Object.freeze(["fhack", "fability", "projects", "awards", "testScores", "clubs"]),
});
const CHOICES = Object.freeze([
  Object.freeze({ name: "people_using", question: "Are people using your product?" }),
  Object.freeze({ name: "have_revenue", question: "Do you have revenue?" }),
]);

function fail(reason) { throw new Error(`YC typed update browser ${reason}`); }
function stable(value) {
  if (Array.isArray(value)) return `[${value.map(stable).join(",")}]`;
  if (value && typeof value === "object") return `{${Object.keys(value).sort().map((key) => `${JSON.stringify(key)}:${stable(value[key])}`).join(",")}}`;
  return JSON.stringify(value);
}
function digest(value) { return createHash("sha256").update(stable(value)).digest("hex"); }
function validateOperation(operation) {
  if (!operation || !Object.hasOwn(ROUTES, operation.operation_type)) fail("operation invalid");
  if (operation.route !== ROUTES[operation.operation_type]) fail("route invalid");
  if (!operation.payload || typeof operation.payload !== "object" || !/^[0-9a-f]{64}$/.test(String(operation.expected_readback_digest || ""))) fail("payload invalid");
}

function createYcTypedUpdateBrowserAdapter(options = {}) {
  const { driver, artifactResolver } = options;
  const methods = ["navigate", "setText", "setChoice", "setFile", "activate", "readText", "readChoice", "readDemo"];
  if (!driver || methods.some((name) => typeof driver[name] !== "function")) fail("driver invalid");

  return Object.freeze({
    async apply(operation) {
      validateOperation(operation);
      await driver.navigate(operation.route);
      if (operation.operation_type === "demo_update") {
        if (typeof artifactResolver !== "function") fail("artifact resolver invalid");
        const artifact = await artifactResolver(operation.payload.demo_video.source_ref);
        if (!artifact || artifact.digest !== operation.payload.demo_video.artifact_digest || artifact.digest !== operation.asset_digest || typeof artifact.path !== "string") fail("artifact binding invalid");
        await driver.setFile(artifact.path);
      } else {
        for (const name of TEXT_FIELDS[operation.operation_type]) await driver.setText(name, operation.payload[name]);
        if (operation.operation_type === "progress_update") {
          for (const choice of CHOICES) await driver.setChoice(choice.question, operation.payload[choice.name] ? "Yes" : "No");
        }
      }
      await driver.activate(ACTIVATIONS[operation.operation_type]);
    },

    async readback(operation) {
      validateOperation(operation);
      await driver.navigate(operation.route);
      if (operation.operation_type === "demo_update") {
        const media = await driver.readDemo();
        return media && media.ready === true
          ? { result: "confirmed", readback_digest: operation.expected_readback_digest }
          : { result: "not_applied", readback_digest: digest({ demo_video: null }) };
      }
      const observed = {};
      for (const name of TEXT_FIELDS[operation.operation_type]) observed[name] = await driver.readText(name);
      if (operation.operation_type === "progress_update") {
        for (const choice of CHOICES) observed[choice.name] = (await driver.readChoice(choice.question)) === "Yes";
      }
      const observedDigest = digest(observed);
      return observedDigest === operation.expected_readback_digest
        ? { result: "confirmed", readback_digest: observedDigest }
        : { result: "not_applied", readback_digest: observedDigest };
    },
  });
}

function createPlaywrightYcTypedUpdateDriver(page, options = {}) {
  const origin = options.origin || "https://apply.ycombinator.com";
  if (!page || typeof page.goto !== "function" || origin !== "https://apply.ycombinator.com") fail("page invalid");
  const exactOne = async (locator, label) => {
    if (await locator.count() !== 1) fail(`${label} cardinality`);
    return locator;
  };
  const questionId = (question) => question === "Are people using your product?" ? "stage" : question === "Do you have revenue?" ? "revenue" : null;
  return Object.freeze({
    async navigate(route) {
      if (!Object.values(ROUTES).includes(route)) fail("navigation route invalid");
      await page.goto(`${origin}${route}`, { waitUntil: "domcontentloaded", timeout: 30_000 });
      const current = new URL(page.url());
      if (current.origin !== origin || current.pathname !== route || current.search || current.hash) fail("navigation readback invalid");
    },
    async setText(name, value) {
      const locator = await exactOne(page.locator(`[name=${name}]`), `field ${name}`);
      await locator.evaluate((element, next) => {
        const prototype = element instanceof HTMLTextAreaElement ? HTMLTextAreaElement.prototype : HTMLInputElement.prototype;
        const setter = Object.getOwnPropertyDescriptor(prototype, "value").set;
        setter.call(element, next);
        for (const type of ["input", "change", "blur"]) element.dispatchEvent(new Event(type, { bubbles: true }));
      }, value);
    },
    async setChoice(question, option) {
      const id = questionId(question);
      if (!id || !["Yes", "No"].includes(option)) fail("choice invalid");
      const container = await exactOne(page.locator(`#${id}`), `question ${id}`);
      if ((await container.locator("label").first().innerText()).trim() !== question) fail("question drift");
      const label = await exactOne(container.getByText(option, { exact: true }), `option ${id}`);
      await label.click();
    },
    async setFile(file) {
      const input = await exactOne(page.locator('input[type=file][accept="video/*"]'), "demo file");
      await input.setInputFiles(file);
      await page.waitForFunction(() => {
        const form = document.querySelector(".video-form");
        const progress = document.querySelector("[role=progressbar]");
        return form?.getAttribute("data-video-saved") === "true" || progress?.getAttribute("aria-valuenow") === "100";
      }, null, { timeout: 120_000 });
    },
    async activate(text) {
      if (!Object.values(ACTIVATIONS).includes(text)) fail("activation invalid");
      const button = await exactOne(page.getByRole("button", { name: text, exact: true }), "activation");
      await button.click({ timeout: 30_000 });
      await page.waitForLoadState("domcontentloaded", { timeout: 30_000 }).catch(() => {});
    },
    async readText(name) {
      const locator = await exactOne(page.locator(`[name=${name}]`), `readback ${name}`);
      return locator.inputValue();
    },
    async readChoice(question) {
      const id = questionId(question);
      if (!id) fail("readback choice invalid");
      const container = await exactOne(page.locator(`#${id}`), `readback question ${id}`);
      return container.evaluate((element) => {
        const candidates = [...element.querySelectorAll("label")].filter((label) => ["Yes", "No"].includes(label.textContent.trim()));
        const selected = candidates.filter((label) => {
          const marker = label.parentElement?.querySelector("div");
          if (!marker) return false;
          const signature = `${marker.className} ${marker.innerHTML}`;
          return /bg-|border-[2-9]|border-\[[2-9]px\]|<div|<span|checked/i.test(signature);
        });
        return selected.length === 1 ? selected[0].textContent.trim() : null;
      });
    },
    async readDemo() {
      await page.waitForFunction(() => {
        const video = document.querySelector("video");
        return video && video.readyState >= 1 && Number.isFinite(video.duration) && video.videoWidth > 0 && video.videoHeight > 0;
      }, null, { timeout: 45_000 }).catch(() => {});
      return page.evaluate(() => {
        const videos = [...document.querySelectorAll("video")];
        if (videos.length !== 1) return { ready: false };
        const video = videos[0];
        let storageOrigin = null;
        try { storageOrigin = new URL(video.currentSrc).origin; } catch {}
        return {
          ready: video.readyState >= 1 && Number.isFinite(video.duration) && video.videoWidth > 0 && video.videoHeight > 0 && storageOrigin === "https://yc-app-vids.s3.us-west-2.amazonaws.com",
          duration_seconds: Number.isFinite(video.duration) ? video.duration : null,
          width: video.videoWidth,
          height: video.videoHeight,
          storage_origin: storageOrigin,
        };
      });
    },
  });
}

module.exports = { createYcTypedUpdateBrowserAdapter, createPlaywrightYcTypedUpdateDriver };
