FROM node:20-bookworm-slim

RUN apt-get update && apt-get install -y --no-install-recommends ca-certificates curl git gh \
  && rm -rf /var/lib/apt/lists/* \
  && npm install --global @openai/codex@0.151.0 \
  && curl -fsSL https://github.com/openai/symphony/releases/download/v0.0.2/symphony-v0.0.2-linux_x86_64 -o /usr/local/bin/symphony \
  && echo "bace377e92b7c244a29da15a88f517c7722ca69e249068395f77ce6912ef39eb  /usr/local/bin/symphony" | sha256sum -c - \
  && chmod 755 /usr/local/bin/symphony

COPY start.sh /usr/local/bin/money-printer-symphony
RUN chmod 755 /usr/local/bin/money-printer-symphony
ENTRYPOINT ["/usr/local/bin/money-printer-symphony"]
