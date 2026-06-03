# anicca-x402-endpoint — production container.
# Spec 09 § 2 T6. Targets Akash (spec 13) but also runs on plain Docker /
# fly.io / Railway. Multi-stage so the runtime image stays under 200 MB.
#
# Build:  docker build -t anicca-x402:0.1 .
# Run:    docker run --rm -p 8403:8403 anicca-x402:0.1
# Health: curl http://localhost:8403/health

# --- Stage 1: install deps + transpile -------------------------------------------------
FROM node:20-alpine AS builder
WORKDIR /app

# pnpm via corepack — matches the local toolchain (pnpm-lock.yaml committed).
RUN corepack enable && corepack prepare pnpm@10.30.3 --activate

COPY package.json pnpm-lock.yaml ./
RUN pnpm install --frozen-lockfile --prod=false

COPY server.ts challenge.ts verify.ts pricing.json ./
# tsx executes TS at runtime; no separate compile step needed. We just need
# the same files in the runtime image.

# --- Stage 2: runtime image -------------------------------------------------------------
FROM node:20-alpine AS runtime
WORKDIR /app
ENV NODE_ENV=production
ENV PORT=8403

# Run as non-root.
RUN addgroup -S anicca && adduser -S anicca -G anicca
USER anicca

# Bring in production-only node_modules + the source files.
COPY --from=builder --chown=anicca:anicca /app/node_modules ./node_modules
COPY --from=builder --chown=anicca:anicca /app/server.ts ./server.ts
COPY --from=builder --chown=anicca:anicca /app/challenge.ts ./challenge.ts
COPY --from=builder --chown=anicca:anicca /app/verify.ts ./verify.ts
COPY --from=builder --chown=anicca:anicca /app/pricing.json ./pricing.json

EXPOSE 8403

HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=3 \
  CMD wget -q --spider --tries=1 http://localhost:8403/health || exit 1

# Use tsx via the local node_modules bin so we don't ship a global install.
ENTRYPOINT ["node_modules/.bin/tsx", "server.ts"]
