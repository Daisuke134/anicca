"use strict";
const BROWSER_REF = "browser-profile://cloakbrowser/daily-driver";
const ENDPOINT = "http://127.0.0.1:9222";
const ROUTE_KEYS = ["form_origin", "origin_binding", "provider_id", "route_id"];
function fail() { throw new Error("funder browser routes invalid"); }
function validateFunderBrowserRoutes(manifest) {
  if (!manifest || manifest.schema_version !== 1 || manifest.browser_ref !== BROWSER_REF
    || manifest.endpoint !== ENDPOINT || manifest.connection_mode !== "connect_over_cdp"
    || manifest.shared_context_count !== 1 || manifest.launch_command != null
    || !Array.isArray(manifest.routes) || manifest.routes.length < 1) fail();
  const ids = new Set();
  for (const route of manifest.routes) {
    if (!route || typeof route !== "object" || Array.isArray(route)
      || JSON.stringify(Object.keys(route).sort()) !== JSON.stringify(ROUTE_KEYS)
      || !/^[a-z0-9][a-z0-9._-]{1,99}$/.test(String(route.route_id || ""))
      || !/^[a-z0-9][a-z0-9._-]{1,99}$/.test(String(route.provider_id || ""))
      || ids.has(route.route_id)) fail();
    ids.add(route.route_id);
    if (route.origin_binding === "exact") {
      let parsed; try { parsed = new URL(route.form_origin); } catch { fail(); }
      if (parsed.origin !== route.form_origin || parsed.protocol !== "https:" || parsed.username || parsed.password) fail();
    } else if (route.origin_binding === "registry_official_form_url") {
      if (route.form_origin !== null) fail();
    } else fail();
  }
  return Object.freeze({ route_count: manifest.routes.length, browser_ref: BROWSER_REF, endpoint: ENDPOINT });
}
module.exports = { validateFunderBrowserRoutes };
