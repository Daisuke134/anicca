#!/usr/bin/env bash
# Fetch arXiv paper PDF and extract text
# Usage: fetch_paper.sh <arxiv_id> [output_dir]
# Example: fetch_paper.sh 2602.09904 /tmp
set -euo pipefail

ARXIV_ID="$1"
OUT_DIR="${2:-/tmp}"
PDF_PATH="${OUT_DIR}/${ARXIV_ID}.pdf"
TXT_PATH="${OUT_DIR}/${ARXIV_ID}.txt"

# Download PDF
curl -sL "https://arxiv.org/pdf/${ARXIV_ID}" -o "$PDF_PATH"

# Extract text (try pdftotext first, fallback to python)
if command -v pdftotext &>/dev/null; then
  pdftotext "$PDF_PATH" "$TXT_PATH"
elif command -v python3 &>/dev/null; then
  python3 -c "
import subprocess, sys
try:
    import fitz  # PyMuPDF
    doc = fitz.open('$PDF_PATH')
    text = '\n'.join(page.get_text() for page in doc)
    with open('$TXT_PATH', 'w') as f: f.write(text)
except ImportError:
    print('ERROR: pdftotext not found and PyMuPDF not installed. Install with: brew install poppler OR pip3 install PyMuPDF', file=sys.stderr)
    sys.exit(1)
"
else
  echo "ERROR: No PDF text extractor available" >&2
  exit 1
fi

echo "$TXT_PATH"
