#!/bin/bash
set -euo pipefail

REPO_ROOT="$(git -C "$(dirname "${BASH_SOURCE[0]}")" rev-parse --show-toplevel)"
KIT="$REPO_ROOT/fundraising/application-kit"
SOURCE="$KIT/deck.md"
OUTPUT="$KIT/deck.pdf"
RECEIPT="$KIT/deck.pdf.receipt.json"
TMP_DIR="$(mktemp -d "${TMPDIR:-/tmp}/life-manager-deck.XXXXXX")"
trap 'rm -rf "$TMP_DIR"' EXIT

pandoc "$SOURCE" --standalone --metadata title="Life Manager" -o "$TMP_DIR/deck.html"
weasyprint "$TMP_DIR/deck.html" "$TMP_DIR/deck.pdf"
mv "$TMP_DIR/deck.pdf" "$OUTPUT"

node - "$KIT/assets.json" "$OUTPUT" "$RECEIPT" <<'NODE'
const fs = require("node:fs");
const crypto = require("node:crypto");
const [assetsPath, pdfPath, receiptPath] = process.argv.slice(2);
const assets = JSON.parse(fs.readFileSync(assetsPath, "utf8"));
const pdf = fs.readFileSync(pdfPath);
const receipt = {
  context_version: assets.context_version,
  context_digest: assets.context_digest,
  artifact: "fundraising/application-kit/deck.pdf",
  sha256: crypto.createHash("sha256").update(pdf).digest("hex"),
  bytes: pdf.length,
};
fs.writeFileSync(receiptPath, `${JSON.stringify(receipt, null, 2)}\n`);
NODE

echo "generated $OUTPUT"
