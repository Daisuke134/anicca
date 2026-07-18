# Purity Boundary Audit — capafy-skills-landing

## Declared Boundaries

- Pure: online filtering, deterministic sorting, HTML escaping, card rendering, page rendering.
- Impure: Capafy subprocess, filesystem overwrite, Netlify production deploy, existing IG agent bio action.

## Observed Boundaries

- `filter_online_agents`, `_render_card`, and `render_html` operate only on passed values and return deterministic data.
- `_fetch_agents` contains the only network-facing subprocess and uses a fixed executable/path/method/endpoint argv without shell expansion.
- `build` contains the only generator filesystem write and overwrites one known `index.html` path.
- Daily shell owns deploy side effects and pins `--site 41c8e52e-b163-442a-84ff-fd866269bf6c`.
- STEP5 keeps the existing commercial/live gate; only the target URL changes.

## Summary

PASS. Pure transformations remain testable without network or disk. External effects are explicit, narrow, logged, and exercised against real services. No hidden write, dynamic shell evaluation, or broadened Instagram posting behavior was introduced.
