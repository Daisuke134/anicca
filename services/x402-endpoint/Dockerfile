# anicca-x402-endpoint production container.
FROM node:20-alpine
WORKDIR /app

ENV NODE_ENV=production
ENV PORT=8403

RUN addgroup -S anicca && adduser -S anicca -G anicca

COPY package.json package-lock.json ./
RUN npm ci --omit=dev

COPY prisma ./prisma
COPY src ./src
RUN npx prisma generate
RUN chown -R anicca:anicca /app

USER anicca
EXPOSE 8403

HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=3 \
  CMD wget -q --spider --tries=1 http://localhost:8403/health || exit 1

CMD ["node", "src/server.js"]
