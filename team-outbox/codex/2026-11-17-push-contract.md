# Push sender contract — integration handoff

POST /manager/push-decisions accepts {decisions: [{subject, delivery_id, context, push_state}]} (1–100).
subject is the stable profile/account ID, permitted ONLY to the authenticated sender service.
context retains the four enumerated app context fields. push_state is {profile: object,
recent_reactions: array (max 50), local_day: ISO date, slot: HH:MM}, max 16 KB.
Response {decisions: [InterventionStore decision]} preserves snake_case decision fields,
including delivery_id, chosen, send, assigned_probability, backend, policy_version.
The SQLite cases record is committed before responding. Same subject/UUID reuses the
record; changed context rejects. Per-user state reaches the model generator.

proxy-manager-mount integration must supply router(..., authenticate_sender=...) with
a service credential validator; the default denies this route. App-token authentication
must never authorize arbitrary subject selection. Use the same pseudonym key as the
app route for observation joins. No deployment or production effects performed here.

The existing generator/store is reused; no parallel decision engine. Astra Advisor
is not exposed in this harness. Source assignment override permits this checkout,
current branch and no push despite legacy Life Manager instructions in docs/team.
