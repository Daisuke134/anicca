---
name: resource-resolver
description: Resolve reusable Life Manager skills, accounts, authenticated browser sessions, and non-secret credential references before signup or reimplementation.
---

# Resource resolver

Call this first whenever work needs an external service, account, session, or capability.
Pass `service` and `capability`. Reuse a returned resource before creating an account or
building a new adapter. The output never contains password, token, or API-key values;
the selected adapter reads those from the local credential SSOT by reference.
