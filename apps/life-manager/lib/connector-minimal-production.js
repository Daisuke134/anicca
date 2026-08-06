"use strict";

const crypto = require("node:crypto");
const path = require("node:path");

const {
  CONNECTOR_CDP_ENDPOINT,
  createConnectorBrowserTargetController,
} = require("./connector-browser-target-controller.js");
const { createConnectorTabOwner } = require("./connector-tab-owner.js");
const { createConnectorTargetLease } = require("./connector-target-lease.js");

const LUMA_DISCOVERY_URL = "https://luma.com/tokyo?k=p";

function invalid() {
  throw new Error("Connector minimal production unavailable");
}

function absoluteDirectory(value) {
  const directory = path.resolve(String(value || ""));
  if (!path.isAbsolute(directory) || directory === path.parse(directory).root) invalid();
  return directory;
}

function ownerToken(value) {
  const token = String(value || "").trim();
  if (!/^[A-Za-z0-9._-]{16,200}$/.test(token)) invalid();
  return token;
}

function createProductionBrowserRail(options = {}) {
  const stateDir = absoluteDirectory(options.stateDir);
  const connectOverCDP = options.connectOverCDP || ((endpoint) => {
    const { chromium } = require("playwright-core");
    return chromium.connectOverCDP(endpoint);
  });
  const createTargetController = options.createTargetController
    || ((input) => createConnectorBrowserTargetController(input));
  const createTargetOwnership = options.createTargetOwnership || ((input) => {
    const targetLease = createConnectorTargetLease({
      ledgerPath: path.join(stateDir, "evidence", "target-leases.json"),
      ownerToken: () => input.ownerToken,
      probeTarget: (pageWebsocket) => input.controller.probe(pageWebsocket),
      closeTarget: (targetId) => input.controller.close(targetId),
    });
    return createConnectorTabOwner({
      endpoint: CONNECTOR_CDP_ENDPOINT,
      targetLease,
    });
  });
  const makeSessionId = options.makeSessionId || (() => crypto.randomUUID());
  if (
    typeof connectOverCDP !== "function"
    || typeof createTargetController !== "function"
    || typeof createTargetOwnership !== "function"
    || typeof makeSessionId !== "function"
  ) invalid();

  return Object.freeze({
    async open(input = {}) {
      const exactOwnerToken = ownerToken(input.ownerToken);
      const browser = await connectOverCDP(CONNECTOR_CDP_ENDPOINT);
      const controller = createTargetController({ browser, endpoint: CONNECTOR_CDP_ENDPOINT });
      if (!controller || typeof controller.create !== "function" || typeof controller.close !== "function") invalid();
      const target = await controller.create();
      let ownership = null;
      let receipt = null;
      try {
        ownership = createTargetOwnership({
          controller,
          ownerToken: exactOwnerToken,
          stateDir,
        });
        if (
          !ownership || typeof ownership.claimExact !== "function"
          || typeof ownership.probe !== "function" || typeof ownership.heartbeat !== "function"
          || typeof ownership.release !== "function"
        ) invalid();
        receipt = await ownership.claimExact({
          canonicalUrl: LUMA_DISCOVERY_URL,
          targetId: target.target_id,
          pageWebsocket: target.page_websocket,
          receiptPath: path.join(stateDir, "evidence", "tab-owner.json"),
        });
        if (await ownership.probe(receipt) !== true) invalid();
        await ownership.heartbeat(receipt);
        const sessionId = String(makeSessionId());
        if (!/^[A-Za-z0-9._-]{3,128}$/.test(sessionId)) invalid();
        return Object.freeze({
          session_id: sessionId,
          target_id: target.target_id,
          page_websocket: target.page_websocket,
          page: target.page,
          ownership,
          receipt,
        });
      } catch (error) {
        if (receipt && ownership) {
          try { await ownership.release(receipt); } catch {}
        } else {
          try { await controller.close(target.target_id); } catch {}
        }
        throw error;
      }
    },

    async navigate(owned, url) {
      if (!owned || !owned.page || !owned.ownership || !owned.receipt) invalid();
      await owned.ownership.heartbeat(owned.receipt);
      await owned.page.goto(String(url), { waitUntil: "domcontentloaded", timeout: 30_000 });
      await owned.ownership.heartbeat(owned.receipt);
    },

    async close(owned) {
      if (!owned || !owned.ownership || !owned.receipt) invalid();
      return owned.ownership.release(owned.receipt);
    },
  });
}

module.exports = { createProductionBrowserRail };
