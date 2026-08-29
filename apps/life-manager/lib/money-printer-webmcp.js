"use strict";

function renderMoneyPrinterWebMcpScript({ csrf } = {}) {
  // This task exposes a read-only GET; never serialize the page CSRF value into the browser tool.
  void csrf;
  return `
(() => {
  if (typeof document === "undefined"
    || !document.modelContext
    || typeof document.modelContext.registerTool !== "function") return;

  const request = async () => {
    const response = await fetch("/api/panel/money-printer", {
      method: "GET",
      credentials: "same-origin",
      headers: { Accept: "application/json" },
    });
    if (!response.ok) throw new Error("inspect_money_printer unavailable");
    return response.json();
  };

  document.modelContext.registerTool({
    name: "inspect_money_printer",
    description: "Inspect the current Money Printer state.",
    inputSchema: {
      type: "object",
      properties: {},
      additionalProperties: false,
    },
    annotations: { readOnlyHint: true },
    execute: () => request(),
  });
})();`;
}

module.exports = { renderMoneyPrinterWebMcpScript };
