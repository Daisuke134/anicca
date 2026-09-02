"use strict";

const ENDPOINT = "http://127.0.0.1:9222";
const ORIGIN = "https://apply.ycombinator.com";
const ALLOWED_ROUTES = Object.freeze([
  "/",
  "/apps/0b61fe42-e383-490d-b60e-04f1ad7ec5df",
  "/apps/0b61fe42-e383-490d-b60e-04f1ad7ec5df/edit/demo",
  "/apps/0b61fe42-e383-490d-b60e-04f1ad7ec5df/edit/progress",
  "/apps/0b61fe42-e383-490d-b60e-04f1ad7ec5df/edit/cofounder",
  "/apps/0b61fe42-e383-490d-b60e-04f1ad7ec5df/edit/video",
  "/bio/721f696b-0566-4a16-bda7-a9c368b1eac1/edit",
]);

function fail(reason) { throw new Error(`YC raw CDP ${reason}`); }
const delay = (milliseconds) => new Promise((resolve) => setTimeout(resolve, milliseconds));

async function openSocket(url) {
  return new Promise((resolve, reject) => {
    const socket = new WebSocket(url);
    const timeout = setTimeout(() => reject(new Error("CDP websocket open timeout")), 15_000);
    socket.addEventListener("open", () => { clearTimeout(timeout); resolve(socket); }, { once: true });
    socket.addEventListener("error", () => { clearTimeout(timeout); reject(new Error("CDP websocket open failed")); }, { once: true });
  });
}

async function createOwnedYcRawCdpPage() {
  const response = await fetch(`${ENDPOINT}/json/new?${encodeURIComponent("about:blank")}`, { method: "PUT" });
  if (!response.ok) fail("target creation failed");
  const target = await response.json();
  if (!target || typeof target.id !== "string" || typeof target.webSocketDebuggerUrl !== "string") fail("target identity invalid");
  const socket = await openSocket(target.webSocketDebuggerUrl);
  let nextId = 1;
  let closed = false;
  const pending = new Map();
  const diagnostics = [];
  const graphqlOperations = new Map();
  socket.addEventListener("message", (event) => {
    let message;
    try { message = JSON.parse(String(event.data)); } catch { return; }
    if (message.method === "Network.requestWillBeSent") {
      try {
        const url = new URL(message.params.request.url);
        if (url.origin === ORIGIN) {
          let operation = null;
          if (url.pathname === "/graphql" && message.params.request.postData) {
            try { operation = JSON.parse(message.params.request.postData).operationName || null; } catch {}
            graphqlOperations.set(message.params.requestId, operation);
          }
          diagnostics.push({ kind: "request", method: message.params.request.method, path: url.pathname, ...(operation ? { operation } : {}) });
        }
      } catch {}
    } else if (message.method === "Network.responseReceived") {
      try {
        const url = new URL(message.params.response.url);
        if (url.origin === ORIGIN) diagnostics.push({ kind: "response", status: message.params.response.status, path: url.pathname, ...(graphqlOperations.get(message.params.requestId) ? { operation: graphqlOperations.get(message.params.requestId) } : {}) });
      } catch {}
    }
    if (!message.id || !pending.has(message.id)) return;
    const waiter = pending.get(message.id);
    pending.delete(message.id);
    if (message.error) waiter.reject(new Error(`CDP ${waiter.method}: ${message.error.message}`));
    else waiter.resolve(message.result || {});
  });
  socket.addEventListener("close", () => {
    closed = true;
    for (const waiter of pending.values()) waiter.reject(new Error("CDP target closed"));
    pending.clear();
  });
  const command = (method, params = {}) => new Promise((resolve, reject) => {
    if (closed) return reject(new Error("CDP target is closed"));
    const id = nextId++;
    pending.set(id, { resolve, reject, method });
    socket.send(JSON.stringify({ id, method, params }));
  });
  await command("Page.enable");
  await command("Runtime.enable");
  await command("DOM.enable");
  await command("Network.enable");

  const evaluate = async (fn, ...args) => {
    const expression = `(${fn.toString()})(...${JSON.stringify(args)})`;
    const result = await command("Runtime.evaluate", { expression, awaitPromise: true, returnByValue: true, userGesture: true });
    if (result.exceptionDetails) fail(`evaluation failed: ${result.exceptionDetails.text || "exception"}`);
    return result.result ? result.result.value : undefined;
  };
  const waitFor = async (fn, args = [], timeout = 30_000) => {
    const deadline = Date.now() + timeout;
    let last;
    while (Date.now() < deadline) {
      try { last = await evaluate(fn, ...args); if (last) return last; } catch {}
      await delay(500);
    }
    return last;
  };
  const navigate = async (route) => {
    if (!ALLOWED_ROUTES.includes(route)) fail("route invalid");
    await command("Page.navigate", { url: `${ORIGIN}${route}` });
    const ready = await waitFor(() => document.readyState === "complete" || document.readyState === "interactive", [], 30_000);
    if (!ready) fail("navigation timeout");
    await delay(1_500);
    const location = await evaluate(() => ({ origin: location.origin, pathname: location.pathname, search: location.search, hash: location.hash }));
    if (!location || location.origin !== ORIGIN || (route !== "/" && location.pathname !== route) || location.search || location.hash) fail("navigation readback invalid");
    return location.pathname;
  };
  const exactCount = async (selector) => evaluate((value) => document.querySelectorAll(value).length, selector);
  const trustedClick = async (fn, ...args) => {
    const point = await evaluate(fn, ...args);
    if (!point || !Number.isFinite(point.x) || !Number.isFinite(point.y)) fail("trusted click target invalid");
    await command("Input.dispatchMouseEvent", { type: "mousePressed", x: point.x, y: point.y, button: "left", clickCount: 1 });
    await command("Input.dispatchMouseEvent", { type: "mouseReleased", x: point.x, y: point.y, button: "left", clickCount: 1 });
    await delay(250);
  };

  return Object.freeze({
    target_id: target.id,
    diagnostics: () => diagnostics.slice(-30),
    evaluate,
    waitFor,
    navigate,
    async setText(name, value) {
      const count = await exactCount(`[name=${name}]`);
      if (count !== 1) fail(`field ${name} cardinality`);
      const changed = await evaluate((fieldName, next) => {
        const element = document.querySelector(`[name=${fieldName}]`);
        const previous = element.value;
        const prototype = element instanceof HTMLTextAreaElement ? HTMLTextAreaElement.prototype : HTMLInputElement.prototype;
        Object.getOwnPropertyDescriptor(prototype, "value").set.call(element, next);
        if (element._valueTracker) element._valueTracker.setValue(previous);
        element.dispatchEvent(new Event("input", { bubbles: true }));
        element.dispatchEvent(new Event("change", { bubbles: true }));
        element.blur();
        return element.value === next;
      }, name, value);
      if (!changed) fail(`field ${name} React setter`);
    },
    async setChoice(question, option) {
      const id = question === "Are people using your product?" ? "stage" : question === "Do you have revenue?" ? "revenue" : null;
      if (!id || !["Yes", "No"].includes(option)) fail("choice invalid");
      const clicked = await evaluate((containerId, expectedQuestion, expectedOption) => {
        const container = document.getElementById(containerId);
        if (!container || container.querySelector("label")?.innerText.trim() !== expectedQuestion) return false;
        const labels = [...container.querySelectorAll("label")].filter((label) => label.innerText.trim() === expectedOption);
        if (labels.length !== 1) return false;
        labels[0].parentElement.click();
        return true;
      }, id, question, option);
      if (!clicked) fail("choice drift");
    },
    async setFile(file) {
      const selector = 'input[type=file][accept="video/*"]';
      if (await exactCount(selector) !== 1) fail("demo file cardinality");
      const object = await command("Runtime.evaluate", { expression: `document.querySelector(${JSON.stringify(selector)})`, returnByValue: false });
      const objectId = object.result && object.result.objectId;
      if (!objectId) fail("demo file node missing");
      const description = await command("DOM.describeNode", { objectId });
      const backendNodeId = description.node && description.node.backendNodeId;
      if (!backendNodeId) fail("demo file backend node missing");
      await command("DOM.setFileInputFiles", { files: [file], backendNodeId });
      const uploaded = await waitFor(() => {
        const form = document.querySelector(".video-form");
        const progress = document.querySelector("[role=progressbar]");
        return form?.getAttribute("data-video-saved") === "true" || progress?.getAttribute("aria-valuenow") === "100";
      }, [], 120_000);
      if (!uploaded) fail("demo upload timeout");
    },
    async activate(text) {
      if (!["Save & back", "Submit update", "Save founder profile"].includes(text)) fail("activation invalid");
      const activation = await evaluate(async (expected) => {
        const buttons = [...document.querySelectorAll("button")].filter((button) => button.innerText.trim() === expected);
        if (buttons.length !== 1) return { activated: false, errors: {} };
        const fiberKey = Object.keys(buttons[0]).find((key) => key.startsWith("__reactFiber$"));
        let fiber = fiberKey ? buttons[0][fiberKey] : null;
        while (fiber && typeof fiber.memoizedProps?.value?.submitForm !== "function") fiber = fiber.return;
        if (!fiber) return { activated: false, errors: {} };
        await fiber.memoizedProps.value.submitForm();
        await new Promise((resolve) => setTimeout(resolve, 100));
        let current = buttons[0][fiberKey];
        while (current && typeof current.memoizedProps?.value?.submitForm !== "function") current = current.return;
        const errors = current?.memoizedProps?.value?.errors || {};
        return { activated: true, errors: Object.fromEntries(Object.entries(errors).map(([key, value]) => [key, typeof value === "string" ? value.slice(0, 240) : typeof value])) };
      }, text);
      if (!activation.activated) fail("Formik submit handler missing");
      if (Object.keys(activation.errors).length) diagnostics.push({ kind: "formik_errors", errors: activation.errors });
      await delay(2_000);
      const validation = await evaluate(() => [...new Set([
        ...[...document.querySelectorAll('[role="alert"], .error, [class*="text-red"]')].map((element) => element.innerText.trim()),
        ...document.body.innerText.split("\n").map((line) => line.trim()).filter((line) => /required|invalid|please|error/i.test(line)),
      ].filter((line) => line && line.length <= 240))].slice(0, 12));
      if (validation.length) diagnostics.push({ kind: "ui_validation", messages: validation });
      await delay(13_000);
    },
    async readText(name) {
      const result = await evaluate((fieldName) => {
        const fields = [...document.querySelectorAll(`[name=${fieldName}]`)];
        return fields.length === 1 ? fields[0].value : null;
      }, name);
      if (result === null) fail(`readback ${name} cardinality`);
      return result;
    },
    async readChoice(question) {
      const id = question === "Are people using your product?" ? "stage" : question === "Do you have revenue?" ? "revenue" : null;
      if (!id) fail("readback choice invalid");
      return evaluate((containerId) => {
        const container = document.getElementById(containerId);
        if (!container) return null;
        const candidates = [...container.querySelectorAll("label")].filter((label) => ["Yes", "No"].includes(label.innerText.trim()));
        const selected = candidates.filter((label) => {
          const marker = label.parentElement?.querySelector("div");
          if (!marker) return false;
          const signature = `${marker.className} ${marker.innerHTML}`;
          return /bg-|border-[2-9]|border-\[[2-9]px\]|<div|<span|checked/i.test(signature);
        });
        return selected.length === 1 ? selected[0].innerText.trim() : null;
      }, id);
    },
    async readDemo() {
      await waitFor(() => {
        const video = document.querySelector("video");
        return video && video.readyState === 4 && Number.isFinite(video.duration) && video.videoWidth > 0 && video.videoHeight > 0;
      }, [], 45_000);
      return evaluate(() => {
        const videos = [...document.querySelectorAll("video")];
        if (videos.length !== 1) return { ready: false };
        const video = videos[0];
        let storageOrigin = null;
        try { storageOrigin = new URL(video.currentSrc).origin; } catch {}
        return { ready: video.readyState === 4 && Number.isFinite(video.duration) && video.videoWidth > 0 && video.videoHeight > 0 && storageOrigin === "https://yc-app-vids.s3.us-west-2.amazonaws.com", duration_seconds: video.duration, width: video.videoWidth, height: video.videoHeight, storage_origin: storageOrigin };
      });
    },
    async close() {
      if (closed) return;
      try { await command("Page.close"); } catch {}
      try { socket.close(); } catch {}
      closed = true;
    },
  });
}

module.exports = { createOwnedYcRawCdpPage };
