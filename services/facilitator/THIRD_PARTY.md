# Third-party source: x402-rs

Life Manager does not vendor or submodule the x402-rs source tree. The
facilitator fetcher uses exactly this public source:

| Field | Pinned value |
|---|---|
| Project | `x402-rs/x402-rs` |
| License | Apache License 2.0 |
| Commit | `d439a91bda1caee486b0f841c4c6dd265fbee9df` |
| Archive | `https://codeload.github.com/x402-rs/x402-rs/tar.gz/d439a91bda1caee486b0f841c4c6dd265fbee9df` |
| Archive SHA-256 | `7b24f6f67561c29174a03d2e5f35068e0e7c8d2c14451794cd0ac08877d57bac` |

`fetch-x402-rs.sh` verifies the archive before extraction, rejects unsafe
archive members, retains upstream `LICENSE`, records a deterministic source
tree digest, and builds with Cargo's locked dependency graph. Its cache is:

```text
${XDG_CACHE_HOME:-$HOME/.cache}/life-manager/x402-rs/<commit>/
├── source.tar.gz
├── archive.sha256
├── commit
├── tree.sha256
├── source/        # includes upstream LICENSE
└── target/        # local generated build output
```

Cache reuse verifies the retained archive and source tree again. A failed
verification removes only that one commit cache and re-fetches the pinned
archive; no neighboring checkout or private repository is consulted.
